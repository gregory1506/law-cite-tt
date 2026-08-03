"""GraphRAG retriever over the idea graph.

- Seed: embed a query with the same fastembed model used for chunks, then
  score candidate idea nodes by cosine over their averaged embeddings.
- Expand: BFS (broad context) or DFS (trace a path) over graph edges.
- Return: ranked context of ideas + their text for an LLM prompt.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np

from .build import DB_PATH, OUT_DIR, unpack

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Retriever:
    def __init__(self, db_path: Path = DB_PATH, out_dir: Path = OUT_DIR):
        self.conn = sqlite3.connect(db_path)
        self.graph = json.loads((out_dir / "graph.json").read_text())
        self.nodes = {n["id"]: n for n in self.graph["nodes"]}
        self.adj: dict[str, list[tuple[str, str, str]]] = {}
        for e in self.graph["edges"]:
            self.adj.setdefault(e["source"], []).append(
                (e["target"], e["type"], e.get("detail", ""))
            )
            self.adj.setdefault(e["target"], []).append(
                (e["source"], e["type"], e.get("detail", ""))
            )

        # persisted idea embeddings (row order matches graph idea nodes)
        self.emb_path = out_dir / "idea_embeddings.npy"
        self.idea_ids = json.loads((out_dir / "idea_ids.json").read_text())
        self.emb = np.load(self.emb_path).astype(np.float32)
        norms = np.linalg.norm(self.emb, axis=1, keepdims=True)
        self.emb = np.divide(self.emb, norms, out=np.zeros_like(self.emb), where=norms != 0)
        self.conn.close()
        self._load_case_edges(out_dir)

    def _load_case_edges(self, out_dir: Path) -> None:
        """Merge CITES_STATUTE edges (case -> chapter) into the graph."""
        case_file = out_dir / "case_edges.json"
        if not case_file.exists():
            return
        ce = json.loads(case_file.read_text())
        for e in ce.get("edges", []):
            src, tgt = e["source"], e["target"]
            detail = e.get("detail", "") or e.get("source_title", "")
            self.adj.setdefault(src, []).append((tgt, e["type"], detail))
            self.adj.setdefault(tgt, []).append((src, e["type"], detail))
            if src not in self.nodes:
                self.nodes[src] = {
                    "id": src,
                    "type": "case",
                    "label": e.get("source_title") or src,
                    "text": detail,
                }
        if ce.get("edges"):
            self._n_case_edges = len(ce["edges"])
        else:
            self._n_case_edges = 0

    def embed_query(self, text: str) -> np.ndarray:
        from fastembed import TextEmbedding

        model = TextEmbedding(EMBED_MODEL)
        v = next(model.embed([text]))
        return np.asarray(v, dtype=np.float32)

    def seed(self, text: str, k: int = 10) -> list[dict]:
        q = self.embed_query(text)
        sims = self.emb @ q
        order = np.argsort(-sims)[:k]
        out = []
        for idx in order:
            iid = self.idea_ids[int(idx)]
            n = self.nodes[iid]
            out.append(
                {
                    "id": iid,
                    "chapter": n["chapter_number"],
                    "section": n["section_ref"],
                    "label": n["label"],
                    "score": float(sims[idx]),
                }
            )
        return out

    def _expandable(self, ntype: str, from_type: str) -> bool:
        """Which neighbours may be traversed. Chapters are transit-only: you
        may step *into* a chapter from a case or concept, then step out to its
        ideas — but you may not fan an idea out to its whole chapter."""
        if ntype in ("idea", "concept", "case"):
            return True
        if ntype == "chapter":
            return from_type in ("case", "concept")
        return False

    def traverse(self, seed_ids: list[str], depth: int = 2, mode: str = "bfs",
                 max_nodes: int = 40) -> list[dict]:
        visited: list[str] = []
        if mode == "bfs":
            queue = list(seed_ids)
            seen = set(seed_ids)
            while queue and len(visited) < max_nodes:
                cur = queue.pop(0)
                cur_type = self.nodes.get(cur, {}).get("type", "")
                visited.append(cur)
                for nbr, etype, detail in self.adj.get(cur, []):
                    if nbr in seen or nbr not in self.nodes:
                        continue
                    if not self._expandable(self.nodes[nbr]["type"], cur_type):
                        continue
                    if len(visited) + len(queue) >= max_nodes:
                        break
                    seen.add(nbr)
                    queue.append(nbr)
        else:  # dfs
            def dfs(node, d):
                if node in seen or len(visited) >= max_nodes:
                    return
                seen.add(node)
                visited.append(node)
                if d >= depth:
                    return
                cur_type = self.nodes.get(node, {}).get("type", "")
                for nbr, etype, detail in self.adj.get(node, []):
                    ntype = self.nodes.get(nbr, {}).get("type")
                    if ntype is None:
                        continue
                    if self._expandable(ntype, cur_type):
                        dfs(nbr, d + 1)

            seen = set()
            for s in seed_ids:
                dfs(s, 0)

        out = []
        for iid in visited:
            n = self.nodes.get(iid)
            if not n:
                continue
            out.append(
                {
                    "id": iid,
                    "type": n["type"],
                    "label": n["label"],
                    "chapter": n.get("chapter_number"),
                    "section": n.get("section_ref"),
                    "heading": n.get("heading", ""),
                    "text": (n.get("text") or "")[:900],
                }
            )
        return out

    def retrieve(self, query: str, k: int = 10, depth: int = 2, mode: str = "bfs",
                 max_nodes: int = 40) -> dict:
        seeds = self.seed(query, k=k)
        seed_ids = [s["id"] for s in seeds]
        context = self.traverse(seed_ids, depth=depth, mode=mode, max_nodes=max_nodes)
        return {
            "query": query,
            "mode": mode,
            "seeds": seeds,
            "context": context,
        }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--mode", choices=["bfs", "dfs"], default="bfs")
    ap.add_argument("--max-nodes", type=int, default=40)
    args = ap.parse_args()

    r = Retriever()
    res = r.retrieve(args.query, k=args.k, depth=args.depth, mode=args.mode,
                     max_nodes=args.max_nodes)
    print(f"QUERY: {res['query']}  (mode={res['mode']})")
    print(f"case edges loaded: {getattr(r, '_n_case_edges', 0)}")
    print(f"SEEDS ({len(res['seeds'])}):")
    for s in res["seeds"]:
        print(f"  {s['score']:.3f}  {s['id']}")
    print(f"\nCONTEXT ({len(res['context'])} nodes):")
    for n in res["context"]:
        print(f"  [{n['type'][:3]}] {n['label'][:70]}")
