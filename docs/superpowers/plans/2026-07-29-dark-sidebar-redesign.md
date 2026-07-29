# citation-tool Dark Legal-Tech Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-theme and re-layout `citation-tool/` (the Svelte customer app) from its current light/top-nav design to a dark legal-tech visual system with a sidebar nav, per the approved spec.

**Architecture:** Nearly all components already consume shared CSS custom properties (`var(--surface)`, `var(--border)`, `var(--accent)`, etc.) defined once in `App.svelte`'s `:global(:root)` block — so most of the re-theme is a single token swap. The remaining work is: (1) a structural change to `App.svelte` (top-nav → sidebar + responsive collapse), (2) a handful of hardcoded `color: #fff` button-text overrides that would read wrong against the new (light) cyan accent, (3) unstyled native `<input>`/`<select>` elements that currently render with browser-default white backgrounds, and (4) two small presentational upgrades called out in the spec (StatsBar tiles, Cite/Chat stub cards).

**Tech Stack:** Svelte 5 (runes), Vite 8, no frontend test framework (verification is `npm run build` + manual browser check), deployed via `wrangler deploy` (Cloudflare Workers static assets) to `law-cite-tt.gjo-ai.workers.dev`.

## Global Constraints

- No functional/logic changes — same components, same data flow, same `src/lib/api.js` calls, same stub auth in `src/lib/auth.js`.
- No frontend test suite exists — every task's verification step is `npm run build` (must succeed with no errors) plus a manual visual check described in the task.
- Visual tokens (exact hex values) are fixed by the spec at `docs/superpowers/specs/2026-07-29-dark-sidebar-redesign-design.md` — do not deviate from the table there.
- Mobile responsive behavior is a simple hamburger/top-bar fallback below 768px — not a fully designed mobile experience.
- Out of scope: the graph explorer feature, any Cite/Chat functionality, any backend change.

---

### Task 1: App shell — dark tokens, global input styling, sidebar layout, login gate, responsive collapse

**Files:**
- Modify: `citation-tool/src/App.svelte` (full rewrite of `<script>`, markup, and `<style>` blocks)

**Interfaces:**
- Produces: the global CSS custom properties (`--bg`, `--surface`, `--border`, `--text`, `--muted`, `--accent`, `--accent-light`, `--accent-text`, `--highlight`, `--highlight-text`, `--radius`) that every other task/component consumes. Also produces global `:global(input)`/`:global(select)` base styling that `SearchBar.svelte`, `LookupPanel.svelte`, and `ChapterBrowser.svelte` inherit without needing their own input color rules.
- Consumes: nothing (this is the root of the token tree).

- [ ] **Step 1: Replace `citation-tool/src/App.svelte` in full**

```svelte
<script>
  import { isAuthenticated, setToken } from "./lib/auth.js";
  import Explore from "./routes/Explore.svelte";
  import Cite from "./routes/Cite.svelte";
  import Chat from "./routes/Chat.svelte";

  let authed = $state(isAuthenticated());
  let tab = $state("explore");
  let navOpen = $state(false);

  function login() {
    // Stub: real auth will be issued by the marketing site's login flow.
    setToken("stub-session-token");
    authed = true;
  }

  function selectTab(t) {
    tab = t;
    navOpen = false;
  }
</script>

{#if !authed}
  <div class="login-gate">
    <div class="login-card">
      <h1>LawCite <span class="accent-text">TT</span></h1>
      <p>Temporal legal engine for the Laws of Trinidad and Tobago</p>
      <p class="prompt">Please sign in to continue.</p>
      <button onclick={login}>Sign in (stub)</button>
    </div>
  </div>
{:else}
  <div class="app-shell">
    <button class="nav-toggle" onclick={() => (navOpen = !navOpen)} aria-label="Toggle navigation">☰</button>
    <aside class="sidebar" class:open={navOpen}>
      <div class="brand">LawCite <span class="accent-text">TT</span></div>
      <nav>
        <button class:active={tab === "explore"} onclick={() => selectTab("explore")}>Explore</button>
        <button class:active={tab === "cite"} onclick={() => selectTab("cite")}>Cite</button>
        <button class:active={tab === "chat"} onclick={() => selectTab("chat")}>Chat</button>
      </nav>
      <div class="auth-status">Signed in (stub)</div>
    </aside>
    <main>
      <div class="main-inner">
        {#if tab === "explore"}
          <Explore />
        {:else if tab === "cite"}
          <Cite />
        {:else if tab === "chat"}
          <Chat />
        {/if}
      </div>
    </main>
  </div>
{/if}

<style>
  :global(:root) {
    --bg: #0a0e17;
    --surface: #111827;
    --border: #1e293b;
    --text: #f1f5f9;
    --muted: #64748b;
    --accent: #22d3ee;
    --accent-light: #0e7490;
    --accent-text: #0a0e17;
    --highlight: rgba(34, 211, 238, 0.2);
    --highlight-text: #67e8f9;
    --radius: 8px;
  }
  :global(body) {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    margin: 0;
  }
  :global(input),
  :global(select) {
    background: var(--bg);
    color: var(--text);
    font-family: inherit;
  }
  :global(input::placeholder) { color: var(--muted); }
  :global(button) { font-family: inherit; }

  .accent-text { color: var(--accent); }

  .app-shell { display: flex; min-height: 100vh; }

  .sidebar {
    width: 200px;
    flex-shrink: 0;
    background: var(--surface);
    border-right: 1px solid var(--border);
    padding: 20px 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .sidebar .brand { color: var(--text); font-weight: 700; font-size: 1.1rem; padding: 0 8px 20px; }
  .sidebar nav { display: flex; flex-direction: column; gap: 6px; }
  .sidebar nav button {
    text-align: left;
    padding: 10px 12px; font-size: 0.9rem; font-weight: 600;
    border: none; border-left: 3px solid transparent;
    background: transparent; color: var(--muted);
    border-radius: 0 var(--radius) var(--radius) 0;
    cursor: pointer;
  }
  .sidebar nav button.active {
    background: var(--border); color: var(--accent); border-left-color: var(--accent);
  }
  .sidebar .auth-status { margin-top: auto; color: var(--muted); font-size: 0.75rem; padding: 0 8px; }

  main { flex: 1; padding: 24px 28px; min-width: 0; }
  .main-inner { max-width: 900px; margin: 0 auto; }

  .nav-toggle { display: none; }

  .login-gate {
    min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 16px;
  }
  .login-card {
    background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 40px 32px; text-align: center; max-width: 420px;
  }
  .login-card h1 { font-size: 1.5rem; margin: 0 0 8px; }
  .login-card p { color: var(--muted); margin: 4px 0; }
  .login-card .prompt { margin-top: 20px; color: var(--text); }
  .login-card button {
    margin-top: 16px; padding: 10px 24px; font-size: 0.95rem; font-weight: 600;
    background: var(--accent); color: var(--accent-text); border: none; border-radius: var(--radius);
    cursor: pointer;
  }

  @media (max-width: 768px) {
    .nav-toggle {
      display: block; position: fixed; top: 12px; left: 12px; z-index: 20;
      background: var(--surface); color: var(--text); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 8px 12px; font-size: 1.1rem; cursor: pointer;
    }
    .sidebar {
      position: fixed; top: 0; left: 0; height: 100vh; z-index: 10;
      transform: translateX(-100%); transition: transform 0.2s ease;
    }
    .sidebar.open { transform: translateX(0); }
    main { padding: 24px 16px; margin-top: 48px; }
  }
</style>
```

- [ ] **Step 2: Verify the build succeeds**

Run: `cd citation-tool && npm run build`
Expected: `✓ built in ...ms`, no errors or warnings.

- [ ] **Step 3: Manual visual check**

Run: `npm run dev`, open the printed localhost URL in a browser.
Check: dark background loads, sidebar shows Explore/Cite/Chat with Explore highlighted, clicking each nav item switches `<main>` content, resizing the window below ~768px hides the sidebar behind a hamburger toggle that reveals it on click, the login gate (if you clear localStorage's stub token) shows a centered dark card.

- [ ] **Step 4: Commit**

```bash
git add citation-tool/src/App.svelte
git commit -m "feat: dark legal-tech theme + sidebar nav for citation-tool shell"
```

---

### Task 2: Fix accent-button text contrast (SearchBar, LookupPanel, Explore sub-tabs)

**Files:**
- Modify: `citation-tool/src/components/SearchBar.svelte:71`
- Modify: `citation-tool/src/components/LookupPanel.svelte:91`
- Modify: `citation-tool/src/routes/Explore.svelte:84`

**Interfaces:**
- Consumes: `--accent`, `--accent-text` from Task 1's `:global(:root)`.
- Produces: nothing new — pure style fix, no new selectors used elsewhere.

These three buttons currently set `color: #fff` against `background: var(--accent)`. With the new light-cyan `--accent` (`#22d3ee`), white text on it is low-contrast/hard to read. Fix: use the dark `--accent-text` token instead.

- [ ] **Step 1: Fix `SearchBar.svelte`**

In `citation-tool/src/components/SearchBar.svelte`, find:
```css
  .search-row button {
    padding: 12px 24px; font-size: 0.95rem; font-weight: 600;
    background: var(--accent); color: #fff;
    border: none; border-radius: var(--radius); cursor: pointer;
  }
```
Replace with:
```css
  .search-row button {
    padding: 12px 24px; font-size: 0.95rem; font-weight: 600;
    background: var(--accent); color: var(--accent-text);
    border: none; border-radius: var(--radius); cursor: pointer;
  }
```

- [ ] **Step 2: Fix `LookupPanel.svelte`**

In `citation-tool/src/components/LookupPanel.svelte`, find:
```css
  .lookup-row button {
    padding: 8px 16px; font-size: 0.85rem; font-weight: 600;
    background: var(--accent); color: #fff;
    border: none; border-radius: var(--radius); cursor: pointer;
  }
```
Replace with:
```css
  .lookup-row button {
    padding: 8px 16px; font-size: 0.85rem; font-weight: 600;
    background: var(--accent); color: var(--accent-text);
    border: none; border-radius: var(--radius); cursor: pointer;
  }
```

- [ ] **Step 3: Fix `Explore.svelte` sub-tab bar**

In `citation-tool/src/routes/Explore.svelte`, find:
```css
  .tab-bar button.active { background: var(--accent); color: #fff; border-color: var(--accent); }
```
Replace with:
```css
  .tab-bar button.active { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
```

Also find (same file):
```css
  .tab-bar button {
    padding: 10px 20px; font-size: 0.85rem; font-weight: 600;
    border: 1px solid var(--border); background: var(--bg);
    cursor: pointer;
  }
```
This is already token-driven and needs no change — leave as-is.

- [ ] **Step 4: Verify the build succeeds**

Run: `cd citation-tool && npm run build`
Expected: `✓ built in ...ms`, no errors.

- [ ] **Step 5: Manual visual check**

Run: `npm run dev`. In the Explore tab, confirm the "Search" button (dark text on cyan) is readable; switch to Section Lookup and confirm the "Look up" button matches; confirm the active "Search / Section Lookup / Browse Chapters" sub-tab shows dark text on cyan, not white-on-cyan.

- [ ] **Step 6: Commit**

```bash
git add citation-tool/src/components/SearchBar.svelte citation-tool/src/components/LookupPanel.svelte citation-tool/src/routes/Explore.svelte
git commit -m "fix: dark text on cyan accent buttons for contrast in dark theme"
```

---

### Task 3: StatsBar tiles + ChapterBrowser hover polish

**Files:**
- Modify: `citation-tool/src/components/StatsBar.svelte` (full rewrite)
- Modify: `citation-tool/src/components/ChapterBrowser.svelte:51`
- Modify: `citation-tool/src/components/ResultCard.svelte:61-64`

**Interfaces:**
- Consumes: `--surface`, `--border`, `--muted`, `--text`, `--radius`, `--accent-light`, `--highlight-text` from Task 1.
- Produces: nothing new consumed elsewhere — these are leaf components with no other component depending on their internal markup.

The approved mockup shows stats as individual dark panel "tiles" rather than a flat text row — this is a markup change (wrapping each stat in its own `<div>`), not just a color swap, but the data/props/logic are unchanged (same `getStats()` call, same fields displayed). Separately, `ChapterBrowser`'s hover shadow (`rgba(0,0,0,0.06)`) is calibrated for a light background and is invisible on the new dark background — swap it for a cyan-tinted glow.

- [ ] **Step 1: Replace `citation-tool/src/components/StatsBar.svelte` in full**

```svelte
<script>
  import { onMount } from "svelte";
  import { getStats } from "../lib/api.js";

  let stats = $state(null);
  let error = $state("");

  onMount(async () => {
    try {
      stats = await getStats();
    } catch (e) {
      error = e.message;
    }
  });
</script>

<div class="stats-bar">
  {#if error}
    <span class="error">Stats unavailable: {error}</span>
  {:else if stats}
    <div class="stat-tile">
      <span class="label">Chapters</span>
      <span class="value">{stats.chapters}</span>
    </div>
    <div class="stat-tile">
      <span class="label">Versions</span>
      <span class="value">{stats.versions}</span>
    </div>
    <div class="stat-tile">
      <span class="label">Chunks</span>
      <span class="value">{stats.chunks.toLocaleString()}</span>
    </div>
    <div class="stat-tile">
      <span class="label">Embedded</span>
      <span class="value">{stats.embedded.toLocaleString()}</span>
    </div>
  {:else}
    <span>Loading stats…</span>
  {/if}
</div>

<style>
  .stats-bar {
    display: flex;
    gap: 12px;
    padding-bottom: 20px;
    flex-wrap: wrap;
  }
  .stat-tile {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 18px;
    flex: 1;
    min-width: 140px;
  }
  .stat-tile .label {
    display: block;
    color: var(--muted);
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .stat-tile .value {
    display: block;
    color: var(--text);
    font-size: 1.3rem;
    font-weight: 700;
    margin-top: 4px;
  }
  .error { color: #f87171; }
</style>
```

- [ ] **Step 2: Fix `ChapterBrowser.svelte` hover state**

In `citation-tool/src/components/ChapterBrowser.svelte`, find:
```css
  .chapter-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
```
Replace with:
```css
  .chapter-card:hover { border-color: var(--accent-light); box-shadow: 0 2px 8px rgba(34, 211, 238, 0.15); }
```

- [ ] **Step 3: Fix `ResultCard.svelte` highlight text color**

In `citation-tool/src/components/ResultCard.svelte`, find:
```css
  .result-text :global(mark) {
    background: var(--highlight);
    padding: 0 2px;
  }
```
Replace with:
```css
  .result-text :global(mark) {
    background: var(--highlight);
    color: var(--highlight-text);
    padding: 0 2px;
  }
```

- [ ] **Step 4: Verify the build succeeds**

Run: `cd citation-tool && npm run build`
Expected: `✓ built in ...ms`, no errors.

- [ ] **Step 5: Manual visual check**

Run: `npm run dev`. On the Explore tab, confirm the stats render as four separate dark tiles with a label above a bold number (matching the mockup), not a flat text row. Switch to "Browse Chapters" and hover a chapter card — confirm a visible cyan-tinted highlight appears (not an invisible black shadow). Run a search (e.g. "absconding debtor") and confirm matched keywords in results show as light-cyan text on a cyan-tinted background, legible against the dark result card.

- [ ] **Step 6: Commit**

```bash
git add citation-tool/src/components/StatsBar.svelte citation-tool/src/components/ChapterBrowser.svelte citation-tool/src/components/ResultCard.svelte
git commit -m "feat: stat tiles for StatsBar, visible hover state for ChapterBrowser, highlight text color for ResultCard"
```

---

### Task 4: Cite / Chat stub card treatment

**Files:**
- Modify: `citation-tool/src/routes/Cite.svelte` (full rewrite)
- Modify: `citation-tool/src/routes/Chat.svelte` (full rewrite)

**Interfaces:**
- Consumes: `--surface`, `--border`, `--radius`, `--muted`, `--text` from Task 1.
- Produces: nothing consumed elsewhere — these are leaf route components with no children.

Per spec section 4: these become centered "Coming soon" cards on the dark background, matching the login-card treatment from Task 1, rather than bare centered text.

- [ ] **Step 1: Replace `citation-tool/src/routes/Cite.svelte` in full**

```svelte
<div class="stub">
  <div class="stub-card">
    <h2>Cite</h2>
    <p>Generate properly formatted legal citations following Trinidad &amp; Tobago conventions.</p>
    <p class="soon">Coming soon.</p>
  </div>
</div>

<style>
  .stub { padding: 48px 16px; display: flex; justify-content: center; }
  .stub-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 40px 32px;
    text-align: center;
    max-width: 420px;
    color: var(--muted);
  }
  .stub-card h2 { color: var(--text); margin-bottom: 8px; }
  .soon { margin-top: 16px; font-size: 0.85rem; }
</style>
```

- [ ] **Step 2: Replace `citation-tool/src/routes/Chat.svelte` in full**

```svelte
<div class="stub">
  <div class="stub-card">
    <h2>Chat</h2>
    <p>Ask questions about the Laws of Trinidad and Tobago in plain English.</p>
    <p class="soon">Coming soon.</p>
  </div>
</div>

<style>
  .stub { padding: 48px 16px; display: flex; justify-content: center; }
  .stub-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 40px 32px;
    text-align: center;
    max-width: 420px;
    color: var(--muted);
  }
  .stub-card h2 { color: var(--text); margin-bottom: 8px; }
  .soon { margin-top: 16px; font-size: 0.85rem; }
</style>
```

- [ ] **Step 3: Verify the build succeeds**

Run: `cd citation-tool && npm run build`
Expected: `✓ built in ...ms`, no errors.

- [ ] **Step 4: Manual visual check**

Run: `npm run dev`. Click Cite, then Chat, in the sidebar. Confirm each shows a centered dark card with heading + description + "Coming soon.", and the sidebar correctly highlights whichever tab is active.

- [ ] **Step 5: Commit**

```bash
git add citation-tool/src/routes/Cite.svelte citation-tool/src/routes/Chat.svelte
git commit -m "style: centered stub cards for Cite/Chat placeholders"
```

---

### Task 5: Full verification pass and Cloudflare Worker deploy

**Files:**
- None (verification + deploy only)

**Interfaces:**
- Consumes: the complete redesign from Tasks 1–4.
- Produces: nothing — terminal task.

- [ ] **Step 1: Clean build**

Run: `cd citation-tool && rm -rf dist && VITE_API_BASE=https://srv1629323.hstgr.cloud npm run build`
Expected: `✓ built in ...ms`, no errors or warnings, `dist/` contains `index.html` + `assets/`.

- [ ] **Step 2: Full manual browser walkthrough**

Run: `npm run preview` (serves the production `dist/` build), open the printed URL.
Check, at both a normal desktop width and a narrow (<768px) width:
- Explore tab: stats tiles render, search/lookup/browse sub-tabs all work and are legible, result cards show cyan-highlighted keyword matches
- Cite tab: centered stub card
- Chat tab: centered stub card
- Sidebar collapses to a hamburger toggle at narrow width and the toggle opens/closes it
- No console errors in devtools

- [ ] **Step 3: Deploy to the Cloudflare Worker**

Run: `wrangler deploy` (from `citation-tool/`)
Expected: output ends with `https://law-cite-tt.gjo-ai.workers.dev` and a version ID, no errors.

- [ ] **Step 4: Verify the live deploy**

Open `https://law-cite-tt.gjo-ai.workers.dev` in a browser. Confirm the dark sidebar layout loads (API calls will fail/show errors until the VPS backend is deployed — that's expected and out of scope for this plan; only the frontend rendering itself needs to be correct).

- [ ] **Step 5: Update project tracking docs**

Add a line to `next_steps.md` under "Completed" noting the redesign, and remove/adjust anything under "Now"/"Soon" that referenced the old light theme if present (check the file first — as of the last edit it did not reference the theme, so this may be a no-op).

- [ ] **Step 6: Commit**

```bash
git add next_steps.md
git commit -m "docs: log citation-tool dark redesign completion" --allow-empty
```
