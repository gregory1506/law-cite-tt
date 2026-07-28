<script>
  let { result, query = "" } = $props();

  function escapeRegExp(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function highlighted(text, q) {
    if (!q) return text;
    const words = q.split(/\s+/).filter((w) => w.length > 2);
    let out = text;
    for (const w of words) {
      const re = new RegExp(`(${escapeRegExp(w)})`, "gi");
      out = out.replace(re, "<mark>$1</mark>");
    }
    return out;
  }
</script>

<div class="result-card">
  <div class="result-meta">
    <span class="chapter">{result.chapter_number || ""}</span>
    <span class="section">s{result.section_ref || ""}</span>
    {#if result.as_at_date}<span>{result.as_at_date}</span>{/if}
    {#if result.score != null}<span>score: {result.score.toFixed(4)}</span>{/if}
  </div>
  <div class="result-text">{@html highlighted(result.chunk_text || "", query)}</div>
  {#if result.pdf_url}
    <div class="source-link">
      📄 <a href={result.pdf_url} target="_blank" rel="noopener">View official PDF on laws.gov.tt</a>
    </div>
  {/if}
</div>

<style>
  .result-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    margin-bottom: 12px;
  }
  .result-meta {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    font-size: 0.8rem;
    color: var(--muted);
    margin-bottom: 8px;
  }
  .result-meta .chapter { font-weight: 600; color: var(--accent); }
  .result-meta .section { font-weight: 600; }
  .result-text {
    font-size: 0.9rem;
    line-height: 1.65;
    max-height: 160px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .result-text :global(mark) {
    background: var(--highlight);
    padding: 0 2px;
  }
  .source-link { font-size: 0.78rem; margin-top: 6px; }
  .source-link a { color: var(--accent-light); }
</style>
