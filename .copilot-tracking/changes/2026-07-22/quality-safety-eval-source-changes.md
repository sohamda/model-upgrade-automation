<!-- markdownlint-disable-file -->
# Release Changes: Evaluation-driven quality/safety scoring source (Phase 1)

**Related Plan**: 20260720-quality-safety-eval-source-research.md (research §3, §4.2 Option A, §5 Phase 0-1)
**Implementation Date**: 2026-07-22

## Summary

Implemented Phase 1 of the evaluation-driven quality/safety scoring source as a
precise structural twin of the existing pricing enrichment pattern. Candidate
`quality_score` and `safety_score` dimensions, previously static catalog
placeholders, can now be overlaid with curated benchmark scores from an injected
`QualitySafetyBenchmarkSource`. The client is constructed only behind the
existing official-sources gate; hermetic runs (`use_official_sources=false`)
leave quality/safety at their catalog placeholders. Enrichment is non-fatal:
missing records or dependency failures degrade to warnings and never mutate
inputs or raise.

## Changes

### Added

* config/quality_safety_benchmarks.yaml - Curated-seed benchmark data. Top comment documents non-authoritative status, the Phase 2 out-of-band `[evaluation]` refresh note, and the formulas (`quality=(mean_likert-1)/4`, `safety=1-defect_rate`). Top-level `benchmarks:` list of 8 entries (`model_id`, `quality_score`, `safety_score`, `provenance`, `as_of_date: "2026-07-22"`): gpt-4o=0.84/0.95, gpt-4o-mini=0.78/0.94, gpt-4.1=0.86/0.96, gpt-4.1-mini=0.80/0.95, gpt-4.1-nano=0.74/0.93, gpt-5.1=0.90/0.97, o3=0.88/0.96, o4-mini=0.82/0.95.
* src/recommender/quality_safety_source.py - `QualitySafetyRecord` frozen slots dataclass; module-level `_validate_score` (rejects bool, non-numeric, out-of-`0..1` via `DependencyUnavailableError`); `QualitySafetyBenchmarkSource` slots dataclass with lazy cached `_load()` and `fetch_record(model_id, region)` (region accepted but ignored in Phase 1; raises for unknown model_id, missing file, YAML errors, and invalid/missing top-level `benchmarks` list).
* src/recommender/quality_safety_enrichment.py - `enrich_quality_safety(target, candidates, qs_client) -> tuple[list[CatalogCandidate], list[str]]`. Structural twin of `enrich_cost_scores`: `_SENTINEL`, per-model cache, catches only `DependencyUnavailableError`, copy-on-return via `dataclasses.replace`, preserves order, never mutates inputs, never raises.
* tests/unit/test_quality_safety_source.py - Source tests: known model returns record; second call uses cache after file unlink; unknown model raises; missing file raises; out-of-range and non-numeric scores raise.
* tests/unit/test_quality_safety_enrichment.py - Enrichment tests: benchmarked candidate scores replaced; missing record keeps static scores and double-warns (unavailable + not-found); dependency failure does not escape and preserves scores; repeated model fetched once; inputs not mutated.

### Modified

* src/recommender/service.py - Added `qs_client: QualitySafetyBenchmarkSource | None = None` to `recommend_candidates`; applies `enrich_quality_safety` after pricing enrichment when a client is supplied; merges `qs_warnings` into `parse_warnings`. Backward compatible (default `None`).
* src/orchestrator/pipeline.py - Constructs `QualitySafetyBenchmarkSource` from `config/quality_safety_benchmarks.yaml` only under `_should_use_official_sources(...)` (else `None`), sharing the official-sources gate with the price client; threads `qs_client` into each `recommend_candidates` call.
* tests/unit/test_recommender_service.py - Added `_StubQualitySafetyClient`; added `RecommenderServiceQualitySafetyTests` verifying benchmark scores flow into ranking (score changes vs baseline for the benchmarked model, unlisted model preserved and warned) and that omitting `qs_client` surfaces no quality/safety warnings. Added imports for `QualitySafetyRecord` and `DependencyUnavailableError`.

## Additional or Deviating Changes

* Enrichment double-warns on an unknown model (one "quality/safety eval unavailable" from the caught fetch, one "quality/safety not found" from the subsequent `record is None` path).
  * This is the faithful mirror of the pricing twin's two-tier degradation (region-unavailable warning plus per-candidate not-found warning). Since the source contract raises for unknown models, the standalone "not found" path is only reachable if a client returns `None` without raising. Test expectations were aligned to this behavior rather than changing the mirrored pattern.
* Ranked results expose the shared `Candidate` contract, which does not carry `quality_score`/`safety_score`.
  * The service test therefore verifies enrichment via the observable ranking `score` (compared against a no-client baseline) plus surfaced warnings, rather than asserting on non-existent candidate attributes.

## Release Summary

Total files affected: 7 (5 added, 2 modified source/pipeline; 1 config added; 3 test files added/modified).

Created:
* config/quality_safety_benchmarks.yaml - curated-seed, non-authoritative benchmark data.
* src/recommender/quality_safety_source.py - benchmark record + source client.
* src/recommender/quality_safety_enrichment.py - non-fatal enrichment (pricing twin).
* tests/unit/test_quality_safety_source.py, tests/unit/test_quality_safety_enrichment.py - new coverage.

Modified:
* src/recommender/service.py - optional `qs_client` param and warning merge.
* src/orchestrator/pipeline.py - gated client construction and injection.
* tests/unit/test_recommender_service.py - service-level enrichment coverage.

Dependency and infrastructure changes: none. Zero new runtime dependencies (stdlib + existing `pyyaml` only).

Validation: `python -m pytest tests/unit -q` → 82 passed (69 baseline + 13 new).

Deferred (Phase 2, out of scope): offline `[evaluation]` refresh tool producing real content-safety/redteam-derived scores; authoritative benchmark coverage replacing curated seeds.
