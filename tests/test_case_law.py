"""Tests for the CCJ case-law crawler and CITES_STATUTE edge extractor."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from graphrag.case_edges import (  # noqa: E402
    build_act_index,
    dedupe,
    extract_edges,
    load_cases,
)
from scraper.case_crawl import extract_body, parse_feed  # noqa: E402

SAMPLE_FEED = """<?xml version="1.0"?><rss><channel>
<item><title>[2006] CCJ 1 (AJ)</title>
<link>https://ccj.org/2006-ccj-1-aj/?utm_source=rss&amp;utm_medium=rss</link></item>
<item><title>[2023] CCJ 13 (AJ) BB</title>
<link>https://ccj.org/ccj-clarifies-direction/?utm_source=rss</link></item>
</channel></rss>"""

SAMPLE_PAGE = """<html><head>
<meta property="og:description" content="The Court dismissed the appeal.
The Criminal Offences Act Ch. 11:01 applied.">
</head><body>
<p>Today the CCJ dismissed the appeal. Section 5 of the Prevention of Crimes Act
Cap. 10:01 was applied.</p>
<p>Short.</p>
<script>var x=1;</script>
</body></html>"""


class TestParseFeed:
    def test_strips_utm_and_returns_pairs(self):
        items = parse_feed(SAMPLE_FEED)
        assert len(items) == 2
        title, url = items[0]
        assert title == "[2006] CCJ 1 (AJ)"
        assert url == "https://ccj.org/2006-ccj-1-aj/"


class TestExtractBody:
    def test_uses_paragraphs_when_present(self):
        body = extract_body(SAMPLE_PAGE)
        assert "Prevention of Crimes Act" in body
        assert "Short." not in body  # filtered (too short)
        assert "var x=1" not in body  # script stripped

    def test_falls_back_to_og_description(self):
        page = "<html><head><meta property='og:description' content='A long case note about the Act. With enough text. Indeed it is quite long.'></head><body><p>hi</p></body></html>"
        body = extract_body(page)
        assert "case note" in body


def _nodes():
    return {
        "chapter:11:01": {"id": "chapter:11:01", "type": "chapter",
                          "label": "Criminal Offences", "chapter_number": "11:01"},
        "chapter:10:01": {"id": "chapter:10:01", "type": "chapter",
                          "label": "Prevention of Crimes", "chapter_number": "10:01"},
        "chapter:75:01": {"id": "chapter:75:01", "type": "chapter",
                          "label": "Income Tax", "chapter_number": "75:01"},
        "chapter:4:20": {"id": "chapter:4:20", "type": "chapter",
                         "label": "Summary Courts", "chapter_number": "4:20"},
        "chapter:5:01": {"id": "chapter:5:01", "type": "chapter",
                         "label": "Arbitration", "chapter_number": "5:01"},
        "idea:11:01|5": {"id": "idea:11:01|5", "type": "idea",
                         "chapter_number": "11:01", "section_ref": "5"},
    }


class TestExtractEdges:
    def test_resolves_chapter_and_title_citations(self, tmp_path):
        cases = [{
            "id": "abc1",
            "title": "[2006] CCJ 1 (AJ)",
            "body": ("The Court applied the Criminal Offences Act, Ch. 11:01 "
                     "and section 5. Counsel also cited the Arbitration Act."),
        }]
        nodes = _nodes()
        edges = dedupe(extract_edges(cases, nodes, build_act_index(nodes)))
        targets = {(e["target"], e["method"]) for e in edges}
        assert ("chapter:11:01", "REGEX") in targets
        assert ("chapter:11:01", "TITLE_MATCH") in targets
        assert ("chapter:5:01", "TITLE_MATCH") in targets
        for e in edges:
            assert e["evidence"] == "EXTRACTED"
            assert e["source"].startswith("case:abc1")

    def test_ignores_unknown_chapters(self):
        cases = [{"id": "x", "title": "t",
                  "body": "The Court cited Ch. 99:99 which does not exist."}]
        nodes = _nodes()
        edges = extract_edges(cases, nodes, build_act_index(nodes))
        assert edges == []

    def test_confidences(self):
        cases = [{
            "id": "abc1",
            "title": "t",
            "body": "The Arbitration Act and Cap. 5:01 were considered.",
        }]
        nodes = _nodes()
        edges = extract_edges(cases, nodes, build_act_index(nodes))
        confs = {(e["target"], e["method"], e["confidence"]) for e in edges}
        assert ("chapter:5:01", "TITLE_MATCH", "high") in confs
        assert ("chapter:5:01", "REGEX", "medium") in confs


class TestLoadCases:
    def test_reads_jsonl(self, tmp_path):
        p = tmp_path / "judgments.jsonl"
        p.write_text(json.dumps({"id": "a", "body": "x"}) + "\n"
                     + json.dumps({"id": "b", "body": "y"}) + "\n")
        out = load_cases(tmp_path)
        assert len(out) == 2
        assert out[0]["id"] == "a"
