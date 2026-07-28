import re

from bs4 import BeautifulSoup

from scraper.models import ChapterDetail, VersionLink

CHAPTER_NUMBER_RE = re.compile(r"(\d+:\d+)")
DOWNLOAD_ID_RE = re.compile(r"/revision/download/(\d+)\?type=act")


def parse_chapter_detail(html: str, current_id: int) -> ChapterDetail:
    soup = BeautifulSoup(html, "html.parser")
    law_detail = soup.find("div", id="law-detail")

    full_title = ""
    if law_detail is not None:
        heading = law_detail.find("h4", class_="font-bold")
        if heading is not None:
            full_title = heading.get_text(strip=True)

    chapter_match = CHAPTER_NUMBER_RE.search(full_title)
    chapter_number = chapter_match.group(1) if chapter_match else ""
    title = re.sub(r"\s*Chap\.?\s*\d+:\d+\s*$", "", full_title).strip()

    description = ""
    metadata = {}
    if law_detail is not None:
        description_tag = law_detail.select_one("aside p strong")
        if description_tag is not None:
            description = description_tag.get_text(strip=True)

        for li in law_detail.select("ul.nav-stacked li"):
            text = li.get_text(" ", strip=True)
            if " - " in text:
                key, _, value = text.partition(" - ")
                metadata[key.strip()] = value.strip()

    versions = []
    activities = soup.find("div", id="activities")
    if activities is not None:
        for li in activities.find_all("li", class_="list-group-item"):
            # each version row has two <a> tags sharing the same download
            # href: an image-thumbnail link and a text link (class="clear")
            # that actually carries the label/date. Only the latter has them.
            link = li.find("a", class_="clear", href=DOWNLOAD_ID_RE)
            if link is None:
                continue
            download_match = DOWNLOAD_ID_RE.search(link["href"])
            date_tag = link.find("small", class_="pull-right")
            label_tag = link.find("strong", class_="block")
            versions.append(
                VersionLink(
                    download_id=int(download_match.group(1)),
                    label=label_tag.get_text(strip=True) if label_tag else "",
                    as_at_date=date_tag.get_text(strip=True) if date_tag else "",
                )
            )

    return ChapterDetail(
        current_id=current_id,
        title=title,
        chapter_number=chapter_number,
        description=description,
        year=metadata.get("Year", ""),
        act_number=metadata.get("Act Number", ""),
        commencement_date=metadata.get("Commencement Date", ""),
        classification=metadata.get("Classification", ""),
        versions=versions,
    )
