from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SectionChunk:
    chapter_number: str
    version_id: str
    section_ref: str
    heading: str
    chunk_text: str
    as_at_date: str = ""
    version_label: str = ""
    chunk_index: int = 0


_MONTH_MAP = {
    "January": "01", "February": "02", "March": "03",
    "April": "04", "May": "05", "June": "06",
    "July": "07", "August": "08", "September": "09",
    "October": "10", "November": "11", "December": "12",
}


def _parse_date(raw: str) -> str:
    parts = raw.split()
    if len(parts) != 3:
        return ""
    p0, p1, year = parts[0], parts[1], parts[2]
    if p0.isdigit() or re.match(r"\d+", p0):
        day = re.sub(r"(st|nd|rd|th)$", "", p0).zfill(2)
        month = _MONTH_MAP.get(p1, "")
    else:
        day = re.sub(r"(st|nd|rd|th)$", "", p1).zfill(2)
        month = _MONTH_MAP.get(p0, "")
    return f"{year}-{month}-{day}" if month else ""


def parse_header(text: str) -> dict:
    first = text.split("\n")[0]
    m = re.match(r"^# (.+?) \((\d+:\d+)\) — (.+)$", first)
    if not m:
        return {}
    date = ""
    dm = re.search(r"as at (\d+\w+ \w+ \d{4}|\w+ \d+\w+ \d{4})", m.group(3))
    if dm:
        date = _parse_date(dm.group(1))
    return {
        "title": m.group(1),
        "chapter": m.group(2),
        "version_label": m.group(3),
        "as_at_date": date,
    }


def _find_body_start(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        if "ARRANGEMENT OF SECTIONS" in line:
            entry_end = i
            for j in range(i + 1, len(lines)):
                s = lines[j].strip()
                if re.match(r"^(\d+[A-Z]?)\.\s+", s):
                    entry_end = j
                elif s == "---" and j - entry_end < 20:
                    return j + 1
                elif s and j - entry_end > 3 and not re.match(
                    r"^(UNOFFICIAL|UPDATED|LAWS OF|MINISTRY|CHAPTER)", s
                ):
                    return j
            break
    for i, line in enumerate(lines):
        if re.match(r"^CHAPTER\s+\d+[:.]", line.strip()):
            is_arr = False
            for k in range(i + 1, min(i + 10, len(lines))):
                if "ARRANGEMENT OF SECTIONS" in lines[k]:
                    is_arr = True
                    break
            if not is_arr:
                return i
    for i in range(3, min(80, len(lines))):
        m = re.match(r"^\s*(\d+[A-Z]?)\.\s+(.+)", lines[i])
        if m:
            rest = m.group(2).strip()
            alpha = sum(1 for c in rest if c.isalpha())
            if len(rest) > 10 and alpha > len(rest) * 0.3:
                return i
    return 0


_SECTION_LINE = re.compile(
    r"^([A-Za-z][A-Za-z\s\-,\']{1,50})\.\s*(\d+[A-Z]?)\.\s+(.+)"
)
_SECTION_LINE_NO_PERIOD = re.compile(
    r"^([A-Za-z][A-Za-z\s\-]{1,50})(\d+[A-Z]?)\.\s+(.+)"
)
_SECTION_NUM_FIRST = re.compile(
    r"^(\d+[A-Z]?)\.\s+(.+)"
)
_SKIP_PREFIX = re.compile(r"^(UNOFFICIAL VERSION|UPDATED TO|LAWS OF|MINISTRY|CHAPTER\s+\d+:|Page|www\.)")
_HEADING_EXTRACT = re.compile(r"^([A-Za-z][A-Za-z\s\-,\']{1,60})\.\s*")


def _has_substantive_text(rest: str) -> bool:
    rest = rest.strip()
    if len(rest) < 4:
        return False
    if re.match(r"^\(\d+\)", rest):
        return True
    alpha = sum(1 for c in rest if c.isalpha())
    return alpha >= 3


def _get_section_info(line: str, stripped: str) -> tuple[str | None, str | None]:
    if _SKIP_PREFIX.match(stripped):
        return None, None

    m = _SECTION_LINE.match(line)
    if m and _has_substantive_text(m.group(3)):
        return m.group(2), m.group(3)

    m = _SECTION_LINE_NO_PERIOD.match(line)
    if m and _has_substantive_text(m.group(3)):
        return m.group(2), m.group(3)

    m = _SECTION_NUM_FIRST.match(stripped)
    if m:
        rest = m.group(2)
        if _has_substantive_text(rest):
            return m.group(1), rest

    return None, None


def extract_section_chunks(text: str) -> list[SectionChunk]:
    header = parse_header(text)
    lines = text.split("\n")
    body_start = _find_body_start(lines)

    raw: list[dict] = []
    cur: dict | None = None

    def emit():
        nonlocal cur
        if cur and cur["lines"]:
            raw.append(cur)
        cur = None

    for i in range(body_start, len(lines)):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            if cur:
                cur["lines"].append(line)
            continue

        if _SKIP_PREFIX.match(stripped):
            if cur:
                cur["lines"].append(line)
            continue

        if stripped == "---":
            if cur:
                cur["lines"].append(line)
            continue

        sec, rest = _get_section_info(line, stripped)
        if sec:
            if cur and cur["section"] != sec:
                emit()
            if not cur or cur["section"] != sec:
                cur = {"section": sec, "rest": rest, "lines": [line]}
            else:
                cur["lines"].append(line)
        elif cur:
            cur["lines"].append(line)

    emit()

    def _is_arrangement_entry(text: str) -> bool:
        lines = text.strip().split("\n")
        if len(lines) == 1:
            line = lines[0].strip()
            m = re.match(r"^(\d+[A-Z]?)\.\s+(.+)$", line)
            if m:
                rest = m.group(2).strip()
                if re.match(r"^[A-Z][a-zA-Z\s\-]+\.?$", rest) and len(rest) < 50:
                    if "." not in rest.strip("."):
                        return True
        return False

    result: list[SectionChunk] = []
    for idx, rs in enumerate(raw):
        ct = "\n".join(rs["lines"]).strip()
        if not ct or _is_arrangement_entry(ct):
            continue
        heading = ""
        hm = _HEADING_EXTRACT.match(rs["lines"][0].strip())
        if hm:
            heading = hm.group(1).strip()
        result.append(
            SectionChunk(
                chapter_number=header.get("chapter", ""),
                version_id="",
                section_ref=rs["section"],
                heading=heading,
                chunk_text=ct,
                as_at_date=header.get("as_at_date", ""),
                version_label=header.get("version_label", ""),
                chunk_index=idx,
            )
        )
    return result


def chunk_markdown_file(filepath: Path) -> list[SectionChunk]:
    text = filepath.read_text(encoding="utf-8", errors="replace")
    return extract_section_chunks(text)
