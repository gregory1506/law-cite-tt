<script>
  import { Menu, MessageSquareText, Search, X } from "@lucide/svelte";
  import { isAuthenticated, setToken } from "./lib/auth.js";
  import Explore from "./routes/Explore.svelte";
  import Chat from "./routes/Chat.svelte";

  let authed = $state(isAuthenticated());
  let navOpen = $state(false);
  let route = $state("research");

  function login() {
    setToken("stub-session-token");
    authed = true;
  }

  function navigate(nextRoute) {
    route = nextRoute;
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
  <div class="mobile-header">
    <button
      class="nav-toggle"
      onclick={() => (navOpen = !navOpen)}
      aria-label={navOpen ? "Close navigation" : "Open navigation"}
      aria-expanded={navOpen}
      aria-controls="primary-navigation"
    >
      {#if navOpen}<X size={20} />{:else}<Menu size={20} />{/if}
    </button>
    <div class="mobile-brand">LawCite <span class="accent-text">TT</span></div>
  </div>

  <div class="app-shell">
    <aside id="primary-navigation" class="sidebar" class:open={navOpen}>
      <div class="brand">LawCite <span class="accent-text">TT</span></div>
      <nav>
        <button
          class:active={route === "research"}
          onclick={() => navigate("research")}
        >
          <Search size={17} aria-hidden="true" />
          Research
        </button>
        <button
          class:active={route === "chat"}
          onclick={() => navigate("chat")}
        >
          <MessageSquareText size={17} aria-hidden="true" />
          Chat
        </button>
      </nav>
      <div class="auth-status">Signed in (stub)</div>
    </aside>
    {#if navOpen}
      <button
        class="backdrop"
        aria-label="Close navigation"
        onclick={() => (navOpen = false)}
      ></button>
    {/if}
    <main>
      <div class="main-inner">
        {#if route === "research"}
          <Explore />
        {:else}
          <Chat />
        {/if}
      </div>
    </main>
  </div>
{/if}

<style>
  :global(:root) {
    --bg: #090d14;
    --surface: #111823;
    --surface-raised: #151e2a;
    --border: #243040;
    --border-strong: #354256;
    --text: #f3f5f7;
    --text-soft: #d7dde5;
    --muted: #8190a5;
    --muted-strong: #a8b3c3;
    --accent: #22d3ee;
    --accent-hover: #67e8f9;
    --accent-strong: #67e8f9;
    --accent-text: #061016;
    --positive: #5eead4;
    --danger: #fca5a5;
    --highlight: rgba(250, 204, 21, 0.2);
    --highlight-text: #fef08a;
    --radius: 7px;
  }
  :global(body) {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.55;
  }
  :global(*) { box-sizing: border-box; }
  :global(input),
  :global(select),
  :global(button) { font: inherit; }
  :global(input::placeholder) { color: var(--muted); }
  .accent-text { color: var(--accent); }
  .app-shell { display: flex; min-height: 100vh; }
  .sidebar {
    width: 216px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 22px 14px;
    border-right: 1px solid var(--border);
    background: var(--surface);
  }
  .brand {
    padding: 0 9px 18px;
    color: var(--text);
    font-size: 1.08rem;
    font-weight: 800;
  }
  .sidebar nav { display: grid; gap: 5px; }
  .sidebar nav button {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 10px 12px;
    border: 0;
    border-left: 3px solid transparent;
    border-radius: 0 var(--radius) var(--radius) 0;
    background: transparent;
    color: var(--muted-strong);
    font-size: 0.86rem;
    font-weight: 700;
    text-align: left;
    cursor: pointer;
  }
  .sidebar nav button.active {
    border-left-color: var(--accent);
    background: #1b2636;
    color: var(--accent);
  }
  .auth-status {
    margin-top: auto;
    padding: 0 9px;
    color: var(--muted);
    font-size: 0.72rem;
  }
  main {
    min-width: 0;
    flex: 1;
    padding: 26px 30px 48px;
  }
  .main-inner { max-width: 980px; margin: 0 auto; }
  .mobile-header,
  .backdrop { display: none; }
  .login-gate {
    display: flex;
    min-height: 100vh;
    align-items: center;
    justify-content: center;
    padding: 16px;
  }
  .login-card {
    width: min(420px, 100%);
    padding: 38px 30px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    text-align: center;
  }
  .login-card h1 { margin: 0 0 8px; font-size: 1.5rem; }
  .login-card p { margin: 4px 0; color: var(--muted); }
  .login-card .prompt { margin-top: 20px; color: var(--text); }
  .login-card button {
    margin-top: 16px;
    padding: 10px 22px;
    border: 0;
    border-radius: var(--radius);
    background: var(--accent);
    color: var(--accent-text);
    font-weight: 750;
    cursor: pointer;
  }
  @media (max-width: 768px) {
    .mobile-header {
      position: fixed;
      inset: 0 0 auto;
      z-index: 30;
      display: flex;
      height: 54px;
      align-items: center;
      gap: 12px;
      padding: 0 12px;
      border-bottom: 1px solid var(--border);
      background: rgba(9, 13, 20, 0.96);
    }
    .mobile-brand { font-size: 0.98rem; font-weight: 800; }
    .nav-toggle {
      display: inline-grid;
      width: 36px;
      height: 36px;
      place-items: center;
      padding: 0;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--surface);
      color: var(--text);
      cursor: pointer;
    }
    .sidebar {
      position: fixed;
      inset: 54px auto 0 0;
      z-index: 25;
      height: calc(100vh - 54px);
      transform: translateX(-100%);
      transition: transform 0.18s ease;
    }
    .sidebar.open { transform: translateX(0); }
    .sidebar .brand { display: none; }
    .backdrop {
      position: fixed;
      inset: 54px 0 0;
      z-index: 20;
      display: block;
      border: 0;
      background: rgba(0, 0, 0, 0.5);
    }
    main {
      padding: 76px 14px 40px;
    }
  }
</style>
