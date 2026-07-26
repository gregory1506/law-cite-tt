from dataclasses import dataclass

import pdfplumber

SCANNED_CHAR_THRESHOLD = 200


@dataclass
class ExtractionResult:
    markdown: str
    character_count: int
    likely_scanned: bool


def extract_pdf_to_markdown(pdf_path: str, title: str) -> ExtractionResult:
    """Extract native text from a PDF and wrap it as markdown.

    This only attempts native text-layer extraction (pdfplumber) — no OCR
    fallback here. A near-empty result (likely_scanned=True) is exactly the
    signal Phase 0 exists to collect: how many of the 533 chapters actually
    need OCR is an open question this reconnaissance run answers with real
    data, rather than something implemented speculatively.
    """
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text.strip())

    full_text = "\n\n---\n\n".join(p for p in pages_text if p)
    character_count = len(full_text)
    markdown = f"# {title}\n\n{full_text}\n"

    return ExtractionResult(
        markdown=markdown,
        character_count=character_count,
        likely_scanned=character_count < SCANNED_CHAR_THRESHOLD,
    )
