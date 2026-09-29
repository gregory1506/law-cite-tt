<script>
  import { Moon, Sun } from "@lucide/svelte";

  let theme = $state(
    document.documentElement.dataset.theme === "light" ? "light" : "dark",
  );

  function toggle() {
    theme = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("lawcite-theme", theme);
    } catch {
      /* storage unavailable */
    }
  }
</script>

<button
  class="theme-toggle"
  type="button"
  onclick={toggle}
  aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
>
  {#if theme === "dark"}
    <Sun size={15} aria-hidden="true" />
    <span>Light mode</span>
  {:else}
    <Moon size={15} aria-hidden="true" />
    <span>Dark mode</span>
  {/if}
</button>

<style>
  .theme-toggle {
    display: flex;
    align-items: center;
    gap: 9px;
    width: 100%;
    padding: 9px 12px;
    border: 0;
    border-radius: var(--radius);
    background: transparent;
    color: var(--muted);
    font-size: var(--text-md);
    font-weight: var(--weight-semibold);
    text-align: left;
    cursor: pointer;
    transition: color var(--dur-fast) var(--ease), background var(--dur-fast) var(--ease);
  }
  .theme-toggle:hover {
    background: var(--accent-soft);
    color: var(--text);
  }
</style>
