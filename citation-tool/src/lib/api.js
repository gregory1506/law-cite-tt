const defaultBase =
  typeof window !== "undefined" &&
  window.location.hostname !== "localhost" &&
  window.location.hostname !== "127.0.0.1"
    ? ""
    : "http://localhost:8000";

const API_BASE = import.meta.env.VITE_API_BASE !== undefined
  ? import.meta.env.VITE_API_BASE
  : defaultBase;



async function getJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function getStats() {
  return getJSON("/api/stats");
}

export function getChapters(limit = 533) {
  return getJSON(`/api/chapters?limit=${limit}`);
}

export function searchGrouped(
  q,
  { mode = "fts", chapter = "", date = "", limit = 20, offset = 0 } = {},
) {
  const params = new URLSearchParams({
    q,
    mode,
    limit: String(limit),
    offset: String(offset),
  });
  if (chapter) params.set("chapter", chapter);
  if (date) params.set("date", date);
  return getJSON(`/api/search/grouped?${params}`);
}

export function lookupSection(chapter, section, date = "", downloadId = null) {
  const params = new URLSearchParams({ chapter, section });
  if (date) params.set("date", date);
  if (downloadId != null) params.set("download_id", String(downloadId));
  return getJSON(`/api/lookup?${params}`);
}

export function resolveCitation(chapter, section, date = "") {
  const params = new URLSearchParams({ chapter, section });
  if (date) params.set("date", date);
  return getJSON(`/api/citations/resolve?${params}`);
}

async function postJSON(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function chat(messages, mode = "research") {
  return postJSON("/api/chat", { messages, mode });
}

export function resolveUrl(url) {
  if (!url) return "#";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `${API_BASE}${url}`;
}

export { API_BASE };

