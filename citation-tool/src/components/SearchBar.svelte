<script>
  import { Search, X } from "@lucide/svelte";

  let {
    chapters = [],
    onSearch,
    onClear = () => {},
    query = $bindable(""),
    mode = $bindable("fts"),
    chapter = $bindable(""),
    date = $bindable(""),
  } = $props();

  const hasSearchState = $derived(Boolean(query || chapter || date));

  function submit() {
    if (!query.trim()) return;
    onSearch({
      query: query.trim(),
      mode,
      chapter: chapter.trim(),
      date,
    });
  }

  function onKeydown(event) {
    if (event.key === "Enter") submit();
  }

  function clearSearch() {
    query = "";
    chapter = "";
    date = "";
    onClear();
  }
</script>

<div class="search-section">
  <div class="search-row">
    <label class="search-input">
      <span class="visually-hidden">Search legislation</span>
      <Search size={19} aria-hidden="true" />
      <input
        type="search"
        bind:value={query}
        onkeydown={onKeydown}
        placeholder="Search legislation"
      />
    </label>

    <label>
      <span class="visually-hidden">Search method</span>
      <select bind:value={mode} aria-label="Search method">
        <option value="fts" title="Find the words you entered">Exact wording</option>
        <option value="hybrid" title="Balance exact wording and related meaning">Best match</option>
        <option value="vector" title="Find provisions with related meaning">Related concepts</option>
      </select>
    </label>

    <div class="search-actions">
      <button class="primary" type="button" onclick={submit} disabled={!query.trim()}>
        <Search size={18} aria-hidden="true" />
        Search
      </button>
      <button
        class="clear-button"
        type="button"
        onclick={clearSearch}
        disabled={!hasSearchState}
        aria-label="Clear search"
      >
        <X size={17} aria-hidden="true" />
        Clear
      </button>
    </div>
  </div>

  <div class="filters-row">
    <label>
      <span>Chapter</span>
      <input
        type="text"
        bind:value={chapter}
        placeholder="All chapters"
        list="chapter-list"
      />
    </label>
    <datalist id="chapter-list">
      {#each chapters as item (item.chapter)}
        <option value={item.chapter}>{item.title}</option>
      {/each}
    </datalist>

    <label>
      <span>Available as at</span>
      <input type="date" bind:value={date} />
    </label>

  </div>
</div>

<style>
  .search-section {
    padding: 16px;
    margin-bottom: 20px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
  }
  .search-row {
    display: grid;
    grid-template-columns: minmax(240px, 1fr) 180px auto;
    gap: 10px;
  }
  .search-actions {
    display: grid;
    grid-template-columns: auto auto;
    gap: 8px;
  }
  .search-input {
    display: flex;
    align-items: center;
    gap: 9px;
    min-width: 0;
    padding: 0 12px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    background: var(--bg);
    color: var(--muted);
  }
  .search-input:focus-within {
    border-color: var(--accent);
    outline: 2px solid rgba(212, 160, 23, 0.16);
  }
  .search-input input {
    width: 100%;
    min-width: 0;
    padding: 11px 0;
    border: 0;
    outline: 0;
    background: transparent;
    color: var(--text);
    font-size: 0.98rem;
  }
  .search-input input::placeholder { color: var(--muted); }
  select,
  .filters-row input {
    width: 100%;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    background: var(--bg);
    color: var(--text);
  }
  select {
    height: 100%;
    padding: 10px 32px 10px 11px;
    font-size: 0.88rem;
  }
  select:focus-visible,
  .filters-row input:focus-visible {
    border-color: var(--accent);
    outline: 2px solid rgba(212, 160, 23, 0.16);
  }
  .primary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    min-width: 112px;
    padding: 11px 18px;
    border: 0;
    border-radius: var(--radius);
    background: var(--accent);
    color: var(--accent-text);
    font-size: 0.9rem;
    font-weight: 750;
    cursor: pointer;
  }
  .primary:hover:not(:disabled) { background: var(--accent-hover); }
  .primary:disabled { cursor: not-allowed; opacity: 0.45; }
  .filters-row {
    display: grid;
    grid-template-columns: minmax(180px, 1fr) minmax(165px, 220px);
    align-items: end;
    gap: 10px;
    margin-top: 12px;
  }
  .filters-row label {
    display: grid;
    gap: 5px;
    color: var(--muted-strong);
    font-size: 0.72rem;
    font-weight: 700;
  }
  .filters-row input {
    min-width: 0;
    padding: 9px 11px;
    font-size: 0.84rem;
  }
  .clear-button {
    display: inline-flex;
    min-height: 42px;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 9px 12px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    background: transparent;
    color: var(--muted-strong);
    font-size: 0.84rem;
    font-weight: 700;
    cursor: pointer;
  }
  .clear-button:hover:not(:disabled) {
    color: var(--text);
    border-color: var(--muted);
  }
  .clear-button:disabled { cursor: not-allowed; opacity: 0.4; }
  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
  @media (max-width: 720px) {
    .search-section { padding: 12px; }
    .search-row { grid-template-columns: minmax(0, 1fr) auto; }
    .search-input { grid-column: 1 / -1; }
    .search-row label:not(.search-input) { min-width: 0; }
    .search-actions { min-width: 196px; }
    .primary { min-width: 104px; }
    .filters-row { grid-template-columns: minmax(0, 1fr) minmax(150px, 0.8fr); }
  }
  @media (max-width: 480px) {
    .search-row { grid-template-columns: 1fr; }
    .search-actions { grid-template-columns: minmax(0, 1fr) auto; min-width: 0; }
    .filters-row { grid-template-columns: 1fr; }
    .primary { width: 100%; }
  }
</style>
