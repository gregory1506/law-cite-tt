from backend.scripts.load_case_edges import (
    _case_title,
    _case_year,
    _webopac_title,
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


def test_webopac_title_from_between_and():
    text = (
        "# abc123\n\n"
        "REPUBLIC OF TRINIDAD AND TOBAGO\n"
        "IN THE HIGH COURT OF JUSTICE\n"
        "Claim No. CV2018-01783\n"
        "BETWEEN\n"
        "DAVLIN THOMAS\n"
        "Claimant\n"
        "AND\n"
        "NARESH SIEWAH\n"
        "Defendant\n"
        "Before the Honourable Madame Justice Mohammed\n"
    )
    assert _webopac_title(text) == "Davlin Thomas v Naresh Siewah"


def test_webopac_title_strips_ordinal_role_suffix():
    text = (
        "BETWEEN\n"
        "RABINDRANATH MARAJ & RAMDATH MAHARAJ\n"
        "AND\n"
        "ZALIMOON KHAN 1st Defendant\n"
    )
    assert _webopac_title(text) == "Rabindranath Maraj & Ramdath Maharaj v Zalimoon Khan"


def test_webopac_title_numbered_parties():
    text = (
        "BETWEEN\n"
        "(1) RANDOLPH PARIA as Administrator\n"
        "(2) ANCIL PARIA\n"
        "(3) LINCOLN PARIA\n"
        "AND\n"
        "(4) GERARD PARIA\n"
    )
    assert _webopac_title(text) == "Randolph Paria as Administrator v Gerard Paria"


def test_webopac_title_court_of_appeal_of_and_pattern():
    text = (
        "REPUBLIC OF TRINIDAD AND TOBAGO\n"
        "Civil Appeal No. 1/2014\n"
        "IN THE COURT OF APPEAL\n"
        "OF\n"
        "JOYCELYN ANN MUNGROO\n"
        "(Legal Personal Representative of Arthur Mungroo, Deceased)\n"
        "AND\n"
        "ERIC SUDAMA\n"
        "APPELLANTS\n"
    )
    assert _webopac_title(text) == "Joycelyn Ann Mungroo v Eric Sudama"


def test_webopac_title_ignores_between_deep_in_body():
    text = (
        "REPUBLIC OF TRINIDAD AND TOBAGO\n"
        "Claim No. CV2017-04598\n"
        "Between\n"
        + "\n".join(f"line {i}" for i in range(50))
        + "\nBETWEEN\nBody party\n"
    )
    assert _webopac_title(text) == "line 0"


def test_webopac_title_skips_boilerplate_after_between():
    text = (
        "Between\n"
        "TRINIDAD AND TOBAGO\n"
        "NATIONAL PETROLEUM MARKETING COMPANY LIMITED\n"
        "Appellant/Interested Party\n"
        "And\n"
        "THE PETROLEUM DEALERS ASSOCIATION\n"
        "Respondent\n"
    )
    assert _webopac_title(text) == "National Petroleum Marketing Company Limited v The Petroleum Dealers Association"


def test_webopac_title_fallback_ignores_prose():
    text = "face. He was convicted of Wounding with Intent and sentenced to five years.\n"
    assert _webopac_title(text) == ""


def test_case_title_uses_record_title_field():
    rec = {"title": "Smith v Jones"}
    assert _case_title(rec) == "Smith v Jones"


def test_case_year_from_delivery_filename_and_delivery_line():
    rec = {"pdf_url": "http://x/LibraryJud/Judgments/HC/x/2018/cv_18_01783DD10apr2019.pdf"}
    assert _case_year(rec) == 2019
    rec2 = {"pdf_url": "http://x/LawTermOpen/2023.pdf", "text": "Date of Delivery 28 September 2023"}
    assert _case_year(rec2) == 2023