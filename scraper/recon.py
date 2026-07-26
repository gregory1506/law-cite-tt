import csv
import re
from pathlib import Path

from scraper.catalog import crawl_full_catalog
from scraper.detail import parse_chapter_detail
from scraper.pdf_to_markdown import extract_pdf_to_markdown

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9]+")


def safe_filename(chapter_number: str, title: str) -> str:
    base = f"{chapter_number}_{title}" if chapter_number else title
    return SAFE_FILENAME_RE.sub("_", base).strip("_")


def run_reconnaissance(
    client,
    base_url: str,
    listing_path: str,
    pdf_dir: Path,
    markdown_dir: Path,
    report_path: Path,
) -> list[dict]:
    pdf_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir.mkdir(parents=True, exist_ok=True)

    listings = crawl_full_catalog(client, base_url=base_url, listing_path=listing_path)
    report_rows = []

    for listing in listings:
        detail_url = f"{base_url}{listing_path}?offset=0&q=&currentid={listing.current_id}"
        detail_response = client.get(detail_url)
        detail = parse_chapter_detail(detail_response.text, listing.current_id)

        if not detail.versions:
            report_rows.append(
                {
                    "chapter_number": detail.chapter_number,
                    "title": detail.title,
                    "current_id": listing.current_id,
                    "status": "no_versions_found",
                    "character_count": 0,
                    "likely_scanned": "",
                }
            )
            continue

        latest_version = detail.versions[0]
        filename = safe_filename(detail.chapter_number, detail.title)
        pdf_path = pdf_dir / f"{filename}.pdf"
        md_path = markdown_dir / f"{filename}.md"

        pdf_response = client.get(
            f"{base_url}/ttdll-web/revision/download/{latest_version.download_id}?type=act"
        )
        pdf_path.write_bytes(pdf_response.content)

        result = extract_pdf_to_markdown(
            str(pdf_path), title=f"{detail.title} ({detail.chapter_number})"
        )
        md_path.write_text(result.markdown)

        report_rows.append(
            {
                "chapter_number": detail.chapter_number,
                "title": detail.title,
                "current_id": listing.current_id,
                "status": "ok",
                "character_count": result.character_count,
                "likely_scanned": result.likely_scanned,
            }
        )

    with open(report_path, "w", newline="") as f:
        fieldnames = list(report_rows[0].keys()) if report_rows else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    return report_rows
