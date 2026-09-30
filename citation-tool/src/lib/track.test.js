import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  analyticsEnabled,
  flush,
  getSessionId,
  initTracking,
  setAnalyticsEnabled,
  track,
  trackPageview,
} from "./track.js";

function flushCalls(fetchMock) {
  return fetchMock.mock.calls.map((call) => JSON.parse(call[1].body));
}

describe("track", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    setAnalyticsEnabled(true);
    flush();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("keeps a stable per-tab session id", () => {
    const sid = getSessionId();
    expect(sid).toMatch(/^[A-Za-z0-9-]+$/);
    expect(getSessionId()).toBe(sid);
    expect(sessionStorage.getItem("lawcite_sid")).toBe(sid);
  });

  it("buffers events and flushes them as one batched payload", () => {
    track("search", { query: "arbitration" });
    track("cite_validate", { chapter: "8:08" });
    flush();

    const fetchMock = globalThis.fetch;
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/events");
    const batches = flushCalls(fetchMock);
    expect(batches).toHaveLength(1);
    expect(batches[0].session_id).toBe(getSessionId());
    expect(batches[0].events.map((e) => e.type)).toEqual([
      "search",
      "cite_validate",
    ]);
    expect(batches[0].events[0].meta.query).toBe("arbitration");
  });

  it("emits dwell between pageviews and a pageview per route", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    const start = Date.now();
    trackPageview("/");
    vi.setSystemTime(start + 750);
    trackPageview("/cite");
    flush();

    const batches = flushCalls(globalThis.fetch);
    const events = batches[0].events;
    expect(events.map((e) => e.type)).toEqual(["pageview", "dwell", "pageview"]);
    expect(events[1].meta.path).toBe("/");
    expect(events[1].meta.ms).toBeGreaterThanOrEqual(750);
    expect(events[2].meta.path).toBe("/cite");
  });

  it("records a session_start once on init", () => {
    initTracking();
    initTracking();
    flush();
    const batches = flushCalls(globalThis.fetch);
    const starts = batches[0].events.filter((e) => e.type === "session_start");
    expect(starts).toHaveLength(1);
  });

  it("flush is a no-op when the buffer is empty", () => {
    flush();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("drops all events when analytics is opted out", () => {
    setAnalyticsEnabled(false);
    expect(analyticsEnabled()).toBe(false);
    track("search", { query: "x" });
    trackPageview("/");
    flush();
    expect(globalThis.fetch).not.toHaveBeenCalled();

    setAnalyticsEnabled(true);
    track("search", { query: "y" });
    flush();
    const batches = flushCalls(globalThis.fetch);
    expect(batches).toHaveLength(1);
    expect(batches[0].events.map((e) => e.type)).toEqual(["search"]);
  });
});
