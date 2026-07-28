from pathlib import Path

import pytest

from scraper.chunker import (
    SectionChunk,
    extract_section_chunks,
    _find_body_start as find_body_start,
    parse_header,
)

FIXTURES = Path(__file__).parent / "fixtures"
DATA = Path("/Volumes/Extreme SSD/law-cite-tt-data")


def _read(chapter: str, file_id: str) -> str:
    path = DATA / "markdown" / chapter / f"{file_id}.md"
    if not path.exists():
        pytest.skip(f"source file not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


class TestParseHeader:
    def test_absconding_debtors_current(self):
        text = _read("8_08_Absconding_Debtors", "105522")
        h = parse_header(text)
        assert h["chapter"] == "8:08"
        assert h["title"] == "Absconding Debtors"
        assert h["as_at_date"] == "2016-12-31"

    def test_original_ordinance(self):
        text = _read("8_08_Absconding_Debtors", "80890")
        h = parse_header(text)
        assert h["chapter"] == "8:08"
        assert "Original" in h["version_label"]

    def test_anatomy(self):
        text = _read("28_06_Anatomy", "106753")
        h = parse_header(text)
        assert h["chapter"] == "28:06"
        assert h["title"] == "Anatomy"


class TestFindBodyStart:
    def test_skips_arrangement(self):
        text = _read("8_08_Absconding_Debtors", "105522")
        lines = text.split("\n")
        start = find_body_start(lines)
        assert start > 0
        body = "\n".join(lines[start:])
        assert "Short title. 1." in body
        assert "ARRANGEMENT OF SECTIONS" not in body

    def test_antibiotics_body(self):
        text = _read("30_02_Antibiotics", "106044")
        lines = text.split("\n")
        start = find_body_start(lines)
        body = "\n".join(lines[start:])
        assert "Short title. 1." in body
        assert "ARRANGEMENT OF SECTIONS" not in body


class TestExtractSections:
    def test_absconding_debtors_has_17_sections(self):
        text = _read("8_08_Absconding_Debtors", "105522")
        chunks = extract_section_chunks(text)
        refs = [c.section_ref for c in chunks]
        assert len(refs) >= 15
        assert "1" in refs
        assert "17" in refs

    def test_section_1_text(self):
        text = _read("8_08_Absconding_Debtors", "105522")
        chunks = extract_section_chunks(text)
        s1 = next(c for c in chunks if c.section_ref == "1")
        assert "Absconding Debtors Act" in s1.chunk_text
        assert "Act" in s1.chunk_text
        assert "Ordinance" not in s1.chunk_text

    def test_section_5_text(self):
        text = _read("8_08_Absconding_Debtors", "105522")
        chunks = extract_section_chunks(text)
        s5 = next(c for c in chunks if c.section_ref == "5")
        assert "intention" in s5.chunk_text
        assert "affidavit" in s5.chunk_text

    def test_accessories_section_1(self):
        text = _read("10_02_Accessories_and_Abettors", "105526")
        chunks = extract_section_chunks(text)
        s1 = next(c for c in chunks if c.section_ref == "1")
        assert "Accessories and Abettors Act" in s1.chunk_text

    def test_antibiotics_section_3(self):
        text = _read("30_02_Antibiotics", "106044")
        chunks = extract_section_chunks(text)
        s3 = next(c for c in chunks if c.section_ref == "3")
        assert "Antibiotics Control Committee" in s3.chunk_text
        assert "Chairman" in s3.chunk_text

    def test_anatomy_section_2_definition_list(self):
        text = _read("28_06_Anatomy", "106753")
        chunks = extract_section_chunks(text)
        s2 = next(c for c in chunks if c.section_ref == "2")
        assert "nearest relative" in s2.chunk_text
        assert "spouse" in s2.chunk_text
        assert "son or daughter" in s2.chunk_text

    def test_anatomy_section_14(self):
        text = _read("28_06_Anatomy", "106753")
        chunks = extract_section_chunks(text)
        s14 = next(c for c in chunks if c.section_ref == "14")
        assert "post-mortem" in s14.chunk_text
        assert len(s14.chunk_text) > 150

    def test_summary_courts_section_3A(self):
        text = _read("4_20_Summary_Courts", "105711")
        chunks = extract_section_chunks(text)
        s3a = next(c for c in chunks if c.section_ref == "3A")
        assert "Magistrate" in s3a.chunk_text

    def test_ads_regulation_section_3(self):
        text = _read("35_53_Advertisements_Regulation", "106095")
        chunks = extract_section_chunks(text)
        s3 = next(c for c in chunks if c.section_ref == "3")
        assert "hoarding" in s3.chunk_text

    def test_income_tax_section_3(self):
        text = _read("85_04_Income_Tax_In_Aid_of_Industry", "106435")
        chunks = extract_section_chunks(text)
        s3 = next(c for c in chunks if c.section_ref == "3")
        assert "allowance" in s3.chunk_text.lower()

    def test_supreme_court_section_4(self):
        text = _read("4_01_Supreme_Court_of_Judicature", "105707")
        chunks = extract_section_chunks(text)
        s4 = next(c for c in chunks if c.section_ref == "4")
        assert "Supreme Court" in s4.chunk_text

    def test_temporal_original_ordinance(self):
        text = _read("8_08_Absconding_Debtors", "80890")
        chunks = extract_section_chunks(text)
        s1 = next(c for c in chunks if c.section_ref == "1")
        assert "Ordinance" in s1.chunk_text

    def test_temporal_1950_edition(self):
        text = _read("8_08_Absconding_Debtors", "23669")
        chunks = extract_section_chunks(text)
        s1 = next(c for c in chunks if c.section_ref == "1")
        assert "Act" in s1.chunk_text

    def test_temporal_accessories_original(self):
        text = _read("10_02_Accessories_and_Abettors", "40413")
        chunks = extract_section_chunks(text)
        s1 = next(c for c in chunks if c.section_ref == "1")
        assert "Ordinance" in s1.chunk_text

    def test_chunks_have_metadata(self):
        text = _read("8_08_Absconding_Debtors", "105522")
        chunks = extract_section_chunks(text)
        assert all(c.chapter_number == "8:08" for c in chunks)
        assert all(c.as_at_date for c in chunks)
