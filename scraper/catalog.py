import re

from bs4 import BeautifulSoup

from scraper.models import ChapterListing

CURRENTID_RE = re.compile(r"currentid=(\d+)")


def parse_listing_page(html: str) -> list[ChapterListing]:
    soup = BeautifulSoup(html, "html.parser")
    law_list = soup.find("ul", id="law-list")
    if law_list is None:
        return []

    listings = []
    for item in law_list.find_all("li", class_="list-group-item"):
        link = item.find("a")
        if link is None:
            continue
        match = CURRENTID_RE.search(link.get("href", ""))
        if match is None:
            continue

        title_tag = link.find("strong", class_="block")
        # the link has two <small> tags: an empty pull-right one and the
        # real subtitle one. Take the one that has text.
        subtitle_tags = link.find_all("small")
        subtitle_text = next(
            (t.get_text(strip=True) for t in subtitle_tags if t.get_text(strip=True)),
            "",
        )

        listings.append(
            ChapterListing(
                current_id=int(match.group(1)),
                title=title_tag.get_text(strip=True) if title_tag else "",
                subtitle=subtitle_text,
            )
        )
    return listings


def crawl_full_catalog(
    client, base_url: str, listing_path: str, page_size: int = 10
) -> list[ChapterListing]:
    all_listings: list[ChapterListing] = []
    offset = 0
    while True:
        url = f"{base_url}{listing_path}?offset={offset}"
        response = client.get(url)
        page_listings = parse_listing_page(response.text)
        if not page_listings:
            break
        all_listings.extend(page_listings)
        offset += page_size
    return all_listings
