# law-cite-tt

## Purpose

A legal citation tool/software for the **Laws of Trinidad and Tobago**. It sources statute data (chapters, acts, revisions, amendments) from the official Digital Law Library at:

https://laws.gov.tt/ttdll-web/revision/list

The goal is to let users look up, browse, and generate properly formatted legal citations for T&T legislation (chapters, acts, sections) instead of manually tracking revisions and PDFs on the government site.

## Data Source

- **Origin**: laws.gov.tt Digital Law Library (Government of the Republic of Trinidad and Tobago), revised laws current to **31 December 2016** as of last check.
- **Organization**: Laws are catalogued by chapter number (e.g. `Chapter 8:08`) with a title, classification (e.g. "CIVIL LAW AND PROCEDURE"), year of original enactment, act number, and commencement date.
- **Revisions**: Each chapter/act may have multiple PDF versions across years (official and unofficial updates) plus amendment/alert metadata.
- **Browse modes on source site**: Constitution, recent updates, unproclaimed acts, revised acts, repealed acts, omitted acts; list views by alphabetical / chronological / legal notice year; keyword search.
- **Observed URL patterns**:
  - List/search: `/ttdll-web/revision/list?offset=0&q=[keyword]&currentid=[ID]`
  - PDF download: `/ttdll-web/revision/download/[ID]?type=act`
- These patterns were captured by manual inspection and are **not guaranteed stable** — verify against the live site before relying on them for scraping/ingestion, and re-check periodically since the site is unofficial-looking gov infrastructure that could change without notice.

## Scope Notes

- This project is a **consumer/aggregator** of the laws.gov.tt data, not a legal-authority source of truth. Always link back to or reference the official chapter/act/PDF for the authoritative text.
- Citation formatting should follow standard Trinidad & Tobago / Caribbean legal citation conventions (chapter number, act/title, year, section) — confirm exact style requirements with the user before hardcoding a citation format.
- Because source PDFs are the canonical documents, expect to need PDF text extraction or parsing as part of any ingestion pipeline.
- Be mindful of scraping etiquette/rate limits against a government site; prefer caching fetched data locally rather than re-fetching on every request.

## Status

Greenfield — no code yet. See `next_steps.md` for current priorities and `work_log.md` / `lessons_learned.md` for ongoing history.
