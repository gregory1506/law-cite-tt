<script>
  import {
    AlertTriangle,
    Check,
    Clipboard,
    ExternalLink,
    FileCheck2,
    FileText,
    Search,
  } from "@lucide/svelte";
  import { onMount } from "svelte";
  import { getChapters, resolveCitation, resolveUrl } from "../lib/api.js";


  let chapters = $state([]);
  let chapter = $state("");
  let section = $state("");
  let date = $state("");
  let result = $state(null);
  let loading = $state(false);
  let error = $state("");
  let copied = $state("");

  onMount(async () => {
    try {
      chapters = await getChapters();
    } catch {
      chapters = [];
    }
  });

  function normalizedChapter(value) {
    const stripped = value.trim().replace(/^chap(?:ter)?\.?\s*/i, "");
    const match = stripped.match(/^(\d{1,3})\s*[:/.\-\s]\s*(\d{1,3})$/);
    return match ? `${Number(match[1])}:${match[2].padStart(2, "0")}` : value.trim();
  }

  function normalizedSection(value) {
    const stripped = value
      .trim()
      .replace(/^(?:sections?|ss?|s)\.?\s*/i, "")
      .replace(/\s+/g, "");
    const match = stripped.match(/^(\d+)([a-z]?)(.*)$/i);
    if (!match) return value.trim();
    const nested = match[3].replace(/\(([a-z]+)\)/gi, (_, letters) => `(${letters.toLowerCase()})`);
    return `${Number(match[1])}${match[2].toUpperCase()}${nested}`;
  }

  async function submit() {
    if (!chapter.trim() || !section.trim()) return;
    loading = true;
    error = "";
    copied = "";
    result = null;
    const requestChapter = normalizedChapter(chapter);
    const requestSection = normalizedSection(section);
    try {
      result = await resolveCitation(requestChapter, requestSection, date);
      chapter = result.normalized_input?.chapter || requestChapter;
      section = result.normalized_input?.section || requestSection;
    } catch (resolveError) {
      error = resolveError.message;
    } finally {
      loading = false;
    }
  }

  function onKeydown(event) {
    if (event.key === "Enter") submit();
  }

  async function copyCitation(value, label) {
    try {
      await navigator.clipboard.writeText(value);
      copied = label;
    } catch {
      error = "Copy failed. Select the citation text and copy it manually.";
    }
  }

  function displayDate(value) {
    if (!value) return "Date unavailable";
    return new Intl.DateTimeFormat("en-TT", {
      year: "numeric",
      month: "long",
      day: "numeric",
      timeZone: "UTC",
    }).format(new Date(`${value}T00:00:00Z`));
  }

  function chooseAlternative(alternative) {
    chapter = alternative.chapter_number;
    if (alternative.section_ref) section = alternative.section_ref;
    result = null;
  }
</script>

<header class="page-heading">
  <div>
    <p class="eyebrow">Source-backed citation check</p>
    <h1>Validate a citation</h1>
    <p>
      Resolve a Trinidad and Tobago statutory provision against exact source
      text, then copy a consistent citation.
    </p>
  </div>
  <div class="heading-mark" aria-hidden="true"><FileCheck2 size={25} /></div>
</header>

<section class="resolver-panel" aria-labelledby="citation-form-heading">
  <div class="panel-intro">
    <h2 id="citation-form-heading">Statutory reference</h2>
    <p>Chapter and section are required. Use a date only for historical research.</p>
  </div>
  <div class="form-grid">
    <label>
      <span>Chapter</span>
      <input
        type="text"
        bind:value={chapter}
        placeholder="e.g. 8:08"
        list="citation-chapters"
        autocomplete="off"
      />
    </label>
    <datalist id="citation-chapters">
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
        placeholder="e.g. 12(3)(a)"
      />
    </label>
    <label>
      <span>Available as at <small>Optional</small></span>
      <input type="date" bind:value={date} onkeydown={onKeydown} />
    </label>
    <button
      class="validate-button"
      type="button"
      onclick={submit}
      disabled={loading || !chapter.trim() || !section.trim()}
    >
      <Search size={17} aria-hidden="true" />
      {loading ? "Validating…" : "Validate citation"}
    </button>
  </div>
</section>

<div class="state-region" aria-live="polite">
  {#if loading}
    <div class="state-card waiting" role="status">
      <span class="state-icon"><Search size={20} /></span>
      <div>
        <strong>Validating citation…</strong>
        <p>Checking the chapter, provision, and eligible source version.</p>
      </div>
    </div>
  {:else if error}
    <div class="state-card error-state" role="alert">
      <span class="state-icon"><AlertTriangle size={20} /></span>
      <div>
        <strong>Citation check unavailable</strong>
        <p>{error}</p>
      </div>
    </div>
  {:else if result?.status === "not_found"}
    <div class="state-card not-found">
      <span class="state-icon"><Search size={20} /></span>
      <div>
        <strong>Citation not found</strong>
        <p>
          No exact source text was found for Chap. {result.normalized_input.chapter},
          s. {result.normalized_input.section}{result.normalized_input.date
            ? ` by ${displayDate(result.normalized_input.date)}`
            : ""}.
        </p>
      </div>
    </div>
    {#if result.alternatives?.length}
      <section class="alternatives" aria-labelledby="alternatives-heading">
        <h2 id="alternatives-heading">Nearby references</h2>
        <div>
          {#each result.alternatives as alternative}
            <button type="button" onclick={() => chooseAlternative(alternative)}>
              <span>{alternative.title}</span>
              <strong>
                Chap. {alternative.chapter_number}{alternative.section_ref
                  ? `, s. ${alternative.section_ref}`
                  : ""}
              </strong>
            </button>
          {/each}
        </div>
      </section>
    {/if}
  {:else if result?.status === "ambiguous"}
    <div class="state-card ambiguous">
      <span class="state-icon"><AlertTriangle size={20} /></span>
      <div>
        <strong>Citation ambiguous</strong>
        <p>
          More than one materially different source row matches this reference.
          Review the alternatives before relying on it.
        </p>
      </div>
    </div>
    {#if result.alternatives?.length}
      <section class="alternatives" aria-labelledby="ambiguous-heading">
        <h2 id="ambiguous-heading">Matching source records</h2>
        <div>
          {#each result.alternatives as alternative}
            <button type="button" onclick={() => chooseAlternative(alternative)}>
              <span>{alternative.title}</span>
              <strong>Chap. {alternative.chapter_number}, s. {alternative.section_ref}</strong>
              <small>
                {alternative.as_at_date
                  ? `Available as at ${displayDate(alternative.as_at_date)}`
                  : "Date unavailable"}
              </small>
            </button>
          {/each}
        </div>
      </section>
    {/if}
  {:else if result?.status === "found"}
    <div class="state-card found">
      <span class="state-icon"><Check size={20} /></span>
      <div>
        <strong>Citation found</strong>
        <p>
          Resolved to an exact provision in the available statutory source corpus.
        </p>
      </div>
    </div>

    <article class="result-card">
      <header class="authority-header">
        <div>
          <p class="authority-label">
            {result.normalized_input.date
              ? `Available as at ${displayDate(result.normalized_input.date)}`
              : "Latest available"}
          </p>
          <h2>{result.authority.title}</h2>
          <p class="authority-ref">
            Chap. {result.authority.chapter_number} · Section {result.authority.section_ref}
          </p>
          {#if result.authority.heading}<p class="heading">{result.authority.heading}</p>{/if}
        </div>
        <a href={resolveUrl(result.authority.pdf_url)} target="_blank" rel="noopener">

          <FileText size={16} aria-hidden="true" />
          Official PDF
          <ExternalLink size={14} aria-hidden="true" />
        </a>
      </header>

      <section class="citation-output" aria-labelledby="citation-output-heading">
        <div class="section-title">
          <h3 id="citation-output-heading">Copy citation</h3>
          <span role="status">{copied ? `${copied} copied` : ""}</span>
        </div>
        <div class="citation-row">
          <div>
            <span>Full citation</span>
            <p>{result.citation.full}</p>
          </div>
          <button
            type="button"
            aria-label="Copy full citation"
            onclick={() => copyCitation(result.citation.full, "Full citation")}
          >
            <Clipboard size={16} aria-hidden="true" />
            Copy
          </button>
        </div>
        <div class="citation-row">
          <div>
            <span>Short citation</span>
            <p>{result.citation.short}</p>
          </div>
          <button
            type="button"
            aria-label="Copy short citation"
            onclick={() => copyCitation(result.citation.short, "Short citation")}
          >
            <Clipboard size={16} aria-hidden="true" />
            Copy
          </button>
        </div>
      </section>

      <section class="source-text" aria-labelledby="source-text-heading">
        <div class="section-title">
          <h3 id="source-text-heading">Exact statutory text</h3>
          <span>
            {result.authority.as_at_date
              ? displayDate(result.authority.as_at_date)
              : "Source date unavailable"}
          </span>
        </div>
        <div class="text-frame">{result.text}</div>
        {#if result.authority.version_label}
          <p class="version-label">{result.authority.version_label}</p>
        {/if}
      </section>
    </article>
  {/if}
</div>

<p class="scope-note">
  LawCite confirms whether a reference resolves in its source corpus. It does
  not claim that a provision is currently in force.
</p>

<style>
  .page-heading {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
    margin-bottom: 22px;
  }
  .eyebrow {
    margin: 0 0 7px;
    color: var(--accent);
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .page-heading h1 { margin: 0; font-size: clamp(1.6rem, 3vw, 2.15rem); line-height: 1.1; }
  .page-heading p:not(.eyebrow) { max-width: 650px; margin: 9px 0 0; color: var(--muted-strong); }
  .heading-mark {
    display: grid;
    width: 50px;
    height: 50px;
    flex: 0 0 auto;
    place-items: center;
    border: 1px solid rgba(34, 211, 238, 0.35);
    border-radius: var(--radius);
    background: linear-gradient(145deg, rgba(34, 211, 238, 0.12), rgba(34, 211, 238, 0.02));
    color: var(--accent);
  }
  .resolver-panel {
    position: relative;
    overflow: hidden;
    padding: 18px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background:
      linear-gradient(90deg, rgba(34, 211, 238, 0.045) 1px, transparent 1px) 0 0 / 32px 32px,
      var(--surface);
  }
  .resolver-panel::before {
    position: absolute;
    inset: 0 auto 0 0;
    width: 3px;
    background: var(--accent);
    content: "";
  }
  .panel-intro { margin-bottom: 15px; }
  .panel-intro h2 { margin: 0; font-size: 0.94rem; }
  .panel-intro p { margin: 4px 0 0; color: var(--muted); font-size: 0.78rem; }
  .form-grid {
    display: grid;
    grid-template-columns: minmax(170px, 1fr) minmax(150px, 0.8fr) minmax(180px, 0.9fr) auto;
    align-items: end;
    gap: 10px;
  }
  label { display: grid; gap: 6px; color: var(--muted-strong); font-size: 0.72rem; font-weight: 750; }
  label small { margin-left: 4px; color: var(--muted); font-size: 0.65rem; font-weight: 600; }
  input {
    width: 100%;
    min-width: 0;
    min-height: 42px;
    padding: 10px 11px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    background: var(--bg);
    color: var(--text);
  }
  input:focus-visible, button:focus-visible, a:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .validate-button {
    display: inline-flex;
    min-height: 42px;
    align-items: center;
    justify-content: center;
    gap: 7px;
    padding: 9px 16px;
    border: 0;
    border-radius: var(--radius);
    background: var(--accent);
    color: var(--accent-text);
    font-weight: 800;
    cursor: pointer;
  }
  .validate-button:disabled { cursor: not-allowed; opacity: 0.45; }
  .state-region { margin-top: 16px; }
  .state-card {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 14px 16px;
    border: 1px solid var(--border);
    border-left-width: 3px;
    border-radius: var(--radius);
    background: var(--surface);
  }
  .state-card .state-icon { display: grid; place-items: center; margin-top: 1px; }
  .state-card strong { display: block; font-size: 0.9rem; }
  .state-card p { margin: 3px 0 0; color: var(--muted-strong); font-size: 0.8rem; }
  .state-card.found { border-left-color: var(--positive); }
  .state-card.found .state-icon { color: var(--positive); }
  .state-card.ambiguous { border-left-color: #fbbf24; }
  .state-card.ambiguous .state-icon { color: #fbbf24; }
  .state-card.error-state { border-left-color: var(--danger); }
  .state-card.error-state .state-icon { color: var(--danger); }
  .state-card.not-found, .state-card.waiting { border-left-color: var(--accent); }
  .state-card.not-found .state-icon, .state-card.waiting .state-icon { color: var(--accent); }
  .result-card {
    margin-top: 10px;
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
  }
  .authority-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 18px;
    padding: 20px;
    border-bottom: 1px solid var(--border);
    background: linear-gradient(145deg, rgba(34, 211, 238, 0.06), transparent 50%);
  }
  .authority-header h2 { margin: 3px 0 0; font-size: 1.23rem; }
  .authority-label {
    margin: 0;
    color: var(--positive);
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .authority-ref { margin: 5px 0 0; color: var(--accent); font-size: 0.8rem; font-weight: 750; }
  .heading { margin: 3px 0 0; color: var(--muted-strong); font-size: 0.82rem; }
  .authority-header a {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    color: var(--text-soft);
    font-size: 0.76rem;
    font-weight: 700;
    text-decoration: none;
  }
  .citation-output, .source-text { padding: 18px 20px; }
  .source-text { border-top: 1px solid var(--border); }
  .section-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
  }
  .section-title h3 { margin: 0; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.06em; }
  .section-title span { color: var(--muted); font-size: 0.72rem; }
  .citation-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding: 11px 12px;
    border: 1px solid var(--border);
    background: var(--bg);
  }
  .citation-row + .citation-row { border-top: 0; }
  .citation-row span { color: var(--muted); font-size: 0.66rem; font-weight: 700; text-transform: uppercase; }
  .citation-row p { margin: 2px 0 0; color: var(--text); font-family: Georgia, "Times New Roman", serif; font-size: 0.92rem; }
  .citation-row button {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    gap: 6px;
    padding: 7px 9px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    background: var(--surface-raised);
    color: var(--text-soft);
    font-size: 0.72rem;
    font-weight: 750;
    cursor: pointer;
  }
  .text-frame {
    max-height: 470px;
    overflow: auto;
    padding: 16px;
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--text-soft);
    font-family: Georgia, "Times New Roman", serif;
    font-size: 0.9rem;
    line-height: 1.68;
    white-space: pre-wrap;
  }
  .version-label { margin: 8px 0 0; color: var(--muted); font-size: 0.72rem; }
  .alternatives { margin-top: 10px; padding: 16px; border: 1px solid var(--border); background: var(--surface); }
  .alternatives h2 { margin: 0 0 10px; font-size: 0.86rem; }
  .alternatives > div { display: grid; gap: 7px; }
  .alternatives button {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 12px;
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--text);
    text-align: left;
    cursor: pointer;
  }
  .alternatives span { color: var(--text-soft); }
  .alternatives strong { color: var(--accent); font-size: 0.78rem; }
  .alternatives small { color: var(--muted); }
  .scope-note { margin: 18px 0 0; color: var(--muted); font-size: 0.72rem; text-align: center; }
  @media (max-width: 850px) {
    .form-grid { grid-template-columns: 1fr 1fr; }
    .validate-button { min-height: 44px; }
  }
  @media (max-width: 560px) {
    .heading-mark { display: none; }
    .resolver-panel { padding: 16px 14px; }
    .form-grid { grid-template-columns: 1fr; }
    .authority-header { display: grid; padding: 17px 15px; }
    .authority-header a { width: fit-content; }
    .citation-output, .source-text { padding: 15px; }
    .citation-row { align-items: flex-start; }
    .citation-row p { overflow-wrap: anywhere; }
    .citation-row button { padding: 8px; }
    .alternatives button { align-items: flex-start; flex-direction: column; }
  }
</style>
