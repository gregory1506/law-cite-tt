import { chat as chatAPI } from "./api.js";
import { buildContextNote } from "./context.svelte.js";
import { getSessionId } from "./track.js";

const STORAGE_KEY = "lawcite-chat-v1";
const MAX_PERSISTED = 40;

function loadSaved() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed.messages)) return null;
    return parsed;
  } catch {
    return null;
  }
}

const saved = loadSaved();

export const chatState = $state({
  open: false,
  messages: saved?.messages || [],
  mode: saved?.mode === "precedent" ? "precedent" : "research",
  input: "",
  sending: false,
  error: "",
  answerReady: false,
});

let controller = null;

function persist() {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        messages: chatState.messages.slice(-MAX_PERSISTED),
        mode: chatState.mode,
      }),
    );
  } catch {
    /* storage unavailable */
  }
}

export function openChat() {
  chatState.open = true;
  chatState.answerReady = false;
}

export function closeChat() {
  chatState.open = false;
}

export function toggleChat() {
  if (chatState.open) closeChat();
  else openChat();
}

export function setMode(mode) {
  if (mode !== "research" && mode !== "precedent") return;
  chatState.mode = mode;
  persist();
}

export function clearChat() {
  chatState.messages = [];
  chatState.error = "";
  chatState.answerReady = false;
  persist();
}

export function stopChat() {
  controller?.abort();
}

export async function sendMessage(text) {
  const trimmed = (text ?? chatState.input).trim();
  if (!trimmed || chatState.sending) return;

  chatState.input = "";
  chatState.error = "";
  chatState.messages = [
    ...chatState.messages,
    { role: "user", content: trimmed },
  ];
  persist();

  chatState.sending = true;
  controller = new AbortController();
  try {
    const note = buildContextNote();
    const lastIndex = chatState.messages.length - 1;
    const history = chatState.messages.map((message, index) => {
      if (message.role === "assistant") {
        return { role: "assistant", content: message.content };
      }
      if (index === lastIndex) {
        const wire = note ? `${note}\n\n${message.content}` : message.content;
        message.wire = wire;
        return { role: "user", content: wire };
      }
      return { role: "user", content: message.wire || message.content };
    });
    const response = await chatAPI(history, chatState.mode, {
      signal: controller.signal,
      sessionId: getSessionId(),
    });
    chatState.messages = [
      ...chatState.messages,
      {
        role: "assistant",
        content: response.answer,
        status: response.status,
        sources: response.sources || [],
      },
    ];
    if (!chatState.open) chatState.answerReady = true;
    persist();
  } catch (requestError) {
    if (requestError?.name === "AbortError") {
      chatState.error = "";
    } else {
      chatState.error = requestError?.message || "Request failed.";
    }
  } finally {
    chatState.sending = false;
    controller = null;
  }
}
