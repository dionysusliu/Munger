"""Configuration API routes for Munger."""
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.models.config import Config
from app.schemas.config import ConfigUpdate, ConfigResponse, ModelInfo

router = APIRouter()


# ---------------------------------------------------------------------------
# Default Configurations
# ---------------------------------------------------------------------------

DEFAULT_CONFIGS = [
    ("llm.default_provider", "openrouter", "Default LLM provider (ollama, openai, anthropic, openrouter, kimi)"),
    ("llm.default_model", "deepseek/deepseek-v4-flash", "Default LLM model name"),
    ("llm.embedding_model", "qwen/qwen3-embedding-8b", "Model used for text embeddings"),
    ("llm.max_context_tokens", "8192", "Maximum context window tokens"),
    ("llm.temperature", "0.7", "Sampling temperature for LLM generation"),
    ("ingest.auto_analyze", "true", "Automatically run Munger analysis after ingestion"),
    ("ingest.auto_create_wiki", "true", "Automatically create wiki pages during ingestion"),
    ("ingest.chunk_size", "2000", "Text chunk size for processing"),
    ("ingest.chunk_overlap", "200", "Overlap between consecutive chunks"),
    ("wiki.auto_index", "true", "Automatically update index.md when wiki changes"),
    ("wiki.auto_log", "true", "Automatically append to log.md on operations"),
    ("search.default_type", "all", "Default search result type filter"),
    ("search.results_per_page", "20", "Default number of search results per page"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _ensure_defaults(db: AsyncSession):
    """Insert default config values if the config table is empty."""
    result = await db.execute(select(Config))
    existing = result.scalars().all()
    if existing:
        return

    for key, value, description in DEFAULT_CONFIGS:
        db.add(Config(key=key, value=value, description=description))
    await db.flush()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
async def get_all_config(db: AsyncSession = Depends(get_db)):
    """Get all configuration values.

    Returns the complete set of key-value configuration pairs stored
    in the database, organized by category prefix.
    """
    await _ensure_defaults(db)

    result = await db.execute(select(Config).order_by(Config.key))
    configs = result.scalars().all()

    # Group by category prefix
    grouped = {}
    for config in configs:
        parts = config.key.split(".", 1)
        category = parts[0] if len(parts) > 1 else "general"
        if category not in grouped:
            grouped[category] = []
        grouped[category].append({
            "id": config.id,
            "key": config.key,
            "value": config.value,
            "description": config.description,
            "updated_at": config.updated_at,
        })

    return {
        "configs": grouped,
        "total": len(configs),
    }


@router.put("/{key}", response_model=ConfigResponse)
async def update_config(
    key: str,
    data: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a configuration value by key.

    Creates the config entry if it does not already exist.
    """
    result = await db.execute(select(Config).where(Config.key == key))
    config = result.scalar_one_or_none()

    if config:
        config.value = data.value
    else:
        config = Config(
            key=key,
            value=data.value,
            description=None,
        )
        db.add(config)

    await db.flush()
    await db.refresh(config)

    return config


@router.get("/models")
async def list_available_models():
    """List available LLM models from all configured providers.

    Returns models from Ollama (if reachable), OpenAI, and Anthropic
    based on the current system configuration.
    """
    settings = get_settings()
    models = []

    # Ollama models
    if settings.ollama_base_url:
        try:
            response = httpx.get(
                f"{settings.ollama_base_url}/api/tags",
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                for model in data.get("models", []):
                    model_name = model.get("name", model.get("model", "unknown"))
                    models.append(ModelInfo(
                        id=f"ollama/{model_name}",
                        name=model_name,
                        provider="ollama",
                        description=f"Ollama model: {model_name}",
                        available=True,
                    ))
            else:
                models.append(ModelInfo(
                    id="ollama/unreachable",
                    name="Ollama (unreachable)",
                    provider="ollama",
                    description=f"Could not reach Ollama at {settings.ollama_base_url}",
                    available=False,
                ))
        except Exception as e:
            models.append(ModelInfo(
                id="ollama/unreachable",
                name="Ollama (unreachable)",
                provider="ollama",
                description=f"Ollama error: {str(e)}",
                available=False,
            ))

    # OpenAI models
    if settings.openai_api_key:
        openai_models = [
            ("gpt-4o", "GPT-4o - Most capable multimodal model"),
            ("gpt-4o-mini", "GPT-4o Mini - Fast and affordable"),
            ("gpt-4-turbo", "GPT-4 Turbo - Legacy high-capability"),
            ("gpt-3.5-turbo", "GPT-3.5 Turbo - Legacy fast model"),
        ]
        for model_id, desc in openai_models:
            models.append(ModelInfo(
                id=f"openai/{model_id}",
                name=model_id,
                provider="openai",
                description=desc,
                available=True,
            ))
    else:
        models.append(ModelInfo(
            id="openai/no-key",
            name="OpenAI (no API key)",
            provider="openai",
            description="Set OPENAI_API_KEY environment variable to enable",
            available=False,
        ))

    # Anthropic models
    if settings.anthropic_api_key:
        anthropic_models = [
            ("claude-sonnet-4-20250514", "Claude Sonnet 4 - Balanced capabilities"),
            ("claude-opus-4-20250514", "Claude Opus 4 - Most capable"),
            ("claude-haiku-4-20250514", "Claude Haiku 4 - Fast and efficient"),
        ]
        for model_id, desc in anthropic_models:
            models.append(ModelInfo(
                id=f"anthropic/{model_id}",
                name=model_id,
                provider="anthropic",
                description=desc,
                available=True,
            ))
    else:
        models.append(ModelInfo(
            id="anthropic/no-key",
            name="Anthropic (no API key)",
            provider="anthropic",
            description="Set ANTHROPIC_API_KEY environment variable to enable",
            available=False,
        ))

    # OpenRouter models
    if settings.openrouter_api_key:
        try:
            response = httpx.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                for model in data.get("data", []):
                    model_id = model.get("id", "unknown")
                    models.append(ModelInfo(
                        id=model_id,
                        name=model_id,
                        provider="openrouter",
                        description=model.get("description", f"OpenRouter: {model_id}"),
                        available=True,
                    ))
            else:
                # Fallback static list
                for model_id, desc in [
                    ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet via OpenRouter"),
                    ("openai/gpt-4o", "GPT-4o via OpenRouter"),
                    ("anthropic/claude-3-opus", "Claude 3 Opus via OpenRouter"),
                    ("meta-llama/llama-3.1-70b", "Llama 3.1 70B via OpenRouter"),
                    ("google/gemini-pro-1.5", "Gemini Pro 1.5 via OpenRouter"),
                ]:
                    models.append(ModelInfo(
                        id=model_id,
                        name=model_id,
                        provider="openrouter",
                        description=desc,
                        available=True,
                    ))
        except Exception:
            # Fallback static list
            for model_id, desc in [
                ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet via OpenRouter"),
                ("openai/gpt-4o", "GPT-4o via OpenRouter"),
                ("anthropic/claude-3-opus", "Claude 3 Opus via OpenRouter"),
                ("meta-llama/llama-3.1-70b", "Llama 3.1 70B via OpenRouter"),
                ("google/gemini-pro-1.5", "Gemini Pro 1.5 via OpenRouter"),
            ]:
                models.append(ModelInfo(
                    id=model_id,
                    name=model_id,
                    provider="openrouter",
                    description=desc,
                    available=True,
                ))
    else:
        models.append(ModelInfo(
            id="openrouter/no-key",
            name="OpenRouter (no API key)",
            provider="openrouter",
            description="Set OPENROUTER_API_KEY environment variable to enable",
            available=False,
        ))

    # Kimi Code models
    if settings.kimi_api_key:
        kimi_models = [
            ("kimi-for-coding", "Kimi Code - official model ID for third-party tools"),
        ]
        for model_id, desc in kimi_models:
            models.append(ModelInfo(
                id=model_id,
                name=model_id,
                provider="kimi",
                description=desc,
                available=True,
            ))
    else:
        models.append(ModelInfo(
            id="kimi/no-key",
            name="Kimi (no API key)",
            provider="kimi",
            description="Set KIMI_API_KEY environment variable to enable Kimi Code API",
            available=False,
        ))

    return {
        "models": models,
        "default_provider": settings.default_llm_provider,
        "default_model": settings.default_llm_model,
    }


@router.post("/test-model")
async def test_model_connection(
    provider: str,
    model: str,
):
    """Test connectivity to an LLM provider.

    Sends a simple ping request to verify the provider is reachable
    and the model is available.
    """
    settings = get_settings()

    if provider == "ollama":
        try:
            # Test with a simple generate request
            response = httpx.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": "Say 'pong' and nothing else.",
                    "stream": False,
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "provider": provider,
                    "model": model,
                    "status": "connected",
                    "response_preview": data.get("response", "")[:200],
                }
            else:
                return {
                    "provider": provider,
                    "model": model,
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text[:500]}",
                }
        except Exception as e:
            return {
                "provider": provider,
                "model": model,
                "status": "error",
                "error": str(e),
            }

    elif provider == "openai":
        if not settings.openai_api_key:
            return {
                "provider": provider,
                "model": model,
                "status": "error",
                "error": "OPENAI_API_KEY not set",
            }
        try:
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say 'pong'"}],
                    "max_tokens": 10,
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return {
                    "provider": provider,
                    "model": model,
                    "status": "connected",
                    "response_preview": content[:200],
                }
            else:
                return {
                    "provider": provider,
                    "model": model,
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text[:500]}",
                }
        except Exception as e:
            return {
                "provider": provider,
                "model": model,
                "status": "error",
                "error": str(e),
            }

    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            return {
                "provider": provider,
                "model": model,
                "status": "error",
                "error": "ANTHROPIC_API_KEY not set",
            }
        try:
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say 'pong'"}],
                    "max_tokens": 10,
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                data = response.json()
                content = data["content"][0]["text"]
                return {
                    "provider": provider,
                    "model": model,
                    "status": "connected",
                    "response_preview": content[:200],
                }
            else:
                return {
                    "provider": provider,
                    "model": model,
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text[:500]}",
                }
        except Exception as e:
            return {
                "provider": provider,
                "model": model,
                "status": "error",
                "error": str(e),
            }

    elif provider == "openrouter":
        if not settings.openrouter_api_key:
            return {
                "provider": provider,
                "model": model,
                "status": "error",
                "error": "OPENROUTER_API_KEY not set",
            }
        try:
            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "https://munger.local",
                    "X-Title": "Munger",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say 'pong'"}],
                    "max_tokens": 10,
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                from app.services.llm_service import extract_assistant_message_text

                data = response.json()
                message = data["choices"][0]["message"]
                content = extract_assistant_message_text(message)
                return {
                    "provider": provider,
                    "model": model,
                    "status": "connected",
                    "response_preview": (content or "(reasoning model returned no text)")[:200],
                }
            else:
                return {
                    "provider": provider,
                    "model": model,
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text[:500]}",
                }
        except Exception as e:
            return {
                "provider": provider,
                "model": model,
                "status": "error",
                "error": str(e),
            }

    elif provider == "kimi":
        if not settings.kimi_api_key:
            return {
                "provider": provider,
                "model": model,
                "status": "error",
                "error": "KIMI_API_KEY not set",
            }
        try:
            response = httpx.post(
                f"{settings.kimi_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.kimi_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say 'pong'"}],
                    "max_tokens": 10,
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return {
                    "provider": provider,
                    "model": model,
                    "status": "connected",
                    "response_preview": content[:200],
                }
            else:
                return {
                    "provider": provider,
                    "model": model,
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text[:500]}",
                }
        except Exception as e:
            return {
                "provider": provider,
                "model": model,
                "status": "error",
                "error": str(e),
            }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {provider}. Supported: ollama, openai, anthropic, openrouter, kimi",
        )
