"""Evaluate graphRAG idea-node recall against the golden set."""
import json
import sys

import numpy as np
from fastembed import TextEmbedding

EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def main() -> int:
    emb = np.load("graphify-out/idea_embeddings.npy").astype(np.float32)
    ids = json.load(open("graphify-out/idea_ids.json"))
    norm = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    model = TextEmbedding(EMB_MODEL)

    gs = json.load(open("tests/fixtures/golden_set.json"))
    entries = gs["entries"]

    hits = misses = skipped = 0
    missed = []
    for e in entries:
        ch = e["citation"]["chapter"]
        sec = e["citation"].get("section")
        if not sec:
            skipped += 1
            continue
        target = f"idea:{ch}|{sec}"
        if target not in ids:
            skipped += 1
            continue
        q = e["expected"].get("text_contains") or " ".join(e["expected"]["must_contain"])
        qv = np.asarray(next(model.embed([q])), dtype=np.float32)
        qv /= np.linalg.norm(qv)
        sim = norm @ qv
        order = np.argsort(-sim)
        rank = [ids[int(i)] for i in order].index(target) + 1
        if rank <= 20:
            hits += 1
        else:
            missed.append((e["id"], ch, sec, rank))

    total = len(entries) - skipped
    print(f"entries: {len(entries)}  evaluated: {total}  skipped: {skipped}")
    print(f"idea-node recall@20: {hits}/{total} = {hits/total:.0%}")
    for m in sorted(missed, key=lambda x: x[3])[:15]:
        print(f"  miss {m[0]} {m[1]}|{m[2]} rank={m[3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
