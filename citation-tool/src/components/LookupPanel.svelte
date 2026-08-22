<script>
  import {
    ChevronDown,
    ChevronUp,
    ExternalLink,
    FileText,
    History,
    Search,
  } from "@lucide/svelte";
  import { lookupSection, resolveUrl } from "../lib/api.js";
  import { formatDate } from "../lib/date.js";


  let { chapters = [] } = $props();

  let chapter = $state("");
  let section = $state("");
  let date = $state("");
  let results = $state(null);
  let loading = $state(false);
  let error = $state("");
  let showHistory = $state(false);

  const chapterTitle = $derived(
    chapters.find((item) => item.chapter === chapter)?.title || "",
  );
  const visibleResults = $derived(
    results && !showHistory ? results.slice(0, 1) : results,
  );

  async function submit() {
    if (!chapter.trim() || !section.trim()) return;
    loading = true;
    error = "";
    results = null;
    showHistory = false;
    try {
      results = await lookupSection(chapter.trim(), section.trim(), date.trim());
    } catch (lookupError) {
      error = lookupError.message;
    } finally {
      loading = false;
    }
  }

  function onKeydown(event) {
    if (event.key === "Enter") submit();
  }

</script>

<div class="lookup-section">
  <div class="lookup-grid">
    <label>
      <span>Chapter</span>
      <input
        type="text"
        bind:value={chapter}
        placeholder="e.g. 8:08"
        list="chapter-list-lookup"
      />
    </label>
    <datalist id="chapter-list-lookup">
      {#each chapters as item (item.chapter)}
        <option value={item.chapter}>{item.title}</option>
      {/each}
    </datalist>

    <label>
      <span>Section</span>
      <input
        type="text"
        bind:value={section}
        onkeydown={onKeydown}
        placeholder="e.g. 1, 3A, 24(1)"
      />
    </label>

    <label>
      <span>Available as at</span>
      <input type="date" bind:value={date} />
    </label>

    <button type="button" onclick={submit} disabled={!chapter.trim() || !section.trim()}>
      <Search size={17} aria-hidden="true" />
      Look up
    </button>
  </div>
</div>

{#if loading}
  <div class="message" role="status">Retrieving provision…</div>
{:else if error}
  <div class="message error" role="alert">Lookup unavailable: {error}</div>
{:else if results && results.length === 0}
  <div class="message">No versions found for this provision.</div>
{:else if results}
  <div class="lookup-heading">
    <div>
      <p class="title">{chapterTitle || "Title unavailable"}</p>
      <p class="reference">Chap. {chapter} · Section {section}</p>
    </div>
    <span>{results.length} version{results.length === 1 ? "" : "s"}</span>
  </div>

  <div class="version-list">
    {#each visibleResults as result, index (result.download_id + (result.as_at_date || ""))}
      <details open={index === 0}>
        <summary>
          <div>
            <strong>
              {index === 0 && !date
                ? "Latest available"
                : formatDate(result.as_at_date, { fallback: "No effective date on file" })}
            </strong>
            {#if index === 0 && !date && result.as_at_date}
              <span>As at {formatDate(result.as_at_date)}</span>
            {/if}
            {#if result.version_label}<span>{result.version_label}</span>{/if}
          </div>
          <ChevronDown class="detail-chevron" size={17} aria-hidden="true" />
        </summary>
        <div class="version-body">
          <div class="result-text">{result.chunk_text}</div>
          {#if resolveUrl(result.pdf_url)}
            <a href={resolveUrl(result.pdf_url)} target="_blank" rel="noopener">
              <FileText size={16} aria-hidden="true" />
              Official PDF
              <ExternalLink size={14} aria-hidden="true" />
            </a>
          {/if}

        </div>
      </details>
    {/each}
  </div>

  {#if results.length > 1}
    <button
      class="history-toggle"
      type="button"
      onclick={() => (showHistory = !showHistory)}
      aria-expanded={showHistory}
    >
      <History size={16} aria-hidden="true" />
      {showHistory ? "Hide historical versions" : `Show ${results.length - 1} historical version${results.length === 2 ? "" : "s"}`}
      {#if showHistory}<ChevronUp size={16} />{:else}<ChevronDown size={16} />{/if}
    </button>
  {/if}
{/if}

<style>
  .lookup-section {
    padding: 16px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
  }
  .lookup-grid {
    display: grid;
    grid-template-columns: minmax(170px, 1fr) minmax(140px, 0.7fr) minmax(165px, 0.8fr) auto;
    align-items: end;
    gap: 10px;
  }
  label {
    display: grid;
    gap: 5px;
    color: var(--muted-strong);
    font-size: 0.72rem;
    font-weight: 700;
  }
  input {
    min-width: 0;
    width: 100%;
    padding: 10px 11px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    background: var(--bg);
    color: var(--text);
    font-size: 0.86rem;
  }
  input:focus-visible {
    border-color: var(--accent);
    outline: 2px solid rgba(34, 211, 238, 0.16);
  }
  .lookup-grid button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    min-height: 40px;
    padding: 9px 16px;
    border: 0;
    border-radius: var(--radius);
    background: var(--accent);
    color: var(--accent-text);
    font-weight: 750;
    cursor: pointer;
  }
  .lookup-grid button:disabled { cursor: not-allowed; opacity: 0.45; }
  .message {
    padding: 44px 16px;
    color: var(--muted);
    text-align: center;
  }
  .message.error { color: var(--danger); }
  .lookup-heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 14px;
    margin: 22px 0 10px;
  }
  .lookup-heading p { margin: 0; }
  .lookup-heading .title { font-weight: 750; }
  .lookup-heading .reference {
    margin-top: 3px;
    color: var(--accent);
    font-size: 0.82rem;
    font-weight: 700;
  }
  .lookup-heading > span {
    color: var(--muted);
    font-size: 0.78rem;
  }
  details {
    margin-bottom: 8px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
  }
  summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding: 12px 14px;
    cursor: pointer;
    list-style: none;
  }
  summary::-webkit-details-marker { display: none; }
  summary > div {
    display: flex;
    align-items: baseline;
    gap: 7px 12px;
    flex-wrap: wrap;
  }
  summary strong { color: var(--text); font-size: 0.86rem; }
  summary span { color: var(--muted); font-size: 0.76rem; }
  details[open] :global(.detail-chevron) { transform: rotate(180deg); }
  .version-body {
    padding: 0 14px 14px;
    border-top: 1px solid var(--border);
  }
  .result-text {
    padding-top: 13px;
    color: var(--text-soft);
    font-family: Georgia, "Times New Roman", serif;
    font-size: 0.95rem;
    line-height: 1.7;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .version-body a {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 13px;
    color: var(--accent-strong);
    font-size: 0.8rem;
    font-weight: 700;
    text-decoration: none;
  }
  .history-toggle {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 8px 0;
    border: 0;
    background: transparent;
    color: var(--accent-strong);
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
  }
  @media (max-width: 760px) {
    .lookup-grid { grid-template-columns: 1fr 1fr; }
  }
  @media (max-width: 480px) {
    .lookup-grid { grid-template-columns: 1fr; }
    .lookup-heading { align-items: flex-start; flex-direction: column; gap: 4px; }
    summary > div { display: grid; gap: 2px; }
  }
</style>
