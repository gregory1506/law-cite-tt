<script>
  import { onMount } from "svelte";
  import { ChevronDown } from "@lucide/svelte";
  import { getChapters, searchGrouped } from "../lib/api.js";
  import SearchBar from "../components/SearchBar.svelte";
  import ResultCard from "../components/ResultCard.svelte";
  import LookupPanel from "../components/LookupPanel.svelte";
  import ChapterBrowser from "../components/ChapterBrowser.svelte";

  let subTab = $state("search");
  let chapters = $state([]);
  let results = $state([]);
  let searched = $state(false);
  let loading = $state(false);
  let loadingMore = $state(false);
  let error = $state("");
  let nextOffset = $state(null);
  let hasMore = $state(false);

  let query = $state("");
  let mode = $state("fts");
  let chapter = $state("");
  let date = $state("");
  let lastSearch = $state({ query: "", mode: "fts", chapter: "", date: "" });

  let chapterLoadError = $state("");

  const uniqueResultChapters = $derived(
    new Set(results.map((item) => item.chapter_number)).size,
  );

  onMount(async () => {
    try {
      chapters = await getChapters();
    } catch (loadError) {
      chapterLoadError = loadError.message;
    }
  });

  async function runSearch(searchInput) {
    loading = true;
    error = "";
    searched = true;
    results = [];
    nextOffset = null;
    hasMore = false;
    lastSearch = searchInput;
    try {
      const response = await searchGrouped(searchInput.query, {
        mode: searchInput.mode,
        chapter: searchInput.chapter,
        date: searchInput.date,
        limit: 20,
      });
      results = response.items;
      nextOffset = response.next_offset;
      hasMore = response.has_more;
    } catch (searchError) {
      error = searchError.message;
    } finally {
      loading = false;
    }
  }

  async function loadMore() {
    if (nextOffset == null || loadingMore) return;
    loadingMore = true;
    error = "";
    try {
      const response = await searchGrouped(lastSearch.query, {
        mode: lastSearch.mode,
        chapter: lastSearch.chapter,
        date: lastSearch.date,
        limit: 20,
        offset: nextOffset,
      });
      results = [...results, ...response.items];
      nextOffset = response.next_offset;
      hasMore = response.has_more;
    } catch (searchError) {
      error = searchError.message;
    } finally {
      loadingMore = false;
    }
  }

  function clearSearch() {
    results = [];
    searched = false;
    loading = false;
    loadingMore = false;
    error = "";
    nextOffset = null;
    hasMore = false;
    lastSearch = { query: "", mode, chapter: "", date: "" };
  }

  function browseToSearch(selectedChapter) {
    chapter = selectedChapter;
    subTab = "search";
    if (query.trim()) {
      runSearch({ query, mode, chapter: selectedChapter, date });
      return;
    }
    results = [];
    searched = false;
    error = "";
    nextOffset = null;
    hasMore = false;
  }
</script>

<div class="page-heading">
  <div>
    <p class="eyebrow">Laws of Trinidad and Tobago</p>
    <h1>Research</h1>
  </div>
  <p class="coverage">{chapters.length || "—"} chapters · historical versions included</p>
</div>

<div class="tab-bar" role="tablist" aria-label="Research tools">
  <button
    role="tab"
    aria-selected={subTab === "search"}
    class:active={subTab === "search"}
    onclick={() => (subTab = "search")}
  >Search</button>
  <button
    role="tab"
    aria-selected={subTab === "lookup"}
    class:active={subTab === "lookup"}
    onclick={() => (subTab = "lookup")}
  >Section lookup</button>
  <button
    role="tab"
    aria-selected={subTab === "browse"}
    class:active={subTab === "browse"}
    onclick={() => (subTab = "browse")}
  >Browse chapters</button>
</div>

{#if chapterLoadError}
  <p class="chapter-load-error" role="alert">Chapter list unavailable: {chapterLoadError}</p>
{/if}

{#if subTab === "search"}
  <SearchBar
    {chapters}
    onSearch={runSearch}
    onClear={clearSearch}
    bind:query
    bind:mode
    bind:chapter
    bind:date
  />

  {#if loading}
    <div class="loading-state" role="status">Searching provisions…</div>
  {:else if error && results.length === 0}
    <div class="message error" role="alert">Search unavailable: {error}</div>
  {:else if searched && results.length === 0}
    <div class="message">No matching provisions found.</div>
  {:else if results.length}
    <div class="result-summary">
      <p>
        Found <strong>{results.length}</strong> provision{results.length === 1 ? "" : "s"}
        {#if uniqueResultChapters > 1}
          across <strong>{uniqueResultChapters}</strong> chapters
        {:else if uniqueResultChapters === 1}
          in <strong>Chapter {results[0].chapter_number}</strong>
        {/if}
        {#if lastSearch.query}for &ldquo;{lastSearch.query}&rdquo;{/if}
        {#if hasMore}&mdash; more available{/if}
      </p>
      {#if lastSearch.date}<span>Available as at {lastSearch.date}</span>{/if}
    </div>

    {#each results as item (item.key)}
      <ResultCard
        {item}
        query={lastSearch.query}
        historicalDate={lastSearch.date}
      />
    {/each}

    {#if error}
      <div class="message error" role="alert">More results unavailable: {error}</div>
    {/if}

    {#if hasMore}
      <button class="load-more" type="button" onclick={loadMore} disabled={loadingMore}>
        <ChevronDown size={17} aria-hidden="true" />
        {loadingMore ? "Loading…" : "Load more provisions"}
      </button>
    {/if}
  {/if}
{:else if subTab === "lookup"}
  <LookupPanel {chapters} />
{:else if subTab === "browse"}
  <ChapterBrowser {chapters} onSelect={browseToSearch} />
{/if}

<style>
  .page-heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 18px;
  }
  .eyebrow {
    margin: 0 0 2px;
    color: var(--muted);
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
  }
  h1 {
    margin: 0;
    color: var(--text);
    font-size: 1.55rem;
    line-height: 1.2;
  }
  .coverage {
    margin: 0;
    color: var(--muted);
    font-size: 0.78rem;
  }
  .tab-bar {
    display: flex;
    margin-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }
  .tab-bar button {
    padding: 9px 16px;
    border: 0;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: var(--muted-strong);
    font-size: 0.84rem;
    font-weight: 700;
    cursor: pointer;
  }
  .tab-bar button.active {
    border-bottom-color: var(--accent);
    color: var(--text);
  }
  .tab-bar button:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .result-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin: 0 0 10px;
    color: var(--muted);
    font-size: 0.8rem;
  }
  .result-summary p { margin: 0; }
  .result-summary span { color: var(--muted-strong); }
  .loading-state,
  .message {
    padding: 44px 16px;
    color: var(--muted);
    text-align: center;
  }
  .message.error { color: var(--danger); }
  .load-more {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    width: 100%;
    min-height: 42px;
    margin-top: 8px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--text);
    font-weight: 700;
    cursor: pointer;
  }
  .load-more:hover:not(:disabled) { border-color: var(--accent); }
  .load-more:disabled { cursor: wait; opacity: 0.45; }
  .chapter-load-error {
    margin: 0 0 12px;
    color: var(--danger);
    font-size: var(--text-xs);
  }
  @media (max-width: 600px) {
    .page-heading { align-items: flex-start; flex-direction: column; gap: 5px; }
    .tab-bar button { flex: 1; padding-inline: 8px; }
    .result-summary { align-items: flex-start; flex-direction: column; gap: 3px; }
  }
</style>
