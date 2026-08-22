# Evidence — LawCite TT Frontend

## Structural Evidence

1. **Interactive elements: 39 total.** App.svelte 6, StatsBar 0, VersionSelector 1, ResultCard 2, ChapterBrowser 2, LookupPanel 6, SearchBar 6, Cite.svelte 9, Explore.svelte 4, Chat.svelte 3.
2. **Max nesting depth: 4** — App → Explore → ResultCard → VersionSelector.
3. **Repeated patterns, same affordance in >1 place:**
   - "Official PDF" link: 4 occurrences (ResultCard:135, LookupPanel:132, Cite:258, Chat:102)
   - Chevron expand/collapse: 4 occurrences (ResultCard, LookupPanel x2, Explore)
   - Chapter input+datalist: 3 occurrences (SearchBar, LookupPanel, Cite)
   - "Available as at" date input: 3 occurrences (SearchBar, LookupPanel, Cite)
   - Loading/status text region: 5 occurrences, only 1 has an actual spinner (Chat)
   - **Status/authority badge: 2 separate implementations** of the same concept (ResultCard `.status` pill vs Cite `.state-card` variants)
   - **`displayDate()` duplicated 3x** with a subtle inconsistency (Cite uses `month:"long"`, others use `"short"`)
   - **Card/tile container: 5 occurrences, 5 different class names**, same visual pattern (StatsBar `.stat-tile`, ChapterBrowser `.chapter-card`, ResultCard `.result-card`, LookupPanel `details`, Cite `.result-card`)
4. **Dead code:** no unused imports/props found. One dead attribute: `Chat.svelte:93` has `key={source.id}` on a plain div inside a non-keyed `{#each}` — a no-op.

## Visual Evidence

1. **Spacing scale (MEASURED, live):** 18 distinct values from 1px–76px, including odd fractional values (7.04px, etc.) — not a clean modular scale.
2. **Type scale (MEASURED, live):** 10 distinct font-sizes (11.52px–24.8px), no clean ratio progression.
3. **Color count:** 12 unique computed values live; 13 named tokens in `:root` (App.svelte:97-114) + 1 undocumented off-palette hardcode (`StatsBar.svelte:71` `#f87171` instead of `var(--danger)` `#fca5a5`).
4. **Lowest contrast (primary text):** `--muted` (#8190a5) on `--surface-raised` = 5.17:1 — passes AA. Disabled-state text drops to ~1.9–2.7:1 (exempt from WCAG, but a thoroughness flag since disabled buttons still show readable-looking text).
5. **States checklist:** Empty PRESENT (Chat), Loading PRESENT (5 routes, INFERRED except Chat MEASURED), Error PRESENT (MEASURED live, but StatsBar's error path bypasses the design-token color, using a hardcoded off-palette red with no `role="alert"` — unlike every other error state which uses `role="alert"` + `var(--danger)`), Success PRESENT (INFERRED, backend was down), Focus PRESENT (`:focus-visible` outline in source across 6+ files), Disabled PRESENT (MEASURED, though Explore's load-more button uses a different disabled treatment — `cursor:wait; opacity:.65` — than every other disabled control's `cursor:not-allowed; opacity:.4-.45`).
   - **Gap found:** Explore.svelte's chapter-dropdown fetch failure only `console.error`s — no visible error UI, unlike the parallel search-failure path in the same file which does set a visible `error` state (Explore.svelte:29-30 vs 52-53).

## Copy & Honesty Evidence

1. Full string inventory collected across all 10 files (App, StatsBar, VersionSelector, ResultCard, ChapterBrowser, LookupPanel, SearchBar, Chat, Cite, Explore) — see subagent transcript for line-by-line list.
2. **One flagged inflation:** `Explore.svelte:112` — "533 chapters · historical versions included" is a hardcoded static claim in markup, not sourced from the live `/api/stats` call that `StatsBar.svelte` actually uses. No other superlatives/inflated claims found anywhere.
3. **No dark patterns found.** The "Sign in (stub)" flow is honestly labeled as a stub and doesn't disguise itself as real auth.
4. **Jargon flags:**
   - `Cite.svelte:207-213` "materially different source row" — DB jargon leaking to users. Plain replacement: "More than one version of this provision could match — review the options below."
   - `ResultCard.svelte:30` / `LookupPanel.svelte` "Date unavailable" pill — ambiguous (no date on file vs. fetch failure). Replacement: "No effective date on file."
   - `Cite.svelte:322` "LawCite confirms whether a reference resolves in its source corpus" — "resolves"/"source corpus" is library-science jargon for a legal-professional non-technical audience.
5. **No label→behavior mismatches** — every examined button/link's label matches its handler.

## Weight & Friction Evidence

1. **Initial JS: 88,689 bytes (86.6 KB)**, gzip 30.16 KB — well under the 100KB "3" threshold. CSS 28.3 KB separate.
2. **Network requests, primary view: 38 (dev-mode, unbundled)** — production build collapses to far fewer; one request failed (`/api/chapters` — backend down during measurement, not a frontend issue).
3. **TTI: ~80ms measured on localhost dev server** (not representative of real-network TTI, but structurally lightweight — no heavy hydration, no blocking third-party scripts).
4. **Idle-screen animation: 0.** Only animation is a `.spinner` (Chat.svelte:271) that's conditional on an active loading state, not idle. One 180ms one-shot sidebar-slide transition, not continuous.
5. **On-load notification/modal/badge: 0 by default.** 6 conditional `role="alert"` error banners exist across files, all gated on an error state — none shown by default, no modals/toasts.

## Accessibility Evidence

1. **Contrast: all 11 primary token pairs PASS WCAG AA**, worst case 5.17–6.0:1 range for muted text. One hardcoded off-palette `#f87171` in StatsBar not modeled against tokens (inconsistency flag, not a failure).
2. **Focus order** follows visual/DOM order: sidebar nav → tabs → search controls. Logical, no tabindex hacks except one.
3. **Keyboard reachability:** all controls are native `button`/`a`/`input`/`select`/`details` **except one** — `ChapterBrowser.svelte:24` uses `div role="button" tabindex="0"` with only `onkeydown` for Enter, **missing Space-key activation** (native button behavior not replicated).
4. **ARIA landmarks: 3** (aside/complementary, nav, main). No banner/contentinfo. Two `<header>` elements are nested inside `<main>` so expose no landmark role per HTML-AAM.
5. **No skip link** anywhere in the app.

## Known Gaps

- Backend API was unreachable during live testing, so Research/Explore success states and the full Cite "citation found" flow were audited from source (INFERRED) rather than measured live.
- Production-bundle network-request count wasn't separately measured (dev-mode module count reported instead; noted as such).
