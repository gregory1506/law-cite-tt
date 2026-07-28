// Stub session handling. Real auth (backed by the marketing site's login)
// is not built yet — this just gates the UI behind a placeholder token
// stored in localStorage so the tab structure can be wired up now.

const STORAGE_KEY = "lawcite_session_token";

export function getToken() {
  return localStorage.getItem(STORAGE_KEY);
}

export function setToken(token) {
  localStorage.setItem(STORAGE_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(STORAGE_KEY);
}

export function isAuthenticated() {
  return Boolean(getToken());
}
