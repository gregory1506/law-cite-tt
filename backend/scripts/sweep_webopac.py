"""Drive the historical-band webOPAC sweep (1873-2017) in a resumable loop.

Calls the crawler year by year with a generous per-year cap; each record is
appended to the SSD JSONL as it is fetched, so interrupting the loop and
re-running it simply continues where it left off. Adds a short pause between
years as extra politeness to the OPAC.

Usage:
    nohup python -m scripts.sweep_webopac --start 1873 --end 2017 \
        --delay 2.5 --year-gap 5 > /tmp/webopac_sweep.log 2>&1 &
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.webopac_crawl import crawl  # noqa: E402

DEFAULT_CAP = 1_000_000


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", type=int, default=1873)
    ap.add_argument("--end", type=int, default=2017)
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP)
    ap.add_argument("--delay", type=float, default=2.5)
    ap.add_argument("--year-gap", type=float, default=5.0,
                    help="extra pause (seconds) between years")
    args = ap.parse_args()

    summary = {"start": args.start, "end": args.end, "per_year": {}}
    total = 0
    for year in range(args.start, args.end + 1):
        started = time.time()
        try:
            result = crawl(str(year), args.cap, args.delay)
        except Exception as exc:  # noqa: BLE001 - keep the sweep alive
            print(f"[{year}] ERROR {type(exc).__name__}: {exc}", flush=True)
            summary["per_year"][str(year)] = {"fetched": 0, "error": str(exc)}
            time.sleep(args.year_gap)
            continue
        total += result["fetched"]
        summary["per_year"][str(year)] = {"fetched": result["fetched"]}
        print(
            f"[{year}] fetched={result['fetched']} "
            f"elapsed={time.time() - started:.0f}s cumulative={total}",
            flush=True,
        )
        time.sleep(args.year_gap)

    Path("webopac_sweep_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"DONE total_fetched={total}")


if __name__ == "__main__":
    main()