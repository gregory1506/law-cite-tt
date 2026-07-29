from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np

try:
    from fastembed import TextEmbedding

    _MODEL = None
except ImportError:
    TextEmbedding = None  # type: ignore


def _fastembed_name(model_name: str) -> str:
    if "/" in model_name:
        return model_name
    return f"sentence-transformers/{model_name}"


def _get_model(model_name: str = "all-MiniLM-L6-v2"):
    global _MODEL
    if TextEmbedding is None:
        raise ImportError("fastembed not installed")
    if _MODEL is None:
        _MODEL = TextEmbedding(model_name=_fastembed_name(model_name))
    return _MODEL


def embed_text(text: str, model_name: str = "all-MiniLM-L6-v2") -> list[float]:
    model = _get_model(model_name)
    vec = next(model.embed([text]))
    return vec.tolist()


def embed_batch(
    texts: list[str], model_name: str = "all-MiniLM-L6-v2", batch_size: int = 32
) -> list[list[float]]:
    model = _get_model(model_name)
    vecs = list(model.embed(texts, batch_size=batch_size))
    return [v.tolist() for v in vecs]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    arr_a = np.array(a, dtype=np.float32)
    arr_b = np.array(b, dtype=np.float32)
    return float(np.dot(arr_a, arr_b))


def pack_embedding(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def unpack_embedding(data: bytes) -> list[float]:
    return list(struct.unpack(f"{len(data) // 4}f", data))


def embed_chunks_from_db(db_path: str | Path, model_name: str = "all-MiniLM-L6-v2"):
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    has_col = conn.execute(
        "PRAGMA table_info(chunks)"
    ).fetchall()
    col_names = [r["name"] for r in has_col]
    if "embedding" not in col_names:
        conn.execute("ALTER TABLE chunks ADD COLUMN embedding BLOB")
        conn.commit()

    rows = conn.execute(
        "SELECT id, chunk_text FROM chunks WHERE embedding IS NULL"
    ).fetchall()

    if not rows:
        conn.close()
        return 0

    texts = [r["chunk_text"] for r in rows]
    ids = [r["id"] for r in rows]
    vecs = embed_batch(texts, model_name=model_name)

    for row_id, vec in zip(ids, vecs):
        conn.execute(
            "UPDATE chunks SET embedding = ? WHERE id = ?",
            (pack_embedding(vec), row_id),
        )

    conn.commit()
    conn.close()
    return len(rows)
