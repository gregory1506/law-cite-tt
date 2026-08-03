"""Build a GraphRAG of legal ideas from the law_cite.db cache.

Reads the existing SQLite cache (chapters, versions, chunks + 384-dim
embeddings) and produces graphify-out/graph.json plus cluster output.

Node types:
  - idea      : unique (chapter_number, section_ref) — the legal proposition
  - chapter   : a statute (parent of ideas)
  - concept   : a defined term extracted from interpretation sections

Edge types (tagged for audit):
  - EXTRACTED  chapter->idea  PART_OF
  - EXTRACTED  idea->idea     CROSS_REF   (explicit "Ch. XX:XX" / "section N")
  - EXTRACTED  idea->concept  MENTIONS
  - INFERRED   idea->idea     SEMANTIC    (embedding cosine top-k)
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

DB_PATH = Path("/Volumes/Extreme SSD/law-cite-tt-data/law_cite.db")
OUT_DIR = Path("graphify-out")

EMBED_DIM = 384
SEMANTIC_TOP_K = 6
SEMANTIC_THRESHOLD = 0.55
CONCEPT_MIN_CHAPTERS = 2
CONCEPT_MIN_IDEAS = 2

CROSS_CHAPTER_RE = re.compile(r"(?:Ch(?:ap)?|Cap)\.?\s*([0-9]{1,2}):([0-9]{1,2})")
CROSS_SECTION_RE = re.compile(r"(?:section|Section|s\.)\s+([0-9]{1,3}(?:[A-Za-z])?)")
DEFINED_TERM_RE = re.compile(r"[“\"]([A-Z][A-Za-z \-']{2,40})[”\"]\s+means")
LISTED_TERM_RE = re.compile(r"(?:the )?expression(?:s)?[“\"]([A-Za-z \-']{2,40})[”\"]")


def unpack(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32).copy()


def norm(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n else v


class Corpus:
    def __init__(self, db_path: Path = DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.chapters: dict[str, dict] = {}
        self.ideas: dict[str, dict] = {}

    def load_chapters(self) -> None:
        for row in self.conn.execute(
            "select chapter_number, title, classification, year, act_number, commencement_date from chapters"
        ):
            self.chapters[row["chapter_number"]] = {
                "id": f"chapter:{row['chapter_number']}",
                "type": "chapter",
                "label": row["title"] or row["chapter_number"],
                "chapter_number": row["chapter_number"],
                "classification": row["classification"],
                "year": row["year"],
                "act_number": row["act_number"],
                "commencement_date": row["commencement_date"],
                "text": row["title"] or "",
            }

    def load_ideas(self) -> None:
        """Group all chunks into canonical idea nodes (chapter|section)."""
        grouped: dict[tuple[str, str], list[sqlite3.Row]] = defaultdict(list)
        for row in self.conn.execute(
            "select chapter_number, section_ref, heading, chunk_text, "
            "as_at_date, version_id, chunk_index, embedding from chunks"
        ):
            grouped[(row["chapter_number"], row["section_ref"])].append(row)

        for (ch, sec), chunks in grouped.items():
            idea_id = f"idea:{ch}|{sec}"
            # pick the newest dated chunk's text; fall back to longest
            dated = [c for c in chunks if c["as_at_date"]]
            best = max(dated, key=lambda c: c["as_at_date"]) if dated else max(
                chunks, key=lambda c: len(c["chunk_text"])
            )
            # average embeddings across all versions (same 384-dim space)
            vecs = [unpack(c["embedding"]) for c in chunks if c["embedding"]]
            emb = norm(np.mean(vecs, axis=0)) if vecs else np.zeros(EMBED_DIM, dtype=np.float32)

            dates = sorted({c["as_at_date"] for c in chunks if c["as_at_date"]})
            self.ideas[idea_id] = {
                "id": idea_id,
                "type": "idea",
                "label": f"{ch} {sec} {best['heading']}".strip(),
                "chapter_number": ch,
                "section_ref": sec,
                "heading": best["heading"] or "",
                "text": best["chunk_text"],
                "n_versions": len({c["version_id"] for c in chunks}),
                "as_at_dates": dates,
                "embedding": emb.tolist(),
            }

    def extract_concepts(self) -> dict[str, dict]:
        """Defined terms that recur across multiple chapters -> concept nodes."""
        term_chapters: dict[str, set] = defaultdict(set)
        term_ideas: dict[str, set] = defaultdict(set)
        term_text: dict[str, str] = {}

        for idea in self.ideas.values():
            text = idea["text"]
            terms = set()
            for m in DEFINED_TERM_RE.finditer(text):
                terms.add(m.group(1).strip())
            for m in LISTED_TERM_RE.finditer(text):
                terms.add(m.group(1).strip())
            for term in terms:
                if len(term) < 3 or term.lower() in {"the", "this", "that"}:
                    continue
                term_chapters[term].add(idea["chapter_number"])
                term_ideas[term].add(idea["id"])
                term_text.setdefault(term, text[:300])

        concepts: dict[str, dict] = {}
        for term, chs in term_chapters.items():
            if len(chs) < CONCEPT_MIN_CHAPTERS:
                continue
            if len(term_ideas[term]) < CONCEPT_MIN_IDEAS:
                continue
            concepts[f"concept:{term}"] = {
                "id": f"concept:{term}",
                "type": "concept",
                "label": term,
                "text": term_text[term],
                "n_chapters": len(chs),
                "n_ideas": len(term_ideas[term]),
            }
        return concepts

    def extract_cross_refs(self) -> list[dict]:
        """EXTRACTED edges from explicit citations in chunk text."""
        edges: list[dict] = []
        for idea in self.ideas.values():
            text = idea["text"]
            for m in CROSS_CHAPTER_RE.finditer(text):
                target = f"chapter:{m.group(1)}:{m.group(2)}"
                if target in self.chapters:
                    edges.append(
                        {
                            "source": idea["id"],
                            "target": target,
                            "type": "CROSS_REF",
                            "evidence": "EXTRACTED",
                            "detail": m.group(0),
                        }
                    )
            same_chapter_secs = set()
            for m in CROSS_SECTION_RE.finditer(text):
                same_chapter_secs.add(m.group(1))
            for sec in same_chapter_secs:
                target = f"idea:{idea['chapter_number']}|{sec}"
                if target in self.ideas and target != idea["id"]:
                    edges.append(
                        {
                            "source": idea["id"],
                            "target": target,
                            "type": "CROSS_REF",
                            "evidence": "EXTRACTED",
                            "detail": f"section {sec}",
                        }
                    )
        return edges

    def idea_mentions_concepts(self, concepts: dict[str, dict]) -> list[dict]:
        edges: list[dict] = []
        for cid, c in concepts.items():
            term = c["label"]
            pat = re.compile(rf"[“\" ]{re.escape(term)}[”\" ,.;:]")
            for iid, idea in self.ideas.items():
                if pat.search(idea["text"]):
                    edges.append(
                        {
                            "source": iid,
                            "target": cid,
                            "type": "MENTIONS",
                            "evidence": "EXTRACTED",
                            "detail": term,
                        }
                    )
        return edges

    def semantic_edges(self) -> list[dict]:
        """INFERRED edges via top-k cosine similarity between idea embeddings.

        Uses blocked matmul to avoid materialising a full 23k x 23k matrix.
        """
        ids = list(self.ideas.keys())
        X = np.array([self.ideas[i]["embedding"] for i in ids], dtype=np.float32)
        norm_X = X / np.linalg.norm(X, axis=1, keepdims=True)

        edges: list[dict] = []
        BLOCK = 512
        for lo in range(0, len(ids), BLOCK):
            hi = min(lo + BLOCK, len(ids))
            block = norm_X[lo:hi]
            sims = block @ norm_X.T  # (BLOCK, N)
            for r in range(hi - lo):
                row = sims[r]
                idx = np.argpartition(-row, SEMANTIC_TOP_K + 1)[: SEMANTIC_TOP_K + 1]
                best = idx[np.argsort(-row[idx])]
                for j in best:
                    if j <= lo + r:  # dedupe + self
                        continue
                    if row[j] < SEMANTIC_THRESHOLD:
                        continue
                    edges.append(
                        {
                            "source": ids[lo + r],
                            "target": ids[int(j)],
                            "type": "SEMANTIC",
                            "evidence": "INFERRED",
                            "weight": round(float(row[j]), 4),
                            "detail": "embedding cosine",
                        }
                    )
        return edges


def build(db_path: Path = DB_PATH, out_dir: Path = OUT_DIR, with_semantic: bool = True) -> dict:
    corpus = Corpus(db_path)
    corpus.load_chapters()
    corpus.load_ideas()
    concepts = corpus.extract_concepts()

    nodes = list(corpus.chapters.values()) + list(corpus.ideas.values()) + list(concepts.values())

    # persist idea embeddings so the retriever doesn't re-aggregate 407k rows
    np.save(out_dir / "idea_embeddings.npy", np.array(
        [corpus.ideas[i]["embedding"] for i in corpus.ideas], dtype=np.float32))
    (out_dir / "idea_ids.json").write_text(json.dumps(list(corpus.ideas.keys())))

    # compute edges first: semantic scoring needs the embeddings still present
    edges = [{"source": c["id"], "target": i["id"], "type": "PART_OF",
              "evidence": "EXTRACTED", "detail": "statute"}
             for cid, c in corpus.chapters.items()
             for i in corpus.ideas.values() if i["chapter_number"] == c["chapter_number"]]
    if with_semantic:
        edges += corpus.semantic_edges()

    for n in nodes:
        n.pop("embedding", None)

    edges += corpus.extract_cross_refs()
    edges += corpus.idea_mentions_concepts(concepts)

    # audit counts
    evidence_counts = Counter(e["evidence"] for e in edges)
    type_counts = Counter(e["type"] for e in edges)
    node_type_counts = Counter(n["type"] for n in nodes)

    # invariant: every edge must resolve to a real node (dangling edges break
    # traversal while being invisible to recall/stat metrics)
    node_ids = {n["id"] for n in nodes}
    dangling = [e for e in edges if e["source"] not in node_ids or e["target"] not in node_ids]
    if dangling:
        raise SystemExit(
            f"build abort: {len(dangling)} dangling edges "
            f"(first: {dangling[0]})"
        )

    out = {
        "meta": {
            "source": str(db_path),
            "nodes": len(nodes),
            "edges": len(edges),
            "node_types": dict(node_type_counts),
            "edge_types": dict(type_counts),
            "evidence": dict(evidence_counts),
        },
        "nodes": nodes,
        "edges": edges,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "graph.json").write_text(json.dumps(out, indent=1))

    report = {
        "graph": out["meta"],
        "clusters": cluster_nodes(nodes, edges),
    }
    (out_dir / "clusters.json").write_text(json.dumps(report, indent=1))
    return out


def cluster_nodes(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """Community detection on the idea backbone via networkx greedy modularity."""
    import networkx as nx

    G = nx.Graph()
    ideas = [n for n in nodes if n["type"] == "idea"]
    for n in ideas:
        G.add_node(n["id"])
    idea_ids = {n["id"] for n in ideas}
    for e in edges:
        if e["source"] in idea_ids and e["target"] in idea_ids:
            G.add_edge(e["source"], e["target"], weight=e.get("weight", 1.0))

    clusters = []
    for i, comm in enumerate(nx.community.greedy_modularity_communities(G, weight="weight")):
        members = []
        for nid in comm:
            node = next(n for n in ideas if n["id"] == nid)
            members.append(
                {
                    "id": nid,
                    "chapter": node["chapter_number"],
                    "section": node["section_ref"],
                    "heading": node["heading"],
                    "label": node["label"],
                }
            )
        clusters.append({"cluster": i, "size": len(members), "members": members})
    clusters.sort(key=lambda c: -c["size"])
    for i, c in enumerate(clusters):
        c["cluster"] = i
    return clusters


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DB_PATH)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--no-semantic", action="store_true")
    args = ap.parse_args()
    result = build(args.db, args.out, with_semantic=not args.no_semantic)
    print(json.dumps(result["meta"], indent=2))
    print(f"\nWrote {args.out / 'graph.json'} and {args.out / 'clusters.json'}")
