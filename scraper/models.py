from dataclasses import dataclass, field


@dataclass
class ChapterListing:
    current_id: int
    title: str
    subtitle: str


@dataclass
class VersionLink:
    download_id: int
    label: str
    as_at_date: str


@dataclass
class ChapterDetail:
    current_id: int
    title: str
    chapter_number: str
    description: str
    year: str
    act_number: str
    commencement_date: str
    classification: str
    versions: list[VersionLink] = field(default_factory=list)
