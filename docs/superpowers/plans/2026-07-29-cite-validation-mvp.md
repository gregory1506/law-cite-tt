# Cite Validation MVP

**Date:** 2026-07-29
**Estimate:** 4-6 focused hours
**Priority:** Next product feature

**Status:** Complete and deployed on 2026-07-30

## Objective

Restore the project's original citation-engine workflow. A lawyer or paralegal
must be able to identify a Trinidad and Tobago statutory provision, optionally
pin it to a historical date, confirm that it resolves to source text, and copy
a consistently formatted citation.

This is a validation workflow, not merely a text formatter.

## Product Position

The primary navigation becomes:

1. Research
2. Cite
3. Chat

Research discovers provisions. Cite validates and formats a known reference.
Chat remains a placeholder until it can return source-grounded answers.

The MVP must not claim that a provision is currently in force. Until the source
pipeline records authoritative commencement, repeal, and amendment status, use
`Latest available` and `Available as at <date>`.

## MVP User Flow

1. Open Cite.
2. Select or enter a chapter number.
3. Enter a section reference.
4. Optionally select an as-at date.
5. Choose **Validate citation**.
6. Receive one explicit outcome:
   - `Citation found`
   - `Citation not found`
   - `Citation ambiguous`
7. For a resolved citation, review:
   - legislation title;
   - canonical chapter and section;
   - matched version and as-at date;
   - exact statutory text;
   - official PDF;
   - formatted citation.
8. Copy the citation with one command.

## Citation Output

The initial formatter should produce a conservative canonical form from
structured database fields:

```text
Absconding Debtors Act, Chap. 8:08, s. 12
```

When a historical date is requested:

```text
Absconding Debtors Act, Chap. 8:08, s. 12
(version available as at 31 December 2012)
```

Before release, confirm punctuation, title treatment, section abbreviations,
subsidiary-legislation treatment, and historical-version notation against
authoritative Trinidad and Tobago court or practice-direction examples. Keep
the formatter rules isolated so corrections do not affect resolution logic.

## Backend Contract

Add a backward-compatible endpoint:

```text
GET /api/citations/resolve
```

Parameters:

- `chapter`: required canonical or user-entered chapter number
- `section`: required provision reference
- `date`: optional ISO as-at date

Proposed response:

```json
{
  "status": "found",
  "normalized_input": {
    "chapter": "8:08",
    "section": "12",
    "date": "2012-12-31"
  },
  "citation": {
    "full": "Absconding Debtors Act, Chap. 8:08, s. 12",
    "short": "Chap. 8:08, s. 12"
  },
  "authority": {
    "title": "Absconding Debtors",
    "chapter_number": "8:08",
    "section_ref": "12",
    "as_at_date": "2012-12-31",
    "version_label": "...",
    "download_id": 51080,
    "pdf_url": "https://laws.gov.tt/..."
  },
  "text": "...",
  "alternatives": []
}
```

Use an enum for `found`, `not_found`, and `ambiguous`. Do not encode validation
failure as an empty successful-looking result.

## Implementation Steps

### 1. Citation Models And Formatter

- Add request/response models under `backend/api/`.
- Add a pure citation formatter with no database access.
- Normalize whitespace, chapter separators, `s`, `ss`, `section`, and common
  capitalization variants.
- Preserve nested section references such as `12(3)(a)`.

### 2. Deterministic Resolver

- Resolve the normalized chapter against `chapters`.
- Resolve the section using the existing exact lookup path.
- Apply the same temporal fallback used by grouped search:
  `COALESCE(versions.as_at_date, chunks.as_at_date)`.
- Return the newest eligible dated version for a requested historical date.
- Return `ambiguous` when multiple materially different rows remain after
  normalization.
- Return a small set of exact chapter/section alternatives where possible.

### 3. API Endpoint

- Add `/api/citations/resolve` without changing `/api/lookup`.
- Construct official PDF URLs in the API.
- Validate malformed dates and empty references with clear `422` responses.
- Keep the endpoint usable independently of the Svelte frontend.

### 4. Cite Interface

- Restore Cite in desktop and mobile navigation.
- Replace the stub with chapter, section, and optional date controls.
- Use autocomplete from the existing chapter catalog.
- Present the validation state before the provision text.
- Show formatted full and short citations with Copy controls.
- Show version metadata and the official PDF beside the resolved authority.
- Avoid raw scores, database IDs, or unsupported legal-status claims.

### 5. Tests

Backend tests:

- canonical exact citation;
- chapter and section normalization;
- nested section reference;
- historical date selection;
- later versions excluded by date;
- migrated chunk-date fallback;
- nonexistent chapter;
- nonexistent section;
- ambiguous result;
- PDF URL and formatted citation;
- unchanged `/api/lookup`.

Frontend tests:

- Cite is present in navigation;
- form submission uses normalized fields;
- found, not-found, ambiguous, loading, and error states;
- full and short citation rendering;
- Copy command;
- historical label;
- keyboard submission and accessible names;
- no `Current` or `in force` claim.

## Verification

Run:

```bash
.venv/bin/pytest tests/test_db_pg.py tests/test_api.py
cd citation-tool
npm test
VITE_API_BASE=https://srv1629323.hstgr.cloud npm run build
```

Browser QA:

- desktop `1440x1000`;
- mobile `390x844`;
- successful current-version resolution;
- successful historical resolution;
- invalid citation;
- copy full and short forms;
- official PDF;
- no horizontal overflow or console errors.

## Deployment

1. Build a new versioned `linux/amd64` API image.
2. Deploy it to Hostinger while retaining
   `lawcite-api:ux-grouped-20260729` for rollback.
3. Verify `/api/citations/resolve`, `/api/lookup`, grouped search, health, and
   CORS publicly.
4. Deploy the Cite-enabled frontend to Cloudflare.
5. Run the production desktop and mobile workflows.

## Deferred

- Free-form citation extraction from paragraphs or uploaded documents.
- Fuzzy `did you mean?` ranking beyond deterministic alternatives.
- Quote-to-provision support verification.
- Citation tables, exports, and matter folders.
- Case-law citations and citator treatment.
- Authoritative `in force`, repealed, amended, or negative-treatment status.

## Definition Of Done

- Cite is a primary route on desktop and mobile.
- A structured statutory reference produces an explicit validation result.
- A resolved result is backed by exact text and an official source PDF.
- Full and short citations can be copied.
- Historical resolution never selects a later or unprovable undated version.
- Invalid and ambiguous references cannot appear valid.
- Existing research and lookup workflows remain functional.
- Backend and frontend tests, production build, and browser QA pass.
