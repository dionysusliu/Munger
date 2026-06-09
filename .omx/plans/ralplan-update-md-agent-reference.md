# Ralplan: Agent Reference Documentation Update

**Source:** `.omc/specs/deep-dive-update-md-agent-reference.md`  
**Trace:** `.omc/specs/deep-dive-trace-update-md-agent-reference.md`  
**Status:** APPROVED v1 (consensus-lite — doc-only, low risk)

---

## RALPLAN-DR Summary

### Principles
1. **Router, not rewrite** — `AGENTS.md` tree points to `ARCHITECTURE.md`; don't duplicate system truth.
2. **Archive, don't erase** — `PLAN.md`/`SPEC.md` get headers only; bodies stay historical.
3. **Cursor-first** — optimize for auto-loaded root `AGENTS.md` + nested touchpoint maps.
4. **Trim, don't gut** — human READMEs keep quick-start; remove stale SQLite/workflow claims.
5. **Smoke-verify** — agent blind task proves docs route correctly.

### Decision Drivers
1. Agents inherit wrong mental model from discoverable stale docs
2. Only root `AGENTS.md` is auto-injected in Cursor
3. User scope excludes `.omx/` and archive body rewrites

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **A (chosen):** Layered AGENTS.md + README trim | Targeted, matches spec, low blast radius | Nested AGENTS.md may not auto-load |
| B: Rewrite PLAN/SPEC to current | Single source | User rejected; high churn |
| C: Only expand root AGENTS.md | Fastest | Misses area-specific touchpoints |

---

## Implementation Phases

### Phase 1 — AGENTS.md tree

| Step | Task |
|------|------|
| 1.1 | Expand root `AGENTS.md`: doc map, archive policy, ports, verify commands, nested pointers |
| 1.2 | Create `app/AGENTS.md`: routes, key files, dev/verify |
| 1.3 | Create `munger/AGENTS.md`: compose, Pigsty, ports, data mounts |
| 1.4 | Create `munger/backend/AGENTS.md`: runtime map, ingest path, skills, tests |

### Phase 2 — Archive + README hygiene

| Step | Task |
|------|------|
| 2.1 | Add archive banner to `PLAN.md`, `SPEC.md` (top only) |
| 2.2 | Create root `README.md` pointer stub |
| 2.3 | Replace `app/README.md` boilerplate |
| 2.4 | Banner + trim `munger/README.md` and `munger/backend/README.md` (SQLite, workflow API, wrong ports, Analysis UI) |

### Phase 3 — Skill clarity

| Step | Task |
|------|------|
| 3.1 | Update `WORKFLOW_ARCH.md`: active vs dormant skills table |
| 3.2 | Cross-check backend `AGENTS.md` matches |

### Phase 4 — Verification

| Step | Task |
|------|------|
| 4.1 | Grep: no SQLite/`/api/workflows` in AGENTS.md tree |
| 4.2 | Agent smoke: prompt fresh agent with AGENTS.md tree only — score ports, DB, skills, routes |

---

## Acceptance Criteria

- [ ] 4-file `AGENTS.md` tree complete
- [ ] Archive banners on PLAN/SPEC
- [ ] README trims done; root README exists
- [ ] WORKFLOW_ARCH marks 1 active + 3 legacy skills
- [ ] Agent smoke checklist passes

## ADR

| Field | Decision |
|-------|----------|
| **Decision** | Layered AGENTS.md router + README trim + WORKFLOW_ARCH skill labels |
| **Why** | Cursor auto-loads thin root doc; ARCHITECTURE.md not injected; stale root docs discoverable |
| **Consequences** | Agents must follow doc map to nested files; human READMEs shorter |
| **Follow-ups** | Optional `.omx/README.md`; CI doc lint |

## Execution Staffing

**Recommended:** `$ralph .omx/plans/ralplan-update-md-agent-reference.md`

| Lane | Agent | Scope |
|------|-------|-------|
| Docs | executor | Phases 1–3 |
| Verify | test-engineer | Phase 4 agent smoke |
