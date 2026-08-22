# Implementation Plan — LawCite TT Design-System Consolidation Redesign

Source: `DESIGN-IS-2026-08-21/04-handoff-prompt.md` (Dieter Rams audit, 19/30, verdict REDESIGN).
Scope: `/Users/gregoryollivierre/GREG_V2/law-cite-tt/citation-tool/src/`.

## Phase 0: Documentation Discovery (facts gathered by direct read, not invented)

**Stack confirmed:** Svelte 5 (runes: `$state`, `$props`, `$derived`, no `$effect` currently used), Vite 8, Vitest 4 + `@testing-library/svelte` 5. No TypeScript — plain `.svelte`/`.js`.

**Conventions to copy, not invent:**
- Props: `let { item, query = "", historicalDate = "" } = $props();` (ResultCard.svelte:13) — destructured with defaults, never `export let`.
- Reactive derived values: `const x = $derived(...)` (ResultCard.svelte:19-39).
- Icons: `import { IconName } from "@lucide/svelte"` then `<IconName size={N} aria-hidden="true" />` — every icon in the app follows this exact import/usage shape (verified across App, ResultCard, Cite, LookupPanel, Explore, Chat).
- Styles: every component/route has its own scoped `<style>` block reading CSS custom properties defined once in `App.svelte:96-115` (`:global(:root) { --bg, --surface, --surface-raised, --border, --border-strong, --text, --text-soft, --muted, --muted-strong, --accent, --accent-hover, --accent-strong, --accent-text, --positive, --danger, --highlight, --highlight-text, --radius }`). No component currently imports a separate CSS/token file — tokens are global via `:global(:root)`.
- Focus rings: `input:focus-visible, button:focus-visible, a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px/3px; }` repeated per-component (Cite.svelte:392, ResultCard.svelte:265-269, Explore.svelte:229) — this is a literal copy-paste block, a 6th duplication not caught in the original audit; fold it into the shared layer in Phase 1.
- `lib/` exports actually available — **do not invent methods beyond these**:
  - `lib/api.js`: `getStats`, `getChapters`, `searchGrouped`, `lookupSection`, `resolveCitation`, `resolveUrl` (exact names confirmed via imports in StatsBar, Cite, LookupPanel, Explore, ResultCard).
  - `lib/auth.js`: `isAuthenticated`, `setToken` (App.svelte:3).
  - `lib/text.js`: `queryTerms`, `excerptAroundQuery`, `highlightSegments` — has its own `text.test.js`. This is the precedent for where new shared utilities belong: **plain exported functions in `src/lib/`, colocated `.test.js` file, no framework**.
- Tests: colocated `ComponentName.test.js` next to the component, using `render`/`screen`/`fireEvent` from `@testing-library/svelte` and `describe/it/expect` from `vitest` (see `ResultCard.test.js`, `App.test.js`, `SearchBar.test.js`, `Chat.test.js`, `Cite.test.js`). New shared components need the same colocated pattern.
- No existing `src/components/ui/` or shared-primitives folder. This plan creates one: `src/components/ui/`.

**Anti-patterns to avoid:**
- Do not introduce `export let` (Svelte 4 syntax) — this codebase is 100% Svelte 5 runes.
- Do not add a CSS-in-JS or Tailwind layer — the existing pattern is scoped `<style>` + global CSS vars; stay in that lane per the non-goals (no component library).
- Do not create new top-level dependencies — `package.json` only has `@lucide/svelte` as a runtime dependency; the redesign must ship with zero new dependencies (protects the 86.6KB budget).

**One additional live bug found during discovery (fold into Phase 1):** `ChapterBrowser.svelte:51` references `var(--accent-light)`, a token that does not exist anywhere in `:root` (App.svelte:96-115 has no `--accent-light`) — this hover style is currently a silent no-op. Fix while touching this file.

---

## Phase 1: Design tokens — lock the type/spacing scale, fix stray hardcodes

**What to implement:**
1. In `App.svelte`'s `:global(:root)` block (lines 96-115), add two new token groups without touching the 13 existing color tokens (Preserve list):
   ```css
   /* Spacing scale — 8px base, replaces 18 ad-hoc values found in audit */
   --space-1: 4px;
   --space-2: 8px;
   --space-3: 12px;
   --space-4: 16px;
   --space-5: 20px;
   --space-6: 24px;
   --space-7: 32px;
   --space-8: 48px;

   /* Type scale — 1.25 modular ratio off a 16px base, replaces 10 ad-hoc font-sizes */
   --text-xs: 0.72rem;   /* 11.52px */
   --text-sm: 0.82rem;   /* 13.1px  */
   --text-base: 1rem;    /* 16px    */
   --text-md: 1.15rem;   /* 18.4px  */
   --text-lg: 1.56rem;   /* 25px    */
   --text-xl: 2rem;      /* 32px    */
   ```
2. Fix `StatsBar.svelte:71` — replace `.error { color: #f87171; }` with `.error { color: var(--danger); }`.
3. Fix `ChapterBrowser.svelte:51` — replace `var(--accent-light)` with `var(--accent)` (the only token that makes semantic sense here; `--accent-hover`/`--accent-strong` are both aliased to the same hex already).
4. Do not do a full find-and-replace of every spacing/font-size value across all 10 files in this phase — that migration happens component-by-component in Phase 2 as each component is touched anyway. Phase 1 only lands the token definitions and the two isolated hardcode fixes so they're available for Phase 2.

**Documentation references:** App.svelte:96-115 (existing token block, copy its structure exactly — flat custom properties, no nesting, no calc()).

**Verification checklist:**
- `grep -n "#f87171" src/components/StatsBar.svelte` returns nothing.
- `grep -n "accent-light" src/components/ChapterBrowser.svelte` returns nothing.
- `npm run dev` — app still renders, StatsBar error state (simulate by stopping backend) shows the same red as every other error banner.
- `npm run test` passes unchanged (no test currently asserts on these exact colors).

**Anti-pattern guards:** Do not remove or rename the 13 existing color tokens (`--bg`, `--surface`, etc.) — they're on the Preserve list and 11 contrast pairs were verified against their current hex values in the audit. Do not add a `rem` vs `px` mix — the existing tokens use hex for color, this plan uses `rem` for type and `px` for spacing to match what's already dominant in each category (spacing values in the audit were measured in px; font-sizes were mixed but existing component styles mostly already use `rem` for font-size, e.g. Cite.svelte:341 `font-size: clamp(1.6rem, 3vw, 2.15rem)`).

---

## Phase 2: Shared `Card` primitive — consolidate 5 duplicate implementations

**What to implement:**
Create `src/components/ui/Card.svelte`:
```svelte
<script>
  let { children, padded = true, class: className = "" } = $props();
</script>

<div class="card {className}" class:padded>
  {@render children?.()}
</div>

<style>
  .card {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
  }
  .card.padded { padding: var(--space-5) var(--space-6); }
</style>
```
This is a copy of the shared shell already common to all 5 duplicates (`border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface);` — verified identical across StatsBar.svelte:50-52, ChapterBrowser.svelte:41-43, ResultCard.svelte:160-163, LookupPanel.svelte:233-236 (on `details`), Cite.svelte:436-438). Padding varies per use site, hence the `padded` prop + `class` passthrough for per-instance overrides (e.g. StatsBar's tighter `12px 18px`).

Migrate each of the 5 call sites to wrap in `<Card>` instead of a locally-styled `<div>`/`<article>`/`<details>`:
- `StatsBar.svelte` — each `.stat-tile` becomes `<Card padded class="stat-tile">`, keep the `.stat-tile` local class only for the label/value layout, delete the border/background/radius rules from its local `<style>`.
- `ChapterBrowser.svelte` — `.chapter-card` becomes `<Card padded class="chapter-card">` (note: this div is also the `role="button"` — see Phase 4 for the keyboard fix, apply both changes together to this file).
- `ResultCard.svelte` — the outer `<article class="result-card">` becomes `<Card padded class="result-card">` wrapping the same children.
- `LookupPanel.svelte` — the `<details>` element cannot become a `<Card>` (semantic HTML requirement for native disclosure behavior) — leave `<details>` as-is but replace its 3 duplicated border/background/radius CSS lines with `border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface);` unchanged (already correct) — **note in the PR that `details` is an intentional exception to the Card consolidation**, not a miss.
- `Cite.svelte` — both `.state-card` and the result `.result-card` wrap in `<Card>`; `.state-card` additionally needs its `border-left-width: 3px` accent stripe, which is not part of the base Card — add it as a local override via the `class` passthrough, not by adding a variant prop to `Card` itself (keeps `Card` minimal per principle #10).

**Documentation references:** Svelte 5 snippet/children syntax — confirm `{@render children?.()}` is the Svelte 5 idiom (this codebase doesn't yet use slots/snippets anywhere, so this is genuinely new syntax for this codebase; verify against the installed `svelte` version's docs before writing, since `^5.56.4` uses runes-mode snippets, not the legacy `<slot>`).

**Verification checklist:**
- `grep -rn "border: 1px solid var(--border);\s*$" src/components/ src/routes/` before/after — count of duplicate border declarations should drop from 5 to 1 (inside `Card.svelte`) plus the intentional `details` exception.
- New `src/components/ui/Card.test.js`: renders children, applies `padded` class conditionally, accepts a passthrough `class`.
- Existing `ResultCard.test.js` and `Cite.test.js` still pass unmodified (Card is a structural wrapper, doesn't change rendered text/roles).
- Visual check via dev server: StatsBar tiles, chapter cards, result cards, and Cite's state-cards render with identical visual appearance to before (no regression screenshot diff needed, but eyeball each of the 3 routes).

**Anti-pattern guards:** Do not add a `variant` prop with hardcoded style branches inside `Card` for the state-card accent stripe or the stat-tile padding — those are call-site concerns, keep `Card` to border/radius/background/padding only, per principle #10 ("as little design as possible") and the explicit anti-pattern "adding new abstractions where a direct change suffices." Do not delete `LookupPanel`'s `<details>` semantics to force it into `<Card>` — native disclosure behavior is a functional requirement, not decoration.

---

## Phase 3: Shared `StatusBadge` primitive + `formatDate` utility

**What to implement:**

1. `src/lib/date.js` (new file, following the `lib/text.js` precedent — plain exported function, no framework):
   ```js
   export function formatDate(value, { fallback = "Date unavailable", month = "short" } = {}) {
     if (!value) return fallback;
     return new Intl.DateTimeFormat("en-TT", {
       year: "numeric",
       month,
       day: "numeric",
       timeZone: "UTC",
     }).format(new Date(`${value}T00:00:00Z`));
   }
   ```
   This replaces the 3 duplicated `displayDate()` functions (ResultCard.svelte:71-79 uses `month:"short"`, no fallback text; LookupPanel.svelte:49-57 uses `month:"short"`, fallback `"Date unavailable"`; Cite.svelte:81-89 uses `month:"long"`, fallback `"Date unavailable"`). Per the audit's move #5, this inconsistency must be resolved *deliberately*: keep `month:"short"` as the default (2 of 3 call sites already use it) and let Cite.svelte opt into `month: "long"` explicitly via the options param — Cite's provision-detail view benefits from the fuller date, the compact list views (ResultCard, LookupPanel) don't need it.
   Add `src/lib/date.test.js` colocated, following `text.test.js`'s structure — assert both the short/long month paths and the fallback path.

2. Update the 3 call sites to `import { formatDate } from "../lib/date.js"` and delete their local `displayDate()` functions:
   - `ResultCard.svelte:71-79` → delete, replace call sites `displayDate(x)` with `formatDate(x)`.
   - `LookupPanel.svelte:49-57` → delete, replace with `formatDate(x)`.
   - `Cite.svelte:81-89` → delete, replace with `formatDate(x, { month: "long" })`.

3. `src/components/ui/StatusBadge.svelte` (new), consolidating ResultCard's `.status` pill and Cite's `.state-card` icon+text pattern *only where they represent the same concept* — re-examine the audit's finding here: ResultCard's badge is a compact inline pill (`Latest available` / `Historical version` / date), while Cite's `.state-card` is a full-width icon+heading+description block for validate-flow states (waiting/error/not-found/ambiguous/found). These are NOT the same component despite both audit findings calling them "status/authority badges" — forcing them into one component would violate principle #10 the other direction (over-abstracting two genuinely different UI needs into one over-flexible component). **Resolution:** keep them as two distinct primitives, but extract only the truly shared part — the compact pill — into `StatusBadge.svelte`, and leave Cite's `.state-card` as a route-local pattern (it's already only used once, inside Cite.svelte, so there's nothing to consolidate there structurally; its inconsistency with ResultCard was a naming/vocabulary overlap, not duplicated code).
   ```svelte
   <script>
     let { children, tone = "neutral" } = $props();
   </script>
   <span class="badge tone-{tone}">{@render children?.()}</span>
   <style>
     .badge {
       padding: 4px 8px;
       border: 1px solid var(--border-strong);
       border-radius: 999px;
       color: var(--muted-strong);
       font-size: var(--text-xs);
       font-weight: 700;
     }
     .badge.tone-positive {
       border-color: rgba(45, 212, 191, 0.45);
       background: rgba(45, 212, 191, 0.1);
       color: var(--positive);
     }
   </style>
   ```
   Migrate `ResultCard.svelte:91` (`<span class:latest={isLatest} class="status">`) to `<StatusBadge tone={isLatest ? "positive" : "neutral"}>{authorityLabel}</StatusBadge>`, deleting the local `.status`/`.status.latest` CSS.

**Documentation references:** `src/lib/text.js` + `src/lib/text.test.js` (exact precedent for the new `date.js`/`date.test.js` pair — same file shape, same test framework).

**Verification checklist:**
- `grep -rn "function displayDate" src/` returns zero matches (all 3 deleted).
- `grep -rn "Intl.DateTimeFormat" src/` returns exactly 1 match (inside `lib/date.js`).
- `npm run test` — new `date.test.js` passes; existing `ResultCard.test.js` (asserts `screen.getByText("Latest available")`) still passes since `formatDate`'s default fallback text is unchanged.
- Dev-server check: ResultCard's date display and Cite's date display look identical to before (short vs long month preserved per the original per-file behavior, now explicit instead of accidental).

**Anti-pattern guards:** Do not force Cite's `.state-card` into `StatusBadge` — re-read the actual UI, not just the audit's label, before abstracting; a wrong merge here would be "restyling areas that already scored 3" energy applied to structure instead of style. Do not silently pick one of `month:"short"`/`month:"long"` and drop the other — the plan must preserve both behaviors via an explicit param, since Cite's fuller date is intentional for its use case (a legal citation detail view).

---

## Phase 4: Thoroughness fixes — missing/rough states, accessibility, disabled-button consistency

**What to implement:**
1. `Explore.svelte:26-32` — the chapter-load `onMount` currently only `console.error`s on failure:
   ```js
   onMount(async () => {
     try {
       chapters = await getChapters();
     } catch (loadError) {
       console.error("Failed to load chapters", loadError);
     }
   });
   ```
   Add a visible error signal, mirroring the existing `error` state pattern already used for search failures in the same file (Explore.svelte:52-53 `catch (searchError) { error = searchError.message; }`):
   ```js
   let chapterLoadError = $state("");
   onMount(async () => {
     try {
       chapters = await getChapters();
     } catch (loadError) {
       chapterLoadError = loadError.message;
     }
   });
   ```
   Render it near the chapter-dependent controls (SearchBar's chapter filter, LookupPanel, ChapterBrowser all consume `chapters`) — add one small inline notice below the tab bar: `{#if chapterLoadError}<p class="chapter-load-error" role="alert">Chapter list unavailable: {chapterLoadError}</p>{/if}`, styled with `color: var(--danger); font-size: var(--text-xs);` to match every other error text in the file.

2. Standardize disabled-button styling — `Explore.svelte:267` currently uses `cursor: wait; opacity: 0.65;` uniquely for `.load-more:disabled`, diverging from every other disabled control's `cursor: not-allowed; opacity: 0.45;` (Cite.svelte:410, SearchBar.svelte, LookupPanel.svelte:206, Chat.svelte:326). Load-more's disabled state only fires during an active fetch (not a validation gate like the others), so `cursor: wait` is semantically more correct — **keep `cursor: wait` but align the opacity to `0.45`** for visual consistency: `.load-more:disabled { cursor: wait; opacity: 0.45; }`.

3. `ChapterBrowser.svelte:24-25` — add Space-key activation to match native `<button>` behavior, since this div is exposed as `role="button" tabindex="0"`:
   ```svelte
   <div
     class="chapter-card"
     onclick={() => onSelect(c.chapter)}
     role="button"
     tabindex="0"
     onkeydown={(e) => {
       if (e.key === "Enter" || e.key === " ") {
         e.preventDefault();
         onSelect(c.chapter);
       }
     }}
   >
   ```
   (`e.preventDefault()` on Space is required to stop the page from scrolling, matching native button behavior.)

4. Add a skip link to `App.svelte`, matching the existing sidebar/main structure:
   ```svelte
   <a href="#main-content" class="skip-link">Skip to content</a>
   ```
   placed as the first child inside the `{:else}` branch (after auth), with `<main id="main-content">` (add the `id` to the existing `<main>` at App.svelte:81). Style: visually hidden until focused, matching common skip-link CSS (`position: absolute; left: -9999px;` on default, `left: var(--space-3); top: var(--space-3);` on `:focus`), using the existing `--accent`/`--surface` tokens for its focused appearance.

**Documentation references:** Explore.svelte:52-53 (existing error-state pattern to copy verbatim for the chapter-load case), Cite.svelte:410 (existing disabled-button convention to align load-more toward).

**Verification checklist:**
- Manually stop the backend, reload the app, confirm a visible "Chapter list unavailable" message appears instead of a silent console-only failure.
- `grep -n "cursor: wait" src/routes/Explore.svelte` — confirm opacity is now `0.45` on that line.
- Keyboard test: Tab to a chapter card in Browse Chapters, press Space — confirm it navigates (previously only Enter worked).
- Keyboard test: Tab from page load — first stop should be the skip link; Enter/Space on it should move focus to `#main-content`.
- Re-run the 11 contrast pairs from the audit's Visual evidence against any new colors introduced (skip-link uses only existing tokens, so this should be a no-op check, not new work).

**Anti-pattern guards:** Do not change `cursor: not-allowed` to `cursor: wait` everywhere or vice versa — the audit's finding was about inconsistent *opacity*, and load-more's `cursor: wait` is actually semantically correct for its fetch-in-progress use case; only the opacity needed to move. Do not add `aria-live` regions beyond what's needed — the new chapter-load error uses `role="alert"` exactly like every other error banner in the file, no new pattern invented.

---

## Phase 5: Copy fixes (principles #4, #6)

**What to implement:**
1. `Cite.svelte:207-213` — replace:
   > "More than one materially different source row matches this reference. Review the alternatives before relying on it."

   with:
   > "More than one version of this provision could match. Review the options below before relying on it."

2. `Cite.svelte:321-323` — replace:
   > "LawCite confirms whether a reference resolves in its source corpus. It does not claim that a provision is currently in force."

   with:
   > "LawCite checks whether a reference matches text in its collection of laws. It does not confirm the law is currently in force."

3. `ResultCard.svelte` (via the new `formatDate` fallback, Phase 3) and `LookupPanel.svelte` — change the `formatDate` fallback string passed at these two call sites from the default `"Date unavailable"` to `"No effective date on file"` **only where it's rendered as a status pill/badge** (ResultCard.svelte:91's `authorityLabel`, LookupPanel's version-list date). Do not change the fallback everywhere `formatDate` is called — Cite.svelte's "Source date unavailable" label (Cite.svelte:308) is a different, already-clear string and stays as-is; this is a targeted copy fix on the 2 flagged ambiguous instances, not a global find-and-replace.

4. `Explore.svelte:112` — replace the hardcoded claim:
   ```svelte
   <p class="coverage">533 chapters · historical versions included</p>
   ```
   with a value sourced from the same `getChapters()` call already made in this file's `onMount` (Explore.svelte:26-32), or from `StatsBar`'s existing `getStats()` call if `StatsBar` is rendered on this route — check which is actually mounted on the Research page before choosing; if neither is guaranteed loaded when this heading renders, derive the count from `chapters.length` (already fetched here) with a static "historical versions included" suffix that isn't a numeric claim:
   ```svelte
   <p class="coverage">{chapters.length || "—"} chapters · historical versions included</p>
   ```

**Documentation references:** None external — this is copy-only, no new APIs.

**Verification checklist:**
- `grep -n "materially different source row" src/` returns zero matches.
- `grep -n "resolves in its source corpus" src/` returns zero matches.
- `grep -n "533 chapters" src/routes/Explore.svelte` returns zero matches; confirm `{chapters.length}` renders the real count once `getChapters()` resolves (dev-server check, since backend was down during the audit).
- Existing tests referencing old copy strings (none found in the audit's Copy & Honesty evidence — verify with `grep -rn "materially different\|resolves in its source corpus\|533 chapters" src/**/*.test.js` before editing, in case a test snapshot depends on old text) — update any that do.

**Anti-pattern guards:** Do not rewrite copy the audit didn't flag — only the 4 specific strings above. Do not turn `"No effective date on file"` into the global default (used everywhere `formatDate` is called) — it fits the pill/badge context, not Cite's dedicated "Source date unavailable" section label.

---

## Final Phase: Verification

1. **Full contrast re-check** — re-verify all 11 primary token pairs from the audit's Accessibility evidence still pass WCAG AA (no color tokens were changed in this plan, only spacing/type tokens added and 2 hardcoded off-palette colors replaced with existing tokens — this should be a no-op confirmation, not new analysis).
2. **Bundle size check** — `npm run build && du -sh dist/assets/*.js` — confirm gzip stays under 100KB (baseline was 86.6KB/30.16KB gzip; two new small files — `Card.svelte`, `StatusBadge.svelte`, `date.js` — should add only a few KB).
3. **Full test suite** — `npm run test` — all existing tests (`App.test.js`, `SearchBar.test.js`, `ResultCard.test.js`, `Chat.test.js`, `Cite.test.js`, `text.test.js`) plus new ones (`Card.test.js`, `StatusBadge.test.js`, `date.test.js`) pass.
4. **Duplication grep sweep** — confirm the audit's specific findings are resolved:
   - `grep -rn "function displayDate" src/` → 0 matches
   - `grep -c "border: 1px solid var(--border);" src/components/*.svelte src/routes/*.svelte` → only `LookupPanel.svelte`'s intentional `details` exception remains outside `Card.svelte`
   - `grep -n "#f87171\|accent-light" src/` → 0 matches
5. **States checklist re-run per route** (Explore, Cite, Chat) — empty/loading/error/success/focus/disabled all present and now visually consistent (disabled opacity unified, chapter-load error now visible).
6. **Manual keyboard pass** — Tab through Research → Cite → Chat, confirm: skip link first, ChapterBrowser cards respond to both Enter and Space, focus rings visible on every control (should be unchanged, just re-confirming no regression from the Card/StatusBadge refactor).
7. **Non-goals check** — diff `git diff --stat` against `main` and confirm no changes to: sidebar nav structure/labels, route names, backend/API files (`lib/api.js` should have zero diff), any new npm dependency in `package.json`.
