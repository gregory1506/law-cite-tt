import json
import tempfile
from pathlib import Path

import pytest

from scraper.db import LawCiteDB

DATA = Path("/Volumes/Extreme SSD/law-cite-tt-data")


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp = f.name
    db = LawCiteDB(tmp)
    db.init_schema()
    yield db
    db.close()
    Path(tmp).unlink(missing_ok=True)


class TestSchema:
    def test_init_creates_tables(self, db):
        conn = db.connect()
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "chapters" in tables
        assert "versions" in tables
        assert "chunks" in tables

    def test_fts_table_created(self, db):
        conn = db.connect()
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "chunks_fts" in tables


class TestIngestion:
    def test_ingest_absconding_debtors(self, db):
        n = db.ingest_chapter("8_08_Absconding_Debtors", DATA / "markdown")
        assert n > 0, "should have ingested some chunks"
        conn = db.connect()
        row = conn.execute("SELECT COUNT(*) as cnt FROM chunks").fetchone()
        assert row["cnt"] == n

    def test_chunks_have_section_refs(self, db):
        db.ingest_chapter("8_08_Absconding_Debtors", DATA / "markdown")
        conn = db.connect()
        rows = conn.execute(
            "SELECT section_ref, chunk_text FROM chunks LIMIT 10"
        ).fetchall()
        assert all(r["section_ref"] for r in rows)

    def test_ingest_multiple_versions(self, db):
        db.ingest_chapter("8_08_Absconding_Debtors", DATA / "markdown")
        conn = db.connect()
        cnt = conn.execute("SELECT COUNT(*) as cnt FROM versions").fetchone()["cnt"]
        assert cnt >= 3, "should have multiple versions"


class TestLookup:
    def test_lookup_section_1(self, db):
        db.ingest_chapter("8_08_Absconding_Debtors", DATA / "markdown")
        results = db.lookup_section("8:08", "1")
        assert len(results) >= 1
        r = results[0]
        assert "Absconding Debtors Act" in r["chunk_text"]
        assert r["chapter_number"] == "8:08"
        assert r["section_ref"] == "1"

    def test_lookup_by_date(self, db):
        db.ingest_chapter("8_08_Absconding_Debtors", DATA / "markdown")
        results = db.lookup_section("8:08", "1", as_at_date="2016-12-31")
        assert len(results) >= 1
        r = results[0]
        assert "Act" in r["chunk_text"]
        assert "Ordinance" not in r["chunk_text"]

    def test_lookup_original_ordinance(self, db):
        db.ingest_chapter("8_08_Absconding_Debtors", DATA / "markdown")
        results = db.lookup_section("8:08", "1")
        texts = [r["chunk_text"] for r in results]
        has_ordinance = any("Ordinance" in t for t in texts)
        assert has_ordinance, "at least one version should say 'Ordinance'"

    def test_lookup_section_3A(self, db):
        db.ingest_chapter("4_20_Summary_Courts", DATA / "markdown")
        results = db.lookup_section("4:20", "3A")
        assert len(results) >= 1
        assert "Magistrate" in results[0]["chunk_text"]

    def test_lookup_nonexistent_returns_empty(self, db):
        db.ingest_chapter("8_08_Absconding_Debtors", DATA / "markdown")
        results = db.lookup_section("8:08", "99")
        assert len(results) == 0


class TestGoldenSet:
    def test_all_golden_entries_retrievable(self, db):
        gl = json.loads(
            (Path(__file__).parent / "fixtures" / "golden_set.json").read_text()
        )
        entries = gl.get("entries", gl) if isinstance(gl, dict) else gl

        chapters_to_ingest = set()
        for e in entries:
            parts = e["source_file"].split("/")
            chapters_to_ingest.add(parts[0])

        for ch in chapters_to_ingest:
            db.ingest_chapter(ch, DATA / "markdown")
        db.rebuild_fts()

        failures = []
        for e in entries:
            cit = e["citation"]
            ch = cit["chapter"]
            sec = cit.get("section", "")
            if not sec:
                continue
            date = e["temporal_context"].get("as_at_date", "")

            if e["expected"].get("should_not_exist"):
                results = db.lookup_section(ch, sec)
                if len(results) > 0:
                    failures.append(f"{e['id']}: should not exist but found")
                continue

            results = db.lookup_section(ch, sec, as_at_date=date) if date else db.lookup_section(ch, sec)
            if not results and date:
                results = db.lookup_section(ch, sec)

            if not results:
                failures.append(f"{e['id']}: no results for {ch} s{sec}")
                continue

            exp = e["expected"]
            tc = exp.get("text_contains", "")
            must = exp.get("must_contain", [])
            must_not = exp.get("must_not_contain", [])
            mc = exp.get("min_chars", 0)

            found_match = False
            for r in results:
                text = r["chunk_text"]
                ok = True
                if tc and tc not in text:
                    ok = False
                if ok and must:
                    for m in must:
                        if m not in text:
                            ok = False
                            break
                if not ok:
                    continue
                for mn in must_not:
                    if mn in text:
                        ok = False
                        break
                if not ok:
                    continue
                if mc and len(text) < mc:
                    ok = False
                if ok:
                    found_match = True
                    break

            if not found_match:
                verdicts = []
                for r in results:
                    text = r["chunk_text"]
                    issues = []
                    if tc and tc not in text:
                        issues.append("no_text_contains")
                    for m in must:
                        if m not in text:
                            issues.append(f"missing:{m}")
                    for mn in must_not:
                        if mn in text:
                            issues.append(f"found:{mn}")
                    if mc and len(text) < mc:
                        issues.append(f"too_short({len(text)}<{mc})")
                    verdicts.append(f"[{len(text)}c/{r['as_at_date']}] {' '.join(issues)}")
                failures.append(f"{e['id']}: {'; '.join(verdicts)}")

        assert not failures, "\n".join(failures[:20])
