<script>
  import ChatDock from "./components/chat/ChatDock.svelte";
  import ChatLauncher from "./components/chat/ChatLauncher.svelte";
  import MobileHeader from "./components/layout/MobileHeader.svelte";
  import Sidebar from "./components/layout/Sidebar.svelte";
  import { isAuthenticated, setToken } from "./lib/auth.js";
  import { initRouter, router } from "./lib/router.svelte.js";
  import Cite from "./routes/Cite.svelte";
  import Explore from "./routes/Explore.svelte";

  initRouter();

  const titles = {
    research: "Research",
    cite: "Validate a citation",
  };

  let authed = $state(isAuthenticated());
  let navOpen = $state(false);

  function login() {
    setToken("stub-session-token");
    authed = true;
  }

  $effect(() => {
    document.title = `${titles[router.route] || "Research"} — LawCite TT`;
  });
</script>

{#if !authed}
  <div class="login-gate">
    <div class="login-card card">
      <h1>LawCite <span class="accent-text">TT</span></h1>
      <p>Temporal legal engine for the Laws of Trinidad and Tobago</p>
      <p class="prompt">Please sign in to continue.</p>
      <button class="btn btn-primary" type="button" onclick={login}>
        Sign in (stub)
      </button>
    </div>
  </div>
{:else}
  <MobileHeader open={navOpen} onToggle={() => (navOpen = !navOpen)} />

  <div class="app-shell">
    <Sidebar open={navOpen} onNavigate={() => (navOpen = false)} />
    {#if navOpen}
      <button
        class="backdrop"
        aria-label="Close navigation"
        onclick={() => (navOpen = false)}
      ></button>
    {/if}
    <main>
      <div class="main-inner">
        {#if router.route === "research"}
          <Explore />
        {:else}
          <Cite />
        {/if}
      </div>
    </main>
  </div>
  <ChatLauncher />
  <ChatDock />
{/if}

<style>
  .app-shell { display: flex; min-height: 100vh; }
  .backdrop { display: none; }
  .accent-text { color: var(--accent); }
  main {
    min-width: 0;
    flex: 1;
    padding: var(--space-8) var(--space-8) 104px;
  }
  .main-inner { max-width: var(--content-max); margin: 0 auto; }
  .login-gate {
    display: flex;
    min-height: 100vh;
    align-items: center;
    justify-content: center;
    padding: var(--space-4);
  }
  .login-card {
    width: min(420px, 100%);
    padding: var(--space-10) var(--space-8);
    text-align: center;
  }
  .login-card h1 {
    margin: 0 0 var(--space-2);
    font-size: var(--text-2xl);
  }
  .login-card p { margin: var(--space-1) 0; color: var(--muted); }
  .login-card .prompt { margin-top: var(--space-5); color: var(--text); }
  .login-card button {
    margin-top: var(--space-4);
    padding: 10px var(--space-6);
  }
  @media (max-width: 768px) {
    .backdrop {
      position: fixed;
      inset: 54px 0 0;
      z-index: 20;
      display: block;
      border: 0;
      background: var(--backdrop);
    }
    main { padding: 76px var(--space-4) 96px; }
  }
</style>
