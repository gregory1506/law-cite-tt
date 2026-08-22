# Scope Lock

**Audited surface:** citation-tool Svelte frontend (LawCite TT), running live at http://localhost:5183 (Vite dev server).
Source root: `/Users/gregoryollivierre/GREG_V2/law-cite-tt/citation-tool/src`

Components audited:
- `App.svelte` — shell / nav / login gate
- `components/StatsBar.svelte`
- `components/VersionSelector.svelte`
- `components/ResultCard.svelte`
- `components/ChapterBrowser.svelte`
- `components/LookupPanel.svelte`
- `components/SearchBar.svelte`
- `routes/Cite.svelte`
- `routes/Explore.svelte`
- `routes/Chat.svelte`

**Primary user:** Trinidad & Tobago legal professionals / researchers looking up statute citations and chapter numbers.

**Primary task:** Search for a case/statute citation or browse chapters, and get an accurate, verifiable citation quickly.

**Constraints:** Deployed as static site to Cloudflare Workers; backend is a separate VPS API proxied through Cloudflare Worker. Stack: Svelte 5 + Vite. Prior work log (memory) indicates a "Dark Legal-Tech" visual direction was chosen and partially implemented (App.svelte shell rewritten with dark token system, sidebar nav — commit 3705bc8, Jul 29 2026). This audit checks current shipped state, not the plan.

**Reference designs / competitors:** None supplied by user this session.

**Input materials:** Live running app (localhost:5183) + source files.
