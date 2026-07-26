from pathlib import Path

BASE_URL = "https://laws.gov.tt"
LISTING_PATH = "/ttdll-web/revision/list"

REQUEST_DELAY_SECONDS = 1.5
MAX_RETRIES = 3

OUTPUT_ROOT = Path("/Volumes/Extreme SSD/law-cite-tt-data")
PDF_DIR = OUTPUT_ROOT / "pdfs"
MARKDOWN_DIR = OUTPUT_ROOT / "markdown"
REPORT_PATH = OUTPUT_ROOT / "recon_report.csv"
