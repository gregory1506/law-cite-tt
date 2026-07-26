# Phase 0: Reconnaissance Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python scraper that crawls the full 533-entry Revised Acts catalog on laws.gov.tt, fetches each chapter's latest PDF, extracts text, converts it to markdown, and writes everything to a local external drive — producing the real data needed to finalize the cloud pipeline design (chunking, OCR necessity, embedding strategy) instead of guessing.

**Architecture:** A rate-limited HTTP client wraps every request to laws.gov.tt. A catalog module paginates the listing page to enumerate all chapters. A detail module fetches and parses each chapter's full record (metadata + version/download links). A PDF module extracts text and flags likely-scanned documents. An orchestrator wires these together and writes PDFs + markdown + a CSV summary report to the external drive. Everything before the orchestrator is pure-function/parsing code tested against real (trimmed) HTML fixtures captured from the live site — no network access in tests.

**Tech Stack:** Python 3.11+, `requests`, `beautifulsoup4`, `pdfplumber`, `pytest`, `reportlab` (test-only, to generate synthetic PDF fixtures).

## Global Constraints

- **No 500s / no server strain on laws.gov.tt.** Sequential requests only, minimum 1.5s delay between requests, exponential backoff on retries, max 3 attempts per request. (Spec: `docs/superpowers/specs/2026-07-26-law-cite-tt-architecture-design.md`, "Scraping etiquette".)
- **Anonymous scraping.** Use a plain, standard browser User-Agent string — never a self-identifying bot/contact UA. No authentication, no cookies beyond default session behavior.
- **Output destination for this phase is local, not cloud:** `/Volumes/Extreme SSD/law-cite-tt-data/pdfs/` and `/Volumes/Extreme SSD/law-cite-tt-data/markdown/`, plus a summary report at `/Volumes/Extreme SSD/law-cite-tt-data/recon_report.csv`.
- **No chunking, embedding, or cloud storage in this phase.** Those are deferred to a follow-up plan written after this phase's output is inspected.
- **Tests never hit the live site.** All parser tests run against saved/trimmed HTML fixtures captured from real pages.

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `scraper/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/fixtures/__init__.py`

**Interfaces:**
- Produces: an importable `scraper` package and a `tests` package pytest can collect, with `requests`, `beautifulsoup4`, `pdfplumber`, `pytest`, and `reportlab` installed.

- [ ] **Step 1: Create the directory structure and empty package files**

```bash
mkdir -p scraper tests/fixtures
touch scraper/__init__.py tests/__init__.py tests/fixtures/__init__.py
```

- [ ] **Step 2: Write `requirements.txt`**

```
requests==2.32.3
beautifulsoup4==4.12.3
pdfplumber==0.11.4
pytest==8.3.3
reportlab==4.2.5
```

- [ ] **Step 3: Write `pyproject.toml`**

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 4: Install dependencies and verify pytest collects cleanly**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest --collect-only
```

Expected: `no tests ran` with no import errors (there are no test files yet).

- [ ] **Step 5: Commit**

```bash
git add requirements.txt pyproject.toml scraper tests
git commit -m "chore: scaffold scraper project structure"
```

---

### Task 2: Rate-limited HTTP client

**Files:**
- Create: `scraper/http_client.py`
- Test: `tests/test_http_client.py`

**Interfaces:**
- Produces: `RateLimitedClient` class in `scraper/http_client.py`, constructor `RateLimitedClient(delay_seconds: float = 1.5, user_agent: str = DEFAULT_USER_AGENT, max_retries: int = 3, sleep_fn=time.sleep, time_fn=time.monotonic)`, method `.get(url: str) -> requests.Response`. Raises the underlying `requests` exception after `max_retries` attempts are exhausted. Treats any HTTP 5xx as retryable; treats 4xx as immediately raised (via `response.raise_for_status()`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_http_client.py
from unittest.mock import MagicMock, patch

import pytest
import requests

from scraper.http_client import RateLimitedClient


def test_enforces_minimum_delay_between_requests():
    fake_time = [0.0]
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        fake_time[0] += seconds

    def fake_monotonic():
        return fake_time[0]

    client = RateLimitedClient(
        delay_seconds=1.5, sleep_fn=fake_sleep, time_fn=fake_monotonic
    )

    with patch.object(requests.Session, "get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        client.get("https://example.com/a")
        fake_time[0] += 0.1  # simulate 0.1s passing before the next call
        client.get("https://example.com/b")

    # first call: no prior request, so no sleep for rate limiting.
    # second call: only 0.1s elapsed, so it must sleep ~1.4s to reach 1.5s.
    assert sleeps == [pytest.approx(1.4, abs=0.01)]


def test_retries_on_server_error_then_succeeds():
    client = RateLimitedClient(delay_seconds=0, max_retries=3, sleep_fn=lambda s: None)
    with patch.object(requests.Session, "get") as mock_get:
        mock_get.side_effect = [
            MagicMock(status_code=500),
            MagicMock(status_code=200),
        ]
        response = client.get("https://example.com/a")

    assert response.status_code == 200
    assert mock_get.call_count == 2


def test_raises_after_exhausting_retries_on_repeated_server_errors():
    client = RateLimitedClient(delay_seconds=0, max_retries=2, sleep_fn=lambda s: None)
    with patch.object(requests.Session, "get") as mock_get:
        mock_get.return_value = MagicMock(status_code=500)
        with pytest.raises(requests.HTTPError):
            client.get("https://example.com/a")

    assert mock_get.call_count == 2


def test_uses_a_standard_anonymous_user_agent_by_default():
    client = RateLimitedClient()
    assert "Mozilla" in client.session.headers["User-Agent"]
    assert "law-cite" not in client.session.headers["User-Agent"].lower()
    assert "bot" not in client.session.headers["User-Agent"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_http_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'scraper.http_client'` (or `ImportError`) for all four tests.

- [ ] **Step 3: Write the implementation**

```python
# scraper/http_client.py
import time

import requests

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class RateLimitedClient:
    """HTTP client enforcing a minimum delay between requests and retrying
    transient/server errors with exponential backoff.

    Used exclusively against laws.gov.tt, a government site with no
    published crawl policy (robots.txt returns 404) — the delay, retry cap,
    and plain browser User-Agent here are self-imposed etiquette, not a
    performance optimization. See docs/superpowers/specs/
    2026-07-26-law-cite-tt-architecture-design.md, "Scraping etiquette".
    """

    def __init__(
        self,
        delay_seconds: float = 1.5,
        user_agent: str = DEFAULT_USER_AGENT,
        max_retries: int = 3,
        sleep_fn=time.sleep,
        time_fn=time.monotonic,
    ):
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        self._sleep = sleep_fn
        self._time = time_fn
        self._last_request_at = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def get(self, url: str) -> requests.Response:
        last_exc = None
        for attempt in range(self.max_retries):
            self._wait_for_slot()
            try:
                response = self.session.get(url, timeout=30)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                self._sleep(self.delay_seconds * (2**attempt))
                continue
            if response.status_code >= 500:
                last_exc = requests.HTTPError(
                    f"Server error {response.status_code} for {url}"
                )
                self._sleep(self.delay_seconds * (2**attempt))
                continue
            response.raise_for_status()
            return response
        raise last_exc

    def _wait_for_slot(self):
        now = self._time()
        if self._last_request_at is not None:
            elapsed = now - self._last_request_at
            if elapsed < self.delay_seconds:
                self._sleep(self.delay_seconds - elapsed)
        self._last_request_at = self._time()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_http_client.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add scraper/http_client.py tests/test_http_client.py
git commit -m "feat: add rate-limited, retrying HTTP client for laws.gov.tt"
```

---

### Task 3: Catalog listing parser + full crawl pagination

**Files:**
- Create: `scraper/models.py`
- Create: `scraper/catalog.py`
- Create: `tests/fixtures/listing_page.html`
- Create: `tests/fixtures/empty_listing_page.html`
- Test: `tests/test_catalog.py`

**Interfaces:**
- Consumes: `RateLimitedClient.get(url: str) -> requests.Response` from Task 2.
- Produces: `ChapterListing` dataclass (`current_id: int`, `title: str`, `subtitle: str`) in `scraper/models.py`; `parse_listing_page(html: str) -> list[ChapterListing]` and `crawl_full_catalog(client, base_url: str, listing_path: str, page_size: int = 10) -> list[ChapterListing]` in `scraper/catalog.py`.

The fixture below is a **trimmed but verbatim** extract of the real sidebar markup captured from `https://laws.gov.tt/ttdll-web/revision/list?offset=0` on 2026-07-26 — surrounding chrome (nav, scripts, footers) is stripped, but every tag, class, and attribute the parser depends on is unmodified real markup, not invented structure.

- [ ] **Step 1: Write the fixture files**

```html
<!-- tests/fixtures/listing_page.html -->
<!DOCTYPE html>
<html><body>
<ul id="law-list" class="list-group auto no-radius m-b-none m-t-n-xxs list-group-lg">
  <li class="list-group-item">
    <a href="/ttdll-web/revision/list?offset=0&amp;q=&amp;currentid=490#email-content" class="clear text-ellipsis">
      <small class="pull-right"></small>
      <strong class="block">Absconding Debtors</strong>
      <small>Chapter 8:08</small>
    </a>
  </li>
  <li class="list-group-item">
    <a href="/ttdll-web/revision/list?offset=0&amp;q=&amp;currentid=474#email-content" class="clear text-ellipsis">
      <small class="pull-right"></small>
      <strong class="block">Accessories and Abettors</strong>
      <small>Chapter 10:02</small>
    </a>
  </li>
  <li class="list-group-item">
    <a href="/ttdll-web/revision/list?offset=0&amp;q=&amp;currentid=960#email-content" class="clear text-ellipsis">
      <small class="pull-right"></small>
      <strong class="block">Accreditation Council of Trinidad and Tobago</strong>
      <small>Chapter 39:06</small>
    </a>
  </li>
  <li class="list-group-item">
    <a href="/ttdll-web/revision/list?offset=0&amp;q=&amp;currentid=486#email-content" class="clear text-ellipsis">
      <small class="pull-right"></small>
      <strong class="block">Administration of Estates</strong>
      <small>Chapter 9:01</small>
    </a>
  </li>
  <li class="list-group-item">
    <a href="/ttdll-web/revision/list?offset=0&amp;q=&amp;currentid=416#email-content" class="clear text-ellipsis">
      <small class="pull-right"></small>
      <strong class="block">Administration of Justice (Deoxyribonucleic Acid)</strong>
      <small>Chapter 5:34</small>
    </a>
  </li>
  <li class="list-group-item">
    <a href="/ttdll-web/revision/list?offset=0&amp;q=&amp;currentid=822#email-content" class="clear text-ellipsis">
      <small class="pull-right"></small>
      <strong class="block">Adoption of Children</strong>
      <small>Chapter 46:03 (The 1946 Act has been repealed and replaced by Act 67 of 2000 - see alert)</small>
    </a>
  </li>
  <li class="list-group-item">
    <a href="/ttdll-web/revision/list?offset=0&amp;q=&amp;currentid=938#email-content" class="clear text-ellipsis">
      <small class="pull-right"></small>
      <strong class="block">Advertisements Regulation</strong>
      <small>Chapter 35:53</small>
    </a>
  </li>
</ul>
</body></html>
```

```html
<!-- tests/fixtures/empty_listing_page.html -->
<!DOCTYPE html>
<html><body>
<ul id="law-list" class="list-group auto no-radius m-b-none m-t-n-xxs list-group-lg">
</ul>
</body></html>
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_catalog.py
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_catalog.py -v
```

Expected: `ModuleNotFoundError: No module named 'scraper.catalog'`.

- [ ] **Step 4: Write `scraper/models.py`**

```python
# scraper/models.py
from dataclasses import dataclass, field


@dataclass
class ChapterListing:
    current_id: int
    title: str
    subtitle: str


@dataclass
class VersionLink:
    download_id: int
    label: str
    as_at_date: str


@dataclass
class ChapterDetail:
    current_id: int
    title: str
    chapter_number: str
    description: str
    year: str
    act_number: str
    commencement_date: str
    classification: str
    versions: list[VersionLink] = field(default_factory=list)
```

- [ ] **Step 5: Write `scraper/catalog.py`**

```python
# scraper/catalog.py
import re

from bs4 import BeautifulSoup

from scraper.models import ChapterListing

CURRENTID_RE = re.compile(r"currentid=(\d+)")


def parse_listing_page(html: str) -> list[ChapterListing]:
    soup = BeautifulSoup(html, "html.parser")
    law_list = soup.find("ul", id="law-list")
    if law_list is None:
        return []

    listings = []
    for item in law_list.find_all("li", class_="list-group-item"):
        link = item.find("a")
        if link is None:
            continue
        match = CURRENTID_RE.search(link.get("href", ""))
        if match is None:
            continue

        title_tag = link.find("strong", class_="block")
        # the link has two <small> tags: an empty pull-right one and the
        # real subtitle one. Take the one that has text.
        subtitle_tags = link.find_all("small")
        subtitle_text = next(
            (t.get_text(strip=True) for t in subtitle_tags if t.get_text(strip=True)),
            "",
        )

        listings.append(
            ChapterListing(
                current_id=int(match.group(1)),
                title=title_tag.get_text(strip=True) if title_tag else "",
                subtitle=subtitle_text,
            )
        )
    return listings


def crawl_full_catalog(
    client, base_url: str, listing_path: str, page_size: int = 10
) -> list[ChapterListing]:
    all_listings: list[ChapterListing] = []
    offset = 0
    while True:
        url = f"{base_url}{listing_path}?offset={offset}"
        response = client.get(url)
        page_listings = parse_listing_page(response.text)
        if not page_listings:
            break
        all_listings.extend(page_listings)
        offset += page_size
    return all_listings
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_catalog.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add scraper/models.py scraper/catalog.py tests/test_catalog.py tests/fixtures/listing_page.html tests/fixtures/empty_listing_page.html
git commit -m "feat: parse and paginate the laws.gov.tt catalog listing"
```

---

### Task 4: Chapter detail parser

**Files:**
- Modify: `scraper/models.py` (already has `VersionLink`/`ChapterDetail` from Task 3 — no changes needed, listed here for reference)
- Create: `scraper/detail.py`
- Create: `tests/fixtures/chapter_detail_page.html`
- Test: `tests/test_detail.py`

**Interfaces:**
- Consumes: `ChapterDetail`, `VersionLink` from `scraper/models.py` (Task 3).
- Produces: `parse_chapter_detail(html: str, current_id: int) -> ChapterDetail` in `scraper/detail.py`.

The fixture is a trimmed, verbatim extract of the detail pane for "Absconding Debtors" (currentid 490), captured from the live site on 2026-07-26 — this is the actual markup returned when a chapter's detail is loaded, including its Versions tab.

- [ ] **Step 1: Write the fixture file**

```html
<!-- tests/fixtures/chapter_detail_page.html -->
<!DOCTYPE html>
<html><body>
<div class="wrapper-lg bg-light" id="law-detail">
  <div class="hbox" id="hbox">
    <aside class="aside-md">
      <div class="text-center"></div>
    </aside>
    <aside>
      <h4 class="font-bold m-b-none m-t-none"><a href="#showact">Absconding Debtors Chap. 8:08</a></h4>
      <p><i class="fa fa-lg fa-circle-o text-primary m-r-sm"></i><strong>
        An Act relating to the arrest of absconding debtors.
      </strong></p>
      <ul class="nav nav-pills nav-stacked ">
        <li class="bg-light dk"><a href="#"><i class="i i-cube m-r-sm"></i> Year - 1898</a></li>
        <li class="bg-light dk"><a href="#"><i class="i i-plus m-r-sm"></i> Act Number - 20</a></li>
        <li class="bg-light dk"><a href="#"><i class="i i-calendar m-r-sm"></i> Commencement Date -  Fri, 5 Aug 1898</a></li>
        <li class="bg-light dk"><a href="#"><i class="i  i-stack2 m-r-sm text-capitalize"></i> Classification - CIVIL LAW AND PROCEDURE</a></li>
      </ul>
    </aside>
  </div>
</div>
<div class="tab-content">
  <div class="panel tab-pane active" id="activities">
    <ul class="list-group no-radius m-b-none m-t-n-xxs list-group-lg no-border">
      <li class="list-group-item">
        <a href="/ttdll-web/revision/download/105522?type=act" class="thumb-sm pull-left m-r-sm">
          <img src="/ttdll-web/assets/icon-pdf.png" class="img-responsive" />
        </a>
        <a href="/ttdll-web/revision/download/105522?type=act" class="clear">
          <strong><small class="pull-right">as at December 31st 2016</small></strong>
          <strong class="block">2006 Revised Edition </strong>
        </a>
      </li>
      <li class="list-group-item">
        <a href="/ttdll-web/revision/download/90849?type=act" class="thumb-sm pull-left m-r-sm">
          <img src="/ttdll-web/assets/icon-pdf.png" class="img-responsive" />
        </a>
        <a href="/ttdll-web/revision/download/90849?type=act" class="clear">
          <strong><small class="pull-right">as at December 31st 2015</small></strong>
          <strong class="block">*Unofficial Update </strong>
        </a>
      </li>
      <li class="list-group-item">
        <a href="/ttdll-web/revision/download/77968?type=act" class="thumb-sm pull-left m-r-sm">
          <img src="/ttdll-web/assets/icon-pdf.png" class="img-responsive" />
        </a>
        <a href="/ttdll-web/revision/download/77968?type=act" class="clear">
          <strong><small class="pull-right">as at December 31st 2014</small></strong>
          <strong class="block">2006 Revised Edition </strong>
        </a>
      </li>
    </ul>
  </div>
</div>
</body></html>
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_detail.py
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_detail.py -v
```

Expected: `ModuleNotFoundError: No module named 'scraper.detail'`.

- [ ] **Step 4: Write `scraper/detail.py`**

```python
# scraper/detail.py
import re

from bs4 import BeautifulSoup

from scraper.models import ChapterDetail, VersionLink

CHAPTER_NUMBER_RE = re.compile(r"(\d+:\d+)")
DOWNLOAD_ID_RE = re.compile(r"/revision/download/(\d+)\?type=act")


def parse_chapter_detail(html: str, current_id: int) -> ChapterDetail:
    soup = BeautifulSoup(html, "html.parser")
    law_detail = soup.find("div", id="law-detail")

    full_title = ""
    if law_detail is not None:
        heading = law_detail.find("h4", class_="font-bold")
        if heading is not None:
            full_title = heading.get_text(strip=True)

    chapter_match = CHAPTER_NUMBER_RE.search(full_title)
    chapter_number = chapter_match.group(1) if chapter_match else ""
    title = re.sub(r"\s*Chap\.?\s*\d+:\d+\s*$", "", full_title).strip()

    description = ""
    metadata = {}
    if law_detail is not None:
        description_tag = law_detail.select_one("aside p strong")
        if description_tag is not None:
            description = description_tag.get_text(strip=True)

        for li in law_detail.select("ul.nav-stacked li"):
            text = li.get_text(" ", strip=True)
            if " - " in text:
                key, _, value = text.partition(" - ")
                metadata[key.strip()] = value.strip()

    versions = []
    activities = soup.find("div", id="activities")
    if activities is not None:
        for li in activities.find_all("li", class_="list-group-item"):
            link = li.find("a", href=DOWNLOAD_ID_RE)
            if link is None:
                continue
            download_match = DOWNLOAD_ID_RE.search(link["href"])
            date_tag = link.find("small", class_="pull-right")
            label_tag = link.find("strong", class_="block")
            versions.append(
                VersionLink(
                    download_id=int(download_match.group(1)),
                    label=label_tag.get_text(strip=True) if label_tag else "",
                    as_at_date=date_tag.get_text(strip=True) if date_tag else "",
                )
            )

    return ChapterDetail(
        current_id=current_id,
        title=title,
        chapter_number=chapter_number,
        description=description,
        year=metadata.get("Year", ""),
        act_number=metadata.get("Act Number", ""),
        commencement_date=metadata.get("Commencement Date", ""),
        classification=metadata.get("Classification", ""),
        versions=versions,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_detail.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add scraper/detail.py tests/test_detail.py tests/fixtures/chapter_detail_page.html
git commit -m "feat: parse chapter detail pages including version download links"
```

---

### Task 5: PDF-to-markdown extraction with scanned-document heuristic

**Files:**
- Create: `scraper/pdf_to_markdown.py`
- Test: `tests/test_pdf_to_markdown.py`

**Interfaces:**
- Produces: `ExtractionResult` dataclass (`markdown: str`, `character_count: int`, `likely_scanned: bool`), `SCANNED_CHAR_THRESHOLD` constant, and `extract_pdf_to_markdown(pdf_path: str, title: str) -> ExtractionResult` in `scraper/pdf_to_markdown.py`.

No PDF binary is checked into the repo — tests generate synthetic PDFs on the fly with `reportlab`, so extraction correctness is verified deterministically without needing a real (large, license-bearing) statute PDF as a fixture.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pdf_to_markdown.py
import pytest
from reportlab.pdfgen import canvas

from scraper.pdf_to_markdown import SCANNED_CHAR_THRESHOLD, extract_pdf_to_markdown


@pytest.fixture
def text_pdf(tmp_path):
    path = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(path))
    c.drawString(100, 750, "Section 1. This is a test provision about absconding debtors.")
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_pdf_to_markdown.py -v
```

Expected: `ModuleNotFoundError: No module named 'scraper.pdf_to_markdown'`.

- [ ] **Step 3: Write `scraper/pdf_to_markdown.py`**

```python
# scraper/pdf_to_markdown.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_pdf_to_markdown.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scraper/pdf_to_markdown.py tests/test_pdf_to_markdown.py
git commit -m "feat: extract PDF text to markdown with a likely-scanned heuristic"
```

---

### Task 6: Reconnaissance orchestrator

**Files:**
- Create: `scraper/config.py`
- Create: `scraper/recon.py`
- Create: `scripts/run_recon.py`
- Test: `tests/test_recon.py`

**Interfaces:**
- Consumes: `RateLimitedClient` (Task 2), `crawl_full_catalog` (Task 3), `parse_chapter_detail` (Task 4), `extract_pdf_to_markdown` (Task 5).
- Produces: `run_reconnaissance(client, base_url: str, listing_path: str, pdf_dir: Path, markdown_dir: Path, report_path: Path) -> list[dict]` in `scraper/recon.py`. Paths are passed explicitly (not read from module globals) so the function is testable against a `tmp_path` without touching the real external drive.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_recon.py
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
            return MagicMock(text=detail_html)
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

    assert safe_filename("46:03", "Adoption of Children (see alert)") == "46_03_Adoption_of_Children_see_alert_"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_recon.py -v
```

Expected: `ModuleNotFoundError: No module named 'scraper.recon'`.

- [ ] **Step 3: Write `scraper/config.py`**

```python
# scraper/config.py
from pathlib import Path

BASE_URL = "https://laws.gov.tt"
LISTING_PATH = "/ttdll-web/revision/list"

REQUEST_DELAY_SECONDS = 1.5
MAX_RETRIES = 3

OUTPUT_ROOT = Path("/Volumes/Extreme SSD/law-cite-tt-data")
PDF_DIR = OUTPUT_ROOT / "pdfs"
MARKDOWN_DIR = OUTPUT_ROOT / "markdown"
REPORT_PATH = OUTPUT_ROOT / "recon_report.csv"
```

- [ ] **Step 4: Write `scraper/recon.py`**

```python
# scraper/recon.py
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
```

- [ ] **Step 5: Write `scripts/run_recon.py`**

```python
# scripts/run_recon.py
"""Entry point for the Phase 0 reconnaissance crawl.

Run manually (not in CI): python scripts/run_recon.py
"""
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
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_recon.py -v
```

Expected: 2 passed.

- [ ] **Step 7: Run the full test suite**

```bash
pytest -v
```

Expected: all 15 tests pass (4 in `test_http_client.py` + 4 in `test_catalog.py` + 2 in `test_detail.py` + 3 in `test_pdf_to_markdown.py` + 2 in `test_recon.py`).

- [ ] **Step 8: Commit**

```bash
git add scraper/config.py scraper/recon.py scripts/run_recon.py tests/test_recon.py
git commit -m "feat: wire up the Phase 0 reconnaissance orchestrator"
```

---

### Task 7: Small-batch dry run against the live site (manual, not automated)

This task is deliberately manual — it is the first time this code touches the real laws.gov.tt server, and the whole point of Task 2's rate limiting is to protect that site. Do not skip straight to the full 533-chapter run.

**Files:**
- Modify: `scraper/config.py` (temporarily, for the dry run only)

- [ ] **Step 1: Temporarily limit the crawl to a handful of chapters for the dry run**

Add an optional `limit` parameter to `crawl_full_catalog` and thread it through `run_reconnaissance`/`scripts/run_recon.py` as a CLI flag (e.g. `python scripts/run_recon.py --limit 5`), OR simpler for a one-off check: run the script, watch it process the first 5–10 chapters, and manually interrupt (Ctrl-C) once you've confirmed real PDFs and markdown are landing correctly on the external drive with no errors in the terminal output.

- [ ] **Step 2: Run it**

```bash
source .venv/bin/activate
python scripts/run_recon.py
```

Watch the terminal for a few iterations, then Ctrl-C once satisfied.

- [ ] **Step 3: Verify the output**

```bash
ls "/Volumes/Extreme SSD/law-cite-tt-data/pdfs" | head
ls "/Volumes/Extreme SSD/law-cite-tt-data/markdown" | head
cat "/Volumes/Extreme SSD/law-cite-tt-data/recon_report.csv"
```

Confirm: PDFs are real (non-zero size, open as valid PDFs), markdown files contain readable extracted text (or are flagged `likely_scanned=True` for older ordinances), and the CSV report has one row per processed chapter with no unexpected errors in the terminal.

- [ ] **Step 4: If everything looks correct, let the script run to completion for all 533 chapters**

```bash
python scripts/run_recon.py
```

At ~1.5s/request and 2 requests per chapter (detail + PDF), expect roughly 533 × 2 × 1.5s ≈ 27 minutes minimum, likely longer with retries. Let it run uninterrupted.

- [ ] **Step 5: Inspect the completed report and report back**

```bash
python3 -c "
import csv
with open('/Volumes/Extreme SSD/law-cite-tt-data/recon_report.csv') as f:
    rows = list(csv.DictReader(f))
print('total:', len(rows))
print('ok:', sum(1 for r in rows if r['status'] == 'ok'))
print('no_versions_found:', sum(1 for r in rows if r['status'] == 'no_versions_found'))
print('likely_scanned:', sum(1 for r in rows if r['likely_scanned'] == 'True'))
"
```

This output — specifically how many chapters are `likely_scanned` — is exactly the real data the follow-up Phase 1 plan (chunking strategy, OCR necessity, embedding pipeline, cloud storage) needs before it can be written without guessing.

- [ ] **Step 6: Commit any leftover config changes from the dry run**

```bash
git add -A
git commit -m "chore: Phase 0 reconnaissance crawl complete"
```
