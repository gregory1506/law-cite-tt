# citation-tool Dark Legal-Tech Redesign

## Context

`citation-tool/` (the Svelte customer app, Phase 2F) currently uses a light theme with top-nav tabs (`App.svelte`). This spec covers a visual + layout modernization pass, chosen through a browser-based mockup comparison, before the next VPS deploy work resumes.

No frontend test suite exists (`package.json` has no test script) — this is a CSS/markup-only change with no logic changes, so verification is manual build + browser check.

## Goals

- Replace the light theme with a "dark legal-tech" visual system (dark navy/near-black background, cyan accent)
- Replace top-nav tabs with a persistent sidebar nav
- Apply the new visual system consistently across the app shell, the Explore tab (the only fully functional surface), and the Cite/Chat stub pages
- No functional/logic changes — same components, same data flow, same auth stub

## Out of scope

- The clickable Obsidian-style graph explorer (semantic-similarity graph over embeddings, or citation cross-reference graph) — flagged as a distinct feature with its own data/scope questions, deferred to a future spec
- Mobile-specific design iteration — a simple hamburger/top-bar fallback below ~768px is included as a reasonable default, not a fully designed mobile experience
- Any change to Cite/Chat functionality — they remain non-functional placeholders, restyled only

## Design

### 1. Visual system (CSS custom properties in `App.svelte`)

Replace the existing `:root` tokens:

| Token | Old (light) | New (dark legal-tech) |
|---|---|---|
| `--bg` | `#f8f9fa` | `#0a0e17` |
| `--surface` | `#ffffff` | `#111827` |
| `--border` | `#dee2e6` | `#1e293b` |
| `--text` | `#212529` | `#f1f5f9` |
| `--muted` | `#6c757d` | `#64748b` |
| `--accent` | `#1a3a5c` | `#22d3ee` |
| `--accent-light` | `#2b5f8a` | `#0e7490` (darker cyan for hover/border states) |
| `--highlight` | `#fff3cd` | `#22d3ee33` (cyan at low opacity, with `#67e8f9` text) |
| `--radius` | `8px` | `8px` (unchanged) |

Typography stays sans-serif (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` — unchanged font stack, only color tokens change).

### 2. App shell layout (`App.svelte`)

- Replace `.top-nav` (horizontal tab bar) with a fixed-width (180px) left sidebar containing:
  - App title/logo at top
  - Explore / Cite / Chat nav items stacked vertically; active item gets a cyan left-border (3px) and tinted background (`--surface`-on-`--bg` distinction)
  - Auth status ("Signed in (stub)") pinned to the bottom of the sidebar
- Main content area (`{#if tab === ...}` block) fills remaining width via flex layout; the routed components (`Explore.svelte`, `Cite.svelte`, `Chat.svelte`) are not restructured, only re-themed
- Login gate (`.login-gate`) restyled as a centered card on the dark background — no structural change, same stub `login()` behavior
- Responsive: below ~768px, sidebar collapses to a top bar with a hamburger toggle that reveals the nav items as a dropdown/overlay. This is a default fallback pattern, not separately mocked up.

### 3. Explore tab components

Re-theme only (no markup/logic changes) — each inherits the new CSS custom properties and gets dark-panel treatment matching the approved mockup:
- `StatsBar.svelte` — stat tiles as dark panels (`--surface` bg, `--border` outline) with cyan-accented numbers
- `SearchBar.svelte` — dark input field, mode indicator pill, cyan primary "Search" button
- `ResultCard.svelte` — dark panel, cyan left-border accent on top/highest-scoring result (or all results — implementation detail, matches mockup's single-accent-border-on-top-result pattern), keyword highlights using the new `--highlight` token
- `LookupPanel.svelte`, `ChapterBrowser.svelte` — same dark panel/border treatment for consistency

### 4. Cite / Chat stub pages

Centered "Coming soon" placeholder card, styled to match (dark panel, muted text), with the sidebar correctly highlighting whichever tab is active. No new functionality added.

## Testing / Verification

No automated frontend tests exist for this project. Verification plan:
1. `npm run build` succeeds with no errors/warnings
2. Manual browser check of all three tabs (Explore functional flow: search/lookup/browse; Cite/Chat stub placeholders) in both desktop and a narrow/mobile viewport
3. Deploy to the Cloudflare Worker (`law-cite-tt.gjo-ai.workers.dev`) and re-check live

## Future work (explicitly deferred)

- Clickable graph explorer over the citation corpus — recommended starting point is the semantic-similarity version (project existing 384-dim embeddings to 2D via UMAP/t-SNE, render with a force-directed graph library, click-to-traverse nearest neighbors via existing vector search) since it needs no new backend extraction work, unlike a true citation cross-reference graph which would require parsing `chunk_text` for citation patterns.
