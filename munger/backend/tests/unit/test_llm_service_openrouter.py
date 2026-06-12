"""Unit tests for OpenRouter LLM provider embedding and validation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.services.llm_service import (
    LLMError,
    LLMService,
    OpenRouterProvider,
    _validate_embedding_dimensions,
    validate_provider_settings,
)


class TestValidateEmbeddingDimensions:
    def test_exact_length_unchanged(self):
        vec = [0.5, 0.5, 0.5, 0.5]
        assert _validate_embedding_dimensions(vec, 4) == vec

    def test_rejects_wrong_length(self):
        with pytest.raises(LLMError, match="do not truncate"):
            _validate_embedding_dimensions([0.1] * 4096, 768)

    def test_rejects_shorter_vector(self):
        with pytest.raises(LLMError, match="expected 768"):
            _validate_embedding_dimensions([0.1, 0.2], 768)


class TestValidateProviderSettings:
    def test_rejects_ollama_embed_with_openrouter(self):
        settings = Settings.model_construct(
            default_llm_provider="openrouter",
            default_llm_model="deepseek/deepseek-v4-flash",
            embedding_model="nomic-embed-text",
            embedding_dimensions=768,
            openrouter_api_key="test-key",
        )
        with pytest.raises(LLMError, match="Ollama-only"):
            validate_provider_settings(settings)

    def test_rejects_unqualified_openrouter_embed_model(self):
        settings = Settings.model_construct(
            default_llm_provider="openrouter",
            default_llm_model="deepseek/deepseek-v4-flash",
            embedding_model="text-embedding-3-small",
            embedding_dimensions=768,
            openrouter_api_key="test-key",
        )
        with pytest.raises(LLMError, match="provider-qualified"):
            validate_provider_settings(settings)

    def test_accepts_openrouter_stack(self):
        settings = Settings(
            LLM_DEFAULT_PROVIDER="openrouter",
            LLM_DEFAULT_MODEL="deepseek/deepseek-v4-flash",
            LLM_EMBEDDING_MODEL="qwen/qwen3-embedding-8b",
            LLM_EMBEDDING_DIMENSIONS=768,
            OPENROUTER_API_KEY="test-key",
        )
        validate_provider_settings(settings)


class TestOpenRouterProviderEmbed:
    def test_embed_posts_dimensions_and_model(self):
        provider = OpenRouterProvider(
            api_key="test-key",
            model="deepseek/deepseek-v4-flash",
            embedding_model="qwen/qwen3-embedding-8b",
            embedding_dimensions=768,
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"embedding": [0.1] * 768}]}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        async def run():
            with patch.object(provider, "_get_client", return_value=mock_client):
                return await provider.embed(["hello world"])

        result = asyncio.run(run())

        assert len(result) == 1
        assert len(result[0]) == 768
        mock_client.post.assert_called_once()
        assert mock_client.post.call_args.args[0] == "/embeddings"
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["model"] == "qwen/qwen3-embedding-8b"
        assert payload["dimensions"] == 768
        assert payload["encoding_format"] == "float"
        assert payload["input"] == ["hello world"]

    def test_embed_rejects_wrong_dimension_response(self):
        provider = OpenRouterProvider(
            api_key="test-key",
            embedding_model="qwen/qwen3-embedding-8b",
            embedding_dimensions=768,
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"embedding": [1.0] * 4096}]}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        async def run():
            with patch.object(provider, "_get_client", return_value=mock_client):
                await provider.embed(["text"])

        with pytest.raises(LLMError, match="do not truncate"):
            asyncio.run(run())

    def test_embed_error_includes_model_name(self):
        provider = OpenRouterProvider(
            api_key="test-key",
            embedding_model="qwen/qwen3-embedding-8b",
            embedding_dimensions=768,
        )
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error":{"message":"bad model"}}'

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "error",
                request=MagicMock(),
                response=mock_response,
            )
        )

        async def run():
            with patch.object(provider, "_get_client", return_value=mock_client):
                await provider.embed(["text"])

        with pytest.raises(LLMError, match="qwen/qwen3-embedding-8b"):
            asyncio.run(run())


class TestOpenRouterProviderChat:
    def test_chat_uses_configured_model(self):
        provider = OpenRouterProvider(
            api_key="test-key",
            model="deepseek/deepseek-v4-flash",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        async def run():
            with patch.object(provider, "_get_client", return_value=mock_client):
                return await provider.chat([{"role": "user", "content": "hi"}])

        text = asyncio.run(run())

        assert text == "ok"
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["model"] == "deepseek/deepseek-v4-flash"


class TestLLMServiceOpenRouter:
    def test_init_rejects_ollama_embedding_with_openrouter(self):
        with pytest.raises(ValueError, match="Ollama-only"):
            Settings(
                LLM_DEFAULT_PROVIDER="openrouter",
                LLM_EMBEDDING_MODEL="nomic-embed-text",
                OPENROUTER_API_KEY="test-key",
            )

    def test_init_succeeds_with_openrouter_stack(self):
        settings = Settings(
            LLM_DEFAULT_PROVIDER="openrouter",
            LLM_DEFAULT_MODEL="deepseek/deepseek-v4-flash",
            LLM_EMBEDDING_MODEL="qwen/qwen3-embedding-8b",
            LLM_EMBEDDING_DIMENSIONS=768,
            OPENROUTER_API_KEY="test-key",
        )
        service = LLMService(settings)
        assert isinstance(service.provider, OpenRouterProvider)
        assert service.provider.model == "deepseek/deepseek-v4-flash"
        assert service.provider.embedding_model == "qwen/qwen3-embedding-8b"
        assert service.provider.embedding_dimensions == 768


class TestInstructorTransportBounds:
    """The instructor path must not inherit openai-python's 600 s default timeout.

    Regression for the live-bench stall: an extraction window's structured call
    sat in flight for many minutes because AsyncOpenAI was built without a
    timeout (600 s default, 2 internal retries). The client must be constructed
    with the same 120 s bound as the raw provider httpx clients and a single
    transport retry.
    """

    def test_instructor_client_bounded_transport(self, monkeypatch):
        import instructor
        import openai

        from pydantic import BaseModel

        captured: dict = {}
        real_async_openai = openai.AsyncOpenAI

        def capturing(*args, **kwargs):
            captured.update(kwargs)
            return real_async_openai(*args, **kwargs)

        class _StopBeforeNetwork(RuntimeError):
            pass

        def explode(client, mode):
            raise _StopBeforeNetwork("client construction captured")

        monkeypatch.setattr(openai, "AsyncOpenAI", capturing)
        monkeypatch.setattr(instructor, "from_openai", explode)

        settings = Settings(
            LLM_DEFAULT_PROVIDER="openrouter",
            LLM_DEFAULT_MODEL="deepseek/deepseek-v4-flash",
            LLM_EMBEDDING_MODEL="qwen/qwen3-embedding-8b",
            LLM_EMBEDDING_DIMENSIONS=768,
            OPENROUTER_API_KEY="test-key",
        )
        service = LLMService(settings)

        class _Out(BaseModel):
            answer: str

        with pytest.raises(_StopBeforeNetwork):
            asyncio.run(
                service._chat_structured_instructor(
                    [{"role": "user", "content": "hi"}], _Out
                )
            )

        assert captured["timeout"] == 120.0
        assert captured["max_retries"] == 1
