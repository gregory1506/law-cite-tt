# ⚖️ LawCite TT — Customer App

The **Svelte 5** frontend for **LawCite TT** — point-in-time legal search, citation
validation, a grounded research assistant, and the Statute Atlas for the Laws of
Trinidad and Tobago.

* **Live app:** https://law.ai.tt
* **Repository root:** [`../`](../) — backend, corpus stats, and architecture docs

## Stack

* **Svelte 5** (Runes API) + **Vite** — no framework, no router library
* Custom history router (`src/lib/router.svelte.js`)
* **Vitest** + Testing Library + jsdom
* **Cloudflare Workers** — static assets + same-origin `/api/*` proxy

## Quick start

```bash
npm install
npm run dev      # http://localhost:5173
npm test         # vitest suite
npm run build    # production bundle → dist/
```

In development the app calls the FastAPI backend at **`http://localhost:8000`**
(see [`../backend`](../backend)); override with `VITE_API_BASE`. On any
non-localhost hostname the app uses **same-origin `/api/*`** — in production the
Worker forwards those requests to the API origin.

## Project structure

```
src/
├── App.svelte              # shell: header, sidebar, route switch, chat dock mount
├── main.js                 # entry point
├── worker.js               # Cloudflare Worker: /api/* → origin, else static assets
├── routes/
│   ├── Explore.svelte      # Research — hybrid search over the corpus
│   └── Cite.svelte         # Cite — citation resolution & validation
├── components/
│   ├── layout/             # Sidebar, Header, ThemeToggle
│   └── chat/               # floating research-assistant dock
├── lib/
│   ├── router.svelte.js    # history-based routing (/, /cite)
│   ├── api.js              # API helpers (search, chat, cases, events, …)
│   ├── chat.svelte.js      # chat state store (sessions, sources, chips)
│   ├── track.js            # privacy-aware analytics beacon (opt-out supported)
│   ├── auth.js             # session helpers (sign-in stub)
│   └── date.js, text.js    # formatting utilities
└── styles/                 # design tokens, light/dark themes
public/
├── laws-graph.html         # self-contained Statute Atlas (533 chapters)
└── metrics.html            # admin analytics dashboard (served at /metrics)
```

## Routes

| Path | View |
| :--- | :--- |
| `/` | Research (hybrid search) |
| `/cite` | Citation validation & copy-ready references |
| `/laws-graph.html` | Statute Atlas — opens in a new tab |
| `/metrics` | Usage-metrics dashboard (admin token required) |

## Testing

```bash
npm test                 # full suite (vitest, jsdom)
npx vitest run src/lib   # pure-logic modules (router, api, track, date, text)
```

`fetch` is mocked in tests, and `import.meta.env.MODE === "test"` disables the
analytics beacon timers so tests never hit the network.

## Deploy

```bash
npm run build
npx wrangler deploy
```

`wrangler.toml` (Worker name `law-cite-tt`) publishes `dist/` as Workers Static
Assets; `src/worker.js` proxies `/api/*` to the API origin and serves everything
else from the asset bundle. Run `npm test` before deploying.

## Privacy

Usage analytics (hashed IPs, per-tab sessions, opt-out toggle in the sidebar)
are described in the root README's
[Privacy & Analytics](../README.md#-privacy--analytics) section. The beacon
implementation lives in `src/lib/track.js`.
