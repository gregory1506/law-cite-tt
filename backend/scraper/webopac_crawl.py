"""Controlled, anonymized crawler for the TT Judiciary webOPAC judgments index."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

from scraper.http_client import RateLimitedClient
from scraper.pdf_to_markdown import extract_pdf_to_markdown

BASE = "https://webopac.ttlawcourts.org"
SEARCH_ACTION = f"{BASE}/scripts/minisa.dll/144/m2ldirect6?DIRECTSEARCH"

ANON_UA = (
    "lawcite-tt-webopac/0.1 (+contact: research@lawcite.example; "
    "generic indexer; no cookies; respects robots.txt)"
)

OUT_DIR = Path("/Volumes/Extreme SSD/law-cite-tt-data/case_law")
JSONL_OUT = OUT_DIR / "webopac.jsonld"
PDF_DIR = OUT_DIR / "webopac_pdfs"
DEFAULT_DELAY = 2.5
DEFAULT_CAP = 50

# --- regex helpers -------------------------------------------------------
# A search results (RECLIST) page carries record links and numbered page links.
RECLIST_LINK_RE = re.compile(r'href="([^"]*\?RECLIST[^"]*)"')
RECORD_LINK_RE = re.compile(r'href="([^"]*\?RECORD[^"]*)"')
PDF_URL_RE = re.compile(r"(?i)https?://[^\s\"'<>]+?\.pdf\b")
_FORM_ACTION = re.compile(r'<form[^>]*action="([^"]*\?SEARCH[^"]*)"')

# RECLIST URLs look like ...//16324435/2/11?RECLIST&TM=... The middle `2`
# is a search-session id that rotates each request; the trailing `/NN` is the
# record offset of that page. Dedup by offset only, so we terminate.
_RECLIST_OFFSET = re.compile(r"/\d+/\d+/(\d+)\?RECLIST")


def search_year(client, year: str):
    """POST the direct-search form for a single delivery year.

    Returns the first RECLIST page HTML plus the set of absolute RECLIST
    page URLs found on it (the numbered result pages 1,2,3...).
    """
    form_html = client.get(SEARCH_ACTION).text
    form_actions = _FORM_ACTION.findall(form_html)
    if not form_actions:
        raise RuntimeError("could not locate the OPAC search form action")
    action = form_actions[0]
    fields = {
        "case_name": "", "title": "", "primary_descs": "",
        "pauth_judge": "", "pubyr_deldate": year,
        "call_number": "", "suit_no": "", "cases_referred": "",
    }
    resp = client.post(action, data=fields)
    html = resp.text
    pages = {urljoin(BASE, u) for u in RECLIST_LINK_RE.findall(html)}
    return html, pages


class SearchClient(RateLimitedClient):
    """Rate-limited client that also supports the form POST used for search."""

    def post(self, url: str, data: dict, **kw):
        last_exc = None
        for attempt in range(self.max_retries):
            self._wait_for_slot()
            try:
                return self.session.post(url, data=data, timeout=30)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                self._sleep(self.delay_seconds * (2 ** attempt))
        raise last_exc


def collect_record_urls(client, year: str):
    """Page RECLIST for a year, returning the set of RECORD page URLs.

    Session ids rotate on every response, so RECLIST URLs are deduplicated by
    their page offset segment rather than the full string.
    """
    first_html, first_pages = search_year(client, year)
    record_urls = set()
    record_urls |= {urljoin(BASE, r) for r in RECORD_LINK_RE.findall(first_html)}
    # A fresh offset-1 page will appear again in responses; track offsets seen.
    seen_offsets = {"1"}
    queue = list(first_pages)
    while queue:
        u = queue.pop(0)
        m = _RECLIST_OFFSET.search(u)
        off = m.group(1) if m else None
        if off in seen_offsets:
            continue
        seen_offsets.add(off)
        body = client.get(u).text
        record_urls |= {urljoin(BASE, r) for r in RECORD_LINK_RE.findall(body)}
        for nxt in RECLIST_LINK_RE.findall(body):
            nm = _RECLIST_OFFSET.search(urljoin(BASE, nxt))
            noff = nm.group(1) if nm else "1"
            if noff not in seen_offsets:
                queue.append(urljoin(BASE, nxt))
    return record_urls


def extract_pdf_link(record_html: str) -> str | None:
    """Find the full-text PDF URL on a RECORD page.

    The OPAC exposes it both as a linked href and as a bare URL in the
    'Full text' field. Prefer a path under /Judgments/ when present.
    """
    candidates = [u for u in PDF_URL_RE.findall(record_html)]
    judgement = [u for u in candidates if "Judgments" in u]
    if judgement:
        return judgement[0].strip()
    return (candidates[0].strip() if candidates else None)

# --- download & persist --------------------------------------------------

def fetch_pdf(client, pdf_url, record_id, year):
    import requests as _requests
    pdf_dir = PDF_DIR / year
    pdf_dir.mkdir(parents=True, exist_ok=True)
    label = hashlib.sha256(pdf_url.encode()).hexdigest()[:10]
    pdf_path = pdf_dir / f"{record_id}_{label}.pdf"
    try:
        data = client.get(pdf_url)
    except (_requests.RequestException, Exception) as exc:
        print(f"  !! skip {pdf_url}: {type(exc).__name__}")
        return None
    try:
        pdf_path.write_bytes(data.content)
        result = extract_pdf_to_markdown(str(pdf_path), str(record_id))
        return pdf_path, result, result.likely_scanned
    except Exception as exc:
        print(f"  !! parse fail {pdf_url}: {type(exc).__name__}")
        return None

def crawl(year, cap, delay):
    JSONL_OUT.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if JSONL_OUT.exists():
        for line in JSONL_OUT.read_text().splitlines():
            if line.strip():
                try:
                    done.add(json.loads(line)["record_id"])
                except (json.JSONDecodeError, KeyError):
                    continue
    client = SearchClient(delay_seconds=delay, user_agent=ANON_UA)
    record_urls = collect_record_urls(client, year)
    print(f"[{year}] records found: {len(record_urls)}")
    n = 0
    for rec_url in sorted(record_urls):
        if cap and n >= cap:
            break
        rid = hashlib.sha256(rec_url.encode()).hexdigest()[:16]
        if rid in done:
            continue
        try:
            page_html = client.get(rec_url).text
            pdf_url = extract_pdf_link(page_html)
            if not pdf_url:
                continue
            fetched = fetch_pdf(client, pdf_url, rid, year)
            if fetched is None:
                continue
            pdf_path, result, scanned = fetched
        except Exception as exc:
            print(f"  !! record fail {rec_url}: {type(exc).__name__} {exc}")
            continue
        rec = {
            "record_id": rid,
            "source_url": rec_url,
            "pdf_url": pdf_url,
            "pdf_path": str(pdf_path),
            "chars": result.character_count,
            "scanned": scanned,
            "text": result.markdown,
            "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with JSONL_OUT.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        n += 1
        print(f"  [{n}/{cap}] {pdf_url} -> {result.character_count} chars")
    return {"year": year, "cap": cap, "fetched": n}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="TT Judiciary webOPAC judgment crawler")
    ap.add_argument("--year", help="single delivery year to enumerate")
    ap.add_argument("--start", type=int, help="start year of a sweep")
    ap.add_argument("--end", type=int, help="end year of a sweep (inclusive)")
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP)
    ap.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    args = ap.parse_args()

    print("crawl policy: real requests against webopac.ttlawcourts.org; "
          "One honest UA, no cookies, no IP rotation.")
    if args.year:
        if args.cap <= 0:
            raise SystemExit("--cap must be > 0")
        print("limit=%d, delay=%ss" % (args.cap, args.delay))
        result = crawl(args.year, args.cap, args.delay)
    elif args.start is not None and args.end is not None:
        lo, hi = sorted((args.start, args.end))
        total = {"fetched": 0}
        for year in range(lo, hi + 1):
            year_res = crawl(str(year), args.cap, args.delay)
            total["fetched"] += year_res["fetched"]
            print(f"== sweep year {year}: fetched {year_res['fetched']}")
        result = total
    else:
        raise SystemExit("provide --year or both --start and --end")
    print(json.dumps(result, indent=2))
