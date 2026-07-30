<script>
  import { History } from "@lucide/svelte";

  let {
    versions = [],
    selectedDownloadId,
    disabled = false,
    onSelect,
  } = $props();

  function handleChange(event) {
    const downloadId = Number(event.currentTarget.value);
    const version = versions.find((item) => item.download_id === downloadId);
    if (version) onSelect(version);
  }

  function versionLabel(version, index) {
    const parts = [];
    if (index === 0 && version.as_at_date) parts.push("Latest available");
    if (version.as_at_date) parts.push(version.as_at_date);
    else parts.push("Date unavailable");
    if (version.version_label) parts.push(version.version_label);
    return parts.join(" · ");
  }
</script>

{#if versions.length > 1}
  <label class="version-control">
    <History size={16} aria-hidden="true" />
    <span>Version</span>
    <select
      value={selectedDownloadId}
      onchange={handleChange}
      {disabled}
      aria-label="Select provision version"
    >
      {#each versions as version, index (version.download_id)}
        <option value={version.download_id}>
          {versionLabel(version, index)}
        </option>
      {/each}
    </select>
  </label>
{/if}

<style>
  .version-control {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    color: var(--muted-strong);
    font-size: 0.8rem;
    font-weight: 600;
  }
  .version-control select {
    min-width: 0;
    max-width: 300px;
    padding: 7px 30px 7px 10px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    background: var(--bg);
    color: var(--text);
    font-size: 0.8rem;
  }
  .version-control select:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  @media (max-width: 600px) {
    .version-control {
      align-items: flex-start;
      flex-wrap: wrap;
    }
    .version-control select {
      width: 100%;
      max-width: none;
    }
  }
</style>
