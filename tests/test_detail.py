from pathlib import Path

from scraper.detail import parse_chapter_detail

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_chapter_metadata():
    html = (FIXTURES / "chapter_detail_page.html").read_text()
    detail = parse_chapter_detail(html, current_id=490)

    assert detail.current_id == 490
    assert detail.title == "Absconding Debtors"
    assert detail.chapter_number == "8:08"
    assert "arrest of absconding debtors" in detail.description
    assert detail.year == "1898"
    assert detail.act_number == "20"
    assert detail.commencement_date == "Fri, 5 Aug 1898"
    assert detail.classification == "CIVIL LAW AND PROCEDURE"


def test_parses_versions_newest_first_as_listed():
    html = (FIXTURES / "chapter_detail_page.html").read_text()
    detail = parse_chapter_detail(html, current_id=490)

    assert len(detail.versions) == 3
    latest = detail.versions[0]
    assert latest.download_id == 105522
    assert latest.label == "2006 Revised Edition"
    assert latest.as_at_date == "as at December 31st 2016"

    unofficial = detail.versions[1]
    assert unofficial.download_id == 90849
    assert unofficial.label == "*Unofficial Update"
