// Usage analytics beacon (beta metrics). Never throws, never blocks the app.

const SID_KEY = "lawcite_sid";
const OPTOUT_KEY = "lawcite_no_analytics";
const ENDPOINT = "/api/events";
const FLUSH_MS = 4000;
const FLUSH_AT = 20;

const TEST_ENV = import.meta.env?.MODE === "test";

let buffer = [];
let timer = null;
let lastPath = "";
let lastAt = 0;
let started = false;

export function analyticsEnabled() {
  try {
    return localStorage.getItem(OPTOUT_KEY) !== "1";
  } catch {
    return true;
  }
}

export function setAnalyticsEnabled(enabled) {
  try {
    localStorage.setItem(OPTOUT_KEY, enabled ? "0" : "1");
  } catch {
    /* storage unavailable */
  }
}

function randomId() {
  try {
    return crypto.randomUUID();
  } catch {
    return `s${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
  }
}

export function getSessionId() {
  try {
    let sid = sessionStorage.getItem(SID_KEY);
    if (!sid) {
      sid = randomId();
      sessionStorage.setItem(SID_KEY, sid);
    }
    return sid;
  } catch {
    return "nosession";
  }
}

function send(batch) {
  const body = JSON.stringify({ session_id: getSessionId(), events: batch });
  try {
    if (typeof navigator !== "undefined" && navigator.sendBeacon) {
      if (navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "application/json" }))) {
        return;
      }
    }
    if (typeof fetch === "function") {
      fetch(ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
      }).catch(() => {});
    }
  } catch {
    /* analytics must never break the app */
  }
}

export function flush() {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  if (!buffer.length) return;
  const batch = buffer.splice(0, buffer.length);
  send(batch);
}

function schedule() {
  if (TEST_ENV || timer || typeof window === "undefined") return;
  timer = setTimeout(() => {
    timer = null;
    flush();
  }, FLUSH_MS);
}

function push(type, meta = {}) {
  if (!analyticsEnabled()) return;
  if (buffer.length >= FLUSH_AT) flush();
  const path =
    typeof location !== "undefined" ? location.pathname + location.search : "";
  buffer.push({ type, path, meta });
  schedule();
}

export function track(type, meta = {}) {
  push(type, meta);
}

export function trackPageview(path) {
  const now = Date.now();
  if (lastPath && lastPath !== path && now - lastAt >= 200) {
    push("dwell", { path: lastPath, ms: now - lastAt });
  }
  lastPath = path;
  lastAt = now;
  push("pageview", { path });
}

export function initTracking() {
  if (started || typeof window === "undefined") return;
  started = true;
  window.addEventListener("pagehide", flush);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flush();
  });
  if (!analyticsEnabled()) return;
  push("session_start", {
    referrer: (typeof document !== "undefined" && document.referrer) || "",
    viewport: [window.innerWidth, window.innerHeight],
  });
}
