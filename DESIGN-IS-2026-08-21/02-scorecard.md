# Scorecard — LawCite TT Frontend

1. Good design is innovative — Score: 2/3
   Evidence: Source-verified chat citations + ambiguous/not-found citation-validation states (01-evidence.md Copy & Structural) are a real refinement over typical link-out citation tools.
   Justification: Clear improvement on an existing pattern (RAG-with-citations, citation resolution), not a genuinely new pattern across the domain — doesn't clear the bar for 3.

2. Good design is useful — Score: 2/3
   Evidence: Primary validate/cite flow completes in minimal steps (chapter+section→submit), but Explore's chapter-dropdown fetch failure only `console.error`s with no visible UI feedback (Explore.svelte:29-30 vs 52-53), stranding the user on that path.
   Justification: Primary task is well-served; an adjacent primary surface (chapter browse) can silently fail with zero user-facing signal.

3. Good design is aesthetic — Score: 1/3
   Evidence: 18 distinct non-modular spacing values, 10 non-modular type sizes, 1 undocumented off-palette hardcoded color (StatsBar.svelte:71 `#f87171` vs `var(--danger)`), and the same card-container pattern implemented under 5 different class names (Visual + Structural evidence).
   Justification: Token discipline exists (13 named colors) but isn't enforced consistently — five-plus inconsistencies puts this below "≤2 minor inconsistencies."

4. Good design is understandable — Score: 1/3
   Evidence: Three unclear/jargon instances found — "materially different source row" (Cite.svelte:207-213), "resolves in its source corpus" (Cite.svelte:322), ambiguous "Date unavailable" pill (ResultCard/LookupPanel).
   Justification: 2-3 controls/strings unclear with jargon present is the exact match for score 1.

5. Good design is unobtrusive — Score: 3/3
   Evidence: Dark chrome recedes (Visual evidence: token system keeps surface/border colors low-contrast against content), no decorative elements found competing with statutory text.
   Justification: Chrome is quiet and consistent; content is the figure throughout all three routes.

6. Good design is honest — Score: 2/3
   Evidence: One flagged inflation — Explore.svelte:112 hardcodes "533 chapters" in markup rather than sourcing it from the live `/api/stats` call StatsBar actually uses. No dark patterns found; "Sign in (stub)" is honestly labeled.
   Justification: Exactly one minor inflation, no manipulation — matches "≤1 minor inflation" for score 2.

7. Good design is long-lasting — Score: 3/3
   Evidence: Flat dark legal-tech token system, no skeuomorphism, no fad gradients or trend typography found in any audited file.
   Justification: No dated visual-trend markers identified across Visual evidence.

8. Good design is thorough down to the last detail — Score: 1/3
   Evidence: Explore's chapter-dropdown failure has no error state (missing); StatsBar's error path bypasses `role="alert"` and the design-token danger color in favor of a raw hardcoded red (rough); disabled-button treatment is inconsistent (load-more uses `cursor:wait;opacity:.65` vs every other disabled control's `cursor:not-allowed;opacity:.4-.45`).
   Justification: One state genuinely missing plus two rough/inconsistent treatments — matches "2-3 states missing" for score 1.

9. Good design is environmentally friendly — Score: 3/3
   Evidence: Initial JS is 88,689 bytes (86.6KB, gzip 30.16KB) — under the 100KB bar; zero idle-screen animation; the one CSS animation (spinner) is gated to an active loading state.
   Justification: Meets all conditions for score 3.

10. Good design is as little design as possible — Score: 1/3
    Evidence: The same card/tile visual pattern is reimplemented under 5 different class names (StatsBar `.stat-tile`, ChapterBrowser `.chapter-card`, ResultCard `.result-card`, LookupPanel `details`, Cite `.result-card`); `displayDate()` is duplicated 3x with a silent inconsistency (Cite uses `month:"long"`, others `"short"`); two separate status-badge systems exist for the same concept (ResultCard `.status` pill vs Cite `.state-card`).
    Justification: 3-5 clearly removable/consolidatable duplications — matches score 1, not 0 (nothing is pure decoration, it's redundant implementation of needed affordances).

**Total: 19/30**
