<!-- Parent: ../AGENTS.md -->

# Frontend Agent Guide (`app/`)

Read [`../ARCHITECTURE.md`](../ARCHITECTURE.md) for full system context. This file covers the React SPA only.

## Stack

React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui (`app/src/components/ui/`).

## Dev

```bash
cd app
npm install
npm run dev    # http://localhost:3000
```

API base URL: `VITE_BACKEND_BASE_URL` or default `http://localhost:18000` (`app/src/lib/api.ts`).

## Wired routes (`app/src/App.tsx`)

| Route | Page | Status |
|-------|------|--------|
| `/` | Dashboard | Wired |
| `/ingest` | Ingest | Wired — upload, trigger ingest, poll status/timeline |
| `/wiki` | WikiBrowser | Wired |
| `/wiki/:slug` | WikiPage | Wired — markdown renderer + wikilinks |

**Unwired** (files exist, not in router — do not implement unless asked):

`Search`, `Entities`, `Graph`, `Analysis`, `Settings`, `Logs`, `Home`

## Key files

| File | Purpose |
|------|---------|
| `src/App.tsx` | Route table |
| `src/lib/api.ts` | Backend client, types |
| `src/pages/WikiPage.tsx` | Frontmatter sidebar, slug map |
| `src/components/wiki/WikiMarkdown.tsx` | GFM, math, highlight, typography |
| `src/lib/remark-wikilink.ts` | `[[wikilink]]` AST plugin |
| `src/lib/frontmatter.ts` | YAML frontmatter splitter |
| `src/lib/wiki.ts` | Wiki API helpers, paginated slug map |
| `src/pages/Ingest.tsx` | Source upload + ingest polling |

## Wiki rendering pipeline

`WikiPage` → `splitFrontmatter()` → `WikiMarkdown` with:

- `remark-gfm`, `remark-math`, `remarkWikilink`
- `rehype-katex`, `rehype-highlight`
- `@tailwindcss/typography` (`prose` classes)

## Layout conventions

- Screens: `app/src/pages/`
- Shared layout: `app/src/components/`
- Utilities: `app/src/lib/`
- UI primitives: `app/src/components/ui/`

## Verify

```bash
npm run build
npm run lint
```
