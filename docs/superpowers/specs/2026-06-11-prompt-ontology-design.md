# Prompt 梳理①期:Ontology 重建 + 公式管道 — 设计文档

日期:2026-06-11
状态:已与用户逐节确认定稿
范围:抽取质量(①期)。enrichment(悬空链接解析:wiki 搜索/联网/LLM/人工编辑)为②期,**本期不做**,另行 brainstorm。

## 1. 背景与问题

Munger ingest pipeline 生成的 entity / wiki 页面存在三类质量问题:

1. **Entity 无 ontology 意义**。如 "Theorem 2" 被抽为 Concept 并独立成页 — 文档内部标号离开原文不可辨认。
2. **公式与图损坏**。wiki 页面充斥死图引用(`![O(\log N)](路径)`)与裸 LaTeX,前端渲染为碎图标。
3. **生成的 section(Key Components / Related Mental Models)中 `[[链接]]` 大量悬空**,指向不存在页面,渲染为 `?unresolved`。

### 根因(代码定位)

| 问题 | 根因 | 位置 |
|---|---|---|
| 无 ontology | `EXTRACT_SYSTEM` 仅 6 行;type 列表字面含 `"person\|concept\|model\|..."` 省略号,LLM 自行猜测词表;无类型定义、无 canonical 命名规则、无反例 | `munger/backend/app/services/extraction_service.py:22` |
| 词表三处漂移 | chunk 路径、全局抽取、normalize 各自维护词表,互不一致 | `extraction_service.py:22` / `llm_service.py:733` / `entity_service.py:310` |
| page_type 失配 | `entity_type` 直接当 `page_type` 传入,`person`/`book`/`paper`/`organization` 在 `type_prompts` 无对应键,全部落 default 模板 | `app/runtime/graphs/nodes/nodes_cognify.py:280` → `llm_service.py:803` |
| 公式损坏 | LiteParse OCR 输出 markdown,公式成 `![LaTeX](死路径)`;管线全程零处理,LLM 原样抄进 wiki;前端无 math 渲染 | `storage_service.py:203`(parse)→ 全下游 |
| 悬空链接 | wiki type prompt 仅一句话(如 "with definition, examples, and related mental models"),LLM 自由发明 section 与 `[[链接]]`,无质量约束;不存在页面渲染为 `?unresolved` | `llm_service.py:803` / `wiki_service.py:330` |

附带发现(本期**不修**,见 §8):entity wiki 页生成输入仅单条 mention excerpt(≤500 字)或 description,不聚合全部 mentions(`nodes_cognify.py:279`)。

## 2. 决策记录(与用户逐项确认)

| # | 议题 | 决策 |
|---|---|---|
| 1 | 范围 | 拆两期。①期 = ontology prompt 重写 + 公式管道;②期 = enrichment |
| 2 | document-local 标号(Theorem N 等) | **直接丢弃**:prompt 加反例硬禁,不抽、不收编、不新增 theorem 类型 |
| 3 | type 词表 | 精简 11 类 → **7 类**,每类定义 + 正反例 |
| 4 | 公式 | **LaTeX 管道打通**:parse 后清洗 → `$...$` → 前端 KaTeX 渲染 |
| 5 | LLM 发明的 `[[链接]]` | **保留(红链哲学)**:死链 = ②期 enrichment 原料;prompt 约束链接质量(canonical 概念名,禁短语碎片);渲染维持 `?unresolved` |
| 6 | wiki 页输入贫血 | **不修**,纯 prompt 层改造 |
| 7 | prompt 组织 | **集中 prompts 模块**(`app/prompts/`),ontology 单一事实源 |
| 8 | 决策落地文档 | 同步更新 `ARCHITECTURE.md` 与 `STATUS.md` |

## 3. Ontology 设计

### 3.1 词表(7 类)

| 类型 | 定义 | 正例 | 吸收旧类 |
|---|---|---|---|
| `person` | 真实具名人物 | Charlie Munger | person |
| `organization` | 公司/机构/项目 | BitTorrent, MIT | organization |
| `work` | 书/论文/文章等具名作品 | Poor Charlie's Almanack | book, paper |
| `concept` | 领域概念,可独立成页 | Consistent Hashing | concept, field |
| `mental_model` | 跨域思维模型 | Network Effects, Redundancy | model, principle |
| `mechanism` | 有因果链的运作机制 | Proof of Stake, Tit-for-tat | mechanism, incentive_structure |
| `event` | 具名历史事件 | Mt. Gox Collapse | event |

### 3.2 抽取规则(进 EXTRACT / GLEAN prompt)

1. **自解释名**:entity 名离开文档必须可独立辨认。硬禁反例清单:`Theorem N`、`Figure N`、`Table N`、`Section N`、`Equation N`、`Chapter N`、"the author"、"this paper" 等 document-local 指称 — 一律不抽。
2. **Canonical 形式**:正式全称、单数、无冠词。带缩写时 name 取全称(如 "Content Identifier" 而非 "CID")。
3. **词表闭合**:7 类逐一给定义 + 1 正例 + 1 反例;禁止 `...` 省略号;类型冲突优先级:`mental_model > mechanism > concept`。
4. **Salience 门槛**:撑得起独立 wiki 页才抽(对齐现有 3–15 entities/chunk 质量带)。

### 3.3 旧数据迁移

一次性 Alembic data migration:`UPDATE` entity 旧 type 按 §3.1 映射表转新值(纯 SQL)。降级为 best-effort:合并类不可精确还原(`work` 统一还原为 `book`,`mental_model` 还原为 `model`,`mechanism` 还原为 `mechanism`),迁移文件中注明。`EntityService._normalize_entity_type` alias map 同步替换(新词表 + 全部旧值映射)。

## 4. Prompt 集中模块

### 4.1 新模块结构

```
munger/backend/app/prompts/
├── __init__.py        # 公开出口
├── ontology.py        # ENTITY_TYPES(7 类定义+正反例)、NAMING_RULES、
│                      # NEGATIVE_PATTERNS(Theorem N 等)— 词表单一事实源
├── extraction.py      # EXTRACT_SYSTEM、GLEAN 系列 — 由 ontology 常量拼装
├── wiki.py            # 7+1 个 page type prompt、WIKILINK_RULES、公式保留指令
└── resolution.py      # PROF_MERGE_SYSTEM、SAME_ENTITY_PROMPT
```

纯 Python 常量,无运行时加载机制、无模板引擎。services 只 import,不再自带 prompt 文本。

### 4.2 改造点清单

| 现址 | 动作 |
|---|---|
| `extraction_service.py:22` `EXTRACT_SYSTEM` | 替换 ← `prompts.extraction`(完整词表 + 规则 + 反例) |
| `extraction_service.py:28` `GLEAN_SYSTEM`、`map_chunk_service.py:40/45` `GLEAN_YES_NO_SYSTEM` / `GLEAN_CONTINUE_SYSTEM` | 统一为 `prompts.extraction` 一份 glean prompt 体系 |
| `llm_service.py:733` `extract_entities` 内嵌词表 | 对齐同一 ontology 常量 |
| `llm_service.py:803` `generate_wiki_page` `type_prompts` | 替换 ← `prompts.wiki`;page_type 映射全覆盖 7 类 + summary,杀掉 default 漏接 |
| wiki 各 type prompt 内容 | 升级:固定 section 结构指引;`[[链接]]` 质量规则(必须 canonical 概念名、可独立成页,禁短语碎片);`$...$` 公式原样保留;**禁编造**(只用所给材料,材料不足写短页不注水) |
| `entity_service.py:310` `_normalize_entity_type` | 新词表 + 旧值映射 |
| `llm_service.py:838` `suggest_links`、`linking_service.py:246` `_llm_same_entity`、`resolution_service.py:23` `PROF_MERGE_SYSTEM` | 文本迁入模块,措辞微调,逻辑不动 |

### 4.3 不动项

- `runtime/agents/ingest_prompt.py` lead agent prompt(纯编排,与内容质量无关)
- `chunk_service.py:19` `CONTEXTUAL_PREFIX_PROMPT`(本期不动)

## 5. 公式/图管道

### 5.1 Backend 清洗器

新文件 `app/services/text_normalizer.py`,纯函数(正则,无 LLM)。在 `StorageService.extract_text` 返回前调用,所有格式统一过一遍(PDF 主要受益)。规则:

1. `![alt](path)` 且 alt 含 LaTeX 特征(`\` 命令、`^`/`_`、数学符号)→ 替换为 `$alt$`;多行公式 → `$$alt$$`。
2. `![alt](path)` 普通图(路径本就不可达)→ 替换为 `*[Figure: alt]*` 文字占位;alt 为空则删除该引用。
3. 其余文本原样通过。

下游(chunk → extraction → embedding → wiki)全链路收益:`content_text` 入库即干净。

### 5.2 Frontend math 渲染

- 新增依赖:`remark-math`、`rehype-katex`、`katex`(CSS)。
- 接入现有 markdown 渲染链(与 `app/src/lib/remark-wikilink.ts` 同链):插件数组 + import,改动极小。
- KaTeX 配置 `throwOnError: false`:渲染失败回显原始 LaTeX 串,不崩页面。

### 5.3 旧数据策略

已 ingest 的 source 不自动重洗(`content_text` 已存脏文本)。处理方式:对目标 source 执行 re-ingest(现有机制)重走新管线。不做批量回填脚本(②期或按需另议)。

## 6. 错误处理

- normalizer 任何异常 → 返回原文本,降级不阻断 ingest(记 warning 日志)。
- 公式识别为启发式,误判容忍:漏判 = 维持现状(裸文本),误判 = 多包一层 `$...$`,KaTeX `throwOnError: false` 兜底。
- prompt 替换不改变 JSON 输出契约(`ExtractionResult` 等 schema 不动),`chat_structured` 重试机制照旧。

## 7. 测试与验收

### 单元测试(`tests/unit/`)

- `test_text_normalizer.py`:LaTeX alt 死图 → `$...$`;普通图 → 占位;无公式文本原样;异常降级返回原文。
- `test_prompts.py`:EXTRACT/GLEAN/wiki prompt 含全部 7 类;含反例清单;不含 `...` 省略号;wiki page_type 映射 7+1 全覆盖、无 default 漏接。
- `test_entity_service.py` 扩展:`_normalize_entity_type` 新词表 + 全部旧值映射(book→work、principle→mental_model 等)。

### 迁移测试

Alembic data migration 升/降级在 `munger_test` DB 跑通(现有 conftest 模式)。

### 集成验收(手动 checklist)

同一篇 PDF re-ingest 后核对:

1. 无 `Theorem N` / `Figure N` 类页面;
2. entity type 全部落在 7 类内;
3. 公式以 KaTeX 渲染,无碎图;
4. 悬空 `[[链接]]` 维持 `?unresolved` 样式,且链接名为 canonical 概念名(非短语碎片)。

### 前端

`npm run lint` + `npm run build` 通过;KaTeX 渲染人工目检。

## 8. 明确排除项(②期或后续)

- enrichment:悬空链接解析(wiki 搜索 / 联网 / LLM / 人工编辑)
- wiki 页输入聚合(全部 mentions / 跨 source)
- 存量 wiki 页批量回填清洗
- `CONTEXTUAL_PREFIX_PROMPT` 改造

## 9. 文档同步

- `ARCHITECTURE.md`:新增 ontology 节(7 类词表 + 抽取规则)、prompts 模块、text_normalizer 位置。
- `STATUS.md`:记录本期决策与完成状态。
