/make-plan Redesign the LawCite TT Svelte frontend (`/Users/gregoryollivierre/GREG_V2/law-cite-tt/citation-tool/src/`). Current design failed audit at 19/30 with gaps concentrated in principles #3 (aesthetic), #4 (understandable), #8 (thorough), and #10 (as little design as possible) — none scored 0.

Verdict paragraph (quoted from 03-verdict.md):
> LawCite TT's dark-legal-tech shell is honest, unobtrusive, accessible (all contrast pairs pass AA, 3 ARIA landmarks, logical focus order), and lightweight (86.6KB JS, zero idle animation) — but it fails the "REFINE" bar on total score because the same handful of UI patterns (card containers, status badges, date formatting) were independently reimplemented 2-5 times each with small inconsistencies, the type/spacing scales were never locked to a modular system, and at least one real state (chapter-dropdown fetch failure) has no visible error UI at all. This isn't a broken product — nothing here fails a load-bearing principle (usefulness, understandability, and honesty all scored ≥1) — but the accumulation of unconsolidated duplication and inconsistency across nearly every surface pushes the total below the REFINE threshold.

Why redesign and not refine: total score (19/30) fell below the REFINE threshold of 20 due to compounding duplication/inconsistency across nearly every component, even though no single principle failed outright.

Preserve from current design (do not discard):
- Sidebar nav + route structure (App.svelte:47-81) — "Research" / "Cite" / "Chat" navigation model works and is accessible (3 ARIA landmarks, logical focus order).
- The 13-token dark palette in `:root` (App.svelte:97-114: `--bg #090d14`, `--surface #111823`, `--surface-raised #151e2a`, `--border #243040`, `--border-strong #354256`, `--text #f3f5f7`, `--text-soft #d7dde5`, `--muted #8190a5`, `--muted-strong #a8b3c3`, `--accent #22d3ee`, `--accent-text #061016`, `--positive #5eead4`, `--danger #fca5a5`, `--highlight`/`--highlight-text`) — all contrast pairs pass WCAG AA, keep the hues and roles as-is.
- The bundle-weight discipline (86.6KB JS gzip 30KB, zero idle animation) — do not introduce a component library or animation system that regresses this.
- The honest, jargon-light copy voice everywhere except the 3 flagged strings (see below) — do not add marketing language.

Discard (structural patterns causing the failures):
- Five independent card-container implementations under five different class names (StatsBar `.stat-tile`, ChapterBrowser `.chapter-card`, ResultCard `.result-card`, LookupPanel `details`, Cite `.result-card`). Evidence: Structural evidence, all five file:line locations captured in the audit. Caused failure on principle #10 and contributed to #3.
- Ad-hoc, unlocked type scale (10 distinct font-sizes, no modular ratio) and spacing scale (18 distinct values including non-round fractions like 7.04px). Evidence: Visual evidence, live-measured computed styles. Caused failure on principle #3.
- Two parallel status-badge systems for the same concept (ResultCard `.status` pill vs Cite `.state-card` variants) and a 3x-duplicated `displayDate()` function with a silent formatting inconsistency (Cite.svelte uses `month:"long"`, ResultCard/LookupPanel use `"short"`). Evidence: Structural evidence §3. Caused failure on principle #10.
- Explore.svelte's chapter-dropdown fetch-failure path, which only `console.error`s with no visible UI (Explore.svelte:29-30), unlike the parallel search-failure path in the same file (Explore.svelte:52-53) which does surface a visible error. Caused failure on principle #8.

Top 5 moves from the audit (verbatim):
1. #10/#3 — Consolidate the 5 card-container implementations into one shared `Card` component. Evidence: Structural evidence §3 (file:line list above).
2. #3 — Lock a modular type scale and spacing scale as CSS custom properties; fix the off-palette hardcode at `StatsBar.svelte:71` (`#f87171` → `var(--danger)`). Evidence: Visual evidence §1-3.
3. #8 — Add a visible error state to Explore's chapter-dropdown failure (Explore.svelte:29-30); standardize disabled-button treatment (load-more currently uniquely uses `cursor:wait;opacity:.65` vs every other control's `cursor:not-allowed;opacity:.4-.45`). Evidence: Visual evidence §5.
4. #4 — Rewrite 3 jargon strings: "materially different source row" (Cite.svelte:207-213) → "More than one version of this provision could match — review the options below"; "resolves in its source corpus" (Cite.svelte:322) → plain language; "Date unavailable" pill (ResultCard/LookupPanel) → "No effective date on file." Evidence: Copy & Honesty §4.
5. #10 — Extract the 3x-duplicated `displayDate()` into one shared utility (resolve the `month:"long"` vs `"short"` inconsistency deliberately); unify the two status-badge implementations into one. Evidence: Structural evidence §3.

Redesign principles in priority order:
1. #10 as little design as possible — one card primitive, one badge primitive, one date utility; every duplicated pattern in the audit gets a single source of truth.
2. #3 aesthetic — a locked modular type scale (pick a ratio, e.g. 1.25) and 8px-based spacing scale, applied everywhere, no ad-hoc values.
3. #8 thorough — every fetch path in every route gets a matching visible error/loading/empty state; disabled-state styling is one shared rule, not per-component.

Deliverables for the plan:
- Component inventory: exact target shape for a shared `Card`, `StatusBadge`, and `formatDate()` utility, with a migration list of every call site to update (StatsBar, ChapterBrowser, ResultCard, LookupPanel, Cite, Explore).
- Token spec: modular type scale + spacing scale definitions, replacing the ad-hoc values found in the audit.
- States checklist per route (Explore, Cite, Chat): confirm empty/loading/error/success/focus/disabled all present and visually consistent after the refactor.
- Copy fixes: the 3 jargon strings above, plus fixing Explore.svelte:112's hardcoded "533 chapters" to read from the live `/api/stats` call (honesty fix, principle #6).
- Small accessibility fix bundled in: `ChapterBrowser.svelte:24`'s `div role="button"` needs Space-key activation (currently Enter-only), and a skip link should be added to `App.svelte`.
- Regression check: re-verify all 11 contrast pairs from the audit still pass AA after any token changes, and re-confirm bundle size stays under 100KB gzip.

Non-goals for this redesign pass:
- Do not change the sidebar navigation model, route structure, or overall dark-legal-tech direction — these scored well and are explicitly preserved.
- Do not add a component library, icon set change, or animation system — the current lightweight footprint (86.6KB JS) is a strength to protect, not a gap to fill.
- Do not touch backend/API contracts — this is presentation-layer only.

Anti-patterns to guard against (specific to REDESIGN):
- Porting the old 5-implementation card pattern under new styling instead of actually consolidating to one component.
- Keeping both old and new badge/date-format code behind a flag indefinitely — this is a full cutover, not a parallel system.
- Redesigning the palette or nav structure just because it's a "redesign" — the Preserve list above is not optional.
