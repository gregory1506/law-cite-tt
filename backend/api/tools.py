from __future__ import annotations

from datetime import date as Date
from typing import Any

from api.citations import format_citation, normalize_chapter, normalize_section
from scraper.db_pg import LawCitePGDB

PDF_BASE = "https://laws.gov.tt/ttdll-web/revision/download"

MAX_TOOL_CHARS = 400


def pdf_url(download_id: int | str) -> str:
    return f"{PDF_BASE}/{download_id}?type=act"


def _snippet(text: str, limit: int = MAX_TOOL_CHARS) -> str:
    text = " ".join(text.split())
    return text[:limit] + ("…" if len(text) > limit else "")


def _source(
    *,
    source_id: str,
    title: str,
    chapter: str = "",
    section: str = "",
    date: str = "",
    url: str = "",
    kind: str = "statute",
) -> dict[str, str]:
    return {
        "id": source_id,
        "title": title,
        "chapter": chapter,
        "section": section,
        "date": date or "",
        "url": url,
        "kind": kind,
    }


async def _search_provisions(
    db: LawCitePGDB,
    *,
    query: str,
    chapter: str = "",
    date: str = "",
    limit: int = 5,
) -> dict[str, Any]:
    payload = await db.search_grouped(
        query,
        mode="fts",
        chapter=chapter,
        as_at_date=date,
        limit=limit,
    )
    lines: list[str] = []
    sources: list[dict[str, str]] = []
    for item in payload["items"]:
        matched = item["matched_version"]
        label = matched["version_label"] or "version"
        as_at = matched["as_at_date"] or "undated"
        url = pdf_url(matched["download_id"])
        source_id = f"chunk:{matched['chunk_id']}"
        lines.append(
            f"- {item['title']} (Chap. {item['chapter_number']}, "
            f"s. {item['section_ref'] or 'whole chapter'}) — {label}, "
            f"available as at {as_at} [Source id: {source_id}]\n"
            f"  {_snippet(matched['chunk_text'])}\n"
            f"  Official PDF: {url}"
        )
        sources.append(
            _source(
                source_id=source_id,
                title=item["title"],
                chapter=item["chapter_number"],
                section=item["section_ref"],
                date=str(as_at or ""),
                url=url,
            )
        )
    text = "\n".join(lines) or (
        "No provisions matched. Try a different query, chapter filter, or date."
    )
    return {"text": text, "sources": sources}


async def _lookup_section(
    db: LawCitePGDB,
    *,
    chapter: str,
    section: str,
    date: str = "",
) -> dict[str, Any]:
    rows = await db.lookup_section(chapter, section, as_at_date=date or None)
    lines: list[str] = []
    sources: list[dict[str, str]] = []
    for i, row in enumerate(rows):
        label = row["version_label"] or "version"
        as_at = str(row["as_at_date"] or "undated")
        url = pdf_url(row["download_id"])
        source_id = f"lookup:{row['download_id']}:{i}"
        lines.append(
            f"- Chap. {row['chapter_number']}, s. {row['section_ref']} — {label}, "
            f"available as at {as_at} [Source id: {source_id}]"
            f"({row['heading'] or 'no heading'})\n  {_snippet(row['chunk_text'])}\n"
            f"  Official PDF: {url}"
        )
        sources.append(
            _source(
                source_id=source_id,
                title=row.get("chapter_number", ""),
                chapter=row["chapter_number"],
                section=row["section_ref"],
                date=as_at,
                url=url,
            )
        )
    text = "\n".join(lines) or (
        f"No source text found for Chap. {chapter}, s. {section} in the corpus."
    )
    return {"text": text, "sources": sources}


async def _resolve_citation(
    db: LawCitePGDB,
    *,
    chapter: str,
    section: str,
    date: str = "",
) -> dict[str, Any]:
    try:
        normalized_chapter = normalize_chapter(chapter)
        normalized_section = normalize_section(section)
    except ValueError as error:
        return {
            "text": f"Invalid citation reference: {error}",
            "sources": [],
        }
    result = await db.resolve_citation(
        normalized_chapter,
        normalized_section,
        as_at_date=date or None,
    )
    if result["status"] != "found":
        alternatives = result.get("alternatives") or []
        alt_text = "\n".join(
            f"- {a['title']} (Chap. {a['chapter_number']}"
            f"{', s. ' + str(a['section_ref']) if a.get('section_ref') else ''})"
            for a in alternatives
        )
        return {
            "text": (
                f"Citation status: {result['status']} for Chap. "
                f"{normalized_chapter}, s. {normalized_section}."
                + (f"\nNearby references:\n{alt_text}" if alt_text else "")
            ),
            "sources": [],
        }

    authority = result["authority"]
    try:
        citation_date = Date.fromisoformat(date) if date else None
    except ValueError:
        citation_date = None
    full, short = format_citation(
        authority["title"],
        normalized_chapter,
        normalized_section,
        citation_date,
    )
    as_at = authority.get("as_at_date") or ""
    url = pdf_url(authority["download_id"])
    source_id = f"chunk:{authority['chunk_id']}"
    source = _source(
        source_id=source_id,
        title=authority["title"],
        chapter=normalized_chapter,
        section=normalized_section,
        date=str(as_at or ""),
        url=url,
    )
    text = (
        f"Status: FOUND — {authority['title']} (Chap. {normalized_chapter}, "
        f"s. {normalized_section})"
        f"{' — ' + str(authority['version_label']) if authority.get('version_label') else ''}"
        f" available as at {as_at or 'undated'}. [Source id: {source_id}]\n"
        f"Full citation: {full}\nShort citation: {short}\n"
        f"Exact statutory text:\n{authority['chunk_text']}\n"
        f"Official PDF: {url}"
    )
    return {"text": text, "sources": [source]}


async def _list_chapters(
    db: LawCitePGDB,
    *,
    query: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    pool = await db.connect()
    sql = "SELECT chapter_number, title FROM chapters"
    params: list[Any] = []
    if query:
        params.extend([f"%{query}%", f"%{query}%"])
        sql += " WHERE chapter_number ILIKE $1 OR title ILIKE $2"
    params.append(limit)
    sql += f" ORDER BY chapter_number LIMIT ${len(params)}"
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    lines = []
    sources = []
    for r in rows:
        source_id = f"chapter:{r['chapter_number']}"
        lines.append(
            f"- Chap. {r['chapter_number']} — {r['title']} [Source id: {source_id}]"
        )
        sources.append(
            _source(
                source_id=source_id,
                title=r["title"],
                chapter=r["chapter_number"],
                url=("https://laws.gov.tt/ttdll-web/revision/list"),
            )
        )
    text = "\n".join(lines) or "No chapters matched that query."
    return {"text": text, "sources": sources}


def _case_label(row: dict[str, Any]) -> str:
    case_id = row.get("case_id") or row.get("id") or ""
    title = (row.get("title") or "").strip()
    return f"{title} ({case_id})" if title else case_id


async def _citing_cases(
    db: LawCitePGDB,
    *,
    chapter: str,
    limit: int = 20,
) -> dict[str, Any]:
    try:
        chapter = normalize_chapter(chapter)
    except ValueError as error:
        return {"text": f"Invalid chapter reference: {error}", "sources": []}
    rows = await db.cases_citing_chapter(chapter, limit=limit)
    lines = []
    sources = []
    for r in rows:
        source_id = r["case_id"]
        label = _case_label(r)
        lines.append(
            f"- {label} cites Chap. {r['chapter_number']} "
            f"[confidence: {r['confidence']}, method: {r['method']}] "
            f"[Source id: {source_id}]"
        )
        sources.append(
            _source(
                source_id=source_id,
                title=(r.get("title") or r["case_id"]),
                chapter=r["chapter_number"],
                kind="case",
            )
        )
    text = "\n".join(lines) or (
        f"No cases in the corpus cite Chap. {chapter}."
    )
    return {"text": text, "sources": sources}


async def _search_cases(
    db: LawCitePGDB,
    *,
    query: str,
    limit: int = 20,
) -> dict[str, Any]:
    rows = await db.search_cases(query, limit=limit)
    lines = []
    sources = []
    for r in rows:
        source_id = r["id"]
        label = _case_label(r)
        extra = ""
        if r.get("year"):
            extra = f" ({r['year']})"
        lines.append(f"- {label}{extra} [Source id: {source_id}]")
        sources.append(
            _source(
                source_id=source_id,
                title=(r.get("title") or r["id"]),
                kind="case",
            )
        )
    text = "\n".join(lines) or f"No cases matched '{query}'. Try a case name."
    return {"text": text, "sources": sources}


async def _expand_case(
    db: LawCitePGDB,
    *,
    case_id: str,
    limit: int = 20,
) -> dict[str, Any]:
    if not case_id.startswith("case:"):
        case_id = f"case:{case_id}"
    case = await db.get_case(case_id)
    if case is None:
        return {
            "text": f"No such case: {case_id}. Use search_cases to find its id.",
            "sources": [],
        }
    citations = await db.case_citations_for(case_id)
    chapters = sorted({c["chapter_number"] for c in citations})
    related = await db.cases_citing_chapters(
        chapters,
        exclude_case_id=case_id,
        limit=limit,
    )

    source_id = f"case:{case['id']}"
    lines = [
        f"Case: {_case_label(case)}",
        "Cited statutes:",
        *(f"- Chap. {c['chapter_number']} ({c['method']}, {c['confidence']})" for c in citations),
    ]
    lines.append("Other cases citing the same statutes (precedent chain):")
    related_sources = []
    for r in related:
        rel_id = r["case_id"]
        lines.append(f"- {_case_label(r)} cites Chap. {r['chapter_number']} [Source id: {rel_id}]")
        related_sources.append(
            _source(
                source_id=rel_id,
                title=(r.get("title") or r["case_id"]),
                chapter=r["chapter_number"],
                kind="case",
            )
        )
    if not related:
        lines.append("- (none)")

    return {
        "text": "\n".join(lines),
        "sources": [
            _source(
                source_id=case["id"],
                title=(case.get("title") or case["id"]),
                kind="case",
            ),
            *related_sources,
        ],
    }


HANDLERS: dict[str, Any] = {
    "search_provisions": _search_provisions,
    "lookup_section": _lookup_section,
    "resolve_citation": _resolve_citation,
    "list_chapters": _list_chapters,
    "citing_cases": _citing_cases,
    "search_cases": _search_cases,
    "expand_case": _expand_case,
}

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_provisions",
            "description": (
                "Search provisions of the Laws of Trinidad and Tobago by keyword. "
                "Returns grouped provisions with the matched statutory text and "
                "official PDF links. Use for open-ended or keyword research questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword or phrase to search (e.g. 'absconding debtor').",
                    },
                    "chapter": {
                        "type": "string",
                        "description": "Optional chapter filter, e.g. '8:08'.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional as-at date (YYYY-MM-DD); only versions available by then.",
                    },
                    "limit": {"type": "integer", "description": "Max provisions (1-10)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_section",
            "description": (
                "Look up the exact statutory text of one section of a chapter of the "
                "Laws of Trinidad and Tobago. Use when the user gives a precise "
                "chapter and section (e.g. Chap. 8:08, s. 4)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chapter": {
                        "type": "string",
                        "description": "Chapter number, e.g. '8:08'.",
                    },
                    "section": {
                        "type": "string",
                        "description": "Section reference, e.g. '4' or '12(3)(a)'.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional as-at date (YYYY-MM-DD).",
                    },
                },
                "required": ["chapter", "section"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resolve_citation",
            "description": (
                "Resolve a statutory citation to a provable source version of the "
                "Laws of Trinidad and Tobago. Returns an explicit found, not_found, "
                "or ambiguous status plus the exact statutory text and citation forms. "
                "Use for 'validate this citation' style questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chapter": {
                        "type": "string",
                        "description": "Chapter number, e.g. '8:08'.",
                    },
                    "section": {
                        "type": "string",
                        "description": "Section reference, e.g. '4' or '12(3)(a)'.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional as-at date (YYYY-MM-DD).",
                    },
                },
                "required": ["chapter", "section"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_chapters",
            "description": (
                "List chapters of the Laws of Trinidad and Tobago, optionally "
                "filtered by a keyword in the chapter number or title."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional keyword to filter chapters.",
                    },
                    "limit": {"type": "integer", "description": "Max chapters (1-50)."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "citing_cases",
            "description": (
                "Find judicial cases in the Trinidad and Tobago case-law corpus "
                "that cite a given chapter of the Laws. Returns case ids and "
                "titles. Use for precedent research: 'which cases cite Chap. 8:08?'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chapter": {
                        "type": "string",
                        "description": "Chapter number, e.g. '8:08'.",
                    },
                    "limit": {"type": "integer", "description": "Max cases (1-50)."},
                },
                "required": ["chapter"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_cases",
            "description": (
                "Search the Trinidad and Tobago case-law corpus by case name. "
                "Returns case ids and titles. Use when the user names a case "
                "and you need its id to look up what it cites."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Case name or part of it, e.g. 'Smith'.",
                    },
                    "limit": {"type": "integer", "description": "Max cases (1-50)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expand_case",
            "description": (
                "Expand a case into a precedent chain: its cited statutes plus "
                "the other cases that cite the same statutes. Pass a case id "
                "from citing_cases or search_cases, e.g. 'case:8eec828c74db14ee'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "Case id, optionally prefixed with 'case:'.",
                    },
                    "limit": {"type": "integer", "description": "Max related cases (1-50)."},
                },
                "required": ["case_id"],
            },
        },
    },
]