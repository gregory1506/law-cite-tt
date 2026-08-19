"""Scan webOPAC record counts per delivery year (no PDF downloads).

Reads the year->record-count shape of the TT Judiciary OPAC so the
historical-band sweep can be sized before any bulk download. Reuses the
crawler's rate-limited client and pagination, at the same delay.

Usage:
    python scan_webopac_years.py --start 1873 --end 2017 --delay 2.5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.webopac_crawl import (  # noqa: E402
    ANON_UA,
    SearchClient,
    collect_record_urls,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", type=int, default=1873)
    ap.add_argument("--end", type=int, default=2017)
    ap.add_argument("--delay", type=float, default=2.5)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()

    client = SearchClient(delay_seconds=args.delay, user_agent=ANON_UA)
    out_path = Path(args.out) if args.out else Path("webopac_scan.jsonl")
    summary = {"start": args.start, "end": args.end, "years": {}}
    total = 0
    for year in range(args.start, args.end + 1):
        started = time.time()
        try:
            urls = collect_record_urls(client, str(year))
        except Exception as exc:  # noqa: BLE001 - keep the sweep alive
            print(f"[{year}] ERROR {type(exc).__name__}: {exc}", flush=True)
            summary["years"][str(year)] = {"records": None, "error": str(exc)}
            continue
        n = len(urls)
        total += n
        summary["years"][str(year)] = {"records": n}
        with out_path.open("a") as fh:
            fh.write(json.dumps({"year": year, "records": n}) + "\n")
        print(
            f"[{year}] records={n} elapsed={time.time() - started:.0f}s "
            f"cumulative={total}",
            flush=True,
        )
    print(json.dumps({"total_records": total}, indent=2))


if __name__ == "__main__":
    main()