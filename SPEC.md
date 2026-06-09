> **ARCHIVED** — Historical snapshot. For current architecture read [ARCHITECTURE.md](./ARCHITECTURE.md) and [AGENTS.md](./AGENTS.md). Do not implement from this file.

# Munger - Specification Document

## Overview
Munger is an automated knowledge base system inspired by Andrej Karpathy's LLM Wiki and Charlie Munger's multi-dimensional thinking framework. It incrementally ingests source materials, extracts entities and concepts, and maintains an interconnected wiki through LLM-powered analysis.

## Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React SPA)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │ Wiki浏览  │ │ 全文搜索  │ │ 图谱视图  │ │ Munger分析面板│    │
│  │ Browse   │ │ Search   │ │ Graph    │ │ Analysis     │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │ 摄取管理  │ │ 实体浏览  │ │ 日志视图  │ │ 设置/配置    │    │
│  │ Ingest   │ │ Entities │ │ Log      │ │ Settings     │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API + WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │ API路由   │ │ 摄取引擎  │ │ Munger   │ │ 搜索/索引    │    │
│  │ Router   │ │ Ingest   │ │ Workflow │ │ Search      │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │ LLM服务   │ │ 实体提取  │ │ 文件存储  │ │ Wiki管理器   │    │
│  │ LLM      │ │ Entity   │ │ Storage  │ │ Wiki Mgr    │    │
│  │ Service  │ │ Extract  │ │ Service  │ │             │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Data Layer                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │ SQLite/  │ │ 文件系统  │ │ Vector   │ │ 索引文件     │    │
│  │ PostgreSQL│ │ (Sources)│ │ Store    │ │ (Index.md) │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.12+)
- **Database**: SQLite (dev) / PostgreSQL (prod) with SQLAlchemy 2.0 + Alembic
- **Vector Search**: sqlite-vec (dev) / pgvector (prod)
- **LLM Integration**: Multi-provider abstraction (OpenAI, Anthropic, Ollama)
- **File Processing**: PyPDF2, python-markdown, beautifulsoup4, trafilatura
- **Task Queue**: Ingestion jobs managed via database status fields

### Frontend
- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite v7.2.4
- **Styling**: Tailwind CSS v3.4.19
- **UI Components**: shadcn/ui
- **Routing**: HashRouter (react-router-dom)
- **State Management**: React Context + hooks
- **Charts**: @xyflow/react for graph visualization, recharts for analytics

### Deployment
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Caddy (optional)

## Data Models

### Source (原始资料)
```python
class Source(Base):
    __tablename__ = "sources"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    filename: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000))  # relative path in sources/
    file_type: Mapped[str] = mapped_column(String(50))  # pdf, txt, md, html, url
    content_hash: Mapped[str] = mapped_column(String(64))  # sha256
    file_size: Mapped[int] = mapped_column()  # bytes
    content_text: Mapped[str | None] = mapped_column(Text)  # extracted text
    content_summary: Mapped[str | None] = mapped_column(Text)  # LLM-generated summary
    source_url: Mapped[str | None] = mapped_column(String(2000))  # for web clips
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, completed, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    wiki_pages: Mapped[list["WikiPage"]] = relationship(back_populates="source")
    munger_analyses: Mapped[list["MungerAnalysis"]] = relationship(back_populates="source")
```

### WikiPage (Wiki页面)
```python
class WikiPage(Base):
    __tablename__ = "wiki_pages"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    slug: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    content: Mapped[str] = mapped_column(Text)  # markdown content
    page_type: Mapped[str] = mapped_column(String(50))  
    # Types: summary, entity, concept, model, mechanism, incentive, 
    #        psychology, comparison, analysis, overview, index, log
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("wiki_pages.id"))
    metadata_json: Mapped[str | None] = mapped_column(Text)  # JSON string
    word_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    source: Mapped["Source | None"] = relationship(back_populates="wiki_pages")
    outgoing_links: Mapped[list["WikiLink"]] = relationship(
        foreign_keys="WikiLink.from_page_id", back_populates="from_page"
    )
    incoming_links: Mapped[list["WikiLink"]] = relationship(
        foreign_keys="WikiLink.to_page_id", back_populates="to_page"
    )
    munger_analyses: Mapped[list["MungerAnalysis"]] = relationship(back_populates="wiki_page")
```

### Entity (实体)
```python
class Entity(Base):
    __tablename__ = "entities"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    # Types: person, concept, model, mechanism, incentive_structure, 
    #        book, paper, organization, field, event, principle
    description: Mapped[str | None] = mapped_column(Text)
    wiki_page_id: Mapped[int | None] = mapped_column(ForeignKey("wiki_pages.id"))
    metadata_json: Mapped[str | None] = mapped_column(Text)
    mention_count: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    wiki_page: Mapped["WikiPage | None"] = relationship()
    mentions: Mapped[list["EntityMention"]] = relationship(back_populates="entity")
```

### EntityMention (实体提及)
```python
class EntityMention(Base):
    __tablename__ = "entity_mentions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    wiki_page_id: Mapped[int | None] = mapped_column(ForeignKey("wiki_pages.id"))
    context: Mapped[str | None] = mapped_column(Text)  # surrounding text
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    entity: Mapped["Entity"] = relationship(back_populates="mentions")
```

### WikiLink (Wiki链接关系)
```python
class WikiLink(Base):
    __tablename__ = "wiki_links"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    from_page_id: Mapped[int] = mapped_column(ForeignKey("wiki_pages.id"))
    to_page_id: Mapped[int] = mapped_column(ForeignKey("wiki_pages.id"))
    link_type: Mapped[str] = mapped_column(String(50), default="reference")
    # Types: reference, contradicts, supports, relates, parent, child
    context: Mapped[str | None] = mapped_column(Text)  # why this link exists
    
    from_page: Mapped["WikiPage"] = relationship(foreign_keys=[from_page_id], back_populates="outgoing_links")
    to_page: Mapped["WikiPage"] = relationship(foreign_keys=[to_page_id], back_populates="incoming_links")
```

### MungerAnalysis (Munger分析结果)
```python
class MungerAnalysis(Base):
    __tablename__ = "munger_analyses"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    wiki_page_id: Mapped[int | None] = mapped_column(ForeignKey("wiki_pages.id"))
    dimension: Mapped[str] = mapped_column(String(50))
    # Dimensions: source, claim, concept, model, mechanism, incentive,
    #             psychology, dual_track, counterargument, checklist, case, decision
    dimension_number: Mapped[int] = mapped_column()  # 1-12
    analysis_content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(default=0.0)  # 0.0-1.0
    key_insights: Mapped[str | None] = mapped_column(Text)  # JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    source: Mapped["Source | None"] = relationship(back_populates="munger_analyses")
    wiki_page: Mapped["WikiPage | None"] = relationship(back_populates="munger_analyses")
```

### IngestionLog (摄取日志)
```python
class IngestionLog(Base):
    __tablename__ = "ingestion_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    log_type: Mapped[str] = mapped_column(String(50))  # ingest, query, lint, analysis
    action: Mapped[str] = mapped_column(String(200))  # brief description
    details: Mapped[str | None] = mapped_column(Text)  # JSON details
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### Config (系统配置)
```python
class Config(Base):
    __tablename__ = "configs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(200), unique=True)
    value: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## API Endpoints

### Sources (原始资料管理)
- `POST /api/sources/upload` - Upload a file (PDF, TXT, MD)
- `POST /api/sources/clip` - Submit a URL for web clipping
- `GET /api/sources` - List all sources (paginated, filterable)
- `GET /api/sources/{id}` - Get source details with extracted content
- `DELETE /api/sources/{id}` - Delete a source (and its wiki pages)
- `POST /api/sources/{id}/ingest` - Trigger ingestion workflow
- `GET /api/sources/{id}/status` - Get ingestion status

### Wiki Pages
- `GET /api/wiki` - List all wiki pages (paginated, filterable by type)
- `GET /api/wiki/{id}` - Get wiki page content
- `GET /api/wiki/slug/{slug}` - Get wiki page by slug
- `PUT /api/wiki/{id}` - Update wiki page (manual edit)
- `POST /api/wiki` - Create wiki page manually
- `DELETE /api/wiki/{id}` - Delete wiki page
- `GET /api/wiki/{id}/links` - Get all links (inbound + outbound)
- `GET /api/wiki/{id}/related` - Get related pages

### Entities (实体管理)
- `GET /api/entities` - List all entities (paginated, filterable by type)
- `GET /api/entities/{id}` - Get entity details
- `GET /api/entities/{id}/mentions` - Get all mentions of entity
- `GET /api/entities/{id}/related` - Get related entities
- `PUT /api/entities/{id}` - Update entity (manual edit)

### Search
- `GET /api/search?q={query}&type={type}` - Full-text search across wiki + sources
- `GET /api/search/semantic?q={query}` - Semantic search using vector embeddings
- `GET /api/search/suggest?q={partial}` - Autocomplete suggestions

### Munger Analysis
- `POST /api/munger/analyze/{source_id}` - Run Munger analysis on a source
- `GET /api/munger/analysis/{wiki_page_id}` - Get Munger analysis for a page
- `GET /api/munger/dimensions` - List all 12 Munger dimensions
- `GET /api/munger/summary/{source_id}` - Get analysis summary dashboard

### Ingestion & Jobs
- `GET /api/jobs` - List active/completed jobs
- `GET /api/jobs/{id}` - Get job status
- `POST /api/jobs/cancel/{id}` - Cancel a running job
- `GET /api/logs` - Get ingestion logs (paginated)

### Config
- `GET /api/config` - Get all config values
- `PUT /api/config/{key}` - Update config value
- `GET /api/config/models` - List available LLM models
- `POST /api/config/test-model` - Test LLM connection

### Health & Info
- `GET /api/health` - Health check
- `GET /api/stats` - System stats (source count, wiki count, entity count)

## Munger Workflow (12 Dimensions)

The Munger analysis workflow processes source material through 12 analytical dimensions:

### Phase 1: Extraction
1. **Source Analysis** (来源) - Document provenance, credibility, context
2. **Claim Extraction** (命题) - Identify core claims, their types, and strength
3. **Concept Identification** (概念) - Extract key concepts with definitions

### Phase 2: Modeling
4. **Universal Model** (普世模型) - Map to interdisciplinary mental models
5. **Mechanism Analysis** (机制) - Trace causal chains, feedback loops, thresholds
6. **Incentive Mapping** (激励) - Identify stakeholders, incentives, principal-agent dynamics

### Phase 3: Critical Thinking
7. **Psychology Check** (心理误判) - Scan for 25 cognitive biases from Munger's framework
8. **Dual-Track Analysis** (双轨分析) - Rational vs. psychological explanations
9. **Counterargument** (反方观点) - Strongest objections, falsifying evidence

### Phase 4: Application
10. **Checklist** (检查清单) - Structured validation checklist
11. **Case Study** (案例) - Historical cases that validate/refute
12. **Decision Review** (决策复盘) - Decision journal format

## File System Structure
```
/munger-data/
  ├── sources/              # Original source materials (immutable)
  │   ├── 2026/
  │   │   ├── 06/
  │   │   │   ├── source_001_article.pdf
  │   │   │   ├── source_002_book_chapter.txt
  │   │   │   └── source_003_web_clip.html
  ├── wiki/                 # LLM-generated wiki pages
  │   ├── index.md          # Content index (auto-generated)
  │   ├── log.md            # Operation log (append-only)
  │   ├── entities/         # Entity pages
  │   ├── concepts/         # Concept pages
  │   ├── models/           # Mental model pages
  │   ├── summaries/        # Source summaries
  │   └── analyses/         # Munger analysis pages
  ├── schema/
  │   └── MUNGER.md         # Munger framework schema (human-editable)
  └── config.yaml           # System configuration
```

## Frontend Routes
```
/                    - Dashboard (stats, recent activity, quick actions)
/wiki                - Wiki browser (list view with filters)
/wiki/:slug          - Wiki page viewer (markdown + graph + Munger analysis)
/search              - Full-text search with filters
/entities            - Entity explorer (grid/list with type filters)
/entities/:id        - Entity detail page
/ingest              - Ingestion management (upload + status + history)
/graph               - Knowledge graph visualization
/munger/:sourceId    - Munger 12-dimension analysis view
/log                 - System log (chronological)
/settings            - Configuration (LLM models, system settings)
```

## LLM Integration Design

### Provider Abstraction
```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str: ...
    
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    
    @property
    @abstractmethod
    def max_tokens(self) -> int: ...

class OpenAIProvider(LLMProvider): ...
class AnthropicProvider(LLMProvider): ...
class OllamaProvider(LLMProvider): ...
```

### Configuration
- `llm.default_provider`: "ollama" | "openai" | "anthropic"
- `llm.default_model`: model name (e.g., "llama3.2", "gpt-4o")
- `llm.ollama_base_url`: "http://localhost:11434"
- `llm.openai_api_key`: "..."
- `llm.anthropic_api_key`: "..."
- `llm.embedding_model`: model for embeddings
- `llm.max_context_tokens`: context window limit

## Ingestion Pipeline

### Step-by-Step Flow
1. **File Reception** - Accept upload or URL submission
2. **Text Extraction** - Extract plain text from PDF/MD/TXT/HTML
3. **Chunking** - Split into manageable chunks (respecting semantic boundaries)
4. **Summary Generation** - LLM generates source summary
5. **Entity Extraction** - Identify and extract entities with types
6. **Wiki Page Creation** - Create/update wiki pages for entities, concepts
7. **Munger Analysis** - Run 12-dimension analysis (optional, can be deferred)
8. **Link Resolution** - Create cross-references between pages
9. **Index Update** - Update index.md with new entries
10. **Log Entry** - Append to log.md

### Status Tracking
Each source has a status field: `pending` → `extracting` → `summarizing` → `extracting_entities` → `creating_pages` → `analyzing` → `completed` | `failed`

## Vector Search
- Store embeddings for wiki pages and source content chunks
- Use cosine similarity for semantic search
- Fallback to full-text search (SQLite FTS5 or PostgreSQL tsvector)

## WebSocket Events
- `ingestion.progress` - Real-time ingestion status updates
- `wiki.updated` - Wiki page updated notification
- `entity.new` - New entity discovered

## Docker Compose Services
```yaml
services:
  munger-backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///data/munger.db
      - DATA_DIR=/app/data
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
  
  munger-frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - munger-backend
```
