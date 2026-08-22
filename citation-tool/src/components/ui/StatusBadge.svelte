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
