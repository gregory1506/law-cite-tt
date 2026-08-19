<script>
  import {
    ChevronDown,
    ChevronUp,
    ExternalLink,
    FileText,
  } from "@lucide/svelte";
  import { lookupSection, resolveUrl } from "../lib/api.js";

  import { excerptAroundQuery, highlightSegments } from "../lib/text.js";
  import VersionSelector from "./VersionSelector.svelte";

  let { item, query = "", historicalDate = "" } = $props();

  let expanded = $state(false);
  let loadingVersion = $state(false);
  let versionError = $state("");
  let selectedVersion = $state(null);
  const activeVersion = $derived(selectedVersion || item.matched_version);

  const isLatest = $derived(
    item.latest_available?.download_id === activeVersion.download_id,
  );
  const authorityLabel = $derived(
    historicalDate
      ? `Available as at ${historicalDate}`
      : isLatest
        ? "Latest available"
        : activeVersion.as_at_date
          ? "Historical version"
          : "Date unavailable",
  );
  const visibleText = $derived(
    expanded
      ? activeVersion.chunk_text
      : excerptAroundQuery(activeVersion.chunk_text, query),
  );
  const segments = $derived(highlightSegments(visibleText, query));
  const canExpand = $derived((activeVersion.chunk_text || "").trim().length > 620);

  async function selectVersion(version) {
    versionError = "";
    if (version.download_id === item.matched_version.download_id) {
      selectedVersion = null;
      expanded = false;
      return;
    }

    loadingVersion = true;
    try {
      const rows = await lookupSection(
        item.chapter_number,
        item.section_ref,
        "",
        version.download_id,
      );
      if (!rows.length) throw new Error("Version text is unavailable.");
      selectedVersion = {
        ...version,
        chunk_text: rows.map((row) => row.chunk_text).join("\n\n"),
        pdf_url: rows[0].pdf_url || version.pdf_url,
      };
      expanded = false;
    } catch (error) {
      versionError = error.message;
    } finally {
      loadingVersion = false;
    }
  }

  function displayDate(value) {
    if (!value) return "";
    return new Intl.DateTimeFormat("en-TT", {
      year: "numeric",
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    }).format(new Date(`${value}T00:00:00Z`));
  }
</script>

<article class="result-card">
  <header>
    <div class="authority">
      <p class="title">{item.title || "Title unavailable"}</p>
      <div class="reference">
        <span>Chap. {item.chapter_number}</span>
        {#if item.section_ref}<span>Section {item.section_ref}</span>{/if}
      </div>
    </div>
    <span class:latest={isLatest} class="status">{authorityLabel}</span>
  </header>

  <div class="version-meta">
    {#if activeVersion.as_at_date}
      <span>As at {displayDate(activeVersion.as_at_date)}</span>
    {/if}
    {#if activeVersion.version_label}
      <span>{activeVersion.version_label}</span>
    {/if}
    {#if item.heading}
      <span>{item.heading}</span>
    {/if}
  </div>

  <div class="excerpt" class:expanded>
    {#each segments as segment}
      {#if segment.match}<mark>{segment.text}</mark>{:else}{segment.text}{/if}
    {/each}
  </div>

  {#if versionError}
    <p class="version-error" role="alert">{versionError}</p>
  {/if}

  <footer>
    <div class="actions">
      {#if canExpand}
        <button
          class="text-button"
          type="button"
          onclick={() => (expanded = !expanded)}
          aria-expanded={expanded}
        >
          {#if expanded}
            <ChevronUp size={16} aria-hidden="true" />
            Show excerpt
          {:else}
            <ChevronDown size={16} aria-hidden="true" />
            Read provision
          {/if}
        </button>
      {/if}
      {#if activeVersion.pdf_url}
        <a
          class="source-link"
          href={resolveUrl(activeVersion.pdf_url)}
          target="_blank"
          rel="noopener"
        >

          <FileText size={16} aria-hidden="true" />
          Official PDF
          <ExternalLink size={14} aria-hidden="true" />
        </a>
      {/if}
    </div>
    <VersionSelector
      versions={item.versions}
      selectedDownloadId={activeVersion.download_id}
      disabled={loadingVersion}
      onSelect={selectVersion}
    />
  </footer>
</article>

<style>
  .result-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px 20px;
    margin-bottom: 12px;
  }
  header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
  }
  .authority { min-width: 0; }
  .title {
    margin: 0;
    color: var(--text);
    font-size: 1rem;
    font-weight: 700;
    line-height: 1.35;
  }
  .reference {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 4px;
    color: var(--accent);
    font-size: 0.82rem;
    font-weight: 700;
  }
  .status {
    flex: 0 0 auto;
    padding: 4px 8px;
    border: 1px solid var(--border-strong);
    border-radius: 999px;
    color: var(--muted-strong);
    font-size: 0.72rem;
    font-weight: 700;
  }
  .status.latest {
    border-color: rgba(45, 212, 191, 0.45);
    background: rgba(45, 212, 191, 0.1);
    color: var(--positive);
  }
  .version-meta {
    display: flex;
    gap: 8px 14px;
    flex-wrap: wrap;
    margin-top: 12px;
    color: var(--muted);
    font-size: 0.78rem;
  }
  .excerpt {
    margin-top: 14px;
    color: var(--text-soft);
    font-family: Georgia, "Times New Roman", serif;
    font-size: 0.98rem;
    line-height: 1.7;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .excerpt :global(mark) {
    background: var(--highlight);
    color: var(--highlight-text);
    padding: 0 2px;
  }
  .version-error {
    margin: 10px 0 0;
    color: var(--danger);
    font-size: 0.82rem;
  }
  footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px 20px;
    flex-wrap: wrap;
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }
  .actions {
    display: flex;
    align-items: center;
    gap: 8px 14px;
    flex-wrap: wrap;
  }
  .text-button,
  .source-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: 32px;
    color: var(--accent-strong);
    font-size: 0.8rem;
    font-weight: 700;
    text-decoration: none;
  }
  .text-button {
    padding: 0;
    border: 0;
    background: transparent;
    cursor: pointer;
  }
  .text-button:hover,
  .source-link:hover { color: var(--accent); }
  .text-button:focus-visible,
  .source-link:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 3px;
  }
  @media (max-width: 600px) {
    .result-card { padding: 16px; }
    header { flex-direction: column; gap: 10px; }
    .status { align-self: flex-start; }
    footer { align-items: flex-start; }
    .excerpt { font-size: 0.94rem; }
  }
</style>
