<script>
  import { onMount } from "svelte";
  import { ChevronDown } from "@lucide/svelte";
  import { getChapters, searchGrouped } from "../lib/api.js";
  import { router, setTab } from "../lib/router.svelte.js";
  import PageHeader from "../components/layout/PageHeader.svelte";
  import SearchBar from "../components/SearchBar.svelte";
  import ResultCard from "../components/ResultCard.svelte";
  import LookupPanel from "../components/LookupPanel.svelte";
  import ChapterBrowser from "../components/ChapterBrowser.svelte";

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

  const subTab = $derived(router.tab);

  onMount(async () => {
    try {
      chapters = await getChapters();
    } catch (loadError) {
      console.error("Failed to load chapters", loadError);
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
    setTab("search");
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

<PageHeader
  eyebrow="Laws of Trinidad and Tobago"
  title="Research"
  meta="533 chapters · historical versions included"
/>

<div class="tab-bar" role="tablist" aria-label="Research tools">
  <button
    role="tab"
    aria-selected={subTab === "search"}
    class:active={subTab === "search"}
    onclick={() => setTab("search")}
  >Search</button>
  <button
    role="tab"
    aria-selected={subTab === "lookup"}
    class:active={subTab === "lookup"}
    onclick={() => setTab("lookup")}
  >Section lookup</button>
  <button
    role="tab"
    aria-selected={subTab === "browse"}
    class:active={subTab === "browse"}
    onclick={() => setTab("browse")}
  >Browse chapters</button>
</div>

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
      <p>Showing {results.length} provision{results.length === 1 ? "" : "s"}</p>
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
      <button class="load-more btn btn-secondary" type="button" onclick={loadMore} disabled={loadingMore}>
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
  .tab-bar {
    display: flex;
    margin-bottom: var(--space-3);
    border-bottom: 1px solid var(--border);
  }
  .tab-bar button {
    padding: 9px var(--space-4);
    border: 0;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: var(--muted-strong);
    font-size: 0.84rem;
    font-weight: var(--weight-semibold);
    cursor: pointer;
    transition: color var(--dur-fast) var(--ease);
  }
  .tab-bar button:hover { color: var(--text); }
  .tab-bar button.active {
    border-bottom-color: var(--accent);
    color: var(--text);
  }
  .result-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    margin: 0 0 var(--space-3);
    color: var(--muted);
    font-size: 0.8rem;
  }
  .result-summary p { margin: 0; }
  .result-summary span { color: var(--muted-strong); }
  .loading-state,
  .message {
    padding: var(--space-12) var(--space-4);
    color: var(--muted);
    text-align: center;
  }
  .message.error { color: var(--danger); }
  .load-more {
    width: 100%;
    min-height: 42px;
    margin-top: var(--space-2);
  }
  .load-more:disabled { cursor: wait; opacity: 0.65; }
  @media (max-width: 600px) {
    .tab-bar button { flex: 1; padding-inline: var(--space-2); }
    .result-summary { align-items: flex-start; flex-direction: column; gap: 3px; }
  }
</style>
