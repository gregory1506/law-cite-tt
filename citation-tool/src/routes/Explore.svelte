<script>
  import { onMount } from "svelte";
  import { getChapters, search } from "../lib/api.js";
  import StatsBar from "../components/StatsBar.svelte";
  import SearchBar from "../components/SearchBar.svelte";
  import ResultCard from "../components/ResultCard.svelte";
  import LookupPanel from "../components/LookupPanel.svelte";
  import ChapterBrowser from "../components/ChapterBrowser.svelte";

  let subTab = $state("search");
  let chapters = $state([]);
  let results = $state(null);
  let loading = $state(false);
  let error = $state("");
  let lastQuery = $state("");
  let searchChapterField = $state("");

  onMount(async () => {
    try {
      chapters = await getChapters();
    } catch (e) {
      // chapter list is a nice-to-have (autocomplete); don't block the page on it
      console.error("Failed to load chapters", e);
    }
  });

  async function runSearch({ query, mode, chapter }) {
    loading = true;
    error = "";
    results = null;
    lastQuery = query;
    try {
      results = await search(query, { mode, chapter, limit: 20 });
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function browseToSearch(chapter) {
    searchChapterField = chapter;
    subTab = "search";
  }
</script>

<StatsBar />

<div class="tab-bar">
  <button class:active={subTab === "search"} onclick={() => (subTab = "search")}>Search</button>
  <button class:active={subTab === "lookup"} onclick={() => (subTab = "lookup")}>Section Lookup</button>
  <button class:active={subTab === "browse"} onclick={() => (subTab = "browse")}>Browse Chapters</button>
</div>

{#if subTab === "search"}
  <SearchBar {chapters} onSearch={runSearch} initialChapter={searchChapterField} />
  {#if loading}
    <div class="spinner"></div>
  {:else if error}
    <div class="no-results">Error: {error}</div>
  {:else if results && results.length === 0}
    <div class="no-results">No matching provisions found.</div>
  {:else if results}
    <p class="count">{results.length} result{results.length > 1 ? "s" : ""}</p>
    {#each results as r (r.id ?? r.chapter_number + r.section_ref + r.as_at_date)}
      <ResultCard result={r} query={lastQuery} />
    {/each}
  {/if}
{:else if subTab === "lookup"}
  <LookupPanel {chapters} />
{:else if subTab === "browse"}
  <ChapterBrowser {chapters} onSelect={browseToSearch} />
{/if}

<style>
  .tab-bar { display: flex; gap: 0; margin-bottom: 16px; }
  .tab-bar button {
    padding: 10px 20px; font-size: 0.85rem; font-weight: 600;
    border: 1px solid var(--border); background: var(--bg);
    cursor: pointer;
  }
  .tab-bar button:first-child { border-radius: var(--radius) 0 0 var(--radius); }
  .tab-bar button:last-child { border-radius: 0 var(--radius) var(--radius) 0; }
  .tab-bar button.active { background: var(--accent); color: #fff; border-color: var(--accent); }
  .no-results { text-align: center; padding: 48px 16px; color: var(--muted); }
  .count { font-size: 0.85rem; color: var(--muted); margin-bottom: 12px; }
  .spinner { text-align: center; padding: 32px; color: var(--muted); }
</style>
