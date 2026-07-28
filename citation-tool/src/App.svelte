<script>
  import { isAuthenticated, setToken } from "./lib/auth.js";
  import Explore from "./routes/Explore.svelte";
  import Cite from "./routes/Cite.svelte";
  import Chat from "./routes/Chat.svelte";

  let authed = $state(isAuthenticated());
  let tab = $state("explore");

  function login() {
    // Stub: real auth will be issued by the marketing site's login flow.
    setToken("stub-session-token");
    authed = true;
  }
</script>

<header>
  <div class="container">
    <h1>LawCite TT</h1>
    <p>Temporal legal engine for the Laws of Trinidad and Tobago</p>
  </div>
</header>

<div class="container">
  {#if !authed}
    <div class="login-gate">
      <p>Please sign in to continue.</p>
      <button onclick={login}>Sign in (stub)</button>
    </div>
  {:else}
    <nav class="top-nav">
      <button class:active={tab === "explore"} onclick={() => (tab = "explore")}>Explore</button>
      <button class:active={tab === "cite"} onclick={() => (tab = "cite")}>Cite</button>
      <button class:active={tab === "chat"} onclick={() => (tab = "chat")}>Chat</button>
    </nav>

    {#if tab === "explore"}
      <Explore />
    {:else if tab === "cite"}
      <Cite />
    {:else if tab === "chat"}
      <Chat />
    {/if}
  {/if}
</div>

<style>
  :global(:root) {
    --bg: #f8f9fa;
    --surface: #ffffff;
    --border: #dee2e6;
    --text: #212529;
    --muted: #6c757d;
    --accent: #1a3a5c;
    --accent-light: #2b5f8a;
    --highlight: #fff3cd;
    --radius: 8px;
  }
  :global(body) {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    margin: 0;
  }
  .container { max-width: 960px; margin: 0 auto; padding: 0 16px; }
  header {
    background: var(--accent);
    color: #fff;
    padding: 24px 0;
    border-bottom: 4px solid var(--accent-light);
  }
  header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
  header p { font-size: 0.9rem; opacity: 0.85; margin-top: 4px; }
  .top-nav { display: flex; gap: 8px; margin: 20px 0 16px; }
  .top-nav button {
    padding: 10px 24px; font-size: 0.9rem; font-weight: 600;
    border: 1px solid var(--border); background: var(--surface);
    border-radius: var(--radius); cursor: pointer;
  }
  .top-nav button.active { background: var(--accent); color: #fff; border-color: var(--accent); }
  .login-gate { text-align: center; padding: 64px 16px; }
  .login-gate button {
    margin-top: 16px; padding: 10px 24px; font-size: 0.95rem; font-weight: 600;
    background: var(--accent); color: #fff; border: none; border-radius: var(--radius);
    cursor: pointer;
  }
</style>
