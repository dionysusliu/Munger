# Munger — As-Built Architecture Diagrams

> **现状文档**(as-built, main @ 2026-06-12, PR #31)。北极星/目标态见
> `docs/superpowers/specs/2026-06-09-munger-data-architecture-design.md`;两者的差异
> 只剩:SP5(Pathway/Ray,10M 规模触发)未建、向量默认仍在 pgvector(LanceDB 在
> `VECTOR_BACKEND` 开关后)。行号为写作时锚点,漂移时按函数名 grep。

---

## 1. 系统架构(容器 / 运行时 / 存储 / 观测)

```mermaid
flowchart TB
    subgraph HOST["docker compose (munger/docker-compose.yml)"]
        FE["munger-frontend\nReact 19 + Vite (HashRouter)\napp/src/"]
        BE["munger-backend\nFastAPI :18000\nbackend/app/main.py"]
        WK["munger-worker\njob daemon\nbackend/app/worker/__main__.py"]
        LGTM["munger-lgtm\nOTel Collector + Tempo/Loki/Prom/Grafana\nGrafana :13001"]
    end
    PG[("Postgres + pgvector\n(external pigsty host)\nsystem of record + graph + vectors(default)")]
    LANCE[("LanceDB (flag VECTOR_BACKEND=lancedb)\nchunk_vectors / entity_vectors\napp/services/lancedb_store.py")]

    FE -->|"REST /api/* (app/src/lib/api.ts)"| BE
    BE -->|SQLAlchemy async| PG
    WK -->|SQLAlchemy async| PG
    BE & WK -->|"VectorStore seam\napp/services/vector_store.py"| LANCE
    BE & WK -->|"OTLP 4318 (env-gated)\napp/observability/otel_setup.py:27"| LGTM
    BE -.->|"enqueue IngestJob(DB 表队列,无 broker)"| PG
    WK -.->|"claim SKIP LOCKED\napp/services/ingest_job_service.py:60"| PG
```

| 组件 | 关键代码 |
|---|---|
| FastAPI 装配(CORS→OTel→routers) | `backend/app/main.py`(module-scope `setup_otel`) |
| Worker 守护(claim 循环 + DBOS launch) | `backend/app/worker/runner.py`, `app/worker/__main__.py` |
| LLM 多 provider + 时长护栏 | `app/services/llm_service.py`(`LLMService.chat:639`,总预算 `_bounded`;structured 见 §2 护栏) |
| 配置(全部 env knobs) | `app/core/config.py`(`Settings`) |
| 观测装配(traces/metrics/logs,env 未设=零开销) | `app/observability/otel_setup.py:27 setup_otel` |

---

## 2. Ingestion Pipeline 全流程

```mermaid
flowchart TB
    UP["上传 POST /api/sources/upload\napp/api/sources.py:68\n(409 = 同 hash 重复)"] --> TRG["POST /api/sources/:id/ingest\napp/api/sources.py:354"]
    TRG --> JOBS[("ingest_jobs 表队列\napp/models/ingest_job.py")]
    JOBS --> CLAIM["worker claim (FOR UPDATE SKIP LOCKED)\napp/services/ingest_job_service.py:60"]
    CLAIM --> RUN["IngestRunner → LangGraph / DBOS\napp/runtime/ingest_runner.py\n(INGEST_ORCHESTRATOR=graph|dbos)"]

    subgraph INTAKE["intake 子图 app/runtime/graphs/intake.py"]
        R["register_source"] --> P["parse_document\n(StorageService 提取文本)"] --> H["hash_dedup\n(同 hash 跳过 cognify)"]
    end
    subgraph COGNIFY["cognify 子图 app/runtime/graphs/cognify.py"]
        C["n_chunk (nodes_cognify.py:48)\nChunkService.split_chunks\n600tok/100 overlap"]
        C --> F["fanout_chunks (:73)\nSend × 窗口\nINGEST_EXTRACTION_WINDOW_CHUNKS=K"]
        F --> M["n_process_chunk / map_window\nmap_chunk_service.py:200\nclaim→连续 run→抽取→按 char 覆盖 demux\n→ 嵌入 → VectorStore.upsert_chunks\n并发 INGEST_CHUNK_WORKER_CONCURRENCY=5"]
        M --> G["n_map_gate (:93)\n回收 stale + wave++\n≤ INGEST_MAP_MAX_WAVES=3 否则 MapIncompleteError"]
        G -->|有 pending| F
        G -->|全 done| RED["n_reduce (:155)\n实体合并(LLM 描述合并)\nmention_method='extract' 写 entity_mentions"]
        RED --> L["n_link (:174) LinkingService\n_embed_entities → VectorStore.upsert_entities\nco-mention diet: 仅 extract mentions\n且共现 chunk ≥ INGEST_COMENTION_MIN_CHUNKS=2"]
        L --> S["n_summarize (:194)\n源摘要 (1 LLM call)"]
        S --> W["n_wiki (:223)\n每实体一页, 门: mention_count ≥\nINGEST_WIKI_MIN_MENTIONS=2"]
        W --> FIN["n_finalize (:366)\nEdgeService.update_for_source\n(edge_service.py:50 证据→聚合边)"]
    end
    RUN --> INTAKE --> COGNIFY
    FIN --> DONE["source.status=completed\nwiki 可读 / 图谱可查"]

    EV[("ingest_events\n(pipeline_step_start/complete,\nUI DAG/Gantt 数据源)")]
    OT["OTel: ingest.step span + httpx 调用 span\npipeline_events.py:194 pipeline_step"]
    INTAKE & COGNIFY -.-> EV
    INTAKE & COGNIFY -.-> OT
```

**抽取调用护栏链**(2026-06-12 实测后加固,`llm_service.py`):
`chat_structured` → instructor(transport timeout = `LLM_STRUCTURED_TIMEOUT_S=60`/attempt,总顶 2×)→ 确定性 4xx 立即中止(`_non_retryable_status`,403 不再烧 6 连重试)→ fallback chat 受 `LLM_CALL_TIMEOUT_S=120` 总时长顶(httpx 超时只管字节间隔,滴流响应靠它兜)。抽取 prompt 带输出预算(`extraction_service.py:22 EXTRACT_SYSTEM`:描述 ≤20 词、≤25 实体/chunk)。

---

## 3. 数据模型(现状 ER)

```mermaid
erDiagram
    SOURCES ||--o{ CHUNKS : has
    SOURCES ||--o{ INGEST_JOBS : queued
    SOURCES ||--o{ INGEST_EVENTS : timeline
    CHUNKS ||--o{ CHUNK_EXTRACTIONS : "raw LLM JSON (evidence)"
    CHUNKS ||--o{ ENTITY_MENTIONS : at
    ENTITIES ||--o{ ENTITY_MENTIONS : mentioned
    ENTITIES ||--o{ ENTITY_RELATIONSHIPS : "evidence (method: extract|co_mention|human)"
    ENTITIES ||--o{ ENTITY_EDGES : "derived weighted adjacency"
    ENTITIES |o--o| ENTITIES : "canonical_entity_id (可逆软合并)"
    ENTITIES }o--o| COMMUNITIES : member
    ENTITIES |o--o| WIKI_PAGES : page
    WIKI_PAGES ||--o{ WIKI_LINKS : from
    ENTITIES ||--o{ LABELED_PAIRS : "human truth (must/cannot link)"
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : has

    ENTITIES {
        int id PK
        string name
        string entity_type
        float salience "PageRank, graph_service"
        int canonical_entity_id FK "resolution 软合并"
        int community_id FK "Louvain"
        vector embedding "pgvector 默认; lancedb 模式下 NULL"
        int mention_count
    }
    CHUNKS {
        int id PK
        int source_id FK
        int chunk_index
        text content
        int doc_char_start "窗口拼接/demux 依据"
        int doc_char_end
        vector embedding "768维, HNSW"
        string map_status "pending/running/done/failed"
    }
    CHAT_MESSAGES {
        int id PK
        string role
        json citations "实体 id, rating 消费时 canonical-COALESCE"
        int rating "+1/-1 → 检索 rerank 因子"
    }
    COMMUNITIES {
        int id PK
        string title "LLM"
        text summary "LLM"
        tsvector search_vector "GIN, ts_rank 搜索"
    }
```

| 层(北极星 least-viable-state) | 表 | 模型文件 |
|---|---|---|
| 原始证据(不可重算) | `chunk_extractions`, `entity_mentions`, `entity_relationships` | `app/models/chunk_extraction.py`, `entity.py`, `entity_relationship.py` |
| 身份 | `entities` | `app/models/entity.py` |
| 人类真值(神圣) | `labeled_pairs`, `chat_messages.rating` | `app/models/labeled_pair.py`, `chat_message.py` |
| 派生(可重建) | `entity_edges`, `communities`, `wiki_pages/links`, salience/community_id/embedding | `entity_edge.py`, `community.py`, `wiki.py` |
| 运维 | `ingest_jobs`, `ingest_events`, `configs` | `ingest_job.py`, `ingest_event.py`, `config.py` |
| 向量 | pgvector 列(默认)或 LanceDB `chunk_vectors`/`entity_vectors` | seam: `app/services/vector_store.py`;迁移: `scripts/migrate_vectors.py` |

Retention(默认关):`POST /api/gc/retention` → `graph_gc_service.purge_aged()` 按
`RETENTION_INGEST_EVENTS_DAYS` / `RETENTION_CHUNK_EXTRACTIONS_DAYS` 老化(后者是证据层,删=放弃重聚合,文档已警示)。

---

## 4. 读路径(search / 检索漏斗 / chat)

```mermaid
flowchart LR
    Q["查询 / chat 轮次"] --> EMB["query embedding\nLLMService.embed_text"]
    Q --> SEED["link_seeds\nretrieval_service.py:34\n(精确名 + trigram + 实体 ANN VectorStore.search_entities\n+ canonical COALESCE 折叠)"]
    SEED --> CH1["图通道: personalized PageRank\ngraph_service.py:56\n(种子偏置, entity_edges)"]
    EMB --> CH2["向量通道: _vector_entities\nretrieval_service.py:66\nVectorStore.search_chunks(池=200)\n→ mentions 聚 MIN(dist)/实体"]
    Q --> CH3["词法通道: _lexical_entities\nretrieval_service.py:90\nwiki FTS → 实体"]
    CH1 & CH2 & CH3 --> RRF["RRF 融合 k=60\nretrieval_service.py:144"]
    RRF --> RANK["rerank: × salience^w\n× 反馈因子 1+0.1·clamp(净评分,±3)\n_feedback_scores :156 (citations canonical-aware)"]
    RANK --> ASM["实体中心装配 search :186\n(实体卡 + top chunks + 邻居)\nGET /api/search/retrieve (app/api/retrieval.py)"]

    ASM --> CHAT["ChatService.ask :100 / ask_stream :121\n检索 → bridge: graph_service.shortest_path :72\n→ LLM 合成(引用) → persist\nPOST /api/chat, /api/chat/stream (SSE meta→delta→done)"]

    SRCH["普通搜索: SearchService\nsemantic :239 (hit-then-hydrate)\nhybrid :301 (RRF + FTS)\nGET /api/search/*"]
    EMB --> SRCH
```

---

## 5. 写回 / 自改进路径(ingest 之外)

```mermaid
flowchart TB
    subgraph FEEDBACK["人类反馈 api/feedback.py → feedback_service.py"]
        FM["merge(a,b,same?)\n→ labeled_pairs + resolve;\nreject 同时拆 canonical"]
        FR["relate(a,b,type)\n→ method='human' 关系 → 边重建"]
        FRT["rate(message,±1)\n→ chat_messages.rating\n→ 检索 rerank 因子(§4)"]
    end
    RES["EntityResolutionService.resolve\nentity_resolution_service.py:113\nblock(pg_trgm) → score(0.5名/0.3向量/0.2邻居)\n→ 连通分量 → canonical 指针(τ_auto=.85)\n+ _flatten_chains 防链\nPOST /api/entities/resolve"]
    EDGE["EdgeService rebuild_all :41 / update_for_source :50\n证据→聚合加权边"]
    GRAPH["GraphService.recompute :87\nPageRank salience + Louvain 社区\nPOST /api/graph/recompute?rebuild_edges=true"]
    REP["CommunityReportService.generate_reports\nLLM 标题/摘要 + tsvector 检索\nPOST /api/communities/reports"]
    GC["GraphGCService (graph_gc_service.py)\nprune_orphans / delete(拒 canonical 根)\npurge_aged(retention)\n/api/gc/*"]

    FM --> RES
    FR --> EDGE
    RES --> EDGE --> GRAPH --> REP
    GC -.->|删后| GRAPH
```

---

## 6. 观测流(SP6)

```mermaid
flowchart LR
    BE["backend (service.name=munger-backend)"] & WK["worker (munger-worker)"] -->|"OTLP http 4318\n(compose 默认开; 裸跑未设 env=no-op)"| L["munger-lgtm"]
    L --> T["Tempo :3200\nTraceQL: {resource.service.name=...}\ningest.step span: step_key/source_id/duration_ms/llm_calls"]
    L --> PR["Prometheus :9090\nmunger.ingest.step.duration 直方图\nmunger.llm.calls 计数"]
    L --> LO["Loki :3100 LogQL"]
    L --> GF["Grafana :13001"]
    A["agents / humans\ncurl 即查 (docs/OBSERVABILITY.md)"] --> T & PR & LO
```

埋点缝:`app/runtime/pipeline_events.py:194 pipeline_step`(一个 contextmanager 盖全部 11 步 + 两条执行路径);httpx 自动埋点让每次 LLM HTTP 调用免费成 span。`ingest_events` 与 LangSmith 不被替代(分别服务产品 UI 与 LLM 语义轨迹)。

---

## 运行红线(本仓铁律)

- **任何东西不允许长时运行**:调用级 `LLM_CALL_TIMEOUT_S=120` / structured 2×60s 总时长顶;运维 watchdog 语义 = 60s 无进展即杀;live bench 已退役(成本/延迟真相 = 本页 §6 的 OTel)。
- compose 只从主 checkout 跑(worktree 无 `.env`)。
- 迁移 migration-only;新行为 flag 默认关(additive)。
- 测试:venv 3.12 + `munger_test`(命令见 `docs/superpowers/STATUS.md`)。
