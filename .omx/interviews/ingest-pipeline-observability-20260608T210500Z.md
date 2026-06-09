# Deep Interview Transcript: ingest-pipeline-observability

**Profile:** Standard (threshold ≤20%)  
**Rounds:** 6  
**Final ambiguity:** 12%  
**Context:** `.omx/context/ingest-pipeline-observability-20260608T210000Z.md`

---

## Round 1 — Intent

**Q:** Primary audience and decision when ingest goes wrong?  
**A:** Operator UI — non-dev users see live progress and step outcomes on Ingest page.

## Round 2 — Outcome

**Q:** What should operators see during 9-tool pipeline run?  
**A:** Human step labels + progress + per-step outcomes (chunk count, entities found, glean added, wiki pages created).

## Round 3 — Scope

**Q:** Where to draw line on advanced tooling for v1?  
**A:** Design event schema now for future OpenTelemetry — don't wire OTel in v1.

## Round 4 — Non-goals

**Q:** What stays out of observability v1?  
**A:** No per-step LLM token/cost tracking.

## Round 5 — Constraints (pressure pass)

**Q:** How should live updates reach Ingest page? (Pressure: operators need plain-language labels, not raw JSON.)  
**A:** Keep 2s polling — enrich status API with `current_step`, `step_index`, `step_metrics`.

## Round 6 — Decision boundaries

**Q:** What may implementation decide without confirmation?  
**A:** All delegate — event schema, UI copy, OTel-ready naming, emit pattern.
