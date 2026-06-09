# Munger Ingestion Pipeline：库选型、Tools 与 SKILLS 设计

## 1. 库选型：LlamaIndex vs GraphRAG vs 自建

### 结论：都不直接依赖，自建 tools + 借鉴算法

| 维度 | Microsoft GraphRAG | LlamaIndex PropertyGraphIndex | 自建 (推荐) |
|------|-------------------|-------------------------------|------------|
| **集成方式** | 独立 CLI pipeline，输出 Parquet 文件；不是 embeddable library | Python library，但带来完整的 VectorStore/GraphStore/Retriever 抽象层 | `@tool` + Pydantic + `instructor` / structured output |
| **与 Munger 现有架构的兼容性** | ❌ 完全不兼容。GraphRAG 有自己的 indexing dataflow，不走你的 FastAPI/Worker/Postgres 路径 | ⚠️ 部分兼容。PropertyGraphIndex 可以用 Neo4j/SimplePropertyGraphStore，但它要接管你的 EntityService 和 WikiService 的职责 | ✅ 完全兼容。Tools 直接调用你已有的 services 层 |
| **Entity extraction 质量** | 最高。有 gleaning 多轮提取 + entity description summarization | 中等。SchemaLLMPathExtractor 单轮提取，无 gleaning | 可以完全复制 GraphRAG 的 gleaning 算法 |
| **Entity resolution** | 简单的 title+type 合并 | 无内置 | 可以做得更好：embedding + LLM cascade |
| **数据库** | 自己的 Parquet + optional Neo4j | 自己的 GraphStore 抽象 | 你的 Postgres (Entity, EntityMention, WikiPage) |
| **增量更新** | ❌ 不支持，每次全量重建 | ⚠️ 有 doc hash dedup，但图更新有限 | ✅ 完全控制增量逻辑 |
| **Python 依赖量** | 重。拉入 graphrag + datashaper + graspologic | 重。拉入 llama-index-core + 一堆 integrations | 轻。instructor + tiktoken |

### 为什么不用 LlamaIndex？

LlamaIndex 的 `PropertyGraphIndex` 表面上很诱人——`from_documents()` 一行代码就能建图。但它的问题在于：

**它要做你的 EntityService**。LlamaIndex 的 `EntityNode`、`Relation`、`PropertyGraphStore` 是一套完整的实体存储抽象。你已经有了 `Entity`、`EntityMention`、`WikiPage`、`WikiLink` 这套 SQLAlchemy ORM。引入 LlamaIndex 意味着要么放弃你的 ORM 让 LlamaIndex 接管存储，要么在两套数据模型之间同步——这是最容易出 bug 的地方。

**它的 extractor 不够好**。`SchemaLLMPathExtractor` 和 `SimpleLLMPathExtractor` 都是单轮提取，没有 gleaning。对于你"线性增长"的核心需求，单轮提取在大文档上的 recall 会显著下降。你需要自己实现 gleaning，到那时 LlamaIndex 的 extractor 就只剩一个 prompt wrapper 的价值了。

**你不需要它的 retrieval 层**。Munger 的 retrieval 是 wiki + full-text search + pgvector，不是 LlamaIndex 的 `KGTableRetriever`。

### 为什么不用 GraphRAG？

GraphRAG 的**算法**是目前最好的（gleaning、community detection、hierarchical summarization），但它的**工程实现**是一个独立的 indexing pipeline，不是一个可以嵌入到你的 Worker 里的 library。它输出 Parquet 文件到本地目录，有自己的 config schema，有自己的 CLI。要把它嵌入 Munger 的 `IngestRunner.run()` 流程里，你要么 fork 它、要么把它当子进程调——都不值得。

### 推荐：自建 tools，借鉴 GraphRAG 的算法

具体来说：

- **Chunking**：用 `tiktoken` 做 token-based splitting（GraphRAG 的做法），或者 `langchain_text_splitters.RecursiveCharacterTextSplitter`
- **Entity extraction + gleaning**：用 `instructor` 库 + Pydantic schema 做 structured output extraction，自己实现 gleaning loop（下面有代码）
- **Entity resolution**：用 embedding cosine similarity + LLM confirm 做 dedup（GraphRAG 只做 title+type 匹配，你可以做得更好）
- **Community detection**：如果将来需要，用 `graspologic` 的 Leiden 算法（这是 GraphRAG 唯一值得直接引用的依赖）

**需要安装的依赖（极轻量）：**

```
instructor          # structured LLM output with retry/validation
tiktoken            # token counting for chunking
pgvector            # Postgres vector extension (你已经有了)
# 可选：
graspologic         # Leiden community detection (Phase 3)
```

---

## 2. Tools 设计

### 设计原则

你当前的 5 个 tools 是 **monolithic** 的：每个 tool 接收 `source_id`，内部完成所有工作。新设计需要把它们拆成**更细粒度的、可组合的 tools**，让 agent 根据 SKILL 指令灵活编排。

核心改变：

| 现有 | 新设计 | 变化原因 |
|------|--------|---------|
| `extract_source_text(source_id)` | `parse_document(source_id)` | 名称更明确 |
| `extract_entities_from_text(source_id)` 一次性提取所有 | `chunk_document(source_id)` + `extract_entities_from_chunks(source_id, chunk_ids)` + `glean_entities(source_id, chunk_ids)` | 拆开实现线性扩展 |
| 无 | `resolve_entities(source_id)` | 新增：dedup + canonicalize |
| `summarize_source(source_id)` | `summarize_source(source_id)` | 保持不变 |
| `create_wiki_pages(source_id)` | `generate_wiki_pages(source_id)` + `link_wiki_pages(source_id)` | 拆开：生成 vs 链接 |
| `finalize_ingest(source_id)` | `finalize_ingest(source_id)` | 保持不变 |

### 目录结构

```
app/runtime/tools/
├── __init__.py
├── parsing.py              # parse_document
├── chunking.py             # chunk_document
├── extraction.py           # extract_entities_from_chunks, glean_entities
├── resolution.py           # resolve_entities
├── summarization.py        # summarize_source
├── wiki_generation.py      # generate_wiki_pages, link_wiki_pages
├── finalization.py         # finalize_ingest
└── schemas/
    ├── __init__.py
    ├── entity.py           # Pydantic schemas for extraction
    └── chunk.py            # Chunk metadata schema
```

### Tool 实现

#### 2.1 Schemas（共用 Pydantic 模型）

```python
# app/runtime/tools/schemas/entity.py
from pydantic import BaseModel, Field

class ExtractedEntity(BaseModel):
    """单个提取的实体"""
    name: str = Field(description="实体的规范名称，使用最完整的标识形式")
    type: str = Field(description="实体类型: person, concept, model, fact, event, organization, technology, book, term")
    description: str = Field(description="基于源文本的实体描述，2-3句话")

class ExtractedRelationship(BaseModel):
    """两个实体之间的关系"""
    source: str = Field(description="关系的源实体名称")
    target: str = Field(description="关系的目标实体名称")
    type: str = Field(description="关系类型: relates_to, part_of, derived_from, influences, contradicts, supports, authored_by, applied_in")
    description: str = Field(description="关系的具体描述")

class ExtractionResult(BaseModel):
    """单个 chunk 的提取结果"""
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)

class GleanResult(BaseModel):
    """Gleaning 补充提取的结果"""
    missed_entities: list[ExtractedEntity] = Field(default_factory=list)
    missed_relationships: list[ExtractedRelationship] = Field(default_factory=list)
    reasoning: str = Field(description="简要说明为什么这些实体在第一轮被遗漏")
```

```python
# app/runtime/tools/schemas/chunk.py
from pydantic import BaseModel, Field

class ChunkMetadata(BaseModel):
    """Chunk 的元数据"""
    chunk_id: str
    source_id: str
    chunk_index: int
    token_count: int
    char_start: int
    char_end: int
    content_preview: str = Field(description="前100字符预览")
```

#### 2.2 parse_document

```python
# app/runtime/tools/parsing.py
from langchain_core.tools import tool
from app.services.storage_service import StorageService

@tool
def parse_document(source_id: str) -> str:
    """从原始文件中提取纯文本。支持 PDF、DOCX、PPTX、Markdown、纯文本。
    
    提取的文本将写入 sources.content_text。
    返回提取状态和字符数。
    """
    storage: StorageService = _get_service("storage")
    
    source = storage.get_source(source_id)
    if not source:
        return f"Error: source {source_id} not found"
    
    # 根据文件类型选择 parser
    text = storage.extract_text(source.file_path)
    
    # 写回 DB
    storage.update_source_text(source_id, text)
    
    return f"Extracted {len(text)} characters from {source.filename}"
```

#### 2.3 chunk_document（核心：线性扩展的基础）

```python
# app/runtime/tools/chunking.py
import tiktoken
from langchain_core.tools import tool

# GraphRAG 研究表明 600 token chunks 提取的实体数量是 2400 token 的近 2 倍
DEFAULT_CHUNK_SIZE = 600
DEFAULT_OVERLAP = 100

@tool
def chunk_document(source_id: str, chunk_size: int = 600, overlap: int = 100) -> str:
    """将文档文本切分为固定大小的 token chunks，存入 chunks 表。
    
    chunk_size 默认 600 tokens（基于 GraphRAG 研究，小 chunk 提取的实体数量
    是大 chunk 的近 2 倍）。每个 chunk 保留与前一个 chunk 的 overlap 以保持上下文连续。
    
    返回创建的 chunk 数量。
    """
    db = _get_service("db")
    source = db.get_source(source_id)
    
    if not source or not source.content_text:
        return f"Error: source {source_id} has no extracted text. Run parse_document first."
    
    encoding = tiktoken.encoding_for_model("gpt-4o")
    tokens = encoding.encode(source.content_text)
    
    chunks = []
    char_offset = 0
    
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk_tokens = tokens[i : i + chunk_size]
        chunk_text = encoding.decode(chunk_tokens)
        
        char_start = source.content_text.find(chunk_text[:50], char_offset)
        if char_start == -1:
            char_start = char_offset
        char_end = char_start + len(chunk_text)
        
        chunks.append({
            "source_id": source_id,
            "chunk_index": len(chunks),
            "content": chunk_text,
            "token_count": len(chunk_tokens),
            "char_start": char_start,
            "char_end": char_end,
        })
        
        char_offset = char_start + (chunk_size - overlap)
    
    # 批量写入 DB
    chunk_ids = db.bulk_create_chunks(chunks)
    
    return f"Created {len(chunk_ids)} chunks (avg {chunk_size} tokens each) for source {source_id}"
```

#### 2.4 extract_entities_from_chunks（核心：chunk-then-extract）

```python
# app/runtime/tools/extraction.py
import asyncio
import instructor
from langchain_core.tools import tool
from .schemas.entity import ExtractionResult, GleanResult

EXTRACTION_PROMPT = """从以下文本中提取所有语义实体（概念、人物、模型、事实、事件、组织、技术、术语等）
以及它们之间的关系。

要求：
1. 使用实体最完整的标识形式（例如 "Charlie Munger" 而不是 "Munger"）
2. 为每个实体提供基于文本的描述
3. 识别实体之间的明确关系
4. 不要遗漏任何重要的实体或关系

文本：
{chunk_text}
"""

@tool
def extract_entities_from_chunks(source_id: str, max_concurrency: int = 5) -> str:
    """对文档的所有 chunks 并行执行 LLM entity extraction。
    
    每个 chunk 独立提取实体和关系，结果写入 entity_extractions 表。
    这是 chunk-then-extract 模式的核心：提取的实体总量随 chunk 数量线性增长。
    
    max_concurrency 控制并行 LLM 调用数量（默认 5，避免 rate limit）。
    返回提取统计。
    """
    db = _get_service("db")
    llm = _get_service("llm")
    
    chunks = db.get_chunks_by_source(source_id)
    if not chunks:
        return f"Error: no chunks found for source {source_id}. Run chunk_document first."
    
    # instructor 封装 LLM client，确保 structured output
    client = instructor.from_openai(llm.get_client())
    
    total_entities = 0
    total_relationships = 0
    
    async def extract_one(chunk):
        result = await client.chat.completions.create(
            model=llm.get_model(),
            response_model=ExtractionResult,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(chunk_text=chunk.content)
            }],
            max_retries=2,  # instructor 的 validation retry
        )
        return chunk.id, result
    
    # 带并发控制的并行提取
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def extract_with_limit(chunk):
        async with semaphore:
            return await extract_one(chunk)
    
    results = asyncio.run(
        asyncio.gather(*[extract_with_limit(c) for c in chunks])
    )
    
    # 批量写入 DB（raw extractions，还未做 dedup）
    for chunk_id, extraction in results:
        db.save_chunk_extraction(
            chunk_id=chunk_id,
            source_id=source_id,
            entities=extraction.entities,
            relationships=extraction.relationships,
        )
        total_entities += len(extraction.entities)
        total_relationships += len(extraction.relationships)
    
    return (
        f"Extracted {total_entities} entities and {total_relationships} relationships "
        f"from {len(chunks)} chunks (avg {total_entities/len(chunks):.1f} entities/chunk)"
    )
```

#### 2.5 glean_entities（核心：防止 recall 下降）

```python
GLEAN_PROMPT = """你之前从同一段文本中提取了以下实体和关系。
请仔细重新阅读文本，找出所有**遗漏的**实体和关系。

常见遗漏类型：
- 隐含但重要的概念（文本讨论了但未明确命名的思维模型、理论）
- 修饰性提及的人物或组织
- 实体之间的间接关系
- 中文/英文别名、缩写对应的完整实体

已提取的实体：
{existing_entities}

原文：
{chunk_text}
"""

@tool
def glean_entities(source_id: str, max_gleanings: int = 1) -> str:
    """对已提取过实体的 chunks 执行 gleaning（二次提取），找出第一轮遗漏的实体。
    
    Gleaning 是 GraphRAG 论文中验证过的技术：将已提取的实体反馈给 LLM，
    要求它找出遗漏项。在 600 token chunk + 1 轮 gleaning 的配置下，
    通常能额外找回 15-25% 的实体。
    
    max_gleanings 控制 gleaning 轮数（默认 1，通常够用；2+ 轮收益递减）。
    返回补充提取的统计。
    """
    db = _get_service("db")
    llm = _get_service("llm")
    client = instructor.from_openai(llm.get_client())
    
    chunks = db.get_chunks_by_source(source_id)
    gleaned_total = 0
    
    for glean_round in range(max_gleanings):
        for chunk in chunks:
            existing = db.get_chunk_extraction(chunk.id)
            if not existing:
                continue
            
            existing_names = [e.name for e in existing.entities]
            
            result = client.chat.completions.create(
                model=llm.get_model(),
                response_model=GleanResult,
                messages=[{
                    "role": "user",
                    "content": GLEAN_PROMPT.format(
                        existing_entities=", ".join(existing_names),
                        chunk_text=chunk.content,
                    )
                }],
            )
            
            if result.missed_entities or result.missed_relationships:
                db.append_chunk_extraction(
                    chunk_id=chunk.id,
                    source_id=source_id,
                    entities=result.missed_entities,
                    relationships=result.missed_relationships,
                )
                gleaned_total += len(result.missed_entities)
    
    return f"Gleaning found {gleaned_total} additional entities across {len(chunks)} chunks"
```

#### 2.6 resolve_entities（核心：dedup + canonicalize）

```python
@tool
def resolve_entities(source_id: str, auto_merge_threshold: float = 0.92, review_threshold: float = 0.78) -> str:
    """对提取的 raw entities 执行去重和规范化。
    
    分三步：
    1. Canonicalize：将实体名称规范化（去除冗余修饰词、统一大小写、合并中英文别名）
    2. Embed + Block：为每个实体生成 embedding，用 cosine similarity 做 semantic blocking
    3. Match + Merge：在 block 内用 LLM 确认是否是同一实体，合并描述
    
    规则：
    - cosine > auto_merge_threshold (默认 0.92)：自动合并
    - review_threshold < cosine < auto_merge_threshold：标记待人工审核
    - cosine < review_threshold (默认 0.78)：视为不同实体
    
    关键设计：naming（叫什么名字）和 identity（是否是同一个东西）分开处理。
    合并后的实体保留所有 source provenance。
    返回合并统计。
    """
    db = _get_service("db")
    llm = _get_service("llm")
    
    # 1. 获取所有 raw extracted entities for this source
    raw_entities = db.get_raw_entities_by_source(source_id)
    
    # 2. Canonicalize names
    # ... (LLM call to normalize names)
    
    # 3. Generate embeddings (pgvector)
    # ... (batch embed entity "name: description" strings)
    
    # 4. Semantic blocking: group entities with cosine > review_threshold
    # ... (SQL: SELECT pairs WHERE cosine_distance < threshold)
    
    # 5. Within each block, LLM-confirm identity
    # ... 
    
    # 6. Merge: create canonical Entity rows, link EntityMention to chunks/sources
    # ...
    
    # 7. Cross-document linking: check if any new entity matches existing DB entities
    # ... (same cosine + LLM pipeline, but against global entity table)
    
    merged_count = 0  # placeholder
    new_count = 0
    
    return (
        f"Entity resolution: {len(raw_entities)} raw → {new_count} new entities, "
        f"{merged_count} merged with existing. "
        f"All entities retain source provenance (entity→chunk→document)."
    )
```

#### 2.7 generate_wiki_pages + link_wiki_pages

```python
# app/runtime/tools/wiki_generation.py

WIKI_PAGE_PROMPT = """为以下实体生成一个 wiki 页面。

实体名称：{entity_name}
实体类型：{entity_type}
实体描述（来自多个来源）：
{descriptions}

来源文档：
{source_references}

要求：
1. 用 markdown 格式输出
2. YAML frontmatter 包含 title, type, sources, related, created, confidence
3. 正文引用来源时使用 [[Source Title]] wikilink 格式
4. 提及相关概念时使用 [[Concept Name]] wikilink 格式
5. 支持中英文混合内容
6. 2-4 段落，不要过长
"""

@tool
def generate_wiki_pages(source_id: str) -> str:
    """为本次 ingest 中新增和更新的实体生成/更新 wiki 页面。
    
    只处理受本次 ingest 影响的实体（新建或新增了来源的实体），不做全量重建。
    每个 wiki 页面包含：
    - YAML frontmatter (title, type, sources[], related[], confidence)
    - Markdown 正文，内含 [[wikilinks]] 引用
    - 来源追溯：每个 claim 关联到具体的 chunk 和 document
    
    返回创建/更新的页面数量。
    """
    db = _get_service("db")
    wiki = _get_service("wiki")
    llm = _get_service("llm")
    
    affected_entities = db.get_entities_affected_by_source(source_id)
    
    created = 0
    updated = 0
    
    for entity in affected_entities:
        # 收集该实体所有来源的描述
        mentions = db.get_entity_mentions(entity.id)
        descriptions = [m.description for m in mentions]
        source_refs = [f"{m.source_title} (chunk {m.chunk_index})" for m in mentions]
        
        # LLM 生成 wiki 内容
        content = llm.generate(
            WIKI_PAGE_PROMPT.format(
                entity_name=entity.name,
                entity_type=entity.type,
                descriptions="\n".join(f"- {d}" for d in descriptions),
                source_references="\n".join(f"- {s}" for s in source_refs),
            )
        )
        
        existing_page = wiki.get_page_by_entity(entity.id)
        if existing_page:
            wiki.update_page(existing_page.id, content)
            updated += 1
        else:
            wiki.create_page(entity_id=entity.id, content=content)
            created += 1
    
    return f"Wiki pages: {created} created, {updated} updated for source {source_id}"


@tool
def link_wiki_pages(source_id: str) -> str:
    """扫描受影响的 wiki 页面，解析 [[wikilinks]]，更新 wiki_links 表。
    
    同时生成 source summary page（汇总该 source 提取的所有实体和关系）。
    返回创建的链接数量。
    """
    db = _get_service("db")
    wiki = _get_service("wiki")
    
    affected_pages = wiki.get_pages_affected_by_source(source_id)
    link_count = 0
    
    for page in affected_pages:
        # 解析 [[wikilinks]]
        links = wiki.parse_wikilinks(page.content)
        for target_title in links:
            target_page = wiki.get_page_by_title(target_title)
            if target_page:
                wiki.create_link(page.id, target_page.id)
                link_count += 1
    
    # 生成 source summary page
    wiki.generate_source_summary_page(source_id)
    
    return f"Created {link_count} wiki links. Source summary page generated."
```

### 新增 DB 表

你现有的 schema 需要加一个 `chunks` 表来支持 chunk-then-extract：

```sql
-- 新增：chunks 表（chunk-then-extract 的基础）
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    embedding vector(1536),               -- pgvector
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(source_id, chunk_index)
);

-- 新增：chunk_extractions 表（raw extraction 结果，dedup 前）
CREATE TABLE chunk_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    entities JSONB NOT NULL DEFAULT '[]',         -- ExtractedEntity[]
    relationships JSONB NOT NULL DEFAULT '[]',    -- ExtractedRelationship[]
    glean_round INTEGER NOT NULL DEFAULT 0,       -- 0=首轮, 1=gleaning
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 修改现有 entity_mentions 表，增加 chunk-level provenance
ALTER TABLE entity_mentions
    ADD COLUMN chunk_id UUID REFERENCES chunks(id),
    ADD COLUMN char_start INTEGER,
    ADD COLUMN char_end INTEGER;
```

---

## 3. SKILLS 设计

SKILL 是 agent 的"执行手册"——告诉 agent 对于某类任务应该按什么顺序调用哪些 tools、注意什么规则、预期什么结果。

### 3.1 顶层 Skill：`default-ingest`

```markdown
---
name: default-ingest
description: >
  完整的文档 ingestion 工作流。将上传的源文件转化为结构化的实体、关系和 wiki 页面。
  支持 PDF、DOCX、PPTX、Markdown、纯文本。支持中英文混合内容。
  设计目标：提取的实体数量随文档大小线性增长，不因文档变长而丢失信息。
allowed-tools:
  - parse_document
  - chunk_document
  - extract_entities_from_chunks
  - glean_entities
  - resolve_entities
  - summarize_source
  - generate_wiki_pages
  - link_wiki_pages
  - finalize_ingest
---

# Default Ingest Workflow

你是 Munger 的 ingestion agent。你的任务是将用户上传的源文件转化为结构化的知识。

## 执行顺序

严格按以下顺序执行。每一步完成后，检查返回值确认成功再进入下一步。
任何一步失败则停止并报告错误。

### Step 1: 解析文档
调用 `parse_document(source_id)` 提取纯文本。

### Step 2: 切分 Chunks
调用 `chunk_document(source_id, chunk_size=600, overlap=100)`。
- chunk_size=600 是经过验证的最优值（GraphRAG 论文发现 600 token chunks
  提取的实体数量是 2400 token 的近 2 倍）
- 对于特别短的文档（< 1200 tokens），chunk_size 可以等于全文长度

### Step 3: 提取实体和关系
调用 `extract_entities_from_chunks(source_id, max_concurrency=5)`。
- 这是 pipeline 中最耗时的步骤，并行度 5 是默认值
- 检查返回的 entities/chunk 比率，正常范围是 3-15 entities/chunk

### Step 4: Gleaning 补充提取
调用 `glean_entities(source_id, max_gleanings=1)`。
- 1 轮 gleaning 通常足够，能额外找回 15-25% 的实体
- 如果 Step 3 的 entities/chunk < 3，考虑用 max_gleanings=2

### Step 5: 实体去重和规范化
调用 `resolve_entities(source_id)`。
- 这步会将 raw entities 合并为 canonical entities
- 同时会与数据库中已有的全局 entities 做 cross-document linking

### Step 6: 生成摘要
调用 `summarize_source(source_id)`。

### Step 7: 生成 Wiki 页面
调用 `generate_wiki_pages(source_id)`。
- 只处理本次 ingest 新增或更新的实体，不做全量重建

### Step 8: 链接 Wiki 页面
调用 `link_wiki_pages(source_id)`。
- 解析所有 [[wikilinks]]，更新 wiki_links 表
- 生成 source summary page

### Step 9: 完成
调用 `finalize_ingest(source_id)`。

## 错误处理

- 如果任何 tool 返回以 "Error:" 开头的字符串，立即停止
- 记录已完成的最后一步，以便后续可以从断点恢复
- 解析失败（Step 1）是最常见的错误源，通常是文件格式不支持

## 质量指标

在 finalize 之前，检查以下指标：
- **entities/chunk 比率**：正常 3-15，< 3 说明提取不充分，> 20 说明可能过度提取
- **去重率**：正常 10-30%，> 50% 说明 chunk overlap 可能过大
- **wiki 页面数 vs entity 数**：应接近 1:1（每个 canonical entity 一个页面）
```

### 3.2 子 Skill：`entity-extract-only`

用于对已有文档重新提取实体（不重新解析和生成 wiki）。

```markdown
---
name: entity-extract-only
description: >
  仅执行实体提取步骤（chunk → extract → glean → resolve），不生成 wiki 页面。
  用于对已有文档重新提取实体，或调试实体提取质量。
allowed-tools:
  - chunk_document
  - extract_entities_from_chunks
  - glean_entities
  - resolve_entities
---

# Entity Extract Only

仅执行实体提取 pipeline，不生成 wiki。适用于：
- 调试实体提取质量
- 用新的 LLM 模型重新提取
- 批量补充提取（文档已解析但实体提取不完整）

## 前提条件

`source.content_text` 必须已存在（即 parse_document 已经执行过）。
如果不存在，报错并建议用户运行 default-ingest。

## 执行顺序

1. `chunk_document(source_id)` — 如果 chunks 已存在，先清除旧 chunks
2. `extract_entities_from_chunks(source_id)`
3. `glean_entities(source_id)`
4. `resolve_entities(source_id)`

## 输出

只写入 entity 相关的表（chunks, chunk_extractions, entities, entity_mentions）。
不触碰 wiki_pages 和 wiki_links。
```

### 3.3 子 Skill：`wiki-regenerate`

用于在实体变化后重新生成 wiki。

```markdown
---
name: wiki-regenerate
description: >
  重新生成指定 source 或所有 sources 的 wiki 页面。
  用于 wiki 模板更新后、prompt 调整后、或手动编辑实体后的批量重建。
allowed-tools:
  - generate_wiki_pages
  - link_wiki_pages
---

# Wiki Regenerate

重新生成 wiki 页面，不重新提取实体。

## 使用场景

- Wiki 模板或 prompt 调整后需要重新生成
- 手动编辑了实体的 type 或 description 后需要更新对应的 wiki 页面
- 修复了 wikilink 解析 bug 后需要重建 links

## 执行顺序

1. `generate_wiki_pages(source_id)` — 会覆盖已有的 wiki 页面内容
2. `link_wiki_pages(source_id)` — 重建所有 wikilinks

## 注意

这是一个相对"廉价"的操作（只有 wiki 生成需要 LLM 调用），
不需要重新 chunk 或提取实体。
```

### 3.4 子 Skill：`munger-12-dimension`

保持你现有的 12 维分析，但改为 agent-callable。

```markdown
---
name: munger-12-dimension
description: >
  对已导入的 source 执行 Munger 风格的 12 维度分析。
  这是一个独立的分析路径，不影响 wiki 页面，结果存入 munger_analyses 表。
  可以在 ingest 完成后单独触发。
allowed-tools:
  - analyze_source_12d
---

# Munger 12-Dimension Analysis

对 source 执行多视角分析，产出结构化的 12 维度报告。

## 前提条件

source 必须已完成 ingest（status = completed），且 content_text 已提取。

## 12 维度

1. 核心论点 (Core Thesis)
2. 证据质量 (Evidence Quality)
3. 反面论证 (Counter-Arguments)
4. 心智模型 (Mental Models Applied)
5. 激励结构 (Incentive Structures)
6. 二阶效应 (Second-Order Effects)
7. 历史类比 (Historical Analogies)
8. 定量分析 (Quantitative Analysis)
9. 风险评估 (Risk Assessment)
10. 信息来源可靠性 (Source Reliability)
11. 认知偏误 (Cognitive Biases)
12. 行动建议 (Actionable Takeaways)

## 执行

单次调用 `analyze_source_12d(source_id)`，LLM 一次性生成所有 12 个维度。
结果存入 munger_analyses 表，前端可以直接渲染。
```

---

## 4. Pipeline 数据流总览

```
User uploads file
       │
       ▼
  ┌─────────────────────────────────────────────────────────┐
  │  parse_document                                          │
  │  原始文件 → content_text (写入 sources 表)                │
  └──────────────────────┬──────────────────────────────────┘
                         │
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │  chunk_document                                          │
  │  content_text → N 个 600-token chunks (写入 chunks 表)    │
  │  关键点：N 随文档大小线性增长                               │
  └──────────────────────┬──────────────────────────────────┘
                         │
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │  extract_entities_from_chunks (并行)                      │
  │  每个 chunk 独立提取 entities + relationships              │
  │  关键点：总 entity 数 ≈ N × (entities/chunk)，线性增长     │
  │  写入 chunk_extractions 表                                │
  └──────────────────────┬──────────────────────────────────┘
                         │
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │  glean_entities                                          │
  │  对每个 chunk 做二次提取，补充遗漏的 15-25% entities       │
  │  追加写入 chunk_extractions 表                            │
  └──────────────────────┬──────────────────────────────────┘
                         │
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │  resolve_entities                                        │
  │  raw entities → canonical entities                       │
  │  1. Canonicalize names (LLM)                             │
  │  2. Embed + semantic block (pgvector cosine)             │
  │  3. Within-block LLM match                               │
  │  4. Cross-document linking (vs global entity table)      │
  │  写入 entities + entity_mentions 表                      │
  └──────────────────────┬──────────────────────────────────┘
                         │
                    ┌────┴────┐
                    ▼         ▼
    ┌─────────────────┐  ┌──────────────────────┐
    │ summarize_source │  │ generate_wiki_pages  │
    │ 全文摘要          │  │ 每个 entity → 1 page │
    └────────┬────────┘  └──────────┬───────────┘
             │                      │
             │                      ▼
             │           ┌──────────────────────┐
             │           │ link_wiki_pages       │
             │           │ [[wikilinks]] → links │
             │           │ + source summary page │
             │           └──────────┬───────────┘
             │                      │
             └──────────┬───────────┘
                        ▼
              ┌──────────────────┐
              │ finalize_ingest  │
              │ status=completed │
              └──────────────────┘
```

## 5. Provenance（来源追溯）数据模型

这是 Munger 与一般 wiki 系统的核心区别——每个 claim 都能追溯到原文。

```
Document (sources)
    │
    │ 1:N
    ▼
Chunk (chunks)
    │  content, char_start, char_end, embedding
    │
    │ 1:N
    ▼
ChunkExtraction (chunk_extractions)
    │  raw entities + relationships (JSONB)
    │  glean_round: 0=首轮, 1=gleaning
    │
    │ N:1 (resolve_entities 聚合)
    ▼
Entity (entities)
    │  canonical name, type, merged_description
    │  embedding (for cross-doc linking)
    │
    │ 1:N
    ▼
EntityMention (entity_mentions)
    │  entity_id → chunk_id → source_id (完整追溯链)
    │  char_start, char_end (在 chunk 中的精确位置)
    │
    │ 1:1
    ▼
WikiPage (wiki_pages)
    │  每个 canonical entity 一个页面
    │  frontmatter.sources[] 列出所有来源文档
    │
    │ N:N (via wiki_links)
    ▼
WikiLink (wiki_links)
    │  页面间 [[wikilinks]]
```

## 6. 关键设计决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 不直接依赖 GraphRAG/LlamaIndex | 自建 tools + 借鉴算法 | 两者的工程实现都与 Munger 的 FastAPI/Worker/Postgres 架构不兼容 |
| Chunk size = 600 tokens | GraphRAG 论文验证 | 600 token chunks 提取的实体数是 2400 token 的近 2 倍 |
| Gleaning = 1 轮 | 收益/成本平衡 | 1 轮额外找回 15-25%，2+ 轮收益递减 |
| Entity resolution 分 naming 和 identity 两步 | 避免误合并 | 直接合并容易把两个同名但不同的实体搞混 |
| instructor + Pydantic 做 structured output | 替代 LlamaIndex 的 extractor | 更轻量，retry/validation 内置，不引入额外抽象层 |
| Wiki 增量更新 | 只处理受影响的实体 | GraphRAG 的全量重建是其最大痛点 |
| Provenance 从 Day 1 就建 | 不可补建 | entity→chunk→document 的追溯链一旦丢失无法重建 |
