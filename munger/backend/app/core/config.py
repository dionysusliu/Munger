"""Application configuration using pydantic-settings."""
import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

# Ollama-local embedding model ids — invalid when LLM_DEFAULT_PROVIDER=openrouter.
OLLAMA_ONLY_EMBEDDING_MODELS = frozenset(
    {
        "nomic-embed-text",
        "mxbai-embed-large",
        "all-minilm",
        "snowflake-arctic-embed",
    }
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "Munger"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, alias="DEBUG")

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://munger_app:Munger.App.2026@pigsty:5432/munger",
        alias="DATABASE_URL",
    )

    # Data directories
    data_dir: str = Field(default="./data", alias="DATA_DIR")
    sources_dir: str = "./data/sources"
    wiki_dir: str = "./data/wiki"
    schema_dir: str = "./data/schema"

    # LLM Configuration
    default_llm_provider: str = Field(default="ollama", alias="LLM_DEFAULT_PROVIDER")
    default_llm_model: str = Field(default="llama3.2", alias="LLM_DEFAULT_MODEL")
    ollama_base_url: str = Field(default="http://host.docker.internal:11434", alias="OLLAMA_BASE_URL")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    kimi_api_key: Optional[str] = Field(default=None, alias="KIMI_API_KEY")
    kimi_base_url: str = Field(default="https://api.kimi.com/coding/v1", alias="KIMI_BASE_URL")
    embedding_model: str = Field(default="nomic-embed-text", alias="LLM_EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=768, alias="LLM_EMBEDDING_DIMENSIONS")
    max_context_tokens: int = Field(default=8192, alias="LLM_MAX_CONTEXT_TOKENS")

    # Ingest pipeline (chunk-then-extract)
    ingest_chunk_size_tokens: int = Field(default=600, alias="INGEST_CHUNK_SIZE_TOKENS")
    ingest_chunk_overlap_tokens: int = Field(default=100, alias="INGEST_CHUNK_OVERLAP_TOKENS")
    ingest_max_gleanings: int = Field(default=1, alias="INGEST_MAX_GLEANINGS")
    ingest_chunk_worker_concurrency: int = Field(default=5, alias="INGEST_CHUNK_WORKER_CONCURRENCY")

    # PDF OCR (LiteParse + bundled Tesseract)
    tessdata_prefix: str = Field(default="/app/tessdata", alias="TESSDATA_PREFIX")
    ocr_enabled: bool = Field(default=True, alias="OCR_ENABLED")
    ocr_language: str = Field(default="eng+chi_sim", alias="OCR_LANGUAGE")

    # Worker / job queue
    worker_concurrency: int = Field(default=0, alias="MUNGER_WORKER_CONCURRENCY")
    worker_id: str = Field(default="worker-1", alias="MUNGER_WORKER_ID")
    job_heartbeat_interval_sec: int = Field(default=30, alias="MUNGER_JOB_HEARTBEAT_INTERVAL_SEC")
    job_stale_minutes: int = Field(default=45, alias="MUNGER_JOB_STALE_MINUTES")

    # Postgres bootstrap (one-shot init only)
    postgres_admin_url: str = Field(
        default="postgresql://dbuser_dba:DBUser.DBA@host.docker.internal:5432/postgres",
        alias="MUNGER_POSTGRES_ADMIN_URL",
    )
    postgres_app_user: str = Field(default="munger_app", alias="MUNGER_POSTGRES_APP_USER")
    postgres_app_password: str = Field(default="Munger.App.2026", alias="MUNGER_DB_PASSWORD")
    postgres_app_db: str = Field(default="munger", alias="MUNGER_POSTGRES_APP_DB")

    # Agent harness
    checkpointer_url: Optional[str] = Field(default=None, alias="MUNGER_CHECKPOINTER_URL")
    max_agent_steps: int = Field(default=24, alias="MUNGER_MAX_AGENT_STEPS")
    skills_dir: str = Field(default="./data/workflows", alias="MUNGER_SKILLS_DIR")
    builtin_skills_dir: str = Field(default="/app/builtin-workflows", alias="MUNGER_BUILTIN_SKILLS_DIR")

    # Ingest orchestrator: "graph" (LangGraph subgraphs, default) | "agent" (legacy agent+gating)
    ingest_orchestrator: str = Field(default="graph", alias="INGEST_ORCHESTRATOR")
    # Map mode for the cognify subgraph: "send" (LangGraph Send fan-out) | "service" (legacy gather)
    ingest_map_mode: str = Field(default="send", alias="INGEST_MAP_MODE")
    ingest_map_max_waves: int = Field(default=3, alias="INGEST_MAP_MAX_WAVES")
    ingest_map_stale_minutes: int = Field(default=15, alias="INGEST_MAP_STALE_MINUTES")
    ingest_instructor_enabled: bool = Field(default=True, alias="INGEST_INSTRUCTOR_ENABLED")
    ingest_allow_null_embedding: bool = Field(default=False, alias="INGEST_ALLOW_NULL_EMBEDDING")

    # Cross-chunk linking tunables (plan §4)
    link_fuzzy_ratio: int = Field(default=90, alias="INGEST_LINK_FUZZY_RATIO")
    link_fuzzy_trgm: float = Field(default=0.45, alias="INGEST_LINK_TRGM")
    link_semantic_cosine: float = Field(default=0.83, alias="INGEST_LINK_SEMANTIC_COSINE")
    link_w_lex: float = Field(default=0.45, alias="INGEST_LINK_W_LEX")
    link_w_sem: float = Field(default=0.55, alias="INGEST_LINK_W_SEM")
    link_auto_merge: float = Field(default=0.92, alias="INGEST_LINK_AUTO_MERGE")
    link_review_low: float = Field(default=0.80, alias="INGEST_LINK_REVIEW_LOW")
    link_relate_min: float = Field(default=0.70, alias="INGEST_LINK_RELATE_MIN")
    link_llm_adjudicate: bool = Field(default=True, alias="INGEST_LINK_LLM_ADJUDICATE")

    # LangSmith observability
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_api_key: Optional[str] = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="munger-ingest", alias="LANGSMITH_PROJECT")
    langsmith_endpoint: Optional[str] = Field(default=None, alias="LANGSMITH_ENDPOINT")

    # CORS
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:13000",
        ]
    )

    class Config:
        env_file = ".env"
        populate_by_name = True

    @model_validator(mode="after")
    def validate_openrouter_embedding_model(self) -> "Settings":
        provider = self.default_llm_provider.lower()
        if provider != "openrouter":
            return self
        embed = self.embedding_model.strip().lower()
        if embed in OLLAMA_ONLY_EMBEDDING_MODELS:
            raise ValueError(
                f"LLM_EMBEDDING_MODEL={self.embedding_model!r} is Ollama-only; "
                "use an OpenRouter model id such as qwen/qwen3-embedding-8b"
            )
        if "/" not in self.embedding_model:
            raise ValueError(
                f"LLM_EMBEDDING_MODEL={self.embedding_model!r} must be provider-qualified "
                "(e.g. qwen/qwen3-embedding-8b) when LLM_DEFAULT_PROVIDER=openrouter"
            )
        return self

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Derive subdirectories from data_dir
        self.sources_dir = os.path.join(self.data_dir, "sources")
        self.wiki_dir = os.path.join(self.data_dir, "wiki")
        self.schema_dir = os.path.join(self.data_dir, "schema")
        if self.skills_dir == "./data/workflows":
            self.skills_dir = os.path.join(self.data_dir, "workflows")
        if not self.checkpointer_url and self.database_url.startswith("postgresql"):
            sync_url = self.database_url.replace("postgresql+psycopg://", "postgresql://", 1)
            self.checkpointer_url = sync_url
        if self.worker_concurrency <= 0:
            import os as _os

            cpus = _os.cpu_count() or 2
            self.worker_concurrency = max(1, cpus - 1)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
