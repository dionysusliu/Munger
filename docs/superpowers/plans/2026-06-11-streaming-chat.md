# Streaming Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Token-streamed chat answers. SSE event sequence per ask: `meta` (session_id, citations, bridge — retrieval finishes BEFORE generation starts) → `delta`* (answer text increments) → `done` (assistant_message_id, enables rating). Non-stream `POST /api/chat` stays untouched.

**Architecture:** `LLMProvider.chat_stream` (base = single-yield fallback wrapping `chat()`, so every provider works; OpenRouter overrides with real SSE via `httpx client.stream` + `aiter_lines`, `"stream": true`, `[DONE]` sentinel, `choices[0].delta.content`). `LLMService.chat_stream` passthrough. `ChatService.ask_stream` reuses `_autotitle/_history/_format_context/_persist`: retrieve+bridge sync → yield meta → accumulate deltas → persist once at end → yield done. API: `POST /api/chat/stream` returns `StreamingResponse` (`text/event-stream`, `data: {json}\n\n` frames). Frontend: `chatSendStream` (fetch + ReadableStream + SSE line parse) → streaming assistant bubble (citations/bridge render from meta immediately, text grows, rating enabled at done).

**Ground truth:** OpenRouterProvider.chat = httpx AsyncClient POST `/chat/completions` payload `{model, messages, temperature, max_tokens}` (llm_service.py ~213); `_get_client` 120s timeout. ScriptedLLMService needs a `chat_stream` (yield script in ≥2 pieces) for tests. Baseline **173 passed, 4 deselected**.

## Tasks
1. **Backend stream core** — provider base fallback + OpenRouter SSE override + `LLMService.chat_stream` + `ChatService.ask_stream` + ScriptedLLMService.chat_stream; tests: event sequence (meta→deltas→done), persisted content == concat(deltas), meta has citations, fallback path (provider without override) still streams one chunk, error mid-stream → no orphan persist (user msg not saved twice; document chosen failure semantics).
2. **SSE endpoint + frontend** — `POST /api/chat/stream` (StreamingResponse; keep `POST /api/chat` as-is); api.ts `chatSendStream(message, sessionId|undefined, onEvent)`; Chat.tsx streams into the assistant bubble (meta-first citations/bridge, done→message id→rating active, session list refresh at done, optimistic rollback on error). Tests: handler collects frames from a monkeypatched ask_stream; routes registered. Frontend build + lint (17 baseline).
3. **Review + ship** — reviewer (stream error paths, partial-stream persist semantics, SSE framing, frontend reader cancellation on unmount/switch), full suite, STATUS+memory, PR, auto-merge.
