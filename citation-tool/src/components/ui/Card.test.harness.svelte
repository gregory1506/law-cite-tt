<script>
  import Card from "./Card.svelte";

  let { text, padded = true, class: className = "" } = $props();
</script>

<Card {padded} class={className}>
  {text}
</Card>
