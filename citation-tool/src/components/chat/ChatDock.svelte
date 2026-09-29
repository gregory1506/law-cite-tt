<script>
  import {
    AlertTriangle,
    ExternalLink,
    Send,
    Square,
    Trash2,
    X,
  } from "@lucide/svelte";
  import { resolveUrl } from "../../lib/api.js";
  import {
    MODE_LABELS,
    dismissContext,
    visibleContext,
  } from "../../lib/context.svelte.js";
  import { router } from "../../lib/router.svelte.js";
  import {
    chatState,
    clearChat,
    closeChat,
    sendMessage,
    setMode,
    stopChat,
  } from "../../lib/chat.svelte.js";

  let scrollEl = $state(null);
  let inputEl = $state(null);

  const chips = $derived.by(() => {
    const { search, lookup, cite } = visibleContext();
    const list = [];
    if (search) {
      list.push({
        key: "search",
        label: `Research · "${search.query}" · ${MODE_LABELS[search.mode] || search.mode}`,
      });
    }
    if (lookup) {
      list.push({
        key: "lookup",
        label: `Lookup · ${lookup.chapter} s.${lookup.section}`,
      });
    }
    if (cite) {
      list.push({
        key: "cite",
        label: `Cite · ${cite.chapter} s.${cite.section}${cite.date ? ` · ${cite.date}` : ""}`,
      });
    }
    return list;
  });

  const suggestions = $derived.by(() => {
    const { search, lookup, cite } = visibleContext();
    const list = [];
    if (cite) {
      list.push(`What does ${cite.chapter} s.${cite.section} say today?`);
      if (cite.date) list.push(`Explain the version in force on ${cite.date}`);
      list.push("Which judgments cite this provision?");
    }
    if (search) {
      list.push(`Summarise the current law on "${search.query}"`);
      list.push("Which cases cite these provisions?");
    }
    if (lookup) {
      list.push(`Explain ${lookup.chapter} s.${lookup.section} in plain language`);
    }
    if (!list.length) {
      return router.route === "cite"
        ? [
            "Validate Chap. 8:08, s. 4 as at today",
            "Which cases cite the Absconding Debtors Act?",
          ]
        : [
            "What does section 4 of the Absconding Debtors Act say?",
            "Which chapters mention fraud?",
          ];
    }
    return list.slice(0, 3);
  });

  function useSuggestion(text) {
    chatState.input = text;
    inputEl?.focus();
  }

  $effect(() => {
    chatState.messages.length;
    chatState.sending;
    if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
  });

  function onKeydown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  const statusCards = {
    error: {
      title: "Request failed",
      note: "The assistant could not complete that request. Try again in a moment.",
    },
    unconfigured: {
      title: "Assistant not configured",
      note: "The language model key is missing on the server, so answers are disabled.",
    },
  };
</script>

<aside
  id="chat-dock"
  class="chat-dock"
  class:open={chatState.open}
  aria-label="Research assistant"
>
  <header class="dock-header">
    <div class="dock-title">
      <h2>Research assistant</h2>
      <div class="mode-switch" role="group" aria-label="Assistant mode">
        <button
          type="button"
          class:active={chatState.mode === "research"}
          onclick={() => setMode("research")}
          title="Grounded answers from the statute corpus"
          aria-pressed={chatState.mode === "research"}
        >
          Research
        </button>
        <button
          type="button"
          class:active={chatState.mode === "precedent"}
          onclick={() => setMode("precedent")}
          title="Case-law precedent and citation chains"
          aria-pressed={chatState.mode === "precedent"}
        >
          Precedent
        </button>
      </div>
    </div>
    <div class="dock-actions">
      {#if chatState.messages.length}
        <button
          type="button"
          class="icon-button"
          onclick={clearChat}
          aria-label="Clear conversation"
          title="Clear conversation"
        >
          <Trash2 size={16} aria-hidden="true" />
        </button>
      {/if}
      <button
        type="button"
        class="icon-button"
        onclick={closeChat}
        aria-label="Close assistant"
        title="Close"
      >
        <X size={17} aria-hidden="true" />
      </button>
    </div>
  </header>

  <div class="chat-scroll" aria-live="polite" bind:this={scrollEl}>
    {#if chatState.messages.length === 0 && !chatState.sending}
      <div class="empty-state">
        <h3>Ask about the Laws of Trinidad and Tobago</h3>
        <p>
          Every answer is checked against the source corpus before it is shown.
        </p>
        <div class="suggestions">
          {#each suggestions as suggestion}
            <button type="button" onclick={() => useSuggestion(suggestion)}>
              {suggestion}
            </button>
          {/each}
        </div>
      </div>
    {/if}

    <div class="message-list">
      {#each chatState.messages as message, index (index)}
        <div class="message {message.role}">
          {#if message.role === "assistant" && message.status === "refused"}
            <div class="refusal">
              <AlertTriangle size={17} aria-hidden="true" />
              <div>
                <strong>Not verified</strong>
                <p>{message.content}</p>
              </div>
            </div>
          {:else if message.role === "assistant" && statusCards[message.status]}
            <div class="status-card {message.status}">
              <AlertTriangle size={17} aria-hidden="true" />
              <div>
                <strong>{statusCards[message.status].title}</strong>
                <p>{message.content || statusCards[message.status].note}</p>
              </div>
            </div>
          {:else}
            <div class="bubble">{message.content}</div>
          {/if}
          {#if message.sources?.length}
            <div class="sources">
              <p class="sources-label">Sources</p>
              {#each message.sources as source (source.id)}
                <div class="source">
                  <span class="source-ref">
                    {source.chapter}{source.section ? ` · s. ${source.section}` : ""}
                  </span>
                  <span class="source-title">{source.title}</span>
                  {#if source.date}<span class="source-date">{source.date}</span>{/if}
                  {#if resolveUrl(source.url)}
                    <a href={resolveUrl(source.url)} target="_blank" rel="noopener">
                      Official PDF
                      <ExternalLink size={12} aria-hidden="true" />
                    </a>
                  {/if}
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>

    {#if chatState.sending}
      <div class="thinking" role="status">
        <span class="spinner" aria-hidden="true"></span>
        Checking the source corpus…
      </div>
    {/if}

    {#if chatState.error}
      <div class="error-banner" role="alert">
        <AlertTriangle size={16} aria-hidden="true" />
        {chatState.error}
      </div>
    {/if}
  </div>

  {#if chips.length}
    <div class="context-row" aria-label="Conversation context">
      {#each chips as chip (chip.key)}
        <button
          type="button"
          class="chip"
          onclick={() => dismissContext(chip.key)}
          aria-label={`Remove context: ${chip.label}`}
          title="Remove this context from the conversation"
        >
          {chip.label}
          <X size={12} aria-hidden="true" />
        </button>
      {/each}
    </div>
  {/if}

  <form
    class="composer"
    onsubmit={(event) => {
      event.preventDefault();
      sendMessage();
    }}
  >
    <textarea
      rows="1"
      aria-label="Message"
      bind:this={inputEl}
      bind:value={chatState.input}
      onkeydown={onKeydown}
      placeholder="Ask a question about a Trinidad and Tobago statute…"
    ></textarea>
    {#if chatState.sending}
      <button
        type="button"
        class="btn btn-secondary stop-button"
        onclick={stopChat}
        aria-label="Stop generating"
      >
        <Square size={15} aria-hidden="true" />
      </button>
    {/if}
    <button
      class="btn btn-primary"
      type="submit"
      aria-label="Send message"
      disabled={chatState.sending || !chatState.input.trim()}
    >
      <Send size={17} aria-hidden="true" />
    </button>
  </form>
</aside>

<style>
  .chat-dock {
    position: fixed;
    inset: 0 0 0 auto;
    z-index: 45;
    display: flex;
    width: var(--dock-w);
    max-width: 100vw;
    height: 100vh;
    height: 100dvh;
    flex-direction: column;
    border-left: 1px solid var(--border);
    background: var(--surface);
    box-shadow: var(--shadow-3);
    visibility: hidden;
    transform: translateX(100%);
    transition:
      transform var(--dur) var(--ease),
      visibility 0s linear var(--dur);
  }
  .chat-dock.open {
    visibility: visible;
    transform: translateX(0);
    transition: transform var(--dur) var(--ease);
  }

  .dock-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-4) var(--space-4) var(--space-3);
    border-bottom: 1px solid var(--border);
  }
  .dock-title { display: grid; gap: var(--space-2); min-width: 0; }
  .dock-title h2 {
    margin: 0;
    font-size: var(--text-base);
    font-weight: var(--weight-bold);
  }
  .mode-switch {
    display: inline-flex;
    width: fit-content;
    padding: 2px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg);
  }
  .mode-switch button {
    padding: 4px 10px;
    border: 0;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--muted);
    font-size: var(--text-xs);
    font-weight: var(--weight-semibold);
    cursor: pointer;
  }
  .mode-switch button.active {
    background: var(--accent-soft);
    color: var(--accent);
  }
  .dock-actions { display: flex; gap: var(--space-1); flex: 0 0 auto; }
  .icon-button {
    display: grid;
    width: 32px;
    height: 32px;
    place-items: center;
    padding: 0;
    border: 0;
    border-radius: var(--radius);
    background: transparent;
    color: var(--muted-strong);
    cursor: pointer;
  }
  .icon-button:hover { background: var(--accent-soft); color: var(--text); }

  .chat-scroll {
    display: flex;
    min-height: 0;
    flex: 1;
    flex-direction: column;
    gap: var(--space-3);
    overflow-y: auto;
    padding: var(--space-4);
  }
  .empty-state {
    display: grid;
    place-items: center;
    align-content: center;
    flex: 1;
    padding: var(--space-10) var(--space-5);
    color: var(--muted-strong);
    text-align: center;
  }
  .empty-state h3 {
    margin: 0 0 var(--space-2);
    color: var(--text);
    font-size: var(--text-base);
  }
  .empty-state p {
    max-width: 320px;
    margin: 0;
    color: var(--muted);
    font-size: var(--text-md);
  }
  .suggestions {
    display: grid;
    width: min(340px, 100%);
    gap: var(--space-2);
    margin-top: var(--space-5);
  }
  .suggestions button {
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface-raised);
    color: var(--text-soft);
    font-size: var(--text-sm);
    text-align: left;
    cursor: pointer;
    transition: border-color var(--dur-fast) var(--ease);
  }
  .suggestions button:hover { border-color: var(--accent-border); color: var(--text); }

  .context-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 0 var(--space-4) var(--space-3);
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    max-width: 100%;
    padding: 4px 9px;
    border: 1px solid var(--accent-border);
    border-radius: var(--radius-full);
    background: var(--accent-soft);
    color: var(--text-soft);
    font-size: var(--text-2xs);
    font-weight: var(--weight-semibold);
    cursor: pointer;
    transition: border-color var(--dur-fast) var(--ease);
  }
  .chip:hover { border-color: var(--accent); color: var(--text); }

  .message-list { display: flex; flex-direction: column; gap: var(--space-3); }
  .message { max-width: 100%; }
  .message.user { display: flex; justify-content: flex-end; }
  .bubble {
    padding: var(--space-3) var(--space-4);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface-raised);
    color: var(--text);
    font-size: var(--text-md);
    line-height: 1.6;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .message.user .bubble {
    border-color: var(--accent-border);
    background: var(--accent-soft);
  }
  .refusal,
  .status-card {
    display: flex;
    align-items: flex-start;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    border: 1px solid var(--border);
    border-left: 3px solid var(--warning);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--muted-strong);
    font-size: var(--text-md);
  }
  .refusal strong,
  .status-card strong { display: block; color: var(--warning); font-size: 0.84rem; }
  .refusal p,
  .status-card p { margin: 3px 0 0; font-size: 0.84rem; }
  .status-card.error { border-left-color: var(--danger); }
  .status-card.error strong { color: var(--danger); }

  .sources { margin-top: var(--space-2); }
  .sources-label {
    margin: 0 0 var(--space-2);
    color: var(--muted);
    font-size: var(--text-2xs);
    font-weight: var(--weight-bold);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .source {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--border);
    background: var(--surface);
    font-size: var(--text-sm);
  }
  .source + .source { border-top: 0; }
  .source-ref { color: var(--accent); font-weight: var(--weight-bold); white-space: nowrap; }
  .source-title {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    color: var(--text-soft);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .source-date { color: var(--muted); white-space: nowrap; }
  .source a {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: var(--accent);
    font-size: var(--text-xs);
    font-weight: var(--weight-semibold);
    text-decoration: none;
    white-space: nowrap;
  }

  .thinking {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--muted);
    font-size: var(--text-sm);
  }
  .spinner {
    width: 14px;
    height: 14px;
    border: 2px solid var(--border-strong);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .error-banner {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    border: 1px solid var(--border);
    border-left: 3px solid var(--danger);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--danger);
    font-size: var(--text-sm);
  }

  .composer {
    display: flex;
    align-items: flex-end;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    border-top: 1px solid var(--border);
  }
  textarea {
    flex: 1 1 auto;
    min-height: 44px;
    max-height: 160px;
    resize: none;
    padding: 11px 12px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    background: var(--bg);
    color: var(--text);
    font-family: inherit;
    font-size: var(--text-md);
    line-height: 1.45;
  }
  textarea:focus-visible {
    border-color: var(--accent);
    outline: 0;
    box-shadow: 0 0 0 2px var(--accent-ring);
  }
  .composer .btn { min-height: 44px; padding: 10px var(--space-4); }
  .stop-button { color: var(--danger); border-color: var(--danger); }

  @media (max-width: 768px) {
    .chat-dock {
      inset: 0;
      z-index: 50;
      width: 100%;
      border-left: 0;
    }
    textarea { min-height: 64px; }
  }
  @media (max-width: 400px) {
    .dock-header { padding: var(--space-3); }
    .chat-scroll { padding: var(--space-3); }
    .composer { padding: var(--space-3); }
  }
</style>
