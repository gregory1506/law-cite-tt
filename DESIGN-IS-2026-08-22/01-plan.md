# Plan — LawCite TT Frontend Distinctiveness Refine

Source audit: `design-is` run 2026-08-22, verdict REFINE (26/30). Full scorecard in the session transcript; key numbers repeated below so each phase is self-contained.

## Phase 0: Codebase Discovery (facts gathered, no external docs needed — this is a token-driven internal design system, not a library integration)

**Sources consulted:** `citation-tool/src/App.svelte`, `citation-tool/src/components/ui/Card.svelte`, `citation-tool/src/components/ui/StatusBadge.svelte`, `citation-tool/src/routes/{Explore,Chat,Cite}.svelte`, `citation-tool/index.html`, plus repo-wide grep.

**Findings:**
1. **Single token source of truth.** All design tokens live in one `:root` block: `App.svelte:97-134` (colors `:97-115`, spacing scale `:117-125`, type scale `:127-133`). 49 usages of `var(--accent...)` and 30 usages of `var(--radius)` across the codebase — every one of them reads from this block, so editing it cascades everywhere. No hardcoded hex values found in reviewed files.
2. **"Inter" is never actually loaded.** `App.svelte:139` sets `font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;` but `index.html` has no `<link>` to Google Fonts, no `@font-face`, and no `@fontsource/*` package in `citation-tool/package.json`. Confirmed via `grep -rn "fonts.google\|@font-face\|fontsource"` → zero hits. In practice every visitor renders the system font (San Francisco / Segoe UI / Roboto depending on OS) — the "Inter" declaration is a no-op. This is the single highest-leverage, lowest-cost distinctiveness lever available: right now there is no deliberate typographic identity at all.
3. **Serif is already used for statute text**, consistently: `Georgia, "Times New Roman", serif` in `components/ResultCard.svelte:191`, `components/LookupPanel.svelte:258`, `routes/Cite.svelte:486,508`. This pairing (serif for legal excerpt text, sans for UI chrome) is a real, existing decision worth keeping — it should anchor the typography phase, not be replaced.
4. **`.heading-mark` decorative icon box is duplicated verbatim** in two files: `routes/Chat.svelte:70` (markup) / `:193-177` (style) and `routes/Cite.svelte:100` (markup) / `:340` (style). `Explore.svelte` has no equivalent — it uses a plain text `.coverage` line instead (`Explore.svelte:114`). This is the concrete #10 finding: a bordered gradient square around a Lucide icon, present on 2 of 3 routes, adding no information the `<h1>` text doesn't already carry.
5. **`.eyebrow` + `<h1>` header pattern is repeated 3×** (`Explore.svelte`, `Chat.svelte`, `Cite.svelte`), each with its own copy of the same handful of CSS declarations rather than a shared component. Out of scope for this refine (structural extraction is a code-quality move, not a design-distinctiveness one) — noted here only so a future pass doesn't rediscover it from scratch.
6. **Accent color:** `--accent: #22d3ee` (cyan), `--accent-hover: #67e8f9`, `--accent-strong: #67e8f9` — `App.svelte:107-109`. This is the color driving buttons, links, active nav state, focus rings, and the badge "positive" tone shares a separate teal (`--positive: #5eead4`, `App.svelte:111`) that reads as nearly the same hue family. No secondary/tertiary hue exists anywhere in the token set — everything is monochrome-cyan-on-dark.

**Allowed changes for this refine (grounded in the above, nothing invented):**
- Edit values inside the existing `:root` token block (`App.svelte:97-134`) — do not introduce a second token source.
- Add a real webfont via a self-hosted `@fontsource` package (no external CDN `<link>` — keeps the app's existing zero-external-request posture; confirmed no other CDN dependency exists in `index.html`).
- Delete/replace the two `.heading-mark` instances — do not invent a new decorative pattern to replace it with; either remove it or fold the icon into the existing `.eyebrow` line.

**Anti-patterns to avoid:**
- Do not touch `Card.svelte`, `StatusBadge.svelte`, spacing scale, or any component that scored 3 in the audit — this is scoped to typography + accent + the two heading-mark instances.
- Do not add a font-loading CDN `<link>` (breaks the app's current zero-external-dependency posture and would need a CSP/analysis pass it hasn't had).
- Do not change the serif excerpt font — it already works and isn't part of the "generic" finding.

---

## Phase 1: Give it a real typographic identity

**What to implement:** Replace the dead "Inter" declaration with an actually-loaded, self-hosted display font for headings (`h1`, `.eyebrow`, `.brand`, `.login-card h1`), while keeping the current system-font stack for dense UI text (buttons, inputs, body copy) so nothing about readability or bundle-weight regresses.

**Steps:**
1. `npm install @fontsource/[chosen-family]` (self-hosted npm package, no external network request at runtime — consistent with current zero-CDN posture).
2. Import the font CSS once in `main.js` (same place other global setup lives).
3. Add a new token, e.g. `--font-display: "<Family>", "Inter", -apple-system, sans-serif;` in `App.svelte:97-134`, next to the existing type scale.
4. Apply `--font-display` to: `.brand` (`App.svelte:174`), `h1` selectors in `Explore.svelte`, `Chat.svelte`, `Cite.svelte`, and `.login-card h1` (`App.svelte:230`). Leave every other `font-family` declaration (buttons, inputs, serif excerpt text) untouched.

**Verification:**
- `grep -rn "font-family" citation-tool/src` shows the new `--font-display` token applied only to heading-level selectors, serif and system-UI declarations unchanged.
- `npm run build` — confirm gzip JS/CSS stay well under the 100KB/500KB thresholds that earned the #9 score of 3 (current: 91KB JS / 31KB gzip JS, 29KB / 5.3KB gzip CSS — a single weight of a display font typically adds 10-25KB, still comfortably under budget).
- Visual check via dev server: headings render in the new face; body/serif text unchanged.

---

## Phase 2: Move off the generic cyan-on-black accent

**What to implement:** Shift the interactive accent hue to something less saturated with the current "AI dark-mode" look, while keeping the same WCAG contrast ratios the current cyan already passes (don't regrade accessibility — audit scored #9/thoroughness partly on this holding up).

**Steps:**
1. In `App.svelte:107-110`, replace `--accent`, `--accent-hover`, `--accent-strong`, `--accent-text` with a new hue. Keep `--positive` (`:111`) and `--danger` (`:112`) as distinct hues from the new accent so semantic meaning (success vs. interactive) doesn't collapse into "everything is teal."
2. Because all 49 `var(--accent...)` call sites read this token, no other file needs editing for the base recolor.
3. Spot-check the handful of places that reference accent via `rgba(34, 211, 238, ...)` literals instead of the token — these will NOT update automatically and need manual conversion to the new hue: `SearchBar.svelte:133,162` (focus-ring `rgba`), `Chat.svelte` `.heading-mark` gradient (being removed in Phase 3 anyway), and any other `rgba(34, 211, 238` hits from `grep -rn "34, 211, 238" citation-tool/src`.

**Verification:**
- `grep -rn "34, 211, 238" citation-tool/src` returns zero hits after the change (confirms no orphaned old-accent literals survive the recolor).
- Run a contrast check on the new `--accent` against `--bg` and `--accent-text` against the new `--accent` — must meet the same WCAG AA threshold the current cyan passes (don't regress the accessibility evidence from the original audit).
- Visual check: buttons, active nav item, links, focus rings all reflect the new hue consistently.

---

## Phase 3: Remove the duplicated decorative heading-mark

**What to implement:** Delete the `.heading-mark` bordered-gradient icon box pattern from `Chat.svelte` and `Cite.svelte` (Explore.svelte already doesn't have one — matching it removes the inconsistency AND the decoration in one move).

**Steps:**
1. Remove markup: `Chat.svelte:70` (`<div class="heading-mark" ...>`) and `Cite.svelte:100`.
2. Remove associated styles: `Chat.svelte:193-` block, `Chat.svelte:369` media-query override, `Cite.svelte:340` block, `Cite.svelte:538` media-query override.
3. Confirm the `<header class="page-heading">` flex layout in each file still reads correctly with only the text column (no orphaned `justify-content: space-between` leaving a stray gap) — adjust to match `Explore.svelte`'s `.page-heading` pattern (`Explore.svelte:191-197`) if needed for consistency.

**Verification:**
- `grep -rn "heading-mark" citation-tool/src` returns zero hits.
- All three routes (Research, Cite, Chat) now share the same header shape — no route-specific decorative box.
- Run existing test suite (`npx vitest run`) — no test currently asserts on `.heading-mark`, but confirm nothing else breaks.

---

## Final Phase: Verification

1. `npm run build` from `citation-tool/` — confirm it still succeeds and bundle size stays within the thresholds noted in Phase 1.
2. `npx vitest run` — all existing tests pass unchanged (this refine touches no component logic, only markup/CSS).
3. Re-grep the anti-pattern list: `grep -rn "34, 211, 238"` (should be empty), `grep -rn "heading-mark"` (should be empty), `grep -rn "\"Inter\"" citation-tool/src/App.svelte` (should show it demoted to a fallback behind the new `--font-display`, not the primary declaration).
4. Manual pass through Research/Cite/Chat in the browser at both desktop and the `768px`/`600px` breakpoints already defined in each file's `@media` blocks, to confirm nothing regressed at mobile widths.
5. Re-score principles #1, #7, #10 against the anchors used in the original audit — confirm each moved up at least one point without any other principle dropping.

**Out of scope for this pass** (explicitly not touched): `Card.svelte`, `StatusBadge.svelte`, spacing scale, radius value, serif excerpt font, the repeated `.eyebrow`/`<h1>` structural duplication across routes (a code-quality DRY concern, not a design-distinctiveness one), auth flow, backend/API.
