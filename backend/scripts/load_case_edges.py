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
import re
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


_ROLE_RE = re.compile(
    r"^(?:the\s+)?(?:co-)?(?:claimant|defendant|appellant|respondent|applicant|"
    r"intervener|co-respondent|petitioner|trustee|executor|administratrix|"
    r"administrator|estate of|representative of|guardian ad litem|next friend|"
    r"party)",
    re.I,
)
_BOILER_RE = re.compile(
    r"^(?:the\s+)?(?:republic of trinidad and tobaga|republic of trinidad and "
    r"tobago|trinidad and tobaga|trinidad and tobago|in the high court of "
    r"justice|in the court of appeal|in the supreme court|in the privy "
    r"council|in the industrial court|in the magistrates|in the family court|"
    r"port of spain|san fernando|tobago|between|and)$",
    re.I,
)
_CLAIM_RE = re.compile(
    r"^(?:claim no\.?|claim number|no\.|cv |cva |ca |hc |cv\b|cva\b)\s",
    re.I,
)
_HEADER_END_RE = re.compile(
    r"^(?:before the honourable|date of delivery|appearances|dated|for the court)",
    re.I,
)


def _title_case(name: str) -> str:
    words = []
    for word in name.split():
        if not word:
            continue
        if word.isupper() and len(word) > 2 and not word.startswith("("):
            word = word.capitalize()
        words.append(word)
    return " ".join(words)


_SUFFIX_RE = re.compile(
    r"\s(?:1st|2nd|3rd|\d+th|first|second|third|fourth|fifth)\s+"
    r"(?:defendant|claimant|respondent|appellant|applicant)|"
    r"\s(?:defendant|claimant|respondent|appellant|applicant)s?\b|"
    r"\s(?:a/c|a\.c\.|aka|a\.k\.a\.|also\s+called|also\s+known\s+as)\b",
    re.I,
)


def _clean_party(line: str) -> str:
    line = line.strip()
    match = _SUFFIX_RE.search(line)
    if match:
        line = line[: match.start()]
    line = line.strip().rstrip(".,;:-")
    return _title_case(line)


def _party_name(lines: list[str]) -> str:
    """Primary party name after BETWEEN/AND: the first name line, cleaned of
    trailing role qualifiers."""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            break
        if stripped.upper() in ("AND", "BETWEEN"):
            break
        numbered = re.match(r"^\(\d+\)\s*(.*)$", stripped)
        if numbered:
            return _clean_party(numbered.group(1))
        if stripped.startswith("(") or _ROLE_RE.match(stripped):
            break
        if _BOILER_RE.match(stripped) or _CLAIM_RE.match(stripped):
            continue
        if _HEADER_END_RE.match(stripped):
            break
        return _clean_party(stripped)
    return ""


def _webopac_title(text: str) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
    upper = [l.upper() for l in lines]
    header = lines[:12]
    header_upper = upper[:12]

    # BETWEEN ... AND ... party header (High Court / most judgments).
    between_idx = next(
        (i for i, l in enumerate(header_upper) if l == "BETWEEN" or l.startswith("BETWEEN ")),
        None,
    )
    if between_idx is not None:
        party1 = _party_name(header[between_idx + 1 :])
        if party1:
            and_idx = next(
                (i for i, l in enumerate(header_upper[between_idx + 1 :]) if l == "AND"),
                None,
            )
            if and_idx is not None:
                party2 = _party_name(header[between_idx + 2 + and_idx :])
                return f"{party1} v {party2}" if party2 else party1
            return party1

    # Court of Appeal header: "...COURT OF APPEAL / OF / <party1> / AND / <party2>".
    of_idx = next(
        (i for i, l in enumerate(header_upper) if l == "OF" or l.startswith("OF ")),
        None,
    )
    if of_idx is not None:
        party1 = _party_name(header[of_idx + 1 :])
        if party1:
            and_idx = next(
                (i for i, l in enumerate(header_upper[of_idx + 1 :]) if l == "AND"),
                None,
            )
            if and_idx is not None:
                party2 = _party_name(header[of_idx + 2 + and_idx :])
                return f"{party1} v {party2}" if party2 else party1
            return party1

    # No party header: fall back to the first short line that reads like a
    # name (uppercase start, not a sentence).
    for line in header:
        if _BOILER_RE.match(line) or _CLAIM_RE.match(line) or _HEADER_END_RE.match(line):
            continue
        if _ROLE_RE.match(line) or line.startswith("("):
            continue
        if line[0].islower() or len(line) > 80:
            continue
        if re.search(r"\s{2,}", line) or line.endswith((".", ":")):
            continue
        return _clean_party(line)
    return ""

    party1 = _party_name(lines[between_idx + 1 :])
    if not party1:
        return ""

    # Look for a standalone AND separator after the BETWEEN block to get party 2.
    and_idx = None
    for i, l in enumerate(upper[between_idx + 1 :]):
        if l == "AND":
            and_idx = between_idx + 1 + i
            break
    if and_idx is None:
        return party1
    party2 = _party_name(lines[and_idx + 1 :])
    return f"{party1} v {party2}" if party2 else party1


def _case_title(rec: dict) -> str:
    title = rec.get("title") or rec.get("case_name") or ""
    if not title:
        title = _webopac_title(rec.get("text") or "")
    return title[:100]


def _case_year(rec: dict) -> int | None:
    for key in ("year", "date"):
        value = rec.get(key)
        if value:
            try:
                return int(str(value)[:4])
            except (TypeError, ValueError):
                continue
    # Delivery-date filename, e.g. "...cv_18_01783DD10apr2019.pdf".
    url = rec.get("pdf_url") or rec.get("source_url") or ""
    match = re.search(r"DD\d{2}(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(\d{4})\.pdf", url, re.I)
    if match:
        return int(match.group(1))
    # "Date of Delivery 28 September 2023" inside the text.
    text = rec.get("text") or ""
    match = re.search(r"date of delivery\s+[\d]{1,2}\s+\w+\s+(\d{4})", text, re.I)
    if match:
        return int(match.group(1))
    # Plain year in the URL, e.g. ".../LawTermOpen/2023.pdf".
    match = re.search(r"/(\d{4})\.pdf", url)
    if match:
        return int(match.group(1))
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
        source_tag = path.stem
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rec["source"] = rec.get("source") or source_tag
                records.append(rec)
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
