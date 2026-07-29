<script>
  import { lookupSection } from "../lib/api.js";

  let { chapters = [] } = $props();

  let chapter = $state("");
  let section = $state("");
  let date = $state("");
  let results = $state(null);
  let loading = $state(false);
  let error = $state("");

  async function submit() {
    if (!chapter.trim() || !section.trim()) return;
    loading = true;
    error = "";
    results = null;
    try {
      results = await lookupSection(chapter.trim(), section.trim(), date.trim());
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function onKeydown(e) {
    if (e.key === "Enter") submit();
  }
</script>

<div class="lookup-section">
  <div class="lookup-row">
    <input type="text" bind:value={chapter} placeholder="Chapter (e.g. 8:08)" list="chapter-list-lookup" />
    <datalist id="chapter-list-lookup">
      {#each chapters as c (c.chapter)}
        <option value={c.chapter}></option>
      {/each}
    </datalist>
    <input
      type="text"
      bind:value={section}
      onkeydown={onKeydown}
      placeholder="Section (e.g. 1, 3A, 24(1))"
    />
    <input
      type="text"
      bind:value={date}
      placeholder="As at date (e.g. 2016-12-31)"
      title="Leave empty for all versions"
    />
    <button onclick={submit}>Look up</button>
  </div>
</div>

<div class="version-timeline">
  {#if loading}
    <div class="spinner"></div>
  {:else if error}
    <div class="no-results">Error: {error}</div>
  {:else if results && results.length === 0}
    <div class="no-results">No versions found for this provision.</div>
  {:else if results}
    <p class="count">{results.length} version{results.length > 1 ? "s" : ""}</p>
    {#each results as r}
      <div class="version-entry">
        <div class="date">
          {r.as_at_date || "No date"}
          {#if r.version_label}— {r.version_label}{/if}
        </div>
        <div class="result-text">{r.chunk_text}</div>
        {#if r.pdf_url}
          <div class="source-link">
            📄 <a href={r.pdf_url} target="_blank" rel="noopener">View official PDF on laws.gov.tt</a>
          </div>
        {/if}
      </div>
    {/each}
  {/if}
</div>

<style>
  .lookup-section { margin-top: 8px; }
  .lookup-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .lookup-row input {
    padding: 8px 12px; font-size: 0.9rem;
    border: 1px solid var(--border); border-radius: var(--radius);
  }
  .lookup-row button {
    padding: 8px 16px; font-size: 0.85rem; font-weight: 600;
    background: var(--accent); color: var(--accent-text);
    border: none; border-radius: var(--radius); cursor: pointer;
  }
  .version-timeline { margin-top: 16px; }
  .version-entry {
    padding: 10px 12px; margin-bottom: 6px;
    border-left: 3px solid var(--accent-light);
    background: var(--surface);
    font-size: 0.85rem;
  }
  .version-entry .date { font-weight: 600; color: var(--accent); }
  .result-text { white-space: pre-wrap; word-break: break-word; margin-top: 4px; }
  .source-link { font-size: 0.78rem; margin-top: 6px; }
  .source-link a { color: var(--accent-light); }
  .no-results { text-align: center; padding: 48px 16px; color: var(--muted); }
  .count { font-size: 0.85rem; color: var(--muted); margin-bottom: 12px; }
  .spinner { text-align: center; padding: 32px; color: var(--muted); }
</style>
