"""Unit tests for MungerLLMChatModel adapter helpers."""

from app.runtime.harness.llm_adapter import _normalize_tool_calls
from app.services.llm_service import extract_assistant_message_text


class TestExtractAssistantMessageText:
    def test_reasoning_model_null_content(self):
        message = {
            "content": None,
            "reasoning": "The answer is 42.",
        }
        assert extract_assistant_message_text(message) == "The answer is 42."

    def test_standard_content(self):
        message = {"content": "hello"}
        assert extract_assistant_message_text(message) == "hello"


class TestNormalizeToolCalls:
    def test_parses_openai_tool_calls(self):
        raw = [
            {
                "id": "call_abc",
                "function": {"name": "extract_source_text", "arguments": '{"source_id": 7}'},
            }
        ]
        normalized = _normalize_tool_calls(raw)
        assert normalized[0]["name"] == "extract_source_text"
        assert normalized[0]["args"] == {"source_id": 7}
