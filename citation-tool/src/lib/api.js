const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

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

export function search(q, { mode = "fts", chapter = "", limit = 20 } = {}) {
  const params = new URLSearchParams({ q, mode, limit: String(limit) });
  if (chapter) params.set("chapter", chapter);
  return getJSON(`/api/search?${params}`);
}

export function lookupSection(chapter, section, date = "") {
  const params = new URLSearchParams({ chapter, section });
  if (date) params.set("date", date);
  return getJSON(`/api/lookup?${params}`);
}
