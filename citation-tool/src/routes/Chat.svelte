<script>
  import { MessageSquareText } from "@lucide/svelte";
</script>

<section class="chat-placeholder" aria-labelledby="chat-heading">
  <header>
    <p>Research assistant</p>
    <h1 id="chat-heading">Chat</h1>
  </header>

  <div class="empty-state">
    <MessageSquareText size={28} strokeWidth={1.7} aria-hidden="true" />
    <h2>Chat is coming soon</h2>
    <p>Use Research to search legislation and review official source PDFs.</p>
  </div>
</section>

<style>
  header {
    padding-bottom: 18px;
    border-bottom: 1px solid var(--border);
  }
  header p {
    margin: 0 0 2px;
    color: var(--muted);
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
  }
  h1 {
    margin: 0;
    font-size: 1.55rem;
    line-height: 1.2;
  }
  .empty-state {
    display: grid;
    min-height: 360px;
    place-items: center;
    align-content: center;
    padding: 48px 20px;
    color: var(--muted-strong);
    text-align: center;
  }
  .empty-state h2 {
    margin: 13px 0 4px;
    color: var(--text);
    font-size: 1rem;
  }
  .empty-state p {
    max-width: 440px;
    margin: 0;
    color: var(--muted);
    font-size: 0.86rem;
  }
</style>
