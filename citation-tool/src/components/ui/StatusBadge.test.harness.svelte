<script>
  import StatusBadge from "./StatusBadge.svelte";

  let { text, tone = "neutral" } = $props();
</script>

<StatusBadge {tone}>
  {text}
</StatusBadge>
