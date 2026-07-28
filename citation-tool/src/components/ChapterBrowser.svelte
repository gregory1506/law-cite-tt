<script>
  let { chapters = [], onSelect } = $props();

  let filter = $state("");

  let filtered = $derived(
    chapters.filter(
      (c) =>
        c.chapter.toLowerCase().includes(filter.toLowerCase()) ||
        c.title.toLowerCase().includes(filter.toLowerCase())
    )
  );
</script>

<div class="filter-row">
  <input type="text" bind:value={filter} placeholder="Filter chapters… e.g. tax, criminal, education" />
</div>

<div class="results">
  {#if filtered.length === 0}
    <div class="no-results">No chapters match that filter.</div>
  {:else}
    {#each filtered as c (c.chapter)}
      <div class="chapter-card" onclick={() => onSelect(c.chapter)} role="button" tabindex="0"
           onkeydown={(e) => e.key === "Enter" && onSelect(c.chapter)}>
        <span class="chapter">{c.chapter}</span>
        <span class="title">{c.title}</span>
      </div>
    {/each}
  {/if}
</div>

<style>
  .filter-row { margin-bottom: 12px; }
  .filter-row input {
    width: 100%;
    padding: 12px 16px; font-size: 1rem;
    border: 2px solid var(--border); border-radius: var(--radius);
  }
  .chapter-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    margin-bottom: 12px;
    cursor: pointer;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
  .chapter-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
  .chapter { font-weight: 600; color: var(--accent); }
  .no-results { text-align: center; padding: 48px 16px; color: var(--muted); }
</style>
