<script>
  let { children, padded = true, class: className = "" } = $props();
</script>

<div class="card {className}" class:padded>
  {@render children?.()}
</div>

<style>
  .card {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
  }
  .card.padded { padding: var(--space-5) var(--space-6); }
</style>
