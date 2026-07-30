from datetime import date

import pytest

from api.citations import (
    citation_title,
    format_citation,
    normalize_chapter,
    normalize_section,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("8:08", "8:08"),
        ("Chap. 8:08", "8:08"),
        ("chapter 8-8", "8:08"),
        ("8 08", "8:08"),
    ],
)
def test_normalize_chapter(raw, expected):
    assert normalize_chapter(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12", "12"),
        ("s. 3a", "3A"),
        ("section 12 (3) (A)", "12(3)(a)"),
        ("ss 24(1)(b)", "24(1)(b)"),
    ],
)
def test_normalize_section(raw, expected):
    assert normalize_section(raw) == expected


@pytest.mark.parametrize("raw", ["", "chapter eight", "8", "8:"])
def test_invalid_chapter_is_rejected(raw):
    with pytest.raises(ValueError):
        normalize_chapter(raw)


@pytest.mark.parametrize("raw", ["", "section twelve", "12(", "12(a"])
def test_invalid_section_is_rejected(raw):
    with pytest.raises(ValueError):
        normalize_section(raw)


def test_formatter_produces_conservative_full_and_short_forms():
    full, short = format_citation("Absconding Debtors", "8:08", "12")

    assert full == "Absconding Debtors Act, Chap. 8:08, s. 12"
    assert short == "Chap. 8:08, s. 12"
    assert citation_title("Summary Courts Act") == "Summary Courts Act"


def test_formatter_labels_requested_historical_date():
    full, _ = format_citation(
        "Absconding Debtors",
        "8:08",
        "12",
        date(2012, 12, 31),
    )

    assert full.endswith("(version available as at 31 December 2012)")
