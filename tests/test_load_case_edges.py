from backend.scripts.load_case_edges import (
    chapter_from_target,
    parse_edges,
)


def _edge(source, target, method="REGEX", confidence="medium", detail=""):
    return {
        "source": source,
        "target": target,
        "type": "CITES_STATUTE",
        "evidence": "EXTRACTED",
        "method": method,
        "confidence": confidence,
        "detail": detail,
    }


def test_chapter_from_target():
    assert chapter_from_target("chapter:5:01") == "5:01"
    assert chapter_from_target("chapter:8:08") == "8:08"


def test_parse_edges_builds_cases_and_citations():
    edges = [
        _edge("case:8eec828c74db14ee", "chapter:5:01", detail="Ch. 5:01"),
        _edge("case:8eec828c74db14ee", "chapter:5:01", detail="Ch. 5:01"),
        _edge("case:0ee59724f387f344", "chapter:48:50"),
    ]
    records = [
        {
            "record_id": "8eec828c74db14ee",
            "title": "Smith v Jones",
            "source": "webopac",
        }
    ]
    cases, citations = parse_edges(edges, records)

    assert len(cases) == 2
    by_id = {c["id"]: c for c in cases}
    assert by_id["case:8eec828c74db14ee"]["title"] == "Smith v Jones"
    assert by_id["case:8eec828c74db14ee"]["record_id"] == "8eec828c74db14ee"
    assert by_id["case:0ee59724f387f344"]["title"] == ""
    assert by_id["case:0ee59724f387f344"]["source"] == ""

    assert len(citations) == 2
    assert citations[0]["chapter_number"] == "5:01"
    assert citations[0]["confidence"] == "medium"


def test_parse_edges_without_records_keeps_blank_titles():
    edges = [_edge("case:8eec828c74db14ee", "chapter:5:01")]
    cases, citations = parse_edges(edges, [])
    assert cases[0]["title"] == ""
    assert cases[0]["year"] is None
    assert len(citations) == 1


def test_parse_edges_extracts_year_from_record():
    edges = [_edge("case:8eec828c74db14ee", "chapter:5:01")]
    records = [
        {
            "record_id": "8eec828c74db14ee",
            "title": "Smith v Jones",
            "year": "2015-03-02",
        }
    ]
    cases, _ = parse_edges(edges, records)
    assert cases[0]["year"] == 2015