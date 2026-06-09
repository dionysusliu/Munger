# Deep Interview Transcript: Wiki MD + Backend Cleanup

**Date:** 2026-06-09  
**Profile:** Standard | **Final ambiguity:** ~14%

## Round 1 — Intent

**Q:** Primary reason for wiki formatting + backend cleanup?  
**A:** Both equally — ship together in one pass.

## Round 2 — Non-goals (user expanded)

**Q:** What is out of scope?  
**A:** No retention of old logic. If DB is fully on Postgres, delete SQLite and workflow code. Frontend stack:
- react-markdown or unified/remark/rehype
- remark-gfm, remark-math + rehype-katex, rehype-highlight/shiki, gray-matter
- Custom remark plugins for [[wikilink]], #tag, ![[embed]]

## Round 3 — Decision Boundaries

**Q:** What can OMX decide without asking?  
**A:** *(skipped)*

## Round 4 — Scope pressure pass

**Q:** What should #tag and ![[embed]] do this pass?  
**A:** Wikilink only — skip #tag and ![[embed]].

## Round 5 — Success Criteria

**Q:** How to judge done?  
**A:** Polished sample wiki page + pytest/build green with zero workflow/SQLite references + Alembic migration drops workflow tables.

## Crystallized Spec

→ `.omx/specs/deep-interview-wiki-md-backend-cleanup.md`
