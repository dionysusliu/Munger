# Munger Ingestion Pipeline — 论文/报告/代码 阅读清单

按 pipeline 阶段组织，每项标注与 Munger 的具体关联。

---

## A. 整体 Pipeline 架构

---

### 2. LightRAG 论文 ⭐⭐

**LightRAG: Simple and Fast Retrieval-Augmented Generation**
Guo et al., 2024
arXiv: [https://arxiv.org/abs/2410.05779](https://arxiv.org/abs/2410.05779)

**与 Munger 的关联：** LightRAG 是 GraphRAG 的轻量替代，关键改进是**增量更新**——新 entity/relationship 可以直接加入已有图，不需要全量重建。GraphRAG 的全量重建（Leiden 社区每次要重跑）是它最大的工程痛点。Munger 的 `generate_wiki_pages` 也应该走增量路径。

代码: [https://github.com/HKUDS/LightRAG](https://github.com/HKUDS/LightRAG)

---

### 3. Karpathy LLM Wiki ⭐⭐⭐

**llm-wiki.md** (GitHub Gist)
Andrej Karpathy, April 2026
Gist: [https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

**与 Munger 的关联：** Munger 就是这个 pattern 的 web-based 自动化实现。核心思想：

- "知识在 ingest 时合成，而不是 query 时"
- 三层架构：raw sources (不可变) → wiki (LLM 生成维护) → schema (规则)
- 三个操作：Ingest（一个 source 触碰 10-15 个 wiki 页面）、Query、Lint
- 在 ~100 sources / ~400K words 规模下工作良好，超过这个规模需要 BM25/vector search

**社区实现参考：**

- `nashsu/llm_wiki` — TypeScript 实现 (React 19 + Tauri + Sigma.js + graphology)
- `llmrix/llm-wiki-skill` — SKILL.md 格式的 wiki 工作流定义
- LLM Wiki v2 (rohitg00): [https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2) — 生产环境经验总结

---

## B. Chunking 策略

### 5. Anthropic Contextual Retrieval ⭐⭐⭐⭐

**Introducing Contextual Retrieval**
Anthropic, September 2024
博客: [https://www.anthropic.com/news/contextual-retrieval](https://www.anthropic.com/news/contextual-retrieval)
Cookbook: [https://platform.claude.com/cookbook/capabilities-contextual-embeddings-guide](https://platform.claude.com/cookbook/capabilities-contextual-embeddings-guide)

**与 Munger 的关联：** chunk 之后可以给每个 chunk 前置一段 LLM 生成的 50-100 token 上下文摘要再做 embedding，实测 top-20 retrieval failure rate 降低 67%（5.7% → 1.9%）。这个技术可以直接应用到 Munger 的 `chunk_document` 工具中，在 embedding 之前为每个 chunk 加上文档级上下文。用 prompt caching 控制成本（~$1.02/M tokens）。

---

---

---

## C. Entity Extraction & Gleaning

### 8. GraphRAG 的 Entity Extraction 实现细节

**Neo4j 集成指南（含 gleaning 实测）** ⭐⭐
[https://neo4j.com/blog/developer/microsoft-graphrag-neo4j/](https://neo4j.com/blog/developer/microsoft-graphrag-neo4j/)

**与 Munger 的关联：** 这篇博文是 GraphRAG entity extraction 最好的实践指南。它详细解释了：

- 默认 entity types (organization, person, event, geo) 需要根据领域调整
- 300 token chunk + 0 gleanings → 平均 ~3 entities/chunk
- gleaning 的实际效果（图表清晰展示多轮提取的增量）
- gpt-4o-mini 做 gleaning 可以大幅降低成本

**GraphRAG 论文中的关键 prompt：**

- `GRAPH_EXTRACTION_PROMPT`: 初始提取
- `CONTINUE_PROMPT`: "MANY entities and relationships were missed..."
- `LOOP_PROMPT`: "Are there still entities that need to be added? YES | NO"

参考实现: [https://learnopencv.com/lightrag/](https://learnopencv.com/lightrag/) （含完整 prompt 展示）

---

### 9. instructor 库 ⭐⭐

**instructor: Structured outputs for LLMs**
GitHub: [https://github.com/567-labs/instructor](https://github.com/567-labs/instructor)
文档: [https://python.useinstructor.com/](https://python.useinstructor.com/)

**与 Munger 的关联：** Munger 的 `extract_entities_from_chunks` 和 `glean_entities` 工具应该用 instructor 做 structured output extraction。核心优势：

- Pydantic BaseModel 直接定义输出 schema
- 自动 retry + validation（LLM 输出不符合 schema 时自动重试）
- 支持 OpenAI、Anthropic、Gemini、Ollama 等 15+ provider
- async 支持（并行提取多个 chunk）

关键用法：`client.chat.completions.create(response_model=ExtractionResult, ...)`

---

### 10. E²GraphRAG

**E²GraphRAG: Streamlining Graph-based RAG for High Efficiency and Effectiveness**
arXiv: [https://arxiv.org/abs/2505.24226](https://arxiv.org/abs/2505.24226)

**与 Munger 的关联：** 提出了在 entity extraction 阶段就做效率优化的方法——通过 token-efficient 的方式减少 LLM 调用开销，同时保持提取质量。如果 Munger 在大批量 ingest 时遇到成本问题，这篇论文的优化策略可以参考。

---

---

---

### 14. LLM-based Entity Resolution 综述

**Optimizing the Interface Between Knowledge Graphs and LLMs for Complex Reasoning**
arXiv: [https://arxiv.org/abs/2505.24478](https://arxiv.org/abs/2505.24478)

**与 Munger 的关联：** 这篇论文详细描述了 Cognee 的完整 pipeline 实现，包括如何用 Pydantic model 定义 entity schema、如何做 content-hash dedup、如何做增量更新。直接可以对照 Munger 的 DB schema 设计。

---

## E. Wiki Generation & Knowledge Synthesis

---

### 16. LLM Wiki v2 — 生产环境经验

**LLM Wiki v2: Extended with lessons from agentmemory**
[https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2)

**与 Munger 的关联：** 总结了 LLM Wiki pattern 在生产环境中的实际问题和解决方案：

- 知识腐化（旧 claim 不更新）→ 需要 Lint 操作
- Entity resolution 是最难的部分
- Contradiction detection 需要专门的 pass
- Provenance tracking 必须从 Day 1 开始

---

## F. Graph Construction & Community Detection

### 17. Leiden 算法

**From Louvain to Leiden: guaranteeing well-connected communities**
Traag, Waltman, van Eck, 2019
[https://www.nature.com/articles/s41598-019-41695-z](https://www.nature.com/articles/s41598-019-41695-z)

Python 实现: `graspologic` 库 (Microsoft)
[https://github.com/microsoft/graspologic](https://github.com/microsoft/graspologic)

**与 Munger 的关联：** GraphRAG 用 Leiden 做层次化社区检测，为每个社区生成摘要。Munger 的 Phase 3 如果需要自动生成 "概览页"（比如把所有 mental model 相关的 entity 聚成一个 topic），Leiden 是目前最好的选择。

---

## G. 工具库 & 框架


| 库                | 用途                                          | Munger 中的位置                                      | 链接                                                                                                 |
| ---------------- | ------------------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| **instructor**   | LLM structured output + Pydantic validation | `extract_entities_from_chunks`, `glean_entities` | [https://github.com/567-labs/instructor](https://github.com/567-labs/instructor)                   |
| **tiktoken**     | Token counting + chunking                   | `chunk_document`                                 | [https://github.com/openai/tiktoken](https://github.com/openai/tiktoken)                           |
| **LangChain**    | `@tool` decorator, LLM abstractions         | 所有 tool 定义                                       | [https://github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)             |
| **LangGraph**    | Agent 编排, state management                  | Worker agent runtime                             | [https://github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)             |
| **pgvector**     | Postgres vector extension                   | Entity embedding + similarity search             | [https://github.com/pgvector/pgvector](https://github.com/pgvector/pgvector)                       |
| **graspologic**  | Leiden community detection                  | Phase 3 topic clustering                         | [https://github.com/microsoft/graspologic](https://github.com/microsoft/graspologic)               |
| **Unstructured** | 文档解析 (PDF, DOCX, etc.)                      | `parse_document`                                 | [https://github.com/Unstructured-IO/unstructured](https://github.com/Unstructured-IO/unstructured) |
| **graphology**   | TypeScript in-memory graph library          | 前端知识图谱                                           | [https://github.com/graphology/graphology](https://github.com/graphology/graphology)               |


---

## H. 推荐阅读顺序

1. **GraphRAG 论文** (A.1) — 理论基础，重点读 Section 2.2 + Appendix A.1
2. **Karpathy LLM Wiki** (A.3) — 产品哲学，理解 "synthesis at ingest time"
3. **Neo4j GraphRAG 集成指南** (C.8) — gleaning 的实操细节
4. **instructor 文档** (C.9) — 熟悉 structured output API
5. **Anthropic Contextual Retrieval** (B.5) — chunking 优化方向
6. **Cognee 架构** (A.4) — 完整 pipeline 参考实现
7. **LightRAG 论文** (A.2) — 增量更新方案
8. **RAPTOR 论文** (B.6) — 层次化摘要（长文档处理的 fallback 方案）

