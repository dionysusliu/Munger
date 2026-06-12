# Ingest Latency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Cut per-window extraction latency ~3x and make slow/blocked provider calls die fast, so a small document ingests in low minutes and a stalled call never holds a step for more than ~60 s (user rule: 60 s without progress = kill).

**Diagnosis (measured, 2026-06-12):** one `chat_structured(ExtractionResult)` window = **54–56 s** across models (deepseek-v4-flash 56 s, qwen3-30b 54 s) with **10,369 chars** of JSON output ≈ 2.6k tokens ÷ ~50 tok/s — latency IS output length; model swap alone doesn't fix it. `EXTRACT_SYSTEM` (extraction_service.py:22) sets no description/entity budget. Provider 4xx (403 ToS seen live) burns instructor 3 retries + fallback 3 retries = 6 wasted calls per window. Instructor transport now bounded 120 s/1 retry (bench T2), but the user rule wants 60 s. Map concurrency default already 5 (config.py:61) — fine.

**Changes:**
1. **Output diet** (`extraction_service.EXTRACT_SYSTEM` + glean): descriptions "one short sentence (≤ 20 words)"; "only salient entities (typically ≤ 25 per chunk)"; relationship description ≤ 12 words. `max_tokens` 4096 → 2048 for extract (glean already 2048). Expected: ~10k → ~3-4k output chars ≈ 3x faster decode.
2. **Fast-fail on non-retryable provider errors** (`llm_service`): a 4xx other than 408/429 is deterministic — `chat_structured` must raise immediately: no instructor re-ask burn, no 3-attempt fallback loop. Implement: catch in `_chat_structured_instructor` (inspect `instructor` retry exception / openai `APIStatusError.status_code`) and re-raise as `LLMError` marked non-retryable; fallback loop in `chat_structured` breaks on the same condition.
3. **Structured-call timeout setting**: `LLM_STRUCTURED_TIMEOUT_S` (default **60**) replaces the hard-coded 120 in the instructor `transport_kwargs`; raw-provider clients keep 120 (chat/wiki paths have longer outputs).
4. **Extraction model override**: `LLM_EXTRACTION_MODEL` (default empty = use `LLM_DEFAULT_MODEL`); `extraction_service` passes `model=` to both extract and glean calls when set. A/B per env, no redeploy of code.

**Ground truth:** `EXTRACT_SYSTEM`/`_extract_chunk` at `app/services/extraction_service.py:22-68` (`max_tokens=4096`); instructor transport at `llm_service.py:~700` (`transport_kwargs = {"timeout": 120.0, "max_retries": 1}`); fallback loop `chat_structured` `llm_service.py:677-684`; settings style `app/core/config.py` (Field alias). Baseline **214 passed, 6 deselected**.

## Tasks
1. Output diet + `LLM_EXTRACTION_MODEL` + tests (prompt contains the budgets; model override reaches chat_structured kwargs; glean too).
2. Fast-fail + `LLM_STRUCTURED_TIMEOUT_S` + tests (403 → single attempt, LLMError raised, no fallback loop; 429 still retries; timeout setting lands in AsyncOpenAI kwargs).
3. Live validation (budgeted): one window probe (expect ≤ ~25 s), then full live bench under the 60s-no-progress/10min watchdog; if it completes, commit `tests/bench/baselines/baseline.json` (closes the bench T2 deferral). Reviewer pass, suite, STATUS/memory/mermaid-check, PR, self-merge.
