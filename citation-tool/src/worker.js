export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/")) {
      const originUrl = new URL(url.pathname + url.search, "https://srv1629323.hstgr.cloud");
      const headers = new Headers(request.headers);
      headers.set("Host", "srv1629323.hstgr.cloud");

      const originReq = new Request(originUrl, {
        method: request.method,
        headers: headers,
        body: ["GET", "HEAD"].includes(request.method) ? null : request.body,
        redirect: "follow",
      });
      return fetch(originReq);
    }
    return env.ASSETS.fetch(request);
  },
};
