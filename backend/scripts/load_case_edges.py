"""Load the case-law citation graph (graphify-out/case_edges.json) into Postgres.

Usage:
    python load_case_edges.py --edges graphify-out/case_edges.json \
        [--records /Volumes/Extreme SSD/law-cite-tt-data/case_law] \
        [--pg <dsn>] [--force]

--records optionally points at the case-law corpus directory (webopac.jsonld,
CCJ jsonl) so each case gets its title/court/year backfilled. Edge source ids
are `case:<sha256-prefix>` which match the crawlers' record ids directly.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--edges",
        default="graphify-out/case_edges.json",
        help="Path to case_edges.json produced by graphrag.case_edges",
    )
    p.add_argument(
        "--records",
        default="",
        help="Optional directory of crawled case-law records (json/jsonl) "
        "for title/court/year backfill",
    )
    p.add_argument(
        "--pg",
        default="postgresql://lawcite:changeme@localhost:5432/lawcite",
        help="Destination Postgres DSN",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Truncate cases/case_citations before loading",
    )
    return p.parse_args()


def chapter_from_target(target: str) -> str:
    return target.removeprefix("chapter:")


def _case_title(rec: dict) -> str:
    return rec.get("title") or rec.get("case_name") or ""


def _case_year(rec: dict) -> int | None:
    for key in ("year", "date"):
        value = rec.get(key)
        if value:
            try:
                return int(str(value)[:4])
            except (TypeError, ValueError):
                continue
    return None


def parse_edges(edges_json: list[dict], records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Build (cases, citations) rows from the edge list and optional records.

    `records` may be empty; cases then carry empty titles but remain linkable
    by their `case:<id>` handle.
    """
    record_map: dict[str, dict] = {}
    for rec in records:
        key = rec.get("id") or rec.get("record_id")
        if key:
            record_map[key] = rec

    cases: dict[str, dict] = {}
    citations: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for edge in edges_json:
        case_id = edge.get("source", "")
        if not case_id.startswith("case:"):
            continue
        short_id = case_id.removeprefix("case:")
        record = record_map.get(short_id, {})
        cases.setdefault(
            case_id,
            {
                "id": case_id,
                "title": _case_title(record),
                "source": record.get("source", ""),
                "record_id": short_id,
                "court": record.get("court", ""),
                "year": _case_year(record),
            },
        )
        chapter = chapter_from_target(edge.get("target", ""))
        if not chapter:
            continue
        key = (case_id, chapter, edge.get("method", "REGEX"))
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "case_id": case_id,
                "chapter_number": chapter,
                "confidence": edge.get("confidence", "medium"),
                "method": edge.get("method", "REGEX"),
                "evidence": edge.get("evidence", "EXTRACTED"),
                "detail": edge.get("detail", ""),
            }
        )

    return list(cases.values()), citations


async def load(
    pool: asyncpg.Pool,
    cases: list[dict],
    citations: list[dict],
    *,
    force: bool = False,
) -> None:
    async with pool.acquire() as conn:
        if force:
            await conn.execute("TRUNCATE case_citations, cases RESTART IDENTITY CASCADE")
        await conn.executemany(
            """
            INSERT INTO cases (id, title, source, record_id, court, year)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                source = EXCLUDED.source,
                record_id = EXCLUDED.record_id,
                court = EXCLUDED.court,
                year = EXCLUDED.year
            """,
            [(c["id"], c["title"], c["source"], c["record_id"], c["court"], c["year"]) for c in cases],
        )
        await conn.executemany(
            """
            INSERT INTO case_citations (case_id, chapter_number, confidence, method, evidence, detail)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            [
                (
                    c["case_id"],
                    c["chapter_number"],
                    c["confidence"],
                    c["method"],
                    c["evidence"],
                    c["detail"],
                )
                for c in citations
            ],
        )


def _load_records(records_dir: Path) -> list[dict]:
    records: list[dict] = []
    for path in sorted(records_dir.glob("*.json*")):
        if path.name.startswith("._"):
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def main() -> None:
    import asyncio

    args = _parse_args()
    edges_json = json.loads(Path(args.edges).read_text()).get("edges", [])

    records = _load_records(Path(args.records)) if args.records else []
    cases, citations = parse_edges(edges_json, records)

    async def _run() -> None:
        pool = await asyncpg.create_pool(args.pg, min_size=1, max_size=4)
        try:
            await load(pool, cases, citations, force=args.force)
        finally:
            await pool.close()

    asyncio.run(_run())

    titled = sum(1 for c in cases if c["title"])
    print(
        f"cases: {len(cases)} (titled: {titled}) | citations: {len(citations)} "
        f"| records matched: {titled if records else 'n/a (no --records)'}"
    )


if __name__ == "__main__":
    main()
