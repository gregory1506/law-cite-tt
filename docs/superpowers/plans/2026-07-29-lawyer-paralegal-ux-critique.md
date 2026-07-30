# LawCite TT Lawyer And Paralegal UX Critique

**Date:** 2026-07-29  
**Artifact reviewed:** Production frontend at `law-cite-tt.gjo-ai.workers.dev`  
**Methods:** Live desktop/mobile browser review, task walkthroughs, code inspection,
and role-based heuristic analysis.

**Implementation plan:** `2026-07-29-lawyer-paralegal-ux-implementation.md`

This is an expert review, not a substitute for interviews with practising
Trinidad and Tobago lawyers and paralegals.

## User Priorities

### Lawyer

- Determine quickly whether a provision is current, historical, or unofficial.
- See the Act title, chapter, section, effective/as-at date, and official source.
- Find exact language without losing related conceptual matches.
- Cite, compare, and defend the authority used.

### Paralegal

- Repeat searches and retrieve documents quickly with minimal re-entry.
- Scan and triage many results without opening every PDF.
- Copy consistent references and collect authorities for a matter.
- Avoid accidentally selecting an obsolete version.

## Live-Test Evidence

- A production search for `absconding debtor` returned 20 results successfully.
- Several top results were the same provision from different years.
- Results led with chapter/section/date and a raw score, but not the Act title.
- Result cards used internally scrolling 160px excerpts.
- The first mobile viewport devoted substantial space to database statistics.
- Search modes exposed implementation terms: FTS, hybrid, and vector.
- The production navigation exposed unfinished Cite and Chat routes.
- No browser console errors occurred; the workflow is technically sound.

## Priority Findings

### P0: Correct The Legal Information Hierarchy

Each result should lead with:

1. Act or Ordinance title.
2. Chapter and section.
3. `Current` or `Historical` status.
4. As-at/effective date.
5. Official-source link.

Hide the raw relevance score from normal users. It does not help a lawyer
assess authority and may imply a level of precision the ranking does not have.

### P0: Group Historical Versions

Do not render every version as an independent result. Group results by
provision, show the current/latest version first, and provide a version selector
or timeline inside the result. This is the most important workflow change
because repeated versions currently crowd out distinct authorities.

### P0: Replace Nested Scrolling With Scannable Excerpts

Remove the fixed-height scrolling text area in each card. Show a short excerpt
around the matching terms, then provide an explicit expand/collapse control.
Nested scrolling slows comparison and is especially awkward on mobile.

### P0: Use Legal-Task Language

Rename search modes:

- `Full-Text Search (fast)` -> `Exact wording`
- `Hybrid (FTS + Vector)` -> `Best match`
- `Vector (Semantic)` -> `Related concepts`

The implementation method can remain in a tooltip or advanced settings.

### P0: Remove Internal Product Metrics From The Primary Workflow

`Chunks` and `Embedded` are operational metrics, not user value. Remove the
four-card stats bar from the search screen, especially on mobile. Replace it
with a restrained data-status line such as `533 chapters · updated <date>` or
move operational counts to an admin status page.

### P0: Do Not Advertise Unfinished Workflows

Hide Cite and Chat from production navigation until they support a complete
task. The current stubs lower confidence in the parts that already work.

## Next-Round Improvements

### P1: Research Controls

- Add current-only, historical date, chapter, and legislation-title filters.
- Change `20 results` to `Showing 20 results` and add pagination/load more.
- Preserve the query, filters, and scroll position when returning from a source.
- Offer a theme toggle; keep dark mode but provide a high-legibility light mode
  for long reading sessions and printing.

### P1: Authority Actions

- Add `Copy reference`, `Open official PDF`, and `Compare versions`.
- Include official/unofficial source status beside the date.
- Provide a stable result permalink.
- Add a compact citation preview once the citation formatter is implemented.

### P2: Repeated Work

- Recent and saved searches.
- Bookmarks or matter folders.
- Multi-select and export of authorities.
- Keyboard-first search and result navigation.
- Search-history audit trail for reproducible research.

## Mobile Findings

- Keep a compact header with the LawCite TT brand visible beside the menu icon.
- Remove the four large metric tiles above search.
- Make the search action full-width or align it predictably with the mode menu.
- Keep result metadata to two clear lines and avoid internal card scroll areas.
- Collapse filters behind a filter control after showing active filter chips.

## Recommended First Implementation

1. Remove the stats bar and hide Cite/Chat.
2. Rename search modes and hide raw scores.
3. Add Act title and authority-status fields to API results.
4. Replace card scrolling with contextual excerpts and expansion.
5. Group versions and default to the latest/current provision.
6. Add current/historical and as-at-date filtering.

Steps 1, 2, and the card presentation are frontend-only. Act titles, reliable
status, grouping, and result totals require API/query changes.

## Validation Study

After the first implementation, run five lawyer and five paralegal sessions
using these tasks:

1. Find the current text of a named section.
2. Find the version in force on a historical date.
3. Find related provisions without knowing exact wording.
4. Copy a reference and open the official source.
5. Compare two versions and explain which one applies.

Measure time-to-correct-authority, obsolete-version errors, unnecessary PDF
opens, search reformulations, and confidence rating.
