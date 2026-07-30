# Lawyer And Paralegal UX Implementation Plan

**Date:** 2026-07-29  
**Source critique:** `2026-07-29-lawyer-paralegal-ux-critique.md`  
**Target:** Production Svelte frontend, FastAPI backend, and PostgreSQL search

## Objective

Make LawCite TT faster and safer for routine legal research by prioritizing
authority metadata, grouping historical versions, reducing technical jargon,
and supporting efficient result scanning on desktop and mobile.

The rollout must preserve the currently working production frontend while the
new backend contract is introduced.

## Product Decisions

- Use `Latest available` rather than `Current` until the source crawler records
  authoritative in-force status.
- Group search results by `(chapter_number, section_ref)`.
- Keep the highest-ranked matching chunk as the group's excerpt.
- Show version summaries in the search response; fetch complete version text
  through the existing lookup workflow only when requested.
- Keep `/api/search` unchanged during rollout and introduce
  `/api/search/grouped`.
- Hide raw search scores from the UI while retaining them in the API for
  diagnostics.
- Remove operational statistics from the main research workflow; retain the
  `/api/stats` endpoint for health/administration.
- Hide Cite and Chat until each supports a complete workflow.

## Proposed Grouped Search Contract

`GET /api/search/grouped`

Parameters:

- `q`: required query
- `mode`: `fts`, `hybrid`, or `vector`
- `chapter`: optional chapter filter
- `date`: optional historical as-at date
- `limit`: number of provision groups, default 20
- `offset`: provision-group offset, default 0

Response:

```json
{
  "items": [
    {
      "key": "9:70::244",
      "title": "Bankruptcy Act",
      "chapter_number": "9:70",
      "section_ref": "244",
      "heading": "Summary administration",
      "matched_version": {
        "version_id": 123,
        "download_id": 51068,
        "as_at_date": "2009-12-31",
        "version_label": "",
        "chunk_text": "...",
        "pdf_url": "https://laws.gov.tt/..."
      },
      "latest_available": {
        "download_id": 51080,
        "as_at_date": "2012-12-31",
        "version_label": ""
      },
      "versions": [
        {
          "download_id": 51080,
          "as_at_date": "2012-12-31",
          "version_label": ""
        }
      ],
      "score": 0.1844
    }
  ],
  "next_offset": null,
  "has_more": false
}
```

`score` remains available for diagnostics but is not rendered.

## Phase 1: Backend Grouped Search

### 1. Add Response Models

Create Pydantic response models in a focused API models module:

- `VersionSummary`
- `MatchedVersion`
- `GroupedSearchItem`
- `GroupedSearchResponse`

Files:

- Add `backend/api/models.py`
- Update `backend/api/main.py`

### 2. Return Legal Metadata

Update search SQL to join `chapters` and return:

- legislation title
- heading
- version label
- version date
- download ID

Do not duplicate title parsing in the frontend.

File:

- `backend/scraper/db_pg.py`

### 3. Rank Unique Provisions

For FTS and vector search:

1. Rank matching chunks.
2. Partition candidates by `(chapter_number, section_ref)`.
3. Select the best matching chunk per provision.
4. Sort provision groups by their best score.
5. Apply a deterministic score/key order, then request `limit + 1` groups after
   `offset` to determine `has_more` and `next_offset`.

Only group rows with a non-empty section reference. Give unstructured rows a
chunk-specific fallback key so unrelated schedules, preliminary text, or OCR
fragments are not collapsed into one provision.

For hybrid search:

1. Retrieve oversampled FTS and vector candidates.
2. Normalize and combine scores as today.
3. Collapse by provision key before applying the requested group limit.
4. Use score, dated-version recency, and chunk ID as deterministic tie-breakers.

Avoid client-side grouping of a flat 20-row response because it can return
fewer than 20 provisions and cannot reliably determine version metadata.

### 4. Batch Version Summaries

For the selected provision keys, run one batch query that returns distinct
available versions ordered by:

```text
as_at_date DESC NULLS LAST, download_id DESC
```

Mark the first dated version as `latest_available`. Do not infer that it is
legally current.

### 5. Add Historical-Date Semantics

When `date` is supplied:

- exclude versions later than the requested date;
- select the best matching eligible version;
- return the requested date in response metadata;
- label the frontend result `Available as at <date>`.

Document how undated versions are handled and cover the rule with tests.

### 6. Keep V1 Stable

Do not change `/api/search` until the frontend has deployed successfully
against `/api/search/grouped`.

## Phase 2: Backend Verification

Replace external-SSD-dependent coverage with synthetic PostgreSQL fixtures for
the grouped-search tests.

Add tests for:

- title and heading enrichment;
- one result per provision despite multiple matching versions;
- deterministic latest-available selection;
- null-date handling;
- historical date filtering;
- chapter filtering;
- FTS grouping;
- vector grouping;
- hybrid grouping before limit;
- `limit + 1` pagination behavior;
- PDF URL construction;
- unchanged `/api/search` response.

Files:

- Update `tests/test_db_pg.py`
- Update `tests/test_api.py`
- Add focused fixture helpers under `tests/` if duplication warrants it

Gate:

```bash
.venv/bin/pytest tests/test_db_pg.py tests/test_api.py
```

## Phase 3: Frontend Research Workflow

### 1. Simplify The App Shell

- Remove `StatsBar` from `Explore`.
- Hide Cite and Chat navigation.
- Keep the LawCite TT brand visible in the mobile header.
- Replace the text hamburger glyph with a Lucide menu icon.
- Add `lucide-svelte` for menu, search, file, copy, chevron, and external-link
  icons.

Files:

- Update `citation-tool/src/App.svelte`
- Update `citation-tool/src/routes/Explore.svelte`
- Remove the unused `StatsBar` import; keep the component until cleanup

### 2. Use Task Language

Render mode labels as:

- `Exact wording`
- `Best match`
- `Related concepts`

Keep API values unchanged.

Add accessible explanations via title/tooltip or help text that does not
dominate the interface.

File:

- Update `citation-tool/src/components/SearchBar.svelte`

### 3. Add Research Filters

- Improve chapter options to show both chapter number and title.
- Add an as-at date control using `input type="date"`.
- Show active filters compactly and provide a clear-filters action.
- Preserve query/filter state while switching between search and lookup.

Files:

- Update `citation-tool/src/components/SearchBar.svelte`
- Update `citation-tool/src/routes/Explore.svelte`
- Update `citation-tool/src/lib/api.js`

### 4. Replace Result Cards

Each provision result should show:

1. Act title.
2. Chapter and section.
3. `Latest available`, `Historical`, or `Date unavailable`.
4. As-at date/version label.
5. A contextual excerpt with highlighted query terms.
6. Actions for expand/collapse and official PDF.

Remove:

- raw relevance score;
- emoji PDF icon;
- fixed-height internal scrolling.

Add an on-demand versions control. Selecting a version calls the lookup
endpoint rather than shipping every full historical text in the initial search.

Replace the current `{@html}` highlighting implementation with safe text-node
token rendering. Imported document text must never be treated as HTML.

Files:

- Rewrite `citation-tool/src/components/ResultCard.svelte`
- Add `citation-tool/src/components/VersionSelector.svelte`
- Add a pure excerpt/highlight helper under `citation-tool/src/lib/`

### 5. Clarify Result Counts

Use `Showing <n> provisions`, not `<n> results`. Add a `Load more` command when
`has_more` is true. Append results without shifting the existing scroll
position.

File:

- Update `citation-tool/src/routes/Explore.svelte`

### 6. Improve Section Lookup

- Use the same legal metadata hierarchy as search.
- Label the newest dated version `Latest available`.
- Collapse historical versions by default.
- Use the shared result/version presentation components where practical.

File:

- Update `citation-tool/src/components/LookupPanel.svelte`

## Phase 4: Frontend Tests And Accessibility

Add:

- Vitest
- `@testing-library/svelte`
- `@testing-library/jest-dom`
- jsdom

Test:

- plain-language mode labels map to correct API values;
- operational statistics and unfinished routes are absent;
- score is not rendered;
- legal title/chapter/section/date hierarchy;
- excerpts expand and collapse without nested scrolling;
- imported HTML-like text is rendered inert and cannot inject markup;
- version selection requests the correct lookup;
- active filters can be cleared;
- loading, empty, error, and load-more states;
- keyboard activation and accessible names.

Files:

- Update `citation-tool/package.json`
- Add `citation-tool/src/**/*.test.js`
- Update Vite/Vitest configuration as needed

Gates:

```bash
cd citation-tool
npm test
npm run build
```

## Phase 5: Visual And Workflow QA

Use the production-shaped database and test:

### Desktop: 1440x1000

- exact wording search;
- related-concepts search;
- chapter filter;
- historical date;
- expand excerpt;
- switch version;
- official PDF;
- load more.

### Mobile: 390x844

- visible brand and navigation;
- first search control visible without metric tiles;
- no horizontal overflow;
- no nested scrolling inside results;
- filters and version controls fit;
- long legislation titles wrap without overlap.

Capture Playwright screenshots and confirm zero browser console errors.

## Phase 6: Deployment

### Backend First

1. Build and test a new `linux/amd64` API image.
2. Deploy it to the VPS while the frontend remains on `/api/search`.
3. Verify `/api/search/grouped`, `/api/search`, stats, FTS, vector, and CORS.
4. Retain image `lawcite-api:ce84113` for rollback.

### Frontend Second

1. Build with the production API base.
2. Deploy to Cloudflare Workers.
3. Run the desktop/mobile Playwright workflows.
4. Confirm the old flat endpoint receives no frontend traffic before later
   deprecation.

Rollback the frontend independently if grouped-search rendering fails.

## Deferred Work

- Calling a version legally `Current` requires validated source semantics or a
  separately maintained authority-status field.
- Real authentication and rate limiting remain the highest production-security
  priority.
- Copy citation, compare versions, saved searches, matter folders, exports, and
  light theme follow after the core search hierarchy is validated.
- Interview five lawyers and five paralegals after the first implementation
  before expanding workflow scope.

## Definition Of Done

- Search returns unique provisions rather than duplicate version rows.
- Every result identifies the legislation, chapter, section, and version date.
- No unsupported `Current` claim appears.
- Users never see raw scores, chunk counts, embedding counts, or search-engine
  implementation terminology.
- Results have contextual excerpts with explicit expansion and no nested scroll.
- Unfinished Cite and Chat routes are absent.
- Desktop and mobile workflows pass with no overflow or console errors.
- Existing `/api/search` remains functional through the rollout.
- Production health, stats, FTS, vector, CORS, and official PDF links still pass.

## Implementation Status

**Completed locally on 2026-07-29:**

- Phases 1-5 are implemented.
- `/api/search/grouped` is backward-compatible with the unchanged flat search endpoint.
- Historical filtering uses `COALESCE(versions.as_at_date, chunks.as_at_date)` to support migrated rows.
- Backend verification: `11 passed, 7 skipped`; skips are legacy tests that require the detached external SSD.
- Frontend verification: `8 passed`; the Vite production build succeeds.
- Playwright verified exact, hybrid, and vector search, pagination, historical cutoff, exact version switching, section lookup, chapter browsing, and mobile navigation.
- Desktop `1440x1000` and mobile `390x844` have no console errors; mobile document width equals the 390px viewport.

**Remaining:**

- Phase 6 deployment must be backend first because the current production API does not yet expose `/api/search/grouped`.
- Retain `lawcite-api:ce84113` as the rollback image.
- Do not deploy the new frontend until the grouped endpoint passes on the VPS.
- Reconcile the pre-existing catalog mismatch that labels some bankruptcy content as `30:50 Burial Grounds`.

## Production Deployment

Completed on 2026-07-29:

- Hostinger API image: `lawcite-api:ux-grouped-20260729`
- Rollback API image retained: `lawcite-api:ce84113`
- Cloudflare Worker: `law-cite-tt`
- Cloudflare version: `98837494-e732-4872-ac61-76751aadc8da`
- Production URL: `https://law-cite-tt.gjo-ai.workers.dev`
- Verified grouped exact search and a `2013-12-31` historical cutoff against the public API.
- Verified desktop `1440x1000` and mobile `390x844`; production console errors: zero.
