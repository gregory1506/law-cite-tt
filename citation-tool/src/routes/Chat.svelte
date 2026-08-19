<script>
  import {
    AlertTriangle,
    ExternalLink,
    FileText,
    MessageSquareText,
    Send,
  } from "@lucide/svelte";
  import { chat, resolveUrl } from "../lib/api.js";


  let messages = $state([]);
  let input = $state("");
  let sending = $state(false);
  let error = $state("");

  async function sendMessage() {
    const text = input.trim();
    if (!text || sending) return;
    input = "";
    error = "";
    messages = [...messages, { role: "user", content: text }];
    sending = true;
    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const response = await chat(history, "research");
      messages = [
        ...messages,
        {
          role: "assistant",
          content: response.answer,
          status: response.status,
          sources: response.sources || [],
        },
      ];
    } catch (sendError) {
      error = sendError.message;
    } finally {
      sending = false;
    }
  }

  function onKeydown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }
</script>

<header class="page-heading">
  <div>
    <p class="eyebrow">Research assistant</p>
    <h1>Chat</h1>
    <p>
      Ask about a provision of the Laws of Trinidad and Tobago. Every answer is
      checked against the source corpus before it is shown.
    </p>
  </div>
  <div class="heading-mark" aria-hidden="true"><MessageSquareText size={25} /></div>
</header>

<div class="chat-scroll" aria-live="polite">
  {#if messages.length === 0 && !sending}
    <div class="empty-state">
      <MessageSquareText size={28} strokeWidth={1.7} aria-hidden="true" />
      <h2>Ask about the Laws of Trinidad and Tobago</h2>
      <p>
        Try "what does section 4 of the Absconding Debtors Act say?" or "which
        chapters mention fraud?"
      </p>
    </div>
  {/if}

  <div class="message-list">
    {#each messages as message (message.content + message.role + messages.indexOf(message))}
      <div class="message {message.role}">
        {#if message.role === "assistant" && message.status === "refused"}
          <div class="refusal">
            <AlertTriangle size={17} aria-hidden="true" />
            <div>
              <strong>Not verified</strong>
              <p>{message.content}</p>
            </div>
          </div>
        {:else}
          <div class="bubble">{message.content}</div>
        {/if}
        {#if message.sources?.length}
          <div class="sources">
            <p class="sources-label">Sources</p>
            {#each message.sources as source}
              <div class="source" key={source.id}>
                <span class="source-ref">
                  {source.chapter}{source.section
                    ? ` · s. ${source.section}`
                    : ""}
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

  {#if sending}
    <div class="thinking" role="status">
      <span class="spinner" aria-hidden="true"></span>
      Checking the source corpus…
    </div>
  {/if}

  {#if error}
    <div class="error-banner" role="alert">
      <AlertTriangle size={16} aria-hidden="true" />
      {error}
    </div>
  {/if}
</div>

<form class="composer" onsubmit={(event) => { event.preventDefault(); sendMessage(); }}>
  <textarea
    rows="1"
    aria-label="Message"
    bind:value={input}
    onkeydown={onKeydown}
    placeholder="Ask a question about a Trinidad and Tobago statute…"
  ></textarea>
  <button
    type="submit"
    aria-label="Send message"
    disabled={sending || !input.trim()}
  >
    <Send size={17} aria-hidden="true" />
  </button>
</form>

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
  .chat-scroll {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 2px 2px 6px;
  }
  .empty-state {
    display: grid;
    min-height: 320px;
    place-items: center;
    align-content: center;
    padding: 48px 20px;
    color: var(--muted-strong);
    text-align: center;
  }
  .empty-state h2 { margin: 13px 0 4px; color: var(--text); font-size: 1rem; }
  .empty-state p { max-width: 480px; margin: 0; color: var(--muted); font-size: 0.86rem; }
  .message-list { display: flex; flex-direction: column; gap: 14px; }
  .message { max-width: 820px; }
  .message.user { align-self: flex-end; }
  .bubble {
    padding: 12px 15px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--text);
    font-size: 0.9rem;
    line-height: 1.6;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .message.user .bubble {
    border-color: var(--border-strong);
    background: linear-gradient(145deg, rgba(34, 211, 238, 0.1), rgba(34, 211, 238, 0.03));
  }
  .refusal {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 13px 15px;
    border: 1px solid var(--border);
    border-left: 3px solid #fbbf24;
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--muted-strong);
  }
  .refusal strong { display: block; color: #fbbf24; font-size: 0.84rem; }
  .refusal p { margin: 3px 0 0; font-size: 0.84rem; }
  .sources { margin-top: 9px; }
  .sources-label {
    margin: 0 0 6px;
    color: var(--muted);
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .source {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 11px;
    border: 1px solid var(--border);
    background: var(--surface);
    font-size: 0.78rem;
  }
  .source + .source { border-top: 0; }
  .source-ref { color: var(--accent); font-weight: 750; white-space: nowrap; }
  .source-title { flex: 1 1 auto; color: var(--text-soft); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .source-date { color: var(--muted); white-space: nowrap; }
  .source a {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: var(--accent);
    font-size: 0.74rem;
    font-weight: 700;
    text-decoration: none;
    white-space: nowrap;
  }
  .thinking {
    display: inline-flex;
    align-items: center;
    gap: 9px;
    color: var(--muted);
    font-size: 0.8rem;
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
    gap: 8px;
    padding: 11px 14px;
    border: 1px solid var(--border);
    border-left: 3px solid var(--danger);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--danger);
    font-size: 0.82rem;
  }
  .composer {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    margin-top: 16px;
    padding-top: 14px;
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
    font-size: 0.9rem;
    line-height: 1.45;
  }
  textarea:focus-visible, button:focus-visible, a:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .composer button {
    display: inline-flex;
    min-height: 44px;
    align-items: center;
    justify-content: center;
    gap: 7px;
    padding: 10px 16px;
    border: 0;
    border-radius: var(--radius);
    background: var(--accent);
    color: var(--accent-text);
    font-weight: 800;
    cursor: pointer;
  }
  .composer button:disabled { cursor: not-allowed; opacity: 0.45; }
  @media (max-width: 560px) {
    .heading-mark { display: none; }
    .source { align-items: flex-start; flex-wrap: wrap; }
    .source a { margin-left: auto; }
  }
</style>
