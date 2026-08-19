# Study log

## 2026-08-18 — law-cite-tt: RAG-shaped, not agentic

Q: Does this project look more like a RAG than an agentic project?

A: Yes — decisively more RAG-shaped. The pipeline is retrieve → validate →
format with no LLM, no reasoning loop, and no tool-calling.

```
      YOUR PROJECT (law-cite-tt)
┌───────────────────────────────────────────┐
│  Query (what did §4 say on 31 Dec 2013?)  │
└───────────────────┬───────────────────────┘
                    ▼
      ┌───────────────────────────────┐
      │   RETRIEVAL (the R in RAG)    │  ◀─ 90% of the system
      │  FTS5 keyword + vector search │
      │  over 407,008 section chunks  │
      │  filtered by chapter / date   │
      └───────────────┬───────────────┘
                      ▼
      ┌───────────────────────────────┐
      │   DETERMINISTIC VALIDATION    │  ◀─ replaces "generation"
      │  found / not-found / ambiguous│
      │  exact source text + PDF link │
      └───────────────┬───────────────┘
                      ▼
                 Final citation
   (no LLM, no agent loop, no tool-calling)

   Agentic would require:
   ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
   │  Reason │→│  Decide  │→│  Use tool│→│  Reflect │  loop
   └─────────┘  └──────────┘  └──────────┘  └──────────┘
```

The pipeline is retrieve → validate → format: chunking, embedding, hybrid
search, and a deterministic resolution layer. There's no LLM generating the
answer, no multi-step reasoning loop, and no tool-calling — so none of the
hallmarks of an agentic system. The only future "generation" surface is the
Chat tab, which is still a placeholder. If it ever wires to an LLM, a classic
RAG flow bolts on top of the retrieval already built.

## 2026-08-18 — Two low-hanging fruit to make it agentic

Both reuse existing infrastructure — no new data, no new services.

```
 OPTION 1 — Chat becomes a tool-calling agent          OPTION 2 — Precedent-chain walker
 ──────────────────────────────────────                ─────────────────────────────────────
 LLM + tool loop over EXISTING API                     LLM + tool loop over EXISTING graph
                                                       
 ┌──────────┐   ┌──────────────────────┐              ┌──────────┐   ┌──────────────────────┐
 │ Question │──▶│ Agent loop (LLM)     │              │ §4 of X  │──▶│ Walk citation graph  │
 └──────────┘   │  reason → pick tool  │              └──────────┘   │ 7,914 edges (built)  │
                └──────┬───────────────┘                             └──────────┬───────────┘
                        │ tools already live                                │
               ┌────────┼────────┐                                 ┌────────┼────────┐
               ▼        ▼        ▼                                 ▼        ▼        ▼
        /search  /lookup  /cite  ✓  =   /stats  /chapters  /cases-citing-§4  /newer-cases
        (grouped  (exact   (found/            existing graph API or scraper output
         prov)    lookup)  ambiguous)

 Effort: ~1 new module (agent loop)     Effort: ~1 graph query + agent loop,
 + LLM key. Tools already exist.        reusing webOPAC/CCJ edges already on SSD.
```

1. **Tool-calling agent over the existing API** — the tools already exist
   (`/search`, `/lookup`, `/cite`, `/chapters` are production endpoints with
   CORS). Wire them into the Chat placeholder plus an LLM loop. Minimal agentic
   skeleton, ~1 new module.
2. **Precedent-chain walker over the citation graph** — the webOPAC sweep
   produced 7,914 case→statute edges and 2,236 case nodes. An agent that asks
   "which cases cite §4, and which cite those cases" walks a chain of precedent
   using already-crawled data. Needs a graph-walk tool + loop.

Both deliver the reason → use tool → reflect → repeat loop with zero new
infrastructure. Option 1 is the entry point; option 2 is the differentiator.