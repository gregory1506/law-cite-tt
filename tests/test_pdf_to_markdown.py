import pytest
from reportlab.pdfgen import canvas

from scraper.pdf_to_markdown import SCANNED_CHAR_THRESHOLD, extract_pdf_to_markdown


@pytest.fixture
def text_pdf(tmp_path):
    path = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(path))
    lines = [
        "Section 1. This is a test provision about absconding debtors.",
        "Section 2. It exists purely to give pdfplumber a realistic amount",
        "of native text to extract, well above the near-empty threshold",
        "that flags a scanned-image PDF with no text layer.",
    ]
    for i, line in enumerate(lines):
        c.drawString(100, 750 - i * 20, line)
    c.save()
    return str(path)


@pytest.fixture
def blank_pdf(tmp_path):
    path = tmp_path / "blank.pdf"
    c = canvas.Canvas(str(path))
    c.showPage()
    c.save()
    return str(path)


def test_extracts_text_and_wraps_as_markdown_with_title_heading(text_pdf):
    result = extract_pdf_to_markdown(text_pdf, title="Absconding Debtors (8:08)")

    assert result.markdown.startswith("# Absconding Debtors (8:08)\n\n")
    assert "absconding debtors" in result.markdown
    assert result.likely_scanned is False


def test_character_count_matches_extracted_text_length(text_pdf):
    result = extract_pdf_to_markdown(text_pdf, title="Absconding Debtors")
    assert result.character_count > 0
    assert result.character_count == len(
        result.markdown.removeprefix("# Absconding Debtors\n\n").rstrip("\n")
    )


def test_flags_near_empty_extraction_as_likely_scanned(blank_pdf):
    result = extract_pdf_to_markdown(blank_pdf, title="Blank Chapter")

    assert result.character_count < SCANNED_CHAR_THRESHOLD
    assert result.likely_scanned is True
