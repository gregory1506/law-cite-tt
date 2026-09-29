<script>
  import { Menu, X } from "@lucide/svelte";

  let { open = false, onToggle = () => {} } = $props();
</script>

<div class="mobile-header">
  <button
    class="nav-toggle"
    onclick={onToggle}
    aria-label={open ? "Close navigation" : "Open navigation"}
    aria-expanded={open}
    aria-controls="primary-navigation"
  >
    {#if open}<X size={20} />{:else}<Menu size={20} />{/if}
  </button>
  <div class="mobile-brand">LawCite <span class="accent-text">TT</span></div>
</div>

<style>
  .mobile-header { display: none; }
  .accent-text { color: var(--accent); }
  .mobile-brand { font-size: 0.98rem; font-weight: var(--weight-bold); }
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
  @media (max-width: 768px) {
    .mobile-header {
      position: fixed;
      inset: 0 0 auto;
      z-index: 30;
      display: flex;
      height: 54px;
      align-items: center;
      gap: var(--space-3);
      padding: 0 var(--space-3);
      border-bottom: 1px solid var(--border);
      background: var(--header-bg);
      backdrop-filter: blur(8px);
    }
  }
</style>
