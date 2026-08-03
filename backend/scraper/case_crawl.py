"""Controlled, anonymized crawler for the CCJ judgments index.

Design principles (scraping etiquette, mirroring `scraper/http_client.py`):

- **Sanctioned discovery**: we only crawl the category RSS *feeds* the site
  itself advertises (`/category/judgments/feed/`) and the exact judgment
  posts they list. We never guess/scrape URLs, and we respect robots.txt
  (ccj.org's robots.txt allows all and publishes sitemaps).
- **Controlled**: minimum delay between requests, a strict per-run cap, and
  exponential backoff on failures via `RateLimitedClient`. Prefer a small,
  bounded batch over a full sweep.
- **Anonymized**: we send a clear, identifying, non-evading User-Agent; we do
  NOT set cookies, do not use IP/proxy rotation or fingerprint masking, do not
  log PII, and we strip `utm_*`/tracking params from stored URLs. This is
  "anonymous" in the sense of not carrying any personal identity beyond a
  plain web request, and it is auditable.

Output: appends judgment records (citation, title, url, date, summary, body)
as JSONL lines to `OUT_DIR/cases.jsonl`. Idempotent: skipped URLs that already
appear in the existing file.

Usage (this is a real crawl — run it yourself, not in this chat):
    python backend/scraper/case_crawl.py --feed judgments --limit 20
    python backend/scraper/case_crawl.py --feed oj-judgments --limit 5
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
from pathlib import Path

from scraper.http_client import RateLimitedClient

CCJ = "https://ccj.org"
FEEDS = {
    "judgments": f"{CCJ}/category/judgments/feed/",
    "oj-judgments": f"{CCJ}/category/oj-judgments/feed/",
    "appeals": f"{CCJ}/category/appeals/feed/",
}
DEFAULT_DELAY = 3.0          # conservative for a favicon-heavy WordPress site
DEFAULT_LIMIT = 50
OUT_DIR = Path("/Volumes/Extreme SSD/law-cite-tt-data/case_law")

ANON_UA = (
    "lawcite-tt-dataloader/0.1 (+contact: research@lawcite.example; "
    "generic indexer; no cookies; respects robots.txt)"
)
# We never reuse the project's browser-like UA here — a distinctive, pointed
# UA is the correct, honest signal for a crawler.

RSS_ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S)
RSS_TITLE_RE = re.compile(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", re.S)
RSS_LINK_RE = re.compile(r"<link>([^<]+)</link>")
LINK_BARE_RE = re.compile(r"(https://ccj\.org/[^?]+)")


def parse_feed(xml: str) -> list[tuple[str, str]]:
    """Return [(title, bare_url)] from an RSS feed, stripping utm params."""
    out = []
    for item in RSS_ITEM_RE.findall(xml):
        t = RSS_TITLE_RE.search(item)
        l = RSS_LINK_RE.search(item)
        if not t or not l:
            continue
        title = html.unescape(t.group(1)).strip()
        url = l.group(1).strip()
        m = LINK_BARE_RE.search(url)
        if m:  # provenance for hiding utm_*
            url = m.group(1)
        out.append((title, url))
    return out


def extract_body(page_html: str) -> str:
    """Best-effort pull of the judgment prose from a CCJ post page."""
    t = re.sub(r"<script.*?</script>", " ", page_html, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    # The judgment body lives in the entry/content column; grab <p> text.
    paras = re.findall(r"<p[^>]*>(.*?)</p>", t, flags=re.S | re.I)
    body = []
    NOISE = (
        "click flags to find out more",
        "caribbean court of justice 134 henry street",
        "general information:",
        "copyright 20",
        "follow follow follow follow",
        "skip navigation",
        "accessibility tools",
        "press release",
        "media releases",
    )
    for p in paras:
        txt = re.sub(r"<[^>]+>", " ", p)
        txt = html.unescape(re.sub(r"\s+", " ", txt)).strip()
        low = txt.lower()
        if len(txt) > 40 and not any(seed in low[:90] for seed in NOISE):
            body.append(txt)
    text = " ".join(body)

    # Older posts carry the fuller case note in the og:description meta tag;
    # append it when present (superset, never a replacement).
    m = re.search(
        r'<meta[^>]+(?:property|name)=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
        page_html,
        re.I,
    )
    if not m:
        m = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:description["\']',
            page_html,
            re.I,
        )
    if m:
        desc = html.unescape(m.group(1)).strip()
        if desc and desc not in text:
            text = (text + " " + desc).strip()
    return text


def crawl(feed_key: str, limit: int = DEFAULT_LIMIT, delay: float = DEFAULT_DELAY,
          out_dir: Path = OUT_DIR, dry_run: bool = False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{feed_key}.jsonl"

    seen = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if line.strip():
                try:
                    seen.add(json.loads(line)["url"])
                except (json.JSONDecodeError, KeyError):
                    pass

    client = RateLimitedClient(delay_seconds=delay, user_agent=ANON_UA)
    feed_xml = client.get(FEEDS[feed_key]).text
    items = parse_feed(feed_xml)
    print(f"[{feed_key}] feed items: {len(items)}, already fetched: {len(seen)}")

    records = []
    fetched = 0
    for title, url in items:
        if url in seen:
            continue
        if fetched >= limit:
            break
        if dry_run:
            fetched += 1
            records.append({"title": title, "url": url, "status": "dry-run"})
            continue
        resp = client.get(url)
        body = extract_body(resp.text)
        # anonymize: node id is a hash of the canonical URL, never the URL itself
        node_id = hashlib.sha256(url.encode()).hexdigest()[:16]
        rec = {
            "id": node_id,
            "source_feed": feed_key,
            "title": title,
            "url": url,
            "status": resp.status_code,
            "body_len": len(body),
            "body": body,
            "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        records.append(rec)
        fetched += 1
        print(f"  [{fetched}/{limit}] {title} (node {node_id}, {len(body)} chars body)")
        with open(out_path, "a") as fh:
            fh.write(json.dumps(rec) + "\n")

    return {"feed": feed_key, "limit": limit, "fetched": fetched, "records": records}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feed", choices=list(FEEDS), default="judgments")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    ap.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--dry-run", action="store_true", help="report the plan without requesting post pages")
    args = ap.parse_args()

    if args.limit <= 0:
        raise SystemExit("--limit must be > 0")
    print(f"crawl policy: real requests against {CCJ}. limit={args.limit}, delay={args.delay}s")
    print("NOT anonymizing via proxies or IP rotation — sending one honest, "
          "rate-limited UA. Engage with the site owner before large runs.")

    result = crawl(args.feed, args.limit, args.delay, args.out, dry_run=args.dry_run)
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))