from __future__ import annotations

import re
from datetime import date

_CHAPTER_PREFIX = re.compile(r"^(?:chap(?:ter)?\.?\s*)?", re.IGNORECASE)
_SECTION_PREFIX = re.compile(r"^(?:sections?|ss?|s)\.?\s*", re.IGNORECASE)
_SECTION_PATTERN = re.compile(r"^(\d+)([A-Za-z]?)(.*)$")
_LEGAL_TITLE_SUFFIX = re.compile(
    r"\b(?:Act|Code|Constitution|Ordinance|Order|Regulations|Rules)\s*$",
    re.IGNORECASE,
)


def normalize_chapter(raw: str) -> str:
    value = _CHAPTER_PREFIX.sub("", raw.strip())
    match = re.fullmatch(r"(\d{1,3})\s*[:/.\-\s]\s*(\d{1,3})", value)
    if not match:
        raise ValueError("Enter a chapter number such as 8:08.")
    first, second = match.groups()
    return f"{int(first)}:{second.zfill(2)}"


def normalize_section(raw: str) -> str:
    value = _SECTION_PREFIX.sub("", raw.strip())
    value = re.sub(r"\s+", "", value)
    match = _SECTION_PATTERN.fullmatch(value)
    if not match or not re.fullmatch(r"(?:\([0-9A-Za-z]+\))*", match.group(3)):
        raise ValueError("Enter a section such as 12, 3A, or 12(3)(a).")
    number, suffix, nested = match.groups()
    nested = re.sub(
        r"\(([A-Za-z]+)\)",
        lambda item: f"({item.group(1).lower()})",
        nested,
    )
    return f"{int(number)}{suffix.upper()}{nested}"


def citation_title(raw_title: str) -> str:
    title = " ".join(raw_title.split()).strip()
    if not title:
        return "Title unavailable"
    if _LEGAL_TITLE_SUFFIX.search(title):
        return title
    return f"{title} Act"


def format_citation(
    title: str,
    chapter: str,
    section: str,
    as_at_date: date | None = None,
) -> tuple[str, str]:
    long_form = f"{citation_title(title)}, Chap. {chapter}, s. {section}"
    if as_at_date:
        readable_date = f"{as_at_date.day} {as_at_date.strftime('%B %Y')}"
        long_form += f" (version available as at {readable_date})"
    return long_form, f"Chap. {chapter}, s. {section}"
