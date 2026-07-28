# Testing Framework — Temporal Legal Citation Engine

Tests define "good." Implementation follows.

---

## 1. Golden Test Set

The single source of truth for all accuracy measurements. Hand-verified against actual PDFs.

### Coverage targets

| Category | Count | Example |
|----------|-------|---------|
| Simple lookup | 10 | `Ch 8:08 Sect 12` — exact section, current version, unambiguous |
| Temporal diff | 10 | `Ch 8:08 Sect 12` at 1950 vs at 2016 — same citation, different expected text |
| Nested reference | 5 | `Ch 8:08 Sect 12(3)(b)` — subsection + sub-subsection |
| Edge cases | 5 | Preamble, schedules, repealed sections, cross-chapter references |

### Schema

```json
{
  "citation": {
    "chapter": "8:08",
    "section": "12",
    "subsection": "3",
    "paragraph": "b"
  },
  "temporal_context": {
    "as_at_date": "1950-06-01",
    "version_label": "Original Act"
  },
  "expected": {
    "text_prefix": "A person who absconds...",
    "min_chars": 50,
    "must_contain": ["absconds", "warrant"],
    "must_not_contain": ["REPEALED"]
  },
  "source": {
    "file": "/Volumes/.../markdown/8_08_Absconding_Debtors/23669.md",
    "page": 12,
    "verified_by": "human",
    "notes": "Section 12(3) unchanged between 1950 and 2006"
  },
  "negative_tests": [
    {"chapter": "10:02", "section": "12", "reason": "wrong chapter"},
    {"chapter": "8:08", "section": "99", "reason": "section does not exist"}
  ]
}
```

---

## 2. Metrics

### Accuracy

| Metric | What it measures | Calculation |
|--------|-----------------|-------------|
| **ExactRecall@1** | Does the exact section text appear as the top result? | `count(correct_at_rank_1) / total_queries` |
| **ExactRecall@5** | Does it appear in the top 5? | `count(correct_in_top_5) / total_queries` |
| **SectionBoundaryRecall** | What % of `Section \d+` markers produce their own chunk? | `count(chunks_starting_at_section_marker) / count(section_markers_in_source)` |
| **SectionBoundaryPrecision** | What % of chunks actually start at a section boundary? | `count(chunks_starting_at_section_marker) / count(total_chunks)` |
| **VersionResolutionAccuracy** | Temporal query returns correct version? | `count(correct_version_returned) / count(temporal_queries)` |
| **NegativePrecision** | Non-existent citations return empty? | `count(empty_results_for_nonexistent) / count(negative_queries)` |
| **CrossChapterIsolation** | Wrong-chapter queries return nothing from the target chapter? | See below |

### Temporal Correctness

| Metric | What it measures |
|--------|-----------------|
| **DateOrderingAccuracy** | Versions returned in correct chronological order? |
| **VersionPinpointAccuracy** | Given date X that falls between version A and B, does the system return version A (not B, not null)? |
| **GapDetectionAccuracy** | Given date before earliest version or after latest, does the system signal "no version for this date"? |
| **AmendmentChainAccuracy** | Traversing `superseded_by` edges yields a continuous, monotonic chain? |

### Performance

| Metric | Threshold | Measurement |
|--------|-----------|-------------|
| **p50 latency** | < 100ms | 1000 random citation lookups |
| **p99 latency** | < 500ms | Same benchmark |
| **Temporal query p50** | < 200ms | 1000 date-filtered queries |
| **Batch embed throughput** | > 10 chunks/sec | Full re-index of 100K chunks |
| **Database size** | < 2GB on disk | After full import |

### Quality

| Metric | Threshold | Measurement |
|--------|-----------|-------------|
| **GarbageRejectionRate** | 100% | Scanned PDFs (Tobago Deeds) produce 0 chunks, flagged as garbage |
| **HeadingAnchoringRate** | 100% | Every chunk's first N chars include chapter/part heading |
| **ChunkSizeP50** | 200-800 chars | Median chunk length should be in this range |
| **ChunkSizeOutlierRate** | < 5% | Chunks < 50 or > 2000 chars flagged for review |

---

## 3. Suite Design

### Framework: pytest with custom markers

```python
@pytest.mark.accuracy
@pytest.mark.recall
def test_exact_citation_returns_correct_chunk(golden_set, citation_engine):
    ...

@pytest.mark.temporal
def test_version_pinpoint_accuracy(golden_set, citation_engine):
    ...

@pytest.mark.chunking
def test_section_boundary_recall(chapter_fixtures, chunker):
    ...

@pytest.mark.performance
@pytest.mark.benchmark
def test_latency_p50(benchmark, citation_engine, random_queries):
    ...

@pytest.mark.robustness
def test_concurrent_readers(citation_engine, random_queries):
    ...
```

### Custom markers

- `@pytest.mark.accuracy` — correctness of retrieval
- `@pytest.mark.temporal` — temporal version resolution
- `@pytest.mark.chunking` — chunk quality metrics
- `@pytest.mark.performance` — latency / throughput
- `@pytest.mark.robustness` — error handling, concurrency
- `@pytest.mark.regression` — tests that verify specific bugs stay fixed
- `@pytest.mark.slow` — tests that take > 10s (excluded from `pytest -v`, run nightly)

### Fixtures

```
tests/
  fixtures/
    golden_set.json                 # 30 hand-verified entries
    markdown_samples/               # 10-15 real markdown files covering different layouts
      Absconding_Debtors_complex.md  # multi-part, schedules, cross-refs
      Summary_Courts_flat.md         # simple sequential sections
      Tobago_Deeds_garbage.md       # scanned/empty
      Constitution_toc.md           # table of contents, preamble
      ...
    db/
      seed.sql                       # pre-populated SQLite for API contract tests
```

---

## 4. Comparison Workflows

The suite is designed to compare approaches, not just pass/fail a single one.

### Chunking strategy comparison

```bash
pytest -k "chunking" --chunk-strategy=section-aware   # baseline
pytest -k "chunking" --chunk-strategy=fixed-256       # alternative
pytest -k "chunking" --chunk-strategy=fixed-512       # alternative
pytest -k "chunking" --chunk-strategy=section-aware+heading-enriched
```

Output: a table comparing SectionBoundaryRecall, SectionBoundaryPrecision, ExactRecall@1, ChunkSizeP50, and GarbageRejectionRate across strategies.

### Embedding model comparison

```bash
pytest -k "recall" --embed-model=voyage-law-2
pytest -k "recall" --embed-model=text-embedding-3-large
pytest -k "recall" --embed-model=voyage-law-2 --chunk-strategy=fixed-512
```

Output: ExactRecall@1/5, latency, and database size per model.

### Database backend comparison

```bash
pytest -k "recall or performance" --db-backend=sqlite-vec
pytest -k "recall or performance" --db-backend=pgvector
```

Output: recall parity + latency comparison.

---

## 5. Pass/Fail Criteria for v1

| Gate | Threshold | Blocks |
|------|-----------|--------|
| ExactRecall@1 on golden set | ≥ 90% | API release |
| ExactRecall@5 on golden set | ≥ 98% | API release |
| VersionResolutionAccuracy | ≥ 95% | Temporal query endpoint |
| NegativePrecision | 100% | Any endpoint (never hallucinate a citation) |
| SectionBoundaryRecall | ≥ 90% | Chunking pipeline acceptance |
| GarbageRejectionRate | 100% | Chunking pipeline acceptance |
| p99 latency | < 500ms | API release |
| CrossChapterIsolation | 0 false positives | Any endpoint |

Before any chunker is written, before any embedding model is chosen — these thresholds define what "done" means. If a strategy doesn't hit them, we try another strategy, not lower the bar.
