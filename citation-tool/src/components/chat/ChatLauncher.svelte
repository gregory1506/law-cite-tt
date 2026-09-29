<script>
  import { MessageSquareText, X } from "@lucide/svelte";
  import { chatState, toggleChat } from "../../lib/chat.svelte.js";
</script>

<button
  class="chat-launcher"
  class:open={chatState.open}
  type="button"
  onclick={toggleChat}
  aria-expanded={chatState.open}
  aria-controls="chat-dock"
  aria-label={chatState.open ? "Close research assistant" : "Open research assistant"}
>
  {#if chatState.open}
    <X size={22} aria-hidden="true" />
  {:else}
    <MessageSquareText size={22} aria-hidden="true" />
  {/if}
  {#if !chatState.open && chatState.sending}
    <span class="dot busy" aria-hidden="true"></span>
  {:else if !chatState.open && chatState.answerReady}
    <span class="dot ready" aria-hidden="true"></span>
  {/if}
</button>

<style>
  .chat-launcher {
    position: fixed;
    right: max(20px, env(safe-area-inset-right));
    bottom: max(20px, env(safe-area-inset-bottom));
    z-index: 40;
    display: grid;
    width: 56px;
    height: 56px;
    place-items: center;
    border: 0;
    border-radius: var(--radius-full);
    background: var(--accent);
    color: var(--accent-text);
    box-shadow: var(--shadow-3);
    cursor: pointer;
    transition:
      right var(--dur) var(--ease),
      background var(--dur-fast) var(--ease),
      transform var(--dur-fast) var(--ease);
  }
  .chat-launcher:hover { background: var(--accent-hover); transform: translateY(-2px); }
  .chat-launcher:active { transform: translateY(0); }
  .chat-launcher.open { right: calc(var(--dock-w) + 20px); }
  .dot {
    position: absolute;
    top: 3px;
    right: 3px;
    width: 12px;
    height: 12px;
    border: 2px solid var(--surface);
    border-radius: var(--radius-full);
  }
  .dot.busy {
    background: var(--warning);
    animation: pulse 1.2s ease-in-out infinite;
  }
  .dot.ready { background: var(--positive); }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.35; }
  }
  @media (max-width: 768px) {
    .chat-launcher.open { right: max(20px, env(safe-area-inset-right)); opacity: 0; pointer-events: none; }
  }
</style>
