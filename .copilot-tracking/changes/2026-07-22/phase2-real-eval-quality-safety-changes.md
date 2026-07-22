<!-- markdownlint-disable-file -->
# Release Changes: Phase 2 — Real Eval Producer for Quality/Safety Benchmarks (Offline Seam)

**Related Plan**: phase2-real-eval-quality-safety-plan.instructions.md
**Implementation Date**: 2026-07-22

## Summary

Added an offline, import-guarded evaluator-client seam (`src/evaluator/quality_safety_eval_client.py`), a local manual refresh script that derives normalized quality/safety scores and rewrites `config/quality_safety_benchmarks.yaml` with additive provenance, a new `[evaluation]` optional dependency extra, a root `tests/conftest.py` that isolates ambient config env vars, and hermetic unit tests. The recommender runtime stays pyyaml-only and the consumer contract (`QualitySafetyBenchmarkSource`, `enrich_quality_safety`) is unchanged.

## Changes

### Added

* tests/conftest.py - Autouse function-scoped fixture clearing `DEPLOYMENT_TYPE` and `ALLOWED_REGIONS` so the suite is immune to ambient config env pollution.
* src/evaluator/quality_safety_eval_client.py - `RawEvalSignals` dataclass, `QualitySafetyEvalClient` Protocol, `StubQualitySafetyEvalClient` (deterministic, no third-party imports), import-guarded `FoundryQualitySafetyEvalClient` (raises `DependencyUnavailableError` when the `[evaluation]` extra is absent), and pure score helpers `clamp01`/`derive_quality_score`/`derive_safety_score`.
* scripts/refresh_quality_safety_benchmarks.py - Local manual producer with argparse (`--dry-run`, `--output`, `--models`, `--run-id`), stub-client default, additive provenance stamping (`source`, `run_id`, `evaluator_version`, `sdk_version`), and a non-mutating dry-run path that needs no Azure.
* tests/unit/test_quality_safety_eval_client.py - Tests for clamp/quality/safety formulas, stub determinism, and the Foundry import-guard raising `DependencyUnavailableError`.
* tests/unit/test_refresh_quality_safety_benchmarks.py - Hermetic tests for the refresh script: dry-run writes nothing, renders 8 valid entries with core + additive keys, and write mode produces parseable YAML.

### Modified

* pyproject.toml - Added `[project.optional-dependencies] evaluation` (`azure-ai-evaluation[redteam]>=1.18.1`, `azure-identity>=1.17`). Runtime `dependencies` left as pyyaml-only.
* tests/unit/test_quality_safety_source.py - Added a backward-compatibility test asserting `QualitySafetyBenchmarkSource.fetch_record` ignores the new additive provenance keys.

### Removed

* None.

## Additional or Deviating Changes

* DD-03: `scripts/refresh_quality_safety_benchmarks.py` inserts the repo root into `sys.path` before importing `src`.
  * Reason: pytest injects the repo root via `pythonpath=["."]`, but standalone execution (`python scripts/...`, the DoD dry-run path) does not, so the `from src...` import failed with `ModuleNotFoundError`. The guarded `sys.path.insert` keeps the DoD dry-run command working without changing runtime behavior.

## Release Summary

Six phases completed. Files created: 4 (`tests/conftest.py`, `src/evaluator/quality_safety_eval_client.py`, `scripts/refresh_quality_safety_benchmarks.py`, `tests/unit/test_quality_safety_eval_client.py`, `tests/unit/test_refresh_quality_safety_benchmarks.py` — 5 total). Files modified: 2 (`pyproject.toml`, `tests/unit/test_quality_safety_source.py`). No runtime dependency changes (pyyaml-only preserved); eval/red-team deps confined to the optional `[evaluation]` extra and never imported on the recommender hot path. Validation: `tests/unit` green at 106 passed both in a clean shell and with `DEPLOYMENT_TYPE=GlobalStandard` ambient; refresh `--dry-run` renders 8 provenance-stamped entries with no Azure and no file mutation; `import src.recommender.service` succeeds without the `[evaluation]` extra installed.
