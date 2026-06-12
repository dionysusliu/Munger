"""LLM service with multi-provider abstraction for OpenAI, Anthropic, Ollama, OpenRouter, and Kimi."""

import asyncio
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from app.core.config import OLLAMA_ONLY_EMBEDDING_MODELS, Settings
from app.observability.langsmith_setup import trace_llm

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when an LLM operation fails."""


def _non_retryable_status(exc: BaseException | None) -> int | None:
    """Walk an exception chain; return a deterministic 4xx status if present.

    408 (timeout) and 429 (rate limit) are transient and stay retryable.
    Covers openai-python errors (``.status_code``) and httpx errors chained
    behind ``LLMError`` (``.response.status_code``).
    """
    seen = 0
    cur = exc
    while cur is not None and seen < 10:
        status = getattr(cur, "status_code", None)
        if status is None:
            response = getattr(cur, "response", None)
            status = getattr(response, "status_code", None)
        if isinstance(status, int) and 400 <= status < 500 and status not in (408, 429):
            return status
        cur = cur.__cause__ or cur.__context__
        seen += 1
    return None


def extract_assistant_message_text(message: dict) -> str:
    """Extract assistant text from chat completion message payloads.

    Reasoning models (e.g. moonshotai/kimi-k2.5 via OpenRouter) may return
    `content: null` with text in `reasoning` or `reasoning_details`.
    """
    content = message.get("content")
    if content:
        return content

    reasoning = message.get("reasoning") or message.get("reasoning_content")
    if reasoning:
        return reasoning

    for item in message.get("reasoning_details") or []:
        if item.get("type") == "reasoning.text" and item.get("text"):
            return item["text"]

    return ""


def _validate_embedding_dimensions(vector: list[float], dimensions: int) -> list[float]:
    """Ensure the provider returned the requested dimension count (no client-side truncation)."""
    if len(vector) == dimensions:
        return vector
    raise LLMError(
        f"Embedding provider returned {len(vector)} dimensions, expected {dimensions}. "
        "Pass dimensions in the API request; do not truncate embeddings client-side."
    )


def validate_provider_settings(settings: Settings) -> None:
    """Reject known-bad provider + embedding model combinations."""
    provider = settings.default_llm_provider.lower()
    embed = settings.embedding_model.strip().lower()
    if provider == "openrouter":
        if embed in OLLAMA_ONLY_EMBEDDING_MODELS:
            raise LLMError(
                f"Embedding model '{settings.embedding_model}' is Ollama-only; "
                "set LLM_EMBEDDING_MODEL to an OpenRouter model (e.g. qwen/qwen3-embedding-8b)"
            )
        if "/" not in settings.embedding_model:
            raise LLMError(
                f"OpenRouter embedding models require a provider-qualified id "
                f"(e.g. qwen/qwen3-embedding-8b); got '{settings.embedding_model}'"
            )


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send a chat completion request and return the response text."""
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...

    @property
    @abstractmethod
    def max_tokens(self) -> int:
        """Return the maximum context token limit for this provider."""
        ...

    async def chat_stream(self, messages: list[dict], **kwargs):
        """Yield answer text increments. Base fallback: one chunk from chat()."""
        yield await self.chat(messages, **kwargs)

    def _truncate_text(self, text: str, max_chars: int = 10000) -> str:
        """Truncate text to fit within context limits."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n...[truncated]"


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (GPT-4, GPT-3.5, etc.)."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.embedding_model = embedding_model
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        self._max_tokens = 128000

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=120.0,
            )
        return self._client

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send chat completion request to OpenAI API."""
        client = self._get_client()
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
            raise LLMError(f"OpenAI API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise LLMError(f"OpenAI chat failed: {e}") from e

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using OpenAI embedding API."""
        client = self._get_client()
        payload = {
            "model": self.embedding_model,
            "input": texts,
        }
        try:
            response = await client.post("/embeddings", json=payload)
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI embedding error: {e.response.status_code} - {e.response.text}")
            raise LLMError(f"OpenAI embedding error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise LLMError(f"OpenAI embedding failed: {e}") from e

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class OpenRouterProvider(OpenAIProvider):
    """OpenRouter - unified API gateway supporting many models via OpenAI-compatible endpoint.

    Supports model IDs like "anthropic/claude-3.5-sonnet", "openai/gpt-4o", etc.
    See https://openrouter.ai/docs for full model list.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-3.5-sonnet",
        embedding_model: str = "openai/text-embedding-3-small",
        embedding_dimensions: int = 768,
        base_url: str = "https://openrouter.ai/api/v1",
        app_url: str = "https://munger.local",
        app_title: str = "Munger",
    ):
        # Call OpenAIProvider's init but override base_url
        super().__init__(
            api_key=api_key,
            model=model,
            embedding_model=embedding_model,
            base_url=base_url,
        )
        self.embedding_dimensions = embedding_dimensions
        self.app_url = app_url
        self.app_title = app_title
        self._max_tokens = 200000

    def _get_client(self) -> httpx.AsyncClient:
        """Override client to include OpenRouter-specific headers."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": self.app_url,
                    "X-Title": self.app_title,
                },
                timeout=120.0,
            )
        return self._client

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send chat completion via OpenRouter, handling reasoning-only responses."""
        client = self._get_client()
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            text = extract_assistant_message_text(message)
            if not text:
                logger.warning("OpenRouter returned empty assistant text for model %s", payload["model"])
            return text
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
            raise LLMError(f"OpenRouter API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"OpenRouter chat error: {e}")
            raise LLMError(f"OpenRouter chat failed: {e}") from e

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings via OpenRouter; request target dims from the API (MRL)."""
        if not texts:
            return []
        client = self._get_client()
        payload = {
            "model": self.embedding_model,
            "input": texts,
            "encoding_format": "float",
            "dimensions": self.embedding_dimensions,
        }
        try:
            response = await client.post("/embeddings", json=payload)
            response.raise_for_status()
            data = response.json()
            raw = [item["embedding"] for item in data["data"]]
            return [
                _validate_embedding_dimensions(vec, self.embedding_dimensions) for vec in raw
            ]
        except httpx.HTTPStatusError as e:
            logger.error(
                "OpenRouter embedding error (model=%s): %s - %s",
                self.embedding_model,
                e.response.status_code,
                e.response.text,
            )
            raise LLMError(
                f"OpenRouter embedding error (model={self.embedding_model}): "
                f"{e.response.status_code}"
            ) from e
        except LLMError:
            raise
        except Exception as e:
            logger.error("OpenRouter embedding error (model=%s): %s", self.embedding_model, e)
            raise LLMError(f"OpenRouter embedding failed (model={self.embedding_model}): {e}") from e


    async def chat_stream(self, messages: list[dict], **kwargs):
        """Stream chat completions from OpenRouter via SSE."""
        client = self._get_client()
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True,
        }
        try:
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    chunk = line[6:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        delta = json.loads(chunk)["choices"][0].get("delta", {}).get("content")
                    except (KeyError, IndexError, json.JSONDecodeError):
                        continue
                    if delta:
                        yield delta
        except httpx.HTTPStatusError as e:
            raise LLMError(f"OpenRouter stream error: {e.response.status_code}") from e


class KimiProvider(OpenAIProvider):
    """Kimi Code API provider using the OpenAI-compatible endpoint.

    Official Kimi Code docs specify:
    - Base URL: https://api.kimi.com/coding/v1
    - Model ID: kimi-for-coding
    """

    def __init__(
        self,
        api_key: str,
        model: str = "kimi-for-coding",
        embedding_model: str = "text-embedding-3-small",
        base_url: str = "https://api.kimi.com/coding/v1",
    ):
        super().__init__(
            api_key=api_key,
            model=model,
            embedding_model=embedding_model,
            base_url=base_url,
        )
        self._max_tokens = 200000

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send chat completion request to Kimi API, capturing reasoning_content if present."""
        client = self._get_client()
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            content = message.get("content", "")
            # Capture reasoning_content for K2 models
            reasoning = message.get("reasoning_content", "")
            if reasoning:
                logger.debug(f"Kimi reasoning_content captured: {reasoning[:200]}...")
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"Kimi API error: {e.response.status_code} - {e.response.text}")
            raise LLMError(f"Kimi API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Kimi chat error: {e}")
            raise LLMError(f"Kimi chat failed: {e}") from e

    async def chat_with_reasoning(self, messages: list[dict], **kwargs) -> dict:
        """Send chat request and return both content and reasoning_content."""
        client = self._get_client()
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            usage = data.get("usage", {})
            return {
                "content": message.get("content", ""),
                "reasoning_content": message.get("reasoning_content", ""),
                "usage": usage,
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Kimi API error: {e.response.status_code} - {e.response.text}")
            raise LLMError(f"Kimi API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Kimi chat error: {e}")
            raise LLMError(f"Kimi chat failed: {e}") from e

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Kimi does not provide embeddings - delegate to a fallback or raise."""
        logger.warning("Kimi does not support embeddings, returning zero vectors")
        return [[0.0] * 768 for _ in texts]


class AnthropicProvider(LLMProvider):
    """Anthropic API provider (Claude models)."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-sonnet-20240229",
        base_url: str = "https://api.anthropic.com/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        self._max_tokens = 200000

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                timeout=120.0,
            )
        return self._client

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send chat completion request to Anthropic API."""
        client = self._get_client()

        # Separate system message from conversation
        system_message = ""
        conversation_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                conversation_messages.append(msg)

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": conversation_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7),
        }
        if system_message:
            payload["system"] = system_message

        try:
            response = await client.post("/messages", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
            raise LLMError(f"Anthropic API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Anthropic chat error: {e}")
            raise LLMError(f"Anthropic chat failed: {e}") from e

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Anthropic does not provide embeddings - delegate to a fallback or raise."""
        # For now, return zero vectors as placeholder
        # In production, use OpenAI or a local embedding model as fallback
        logger.warning("Anthropic does not support embeddings, returning zero vectors")
        return [[0.0] * 768 for _ in texts]

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        embedding_model: str = "nomic-embed-text",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embedding_model = embedding_model
        self._client: Optional[httpx.AsyncClient] = None
        self._max_tokens = 8192

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=300.0,  # Longer timeout for local inference
            )
        return self._client

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send chat request to Ollama API."""
        client = self._get_client()
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_ctx": kwargs.get("num_ctx", 8192),
            },
        }
        try:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.status_code} - {e.response.text}")
            raise LLMError(f"Ollama API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise LLMError(f"Ollama chat failed: {e}") from e

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Ollama embedding API."""
        client = self._get_client()
        embeddings = []
        for text in texts:
            payload = {
                "model": self.embedding_model,
                "prompt": text,
            }
            try:
                response = await client.post("/api/embeddings", json=payload)
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])
            except httpx.HTTPStatusError as e:
                logger.error(f"Ollama embedding error: {e.response.status_code} - {e.response.text}")
                raise LLMError(f"Ollama embedding error: {e.response.status_code}") from e
            except Exception as e:
                logger.error(f"Ollama embedding error: {e}")
                raise LLMError(f"Ollama embedding failed: {e}") from e
        return embeddings

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class LLMService:
    """Unified LLM service that routes to the configured provider."""

    def __init__(self, settings: Settings):
        self.settings = settings
        validate_provider_settings(settings)
        self.provider = self._create_provider(settings)
        # Telemetry counters: incremented by chat(), _chat_structured_instructor(),
        # embed_texts(), and chat_stream().  chat_structured fallback calls chat()
        # so it is counted there; the instructor path is counted in
        # _chat_structured_instructor() to avoid double-counting.
        self.stats: dict[str, int] = {"calls": 0, "ms": 0}
        logger.info(
            "LLM service initialized: provider=%s chat_model=%s embedding_model=%s embedding_dims=%s",
            settings.default_llm_provider,
            settings.default_llm_model,
            settings.embedding_model,
            settings.embedding_dimensions,
        )

    def _create_provider(self, settings: Settings) -> LLMProvider:
        provider_name = settings.default_llm_provider.lower()
        validate_provider_settings(settings)

        if provider_name == "openai":
            if not settings.openai_api_key:
                raise LLMError("OpenAI API key not configured")
            return OpenAIProvider(
                api_key=settings.openai_api_key,
                model=settings.default_llm_model,
            )
        elif provider_name == "anthropic":
            if not settings.anthropic_api_key:
                raise LLMError("Anthropic API key not configured")
            return AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=settings.default_llm_model,
            )
        elif provider_name == "ollama":
            return OllamaProvider(
                base_url=settings.ollama_base_url,
                model=settings.default_llm_model,
                embedding_model=settings.embedding_model,
            )
        elif provider_name == "openrouter":
            if not settings.openrouter_api_key:
                raise LLMError("OpenRouter API key not configured")
            return OpenRouterProvider(
                api_key=settings.openrouter_api_key,
                model=settings.default_llm_model,
                embedding_model=settings.embedding_model,
                embedding_dimensions=settings.embedding_dimensions,
            )
        elif provider_name == "kimi":
            if not settings.kimi_api_key:
                raise LLMError("Kimi API key not configured")
            return KimiProvider(
                api_key=settings.kimi_api_key,
                model=settings.default_llm_model,
                base_url=settings.kimi_base_url,
                embedding_model=settings.embedding_model,
            )
        else:
            raise LLMError(f"Unknown LLM provider: {provider_name}")

    # ------------------------------------------------------------------
    # Core LLM operations
    # ------------------------------------------------------------------

    async def _bounded(self, coro, *, op: str):
        """Enforce a TOTAL wall-clock budget on a provider call.

        httpx/openai timeouts only bound gaps between bytes — a congested
        provider trickling a response never trips them (observed: one wiki-page
        chat call held a pipeline step for 15 minutes). Nothing is allowed to
        run long: every call gets a hard total-duration ceiling.
        """
        budget = self.settings.llm_call_timeout_s
        try:
            return await asyncio.wait_for(coro, timeout=budget)
        except asyncio.TimeoutError as exc:
            raise LLMError(f"{op} exceeded total budget of {budget:.0f}s") from exc

    @trace_llm(name="llm_chat", run_type="llm")
    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send a chat request to the configured provider.

        Primary telemetry point for all non-instructor chat calls (including the
        fallback path of chat_structured).  _chat_structured_instructor counts
        separately so calls are never double-counted.
        """
        t0 = time.perf_counter()
        result = await self._bounded(self.provider.chat(messages, **kwargs), op="chat")
        self.stats["calls"] += 1
        self.stats["ms"] += int((time.perf_counter() - t0) * 1000)
        return result

    async def chat_stream(self, messages: list[dict], **kwargs):
        """Stream chat increments from the configured provider.

        Counts one call; ms measured to stream completion.
        """
        t0 = time.perf_counter()
        try:
            async for piece in self.provider.chat_stream(messages, **kwargs):
                yield piece
        finally:
            self.stats["calls"] += 1
            self.stats["ms"] += int((time.perf_counter() - t0) * 1000)

    @trace_llm(name="llm_embed", run_type="embedding")
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []
        t0 = time.perf_counter()
        result = await self._bounded(self.provider.embed(texts), op="embed")
        self.stats["calls"] += 1
        self.stats["ms"] += int((time.perf_counter() - t0) * 1000)
        return result

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        embeddings = await self.embed_texts([text])
        return embeddings[0] if embeddings else []

    async def chat_structured(
        self,
        messages: list[dict],
        response_model: type,
        *,
        max_retries: int = 3,
        **kwargs,
    ):
        """Return a Pydantic model from LLM output with validation retries.

        Deterministic provider rejections (4xx other than 408/429) abort
        immediately — retrying a 403/404 burns calls and stalls pipeline steps
        without any chance of success.
        """
        if self.settings.ingest_instructor_enabled:
            try:
                return await self._chat_structured_instructor(
                    messages, response_model, max_retries=max_retries, **kwargs
                )
            except Exception as exc:
                status = _non_retryable_status(exc)
                if status is not None:
                    raise LLMError(
                        f"Structured chat aborted: non-retryable provider error {status}"
                    ) from exc
                logger.warning("Instructor structured chat failed, falling back: %s", exc)

        last_error: Exception | None = None
        for _ in range(max_retries):
            try:
                raw = await self.chat(messages, **kwargs)
                return response_model.model_validate(self._parse_json_object(raw))
            except Exception as exc:
                last_error = exc
                if _non_retryable_status(exc) is not None:
                    break
        raise LLMError(
            f"Structured chat failed after {max_retries} retries: {last_error}"
        ) from last_error

    async def _chat_structured_instructor(
        self,
        messages: list[dict],
        response_model: type,
        *,
        max_retries: int = 3,
        **kwargs,
    ):
        import instructor
        from openai import AsyncOpenAI

        provider = self.settings.default_llm_provider.lower()
        model = kwargs.get("model", self.settings.default_llm_model)
        # openai-python defaults to a 600 s timeout with 2 internal retries; an
        # unbounded structured call can stall a pipeline step for tens of
        # minutes. Bound every transport attempt (LLM_STRUCTURED_TIMEOUT_S,
        # default 60 s) and keep one transport retry — validation re-asks are
        # instructor's job, not the transport's.
        transport_kwargs = {
            "timeout": self.settings.llm_structured_timeout_s,
            "max_retries": 1,
        }
        if provider == "openai":
            if not self.settings.openai_api_key:
                raise LLMError("OpenAI API key not configured")
            client = instructor.from_openai(
                AsyncOpenAI(api_key=self.settings.openai_api_key, **transport_kwargs),
                mode=instructor.Mode.JSON,
            )
        elif provider == "ollama":
            client = instructor.from_openai(
                AsyncOpenAI(
                    base_url=f"{self.settings.ollama_base_url.rstrip('/')}/v1",
                    api_key="ollama",
                    **transport_kwargs,
                ),
                mode=instructor.Mode.JSON,
            )
        elif provider == "openrouter":
            if not self.settings.openrouter_api_key:
                raise LLMError("OpenRouter API key not configured")
            client = instructor.from_openai(
                AsyncOpenAI(
                    api_key=self.settings.openrouter_api_key,
                    base_url="https://openrouter.ai/api/v1",
                    **transport_kwargs,
                ),
                mode=instructor.Mode.JSON,
            )
        else:
            raise LLMError(f"Instructor unsupported for provider: {provider}")

        # Count here (instructor path bypasses self.chat(), so we track separately).
        # Total-duration ceiling on top of the per-attempt transport timeout:
        # the whole instructor exchange (validation re-asks included) gets
        # 2x the structured budget — a trickling response must not hold a
        # pipeline step open (nothing is allowed to run long).
        total_budget = 2 * self.settings.llm_structured_timeout_s
        t0 = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_model=response_model,
                    max_retries=max_retries,
                    temperature=kwargs.get("temperature", 0.2),
                    max_tokens=kwargs.get("max_tokens", 4096),
                ),
                timeout=total_budget,
            )
        except asyncio.TimeoutError as exc:
            raise LLMError(
                f"structured chat exceeded total budget of {total_budget:.0f}s"
            ) from exc
        self.stats["calls"] += 1
        self.stats["ms"] += int((time.perf_counter() - t0) * 1000)
        return result

    # ------------------------------------------------------------------
    # Munger-specific LLM operations
    # ------------------------------------------------------------------

    async def summarize(self, text: str, max_length: int = 1000) -> str:
        """Generate a concise summary of the given text."""
        truncated = self.provider._truncate_text(text, 12000)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a concise summarizer. Summarize the following text "
                    f"in no more than {max_length} characters. Capture the main ideas, "
                    "key claims, and important concepts. Use clear, structured language."
                ),
            },
            {"role": "user", "content": truncated},
        ]
        try:
            result = await self.chat(messages, max_tokens=2048)
            return result.strip()
        except LLMError:
            return ""

    async def extract_entities(self, text: str) -> list[dict]:
        """Extract named entities from text with types and descriptions."""
        truncated = self.provider._truncate_text(text, 10000)
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract named entities from the following text. "
                    "Return ONLY a JSON array of objects with this exact format:\n"
                    '[{"name": "Entity Name", "type": "person|concept|model|'
                    'mechanism|incentive_structure|book|paper|organization|'
                    'field|event|principle", "description": "Brief description"}]\n'
                    "Include only the most important and frequently mentioned entities. "
                    "Return ONLY the JSON array, no other text."
                ),
            },
            {"role": "user", "content": truncated},
        ]
        try:
            result = await self.chat(messages, max_tokens=4096, temperature=0.3)
            return self._parse_json_array(result)
        except LLMError:
            return []

    async def analyze_dimension(
        self, text: str, dimension: str, questions: list[str]
    ) -> dict:
        """Analyze text against a specific Munger dimension."""
        truncated = self.provider._truncate_text(text, 8000)
        questions_text = "\n".join(f"- {q}" for q in questions)
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are performing a Munger-style analysis on the dimension: '{dimension}'.\n"
                    "Answer the following questions based on the provided text.\n"
                    "Return ONLY a JSON object with this exact format:\n"
                    '{"analysis": "Your detailed analysis here", '
                    '"confidence": 0.85, '
                    '"key_insights": ["Insight 1", "Insight 2"]}\n'
                    f"Confidence should be a float between 0 and 1.\n"
                    f"Questions:\n{questions_text}"
                ),
            },
            {"role": "user", "content": truncated},
        ]
        try:
            result = await self.chat(messages, max_tokens=4096, temperature=0.5)
            return self._parse_json_object(result)
        except LLMError:
            return {"analysis": "", "confidence": 0.0, "key_insights": []}

    async def analyze_source(self, text: str, dimension: str) -> str:
        """Analyze source text from a specific analytical perspective."""
        truncated = self.provider._truncate_text(text, 10000)
        messages = [
            {
                "role": "system",
                "content": (
                    f"Analyze the following source text from the perspective of '{dimension}'.\n"
                    "Provide a thorough, structured analysis. Be concise but comprehensive."
                ),
            },
            {"role": "user", "content": truncated},
        ]
        try:
            return await self.chat(messages, max_tokens=4096)
        except LLMError:
            return ""

    async def generate_wiki_page(
        self, title: str, content: str, page_type: str = "summary"
    ) -> str:
        """Generate wiki page content from source material."""
        truncated = self.provider._truncate_text(content, 12000)
        type_prompts = {
            "summary": "Create a well-structured summary wiki page.",
            "entity": "Create a detailed entity wiki page with background, significance, and related concepts.",
            "concept": "Create a concept wiki page with definition, examples, and related mental models.",
            "model": "Create a mental model wiki page with explanation, examples, and applications.",
            "mechanism": "Create a mechanism wiki page explaining how it works with causal chains.",
            "incentive": "Create an incentive structure wiki page with stakeholder analysis.",
            "psychology": "Create a psychology wiki page about cognitive biases and mental patterns.",
            "analysis": "Create an analysis wiki page with structured reasoning.",
        }
        prompt = type_prompts.get(
            page_type, "Create a well-structured wiki page in markdown format."
        )
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a wiki editor. {prompt}\n"
                    "Use markdown formatting with headers, lists, and links.\n"
                    "Use [[Page Name]] syntax for internal wiki links where relevant.\n"
                    f"Title: {title}"
                ),
            },
            {"role": "user", "content": truncated},
        ]
        try:
            return await self.chat(messages, max_tokens=4096)
        except LLMError:
            return f"# {title}\n\n_(Content generation failed)_\n"

    async def suggest_links(
        self, page_content: str, all_pages: list[dict]
    ) -> list[dict]:
        """Suggest wiki links from page content to existing pages."""
        if not all_pages:
            return []

        pages_text = "\n".join(
            f"- {p['title']} (id: {p['id']}, type: {p.get('page_type', 'unknown')})"
            for p in all_pages[:50]  # Limit to avoid context overflow
        )
        truncated_content = self.provider._truncate_text(page_content, 5000)

        messages = [
            {
                "role": "system",
                "content": (
                    "Suggest relevant wiki links from the given page content to existing pages.\n"
                    "Return ONLY a JSON array of objects:\n"
                    '[{"to_page_id": 1, "link_type": "reference|contradicts|supports|relates", '
                    '"context": "Why this link is relevant"}]\n'
                    "Only suggest genuinely relevant connections. Return ONLY the JSON array."
                ),
            },
            {
                "role": "user",
                "content": f"Page content:\n{truncated_content}\n\nExisting pages:\n{pages_text}",
            },
        ]
        try:
            result = await self.chat(messages, max_tokens=2048, temperature=0.3)
            return self._parse_json_array(result)
        except LLMError:
            return []

    # ------------------------------------------------------------------
    # JSON parsing helpers
    # ------------------------------------------------------------------

    def _parse_json_array(self, text: str) -> list:
        """Extract and parse a JSON array from LLM response text."""
        text = text.strip()
        # Try to extract JSON from code blocks
        if "```" in text:
            match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        # Try to find array brackets
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON array from: {text[:200]}")
            return []

    def _parse_json_object(self, text: str) -> dict:
        """Extract and parse a JSON object from LLM response text."""
        text = text.strip()
        if "```" in text:
            match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON object from: {text[:200]}")
            return {"analysis": text, "confidence": 0.0, "key_insights": []}

    async def get_available_models(self) -> list[dict]:
        """Query all configured providers for available models.

        Returns a list of model dicts with id, name, provider, description, available.
        """
        models = []

        # Ollama models
        try:
            client = httpx.AsyncClient(timeout=5.0)
            response = await client.get(
                f"{self.settings.ollama_base_url}/api/tags"
            )
            if response.status_code == 200:
                data = response.json()
                for model in data.get("models", []):
                    model_name = model.get("name", model.get("model", "unknown"))
                    models.append({
                        "id": f"ollama/{model_name}",
                        "name": model_name,
                        "provider": "ollama",
                        "description": f"Ollama model: {model_name}",
                        "available": True,
                    })
            await client.aclose()
        except Exception as e:
            logger.debug(f"Could not fetch Ollama models: {e}")
            models.append({
                "id": "ollama/unreachable",
                "name": "Ollama (unreachable)",
                "provider": "ollama",
                "description": f"Ollama not reachable at {self.settings.ollama_base_url}",
                "available": False,
            })

        # OpenAI models
        if self.settings.openai_api_key:
            for model_id, desc in [
                ("gpt-4o", "GPT-4o - Most capable multimodal model"),
                ("gpt-4o-mini", "GPT-4o Mini - Fast and affordable"),
                ("gpt-4-turbo", "GPT-4 Turbo - Legacy high-capability"),
                ("gpt-3.5-turbo", "GPT-3.5 Turbo - Legacy fast model"),
            ]:
                models.append({
                    "id": f"openai/{model_id}",
                    "name": model_id,
                    "provider": "openai",
                    "description": desc,
                    "available": True,
                })
        else:
            models.append({
                "id": "openai/no-key",
                "name": "OpenAI (no API key)",
                "provider": "openai",
                "description": "Set OPENAI_API_KEY environment variable to enable",
                "available": False,
            })

        # Anthropic models
        if self.settings.anthropic_api_key:
            for model_id, desc in [
                ("claude-sonnet-4-20250514", "Claude Sonnet 4 - Balanced capabilities"),
                ("claude-opus-4-20250514", "Claude Opus 4 - Most capable"),
                ("claude-haiku-4-20250514", "Claude Haiku 4 - Fast and efficient"),
            ]:
                models.append({
                    "id": f"anthropic/{model_id}",
                    "name": model_id,
                    "provider": "anthropic",
                    "description": desc,
                    "available": True,
                })
        else:
            models.append({
                "id": "anthropic/no-key",
                "name": "Anthropic (no API key)",
                "provider": "anthropic",
                "description": "Set ANTHROPIC_API_KEY environment variable to enable",
                "available": False,
            })

        # OpenRouter models
        if self.settings.openrouter_api_key:
            try:
                client = httpx.AsyncClient(timeout=10.0)
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {self.settings.openrouter_api_key}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    for model in data.get("data", []):
                        model_id = model.get("id", "unknown")
                        models.append({
                            "id": model_id,
                            "name": model_id,
                            "provider": "openrouter",
                            "description": model.get("description", f"OpenRouter: {model_id}"),
                            "available": True,
                        })
                else:
                    # Fallback static list
                    for model_id, desc in [
                        ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet via OpenRouter"),
                        ("openai/gpt-4o", "GPT-4o via OpenRouter"),
                        ("anthropic/claude-3-opus", "Claude 3 Opus via OpenRouter"),
                        ("meta-llama/llama-3.1-70b", "Llama 3.1 70B via OpenRouter"),
                        ("google/gemini-pro-1.5", "Gemini Pro 1.5 via OpenRouter"),
                    ]:
                        models.append({
                            "id": model_id,
                            "name": model_id,
                            "provider": "openrouter",
                            "description": desc,
                            "available": True,
                        })
                await client.aclose()
            except Exception as e:
                logger.debug(f"Could not fetch OpenRouter models: {e}")
                # Fallback static list
                for model_id, desc in [
                    ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet via OpenRouter"),
                    ("openai/gpt-4o", "GPT-4o via OpenRouter"),
                    ("anthropic/claude-3-opus", "Claude 3 Opus via OpenRouter"),
                    ("meta-llama/llama-3.1-70b", "Llama 3.1 70B via OpenRouter"),
                    ("google/gemini-pro-1.5", "Gemini Pro 1.5 via OpenRouter"),
                ]:
                    models.append({
                        "id": model_id,
                        "name": model_id,
                        "provider": "openrouter",
                        "description": desc,
                        "available": True,
                    })
        else:
            models.append({
                "id": "openrouter/no-key",
                "name": "OpenRouter (no API key)",
                "provider": "openrouter",
                "description": "Set OPENROUTER_API_KEY environment variable to enable",
                "available": False,
            })

        # Kimi Code models
        if self.settings.kimi_api_key:
            for model_id, desc in [
                ("kimi-for-coding", "Kimi Code - official model ID for third-party tools"),
            ]:
                models.append({
                    "id": model_id,
                    "name": model_id,
                    "provider": "kimi",
                    "description": desc,
                    "available": True,
                })
        else:
            models.append({
                "id": "kimi/no-key",
                "name": "Kimi (no API key)",
                "provider": "kimi",
                "description": "Set KIMI_API_KEY environment variable to enable Kimi Code API",
                "available": False,
            })

        return models

    async def close(self):
        """Close the underlying provider connections."""
        await self.provider.close()
