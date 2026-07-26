import csv
from pathlib import Path
from unittest.mock import MagicMock

from scraper.recon import run_reconnaissance

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_pdf_bytes(tmp_path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "source.pdf"
    c = canvas.Canvas(str(path))
    c.drawString(100, 750, "Section 1. Test text for reconnaissance run.")
    c.save()
    return path.read_bytes()


def test_writes_pdf_and_markdown_for_each_chapter_and_a_summary_report(tmp_path):
    listing_html = (FIXTURES / "listing_page.html").read_text()
    empty_html = (FIXTURES / "empty_listing_page.html").read_text()
    detail_html = (FIXTURES / "chapter_detail_page.html").read_text()
    pdf_bytes = _fake_pdf_bytes(tmp_path)

    fake_client = MagicMock()

    def fake_get(url):
        if "revision/list?offset=0" in url and "currentid" not in url:
            return MagicMock(text=listing_html)
        if "revision/list?offset=10" in url:
            return MagicMock(text=empty_html)
        if "currentid=" in url:
            # give each chapter a distinct title/chapter number by patching
            # the shared fixture, so each one gets a unique filename on disk
            # (real chapters obviously differ; the shared fixture wouldn't
            # exercise that unless nudged apart here).
            current_id = url.rsplit("currentid=", 1)[1]
            per_chapter_html = detail_html.replace(
                "Absconding Debtors Chap. 8:08",
                f"Test Chapter {current_id} Chap. 1:{current_id}",
            )
            return MagicMock(text=per_chapter_html)
        if "revision/download/" in url:
            return MagicMock(content=pdf_bytes)
        raise AssertionError(f"unexpected URL requested: {url}")

    fake_client.get.side_effect = fake_get

    pdf_dir = tmp_path / "pdfs"
    markdown_dir = tmp_path / "markdown"
    report_path = tmp_path / "recon_report.csv"

    rows = run_reconnaissance(
        fake_client,
        base_url="https://laws.gov.tt",
        listing_path="/ttdll-web/revision/list",
        pdf_dir=pdf_dir,
        markdown_dir=markdown_dir,
        report_path=report_path,
    )

    # 7 chapters in the fixture listing page, one detail+PDF fetch each
    assert len(rows) == 7
    assert all(row["status"] == "ok" for row in rows)

    written_pdfs = list(pdf_dir.glob("*.pdf"))
    written_md = list(markdown_dir.glob("*.md"))
    assert len(written_pdfs) == 7
    assert len(written_md) == 7

    with open(report_path) as f:
        report_rows = list(csv.DictReader(f))
    assert len(report_rows) == 7
    assert report_rows[0]["status"] == "ok"


def test_safe_filename_strips_unsafe_characters():
    from scraper.recon import safe_filename

    # trailing punctuation collapses to an underscore, which is then
    # stripped by safe_filename so filenames never end in a stray "_"
    assert safe_filename("46:03", "Adoption of Children (see alert)") == "46_03_Adoption_of_Children_see_alert"
