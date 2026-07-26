from pathlib import Path
from unittest.mock import MagicMock

from scraper.catalog import crawl_full_catalog, parse_listing_page

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_all_entries_on_a_listing_page():
    html = (FIXTURES / "listing_page.html").read_text()
    listings = parse_listing_page(html)

    assert len(listings) == 7
    first = listings[0]
    assert first.current_id == 490
    assert first.title == "Absconding Debtors"
    assert first.subtitle == "Chapter 8:08"


def test_parses_subtitle_with_alert_text_intact():
    html = (FIXTURES / "listing_page.html").read_text()
    listings = parse_listing_page(html)

    adoption = next(l for l in listings if l.current_id == 822)
    assert "Chapter 46:03" in adoption.subtitle
    assert "repealed and replaced" in adoption.subtitle


def test_parse_listing_page_returns_empty_list_for_empty_page():
    html = (FIXTURES / "empty_listing_page.html").read_text()
    assert parse_listing_page(html) == []


def test_crawl_full_catalog_paginates_until_an_empty_page():
    listing_html = (FIXTURES / "listing_page.html").read_text()
    empty_html = (FIXTURES / "empty_listing_page.html").read_text()

    fake_client = MagicMock()
    fake_client.get.side_effect = [
        MagicMock(text=listing_html),
        MagicMock(text=listing_html),
        MagicMock(text=empty_html),
    ]

    listings = crawl_full_catalog(
        fake_client, base_url="https://laws.gov.tt", listing_path="/ttdll-web/revision/list", page_size=10
    )

    assert len(listings) == 14  # 7 entries per page, 2 non-empty pages
    assert fake_client.get.call_count == 3
    called_urls = [call.args[0] for call in fake_client.get.call_args_list]
    assert called_urls == [
        "https://laws.gov.tt/ttdll-web/revision/list?offset=0",
        "https://laws.gov.tt/ttdll-web/revision/list?offset=10",
        "https://laws.gov.tt/ttdll-web/revision/list?offset=20",
    ]
