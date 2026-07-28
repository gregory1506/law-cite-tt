import csv
import re
from pathlib import Path

import requests

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
    """Crawl the full catalog and fetch every historical version of every
    chapter, not just the current one — needed to support amendment/
    timeline tracking later, not just "is this valid right now" lookups.
    """
    pdf_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir.mkdir(parents=True, exist_ok=True)

    listings = crawl_full_catalog(client, base_url=base_url, listing_path=listing_path)

    # Pre-scan for .recon_done markers so we can skip without HTTP requests.
    # Each file stores "current_id,version_count" (e.g. "490,12").
    done_by_id: dict[int, tuple[str, int]] = {}
    for d in pdf_dir.iterdir():
        if d.is_dir():
            done_file = d / ".recon_done"
            if done_file.exists():
                cid_str, _, count_str = done_file.read_text().strip().partition(",")
                done_by_id[int(cid_str)] = (d.name, int(count_str) if count_str else 0)

    report_rows = []

    for listing in listings:
        if listing.current_id in done_by_id:
            _, version_count = done_by_id[listing.current_id]
            for _ in range(version_count):
                report_rows.append(
                    {
                        "chapter_number": "",
                        "title": listing.title,
                        "current_id": listing.current_id,
                        "download_id": "",
                        "version_label": "",
                        "as_at_date": "",
                        "status": "skipped",
                        "character_count": 0,
                        "likely_scanned": "",
                    }
                )
            continue

        detail_url = f"{base_url}{listing_path}?offset=0&q=&currentid={listing.current_id}"
        detail_response = client.get(detail_url)
        detail = parse_chapter_detail(detail_response.text, listing.current_id)

        if not detail.versions:
            report_rows.append(
                {
                    "chapter_number": detail.chapter_number,
                    "title": detail.title,
                    "current_id": listing.current_id,
                    "download_id": "",
                    "version_label": "",
                    "as_at_date": "",
                    "status": "no_versions_found",
                    "character_count": 0,
                    "likely_scanned": "",
                }
            )
            continue

        chapter_folder = safe_filename(detail.chapter_number, detail.title)
        chapter_pdf_dir = pdf_dir / chapter_folder
        chapter_md_dir = markdown_dir / chapter_folder

        expected_count = len(detail.versions)
        if chapter_pdf_dir.exists():
            on_disk = len(list(chapter_pdf_dir.glob("*.pdf")))
            if on_disk == expected_count:
                chapter_pdf_dir.joinpath(".recon_done").write_text(f"{listing.current_id},{expected_count}")
                for v in detail.versions:
                    report_rows.append(
                        {
                            "chapter_number": detail.chapter_number,
                            "title": detail.title,
                            "current_id": listing.current_id,
                            "download_id": v.download_id,
                            "version_label": v.label,
                            "as_at_date": v.as_at_date,
                            "status": "skipped",
                            "character_count": 0,
                            "likely_scanned": "",
                        }
                    )
                continue

        chapter_pdf_dir.mkdir(parents=True, exist_ok=True)
        chapter_md_dir.mkdir(parents=True, exist_ok=True)

        for version in detail.versions:
            pdf_path = chapter_pdf_dir / f"{version.download_id}.pdf"
            md_path = chapter_md_dir / f"{version.download_id}.md"

            try:
                pdf_response = client.get(
                    f"{base_url}/ttdll-web/revision/download/{version.download_id}?type=act"
                )
            except requests.RequestException:
                report_rows.append(
                    {
                        "chapter_number": detail.chapter_number,
                        "title": detail.title,
                        "current_id": listing.current_id,
                        "download_id": version.download_id,
                        "version_label": version.label,
                        "as_at_date": version.as_at_date,
                        "status": "download_error",
                        "character_count": 0,
                        "likely_scanned": "",
                    }
                )
                continue

            pdf_path.write_bytes(pdf_response.content)

            if not pdf_response.content.startswith(b"%PDF"):
                report_rows.append(
                    {
                        "chapter_number": detail.chapter_number,
                        "title": detail.title,
                        "current_id": listing.current_id,
                        "download_id": version.download_id,
                        "version_label": version.label,
                        "as_at_date": version.as_at_date,
                        "status": "bad_download",
                        "character_count": 0,
                        "likely_scanned": "",
                    }
                )
                pdf_path.unlink(missing_ok=True)
                continue

            result = extract_pdf_to_markdown(
                str(pdf_path),
                title=f"{detail.title} ({detail.chapter_number}) — {version.label} {version.as_at_date}",
            )
            md_path.write_text(result.markdown)

            report_rows.append(
                {
                    "chapter_number": detail.chapter_number,
                    "title": detail.title,
                    "current_id": listing.current_id,
                    "download_id": version.download_id,
                    "version_label": version.label,
                    "as_at_date": version.as_at_date,
                    "status": "ok",
                    "character_count": result.character_count,
                    "likely_scanned": result.likely_scanned,
                }
            )

        done_by_id[listing.current_id] = (chapter_folder, expected_count)
        chapter_pdf_dir.joinpath(".recon_done").write_text(f"{listing.current_id},{expected_count}")

    with open(report_path, "w", newline="") as f:
        fieldnames = list(report_rows[0].keys()) if report_rows else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    return report_rows
