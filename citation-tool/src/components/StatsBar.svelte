<script>
  import { onMount } from "svelte";
  import { getStats } from "../lib/api.js";

  let stats = $state(null);
  let error = $state("");

  onMount(async () => {
    try {
      stats = await getStats();
    } catch (e) {
      error = e.message;
    }
  });
</script>

<div class="stats-bar">
  {#if error}
    <span class="error">Stats unavailable: {error}</span>
  {:else if stats}
    <span>Chapters: <strong>{stats.chapters}</strong></span>
    <span>Versions: <strong>{stats.versions}</strong></span>
    <span>Chunks: <strong>{stats.chunks.toLocaleString()}</strong></span>
    <span>Embedded: <strong>{stats.embedded.toLocaleString()}</strong></span>
  {:else}
    <span>Loading stats…</span>
  {/if}
</div>

<style>
  .stats-bar {
    display: flex;
    gap: 24px;
    padding: 12px 0;
    font-size: 0.8rem;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    margin-bottom: 20px;
    flex-wrap: wrap;
  }
  .stats-bar strong { color: var(--text); }
  .error { color: #b3261e; }
</style>
