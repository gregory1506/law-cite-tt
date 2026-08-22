<script>
  import { onMount } from "svelte";
  import { getStats } from "../lib/api.js";
  import Card from "./ui/Card.svelte";

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
    <Card padded class="stat-tile">
      <span class="label">Chapters</span>
      <span class="value">{stats.chapters}</span>
    </Card>
    <Card padded class="stat-tile">
      <span class="label">Versions</span>
      <span class="value">{stats.versions}</span>
    </Card>
    <Card padded class="stat-tile">
      <span class="label">Chunks</span>
      <span class="value">{stats.chunks.toLocaleString()}</span>
    </Card>
    <Card padded class="stat-tile">
      <span class="label">Embedded</span>
      <span class="value">{stats.embedded.toLocaleString()}</span>
    </Card>
  {:else}
    <span>Loading stats…</span>
  {/if}
</div>

<style>
  .stats-bar {
    display: flex;
    gap: 12px;
    padding-bottom: 20px;
    flex-wrap: wrap;
  }
  :global(.card.stat-tile.padded) {
    padding: 12px 18px;
    flex: 1;
    min-width: 140px;
  }
  :global(.stat-tile) .label {
    display: block;
    color: var(--muted);
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0;
  }
  :global(.stat-tile) .value {
    display: block;
    color: var(--accent);
    font-size: 1.3rem;
    font-weight: 700;
    margin-top: 4px;
  }
  .error { color: var(--danger); }
</style>
