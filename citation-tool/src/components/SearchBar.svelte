<script>
  let { chapters = [], onSearch, initialChapter = "" } = $props();

  let query = $state("");
  let mode = $state("fts");
  let chapter = $state("");

  $effect(() => {
    if (initialChapter) chapter = initialChapter;
  });

  function submit() {
    if (!query.trim()) return;
    onSearch({ query: query.trim(), mode, chapter: chapter.trim() });
  }

  function onKeydown(e) {
    if (e.key === "Enter") submit();
  }
</script>

<div class="search-section">
  <div class="search-row">
    <!-- svelte-ignore a11y_autofocus -->
    <input
      type="text"
      bind:value={query}
      onkeydown={onKeydown}
      placeholder="Search laws… e.g. murder, tax exemption, absconding debtor"
      autofocus
    />
    <select bind:value={mode}>
      <option value="fts">Full-Text Search (fast)</option>
      <option value="hybrid">Hybrid (FTS + Vector)</option>
      <option value="vector">Vector (Semantic)</option>
    </select>
    <button onclick={submit}>Search</button>
  </div>
  <div class="filters-row">
    <input
      type="text"
      bind:value={chapter}
      placeholder="Chapter (optional, e.g. 8:08, 48:50)"
      list="chapter-list"
    />
    <datalist id="chapter-list">
      {#each chapters as c (c.chapter)}
        <option value={c.chapter}></option>
      {/each}
    </datalist>
  </div>
</div>

<style>
  .search-section { margin-bottom: 24px; }
  .search-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .search-row input[type="text"] {
    flex: 1; min-width: 200px;
    padding: 12px 16px; font-size: 1rem;
    border: 2px solid var(--border); border-radius: var(--radius);
    outline: none;
  }
  .search-row input[type="text"]:focus { border-color: var(--accent-light); }
  .search-row select {
    padding: 12px; font-size: 0.9rem;
    border: 2px solid var(--border); border-radius: var(--radius);
    background: var(--surface);
  }
  .search-row button {
    padding: 12px 24px; font-size: 0.95rem; font-weight: 600;
    background: var(--accent); color: var(--accent-text);
    border: none; border-radius: var(--radius); cursor: pointer;
  }
  .search-row button:hover { background: var(--accent-light); }
  .filters-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
  .filters-row input {
    flex: 1; min-width: 150px;
    padding: 8px 12px; font-size: 0.85rem;
    border: 1px solid var(--border); border-radius: var(--radius);
  }
</style>
