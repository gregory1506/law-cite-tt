from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scraper.db import LawCiteDB
from scraper.embed import cosine_similarity, embed_batch, embed_text, pack_embedding
from scraper.search import SearchEngine

DATA = Path("/Volumes/Extreme SSD/law-cite-tt-data")


@pytest.fixture
def db_and_engine(tmp_path):
    db_path = tmp_path / "test_search.db"
    db = LawCiteDB(db_path)
    engine = SearchEngine(db_path)
    yield db, engine
    engine.close()
    db.close()


@pytest.fixture
def seeded_db(db_and_engine):
    db, engine = db_and_engine
    db.ingest_chapter("8_08_Absconding_Debtors", DATA / "markdown")
    db.ingest_chapter("4_20_Summary_Courts", DATA / "markdown")
    db.rebuild_fts()
    return db, engine


class TestEmbed:
    def test_embed_text_returns_384_floats(self):
        vec = embed_text("This Act may be cited as the Absconding Debtors Act")
        assert len(vec) == 384
        assert all(isinstance(v, float) for v in vec)

    def test_embed_batch_parallels_single(self):
        texts = ["first text", "second text", "third text"]
        vecs = embed_batch(texts)
        assert len(vecs) == 3
        assert all(len(v) == 384 for v in vecs)

    def test_cosine_similarity_same_is_approx_1(self):
        vec = embed_text("test string")
        assert cosine_similarity(vec, vec) > 0.999

    def test_cosine_similarity_orthogonal(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert abs(cosine_similarity(a, b)) < 0.001

    def test_pack_unpack_roundtrip(self):
        vec = [0.1, 0.2, 0.3, 0.0, -0.5]
        data = pack_embedding(vec)
        from scraper.embed import unpack_embedding

        restored = unpack_embedding(data)
        assert len(restored) == len(vec)
        for a, b in zip(vec, restored):
            assert abs(a - b) < 1e-6


class TestSearchEngine:
    def test_fts_finds_by_keyword(self, seeded_db):
        db, engine = seeded_db
        results = engine.fts_search("absconding")
        assert len(results) > 0
        assert all("absconding" in r["chunk_text"].lower() for r in results)

    def test_fts_filters_by_chapter(self, seeded_db):
        db, engine = seeded_db
        results = engine.fts_search("absconding", chapter="8:08")
        assert len(results) > 0
        assert all(r["chapter_number"] == "8:08" for r in results)

    def test_fts_excludes_other_chapter(self, seeded_db):
        db, engine = seeded_db
        results = engine.fts_search("absconding", chapter="4:20")
        assert len(results) == 0

    def test_vector_search_returns_scored(self, seeded_db):
        db, engine = seeded_db
        if not engine.has_embeddings():
            from scraper.embed import embed_chunks_from_db
            embed_chunks_from_db(engine.db_path)
        results = engine.vector_search("absconding debtor")
        assert len(results) > 0
        assert all("score" in r for r in results)
        assert results[0]["score"] >= results[-1]["score"]

    def test_vector_search_filters_by_chapter(self, seeded_db):
        db, engine = seeded_db
        if not engine.has_embeddings():
            from scraper.embed import embed_chunks_from_db
            embed_chunks_from_db(engine.db_path)
        results = engine.vector_search("absconding debtor", chapter="8:08")
        assert len(results) > 0
        assert all(r["chapter_number"] == "8:08" for r in results)

    def test_hybrid_combines_both(self, seeded_db):
        db, engine = seeded_db
        if not engine.has_embeddings():
            from scraper.embed import embed_chunks_from_db
            embed_chunks_from_db(engine.db_path)
        results = engine.hybrid_search("absconding debtor")
        assert len(results) > 0

    def test_has_embeddings_returns_false_without_embed(self, db_and_engine):
        db, engine = db_and_engine
        assert not engine.has_embeddings()

    def test_has_embeddings_returns_true_with_embed(self, seeded_db):
        db, engine = seeded_db
        if not engine.has_embeddings():
            from scraper.embed import embed_chunks_from_db
            embed_chunks_from_db(engine.db_path)
        assert engine.has_embeddings()
