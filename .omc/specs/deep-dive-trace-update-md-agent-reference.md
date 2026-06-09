# Deep Dive Trace: update-md-agent-reference

## Observed Result

User wants to update `*.md` files so future agents have reliable reference material. User adjusted scope: **focus doc hierarchy + coverage gaps**; keep `PLAN.md` / `SPEC.md` as archives (do not rewrite bodies).

## Ranked Hypotheses

| Rank | Hypothesis | Confidence | Evidence Strength | Why it leads |
|------|------------|------------|-------------------|--------------|
| 1 | Agent doc hierarchy missing — thin auto-loaded `AGENTS.md`, no nested docs, no read-order routing | High | Strong | Only root `AGENTS.md` is workspace-injected; no pointer to `ARCHITECTURE.md`; no `<!-- Parent: -->` tree |
| 2 | Coverage gaps hurt agents — ports, `munger_test`, active vs dormant skills, unwired routes, data boundaries | High | Strong | `ARCHITECTURE.md` correct but not in default surface; `munger/README.md` contradicts compose ports and workflow UX |
| 3 | Archive contamination — `PLAN.md`/`SPEC.md` stale but discoverable without labels | Medium–High | Moderate | Tier-2 contradictions with code proven; behavioral harm unmeasured |

## Evidence Summary by Hypothesis

### Hypothesis 1 — Hierarchy

- Root `AGENTS.md` ~30 lines: conventions only, no architecture, no doc map.
- Single `AGENTS.md` in repo; no `app/AGENTS.md`, `munger/AGENTS.md`, `munger/backend/AGENTS.md`.
- `ARCHITECTURE.md` (~292 lines) is canonical system truth but **not** auto-loaded.
- `.omx/` (30+ artifacts) and `.omc/` interleave with canonical paths in search with no disclaimer.
- `munger/README.md` duplicates long product docs with stale workflow DSL content.

### Hypothesis 2 — Coverage gaps

| Gap | Current truth | What agents may read instead |
|-----|---------------|------------------------------|
| Ports | Dev `:3000`, API `:18000`, Docker UI `:13000` | README `:3000` + `:8000` |
| Backend tests | `TEST_DATABASE_URL` → `munger_test` required | `AGENTS.md` says `pytest` only |
| Skills | 1 active (`default-ingest`); 3 legacy `{{step:}}` files | README lists 4 runnable workflows |
| Frontend routes | 4 wired (`/`, `/ingest`, `/wiki`, `/wiki/:slug`) | README Step 7 → Analysis page (unwired, mock data) |
| Wiki data | DB is source of truth; `munger/data/wiki/` is export | Agents may edit export files |
| Workflows path | Source: `munger/backend/data/workflows/` | Runtime mount `munger/data/` has no workflows |

### Hypothesis 3 — Archive contamination

- `PLAN.md`: SQLite, `workflows.py`, `test_workflows_api.py`, Phase 2 SQLite checkpointer — all removed/superseded.
- `SPEC.md`: SQLite dev, WebSocket, `/api/jobs`, workflow-centric ingest — contradicted by code.
- Neither file labeled archive; `SPEC.md` title reads as canonical specification.
- `ARCHITECTURE.md` explicitly documents out-of-scope items agents might wrongly assume from archives.

## Evidence Against / Missing Evidence

- `ARCHITECTURE.md` is strong when agents find it.
- `conftest.py` hard-blocks tests against production `munger` DB even if docs omit `munger_test`.
- `PLAN.md` partially current on LangGraph ingest direction.
- **No session evidence** yet that agents actually read stale docs first and implement wrong facts.

## Per-Lane Critical Unknowns

- **Lane 1 (hierarchy):** Do agents read stale docs and act on wrong facts in practice, or does code/`ARCHITECTURE.md` self-correct?
- **Lane 2 (coverage):** Which documentation surface do agents use on first turn — injected `AGENTS.md` only, or also `munger/README.md` / glob discovery?
- **Lane 3 (archive):** Do agents encounter `PLAN.md`/`SPEC.md` before `ARCHITECTURE.md` when answering architecture questions?

## Rebuttal Round

**Best rebuttal:** Agents read code; stale docs are harmless noise if `ARCHITECTURE.md` exists.

**Why leader held:** Workspace rules inject `AGENTS.md`, not `ARCHITECTURE.md`. Root `SPEC.md` title is high-salience false authority. Partial accuracy increases danger. Structural mis-routing is proven; behavioral rate is the open question.

## Convergence / Separation Notes

- Lanes 1 and 3 converge on **missing doc router at agent entry point**.
- Lane 2 adds **specific touchpoint content** the router must point to.
- `.omx`/`.omc` are session artifacts; `PLAN.md`/`SPEC.md` are worse because they look permanent.

## Most Likely Explanation

Munger has accurate architecture in `ARCHITECTURE.md`, but the **agent-facing doc system is flat and mis-routing**: thin auto-loaded `AGENTS.md`, no layered agent docs, stale root archives unlabeled, and operator READMEs contradicting compose/code. Fix is **hierarchy + routing + targeted coverage inserts**, not rewriting archive bodies or duplicating `ARCHITECTURE.md` into every file.

## Critical Unknown

**Target audience split:** Should agent docs optimize for Cursor auto-loaded rules only, or also OMX/deep-dive session artifacts (`.omx/`)? That choice drives whether `.omx` gets explicit “never canonical” policy in `AGENTS.md`.

## Recommended Discriminating Probe

Controlled blind task: agent given only `AGENTS.md` + `munger/README.md` (no `ARCHITECTURE.md`) — verify stack, run tests, identify active skill. Score wrong ports/DB/workflows. Repeat with doc map in `AGENTS.md` pointing to `ARCHITECTURE.md`.

## Proposed Doc Hierarchy (evidence-backed)

```
/AGENTS.md                 ← Router: canonical vs archive vs .omx (auto-loaded)
├── ARCHITECTURE.md        ← System truth (link, don't duplicate)
├── PLAN.md, SPEC.md       ← Archive headers only (user: no body rewrite)
├── .omx/, .omc/           ← Session artifacts — never source of truth
├── app/AGENTS.md          ← Frontend touchpoints, routes, dev :3000
└── munger/
    ├── AGENTS.md          ← Docker, compose, Pigsty, ports
    └── backend/AGENTS.md  ← pytest/munger_test, runtime/, API, skills
```
