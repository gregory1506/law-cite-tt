"""Entry point for the Phase 0 reconnaissance crawl.

Run manually (not in CI): python scripts/run_recon.py
"""
import sys
from pathlib import Path

# running this file directly only puts scripts/ on sys.path, not the
# project root, so `import scraper` fails unless we add it ourselves.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.config import (
    BASE_URL,
    LISTING_PATH,
    MARKDOWN_DIR,
    MAX_RETRIES,
    PDF_DIR,
    REPORT_PATH,
    REQUEST_DELAY_SECONDS,
)
from scraper.http_client import RateLimitedClient
from scraper.recon import run_reconnaissance

if __name__ == "__main__":
    client = RateLimitedClient(
        delay_seconds=REQUEST_DELAY_SECONDS, max_retries=MAX_RETRIES
    )
    rows = run_reconnaissance(
        client,
        base_url=BASE_URL,
        listing_path=LISTING_PATH,
        pdf_dir=PDF_DIR,
        markdown_dir=MARKDOWN_DIR,
        report_path=REPORT_PATH,
    )
    ok = sum(1 for r in rows if r["status"] == "ok")
    scanned = sum(1 for r in rows if r.get("likely_scanned") is True)
    print(f"Processed {len(rows)} chapters: {ok} ok, {scanned} likely scanned.")
    print(f"Report written to {REPORT_PATH}")
