<script>
  import { FileCheck2, Search } from "@lucide/svelte";
  import { navigate, router } from "../../lib/router.svelte.js";
  import ThemeToggle from "./ThemeToggle.svelte";

  let { open = false, onNavigate = () => {} } = $props();

  function go(route) {
    navigate(route);
    onNavigate();
  }
</script>

<aside id="primary-navigation" class="sidebar" class:open>
  <div class="brand">LawCite <span class="accent-text">TT</span></div>
  <nav aria-label="Primary">
    <button
      class:active={router.route === "research"}
      onclick={() => go("research")}
      aria-current={router.route === "research" ? "page" : undefined}
    >
      <Search size={17} aria-hidden="true" />
      Research
    </button>
    <button
      class:active={router.route === "cite"}
      onclick={() => go("cite")}
      aria-current={router.route === "cite" ? "page" : undefined}
    >
      <FileCheck2 size={17} aria-hidden="true" />
      Cite
    </button>
  </nav>
  <div class="sidebar-footer">
    <ThemeToggle />
    <p class="auth-status">Signed in (stub)</p>
  </div>
</aside>

<style>
  .sidebar {
    width: var(--sidebar-w);
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-6) var(--space-4);
    border-right: 1px solid var(--border);
    background: var(--surface);
  }
  .brand {
    padding: 0 var(--space-2) var(--space-5);
    color: var(--text);
    font-size: var(--text-lg);
    font-weight: var(--weight-bold);
    letter-spacing: -0.01em;
  }
  .accent-text { color: var(--accent); }
  nav { display: grid; gap: var(--space-1); }
  nav button {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: 10px var(--space-3);
    border: 0;
    border-left: 3px solid transparent;
    border-radius: 0 var(--radius) var(--radius) 0;
    background: transparent;
    color: var(--muted-strong);
    font-size: var(--text-md);
    font-weight: var(--weight-semibold);
    text-align: left;
    cursor: pointer;
    transition:
      background var(--dur-fast) var(--ease),
      color var(--dur-fast) var(--ease);
  }
  nav button:hover {
    background: var(--accent-faint);
    color: var(--text);
  }
  nav button.active {
    border-left-color: var(--accent);
    background: var(--nav-active);
    color: var(--accent);
  }
  .sidebar-footer {
    margin-top: auto;
    display: grid;
    gap: var(--space-1);
    padding-top: var(--space-4);
    border-top: 1px solid var(--border);
  }
  .auth-status {
    margin: 0;
    padding: var(--space-1) var(--space-2) 0;
    color: var(--muted);
    font-size: var(--text-xs);
  }
  @media (max-width: 768px) {
    .sidebar {
      position: fixed;
      inset: 54px auto 0 0;
      z-index: 25;
      height: calc(100vh - 54px);
      transform: translateX(-100%);
      transition: transform var(--dur) var(--ease);
    }
    .sidebar.open { transform: translateX(0); }
    .brand { display: none; }
  }
</style>
