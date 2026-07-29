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
