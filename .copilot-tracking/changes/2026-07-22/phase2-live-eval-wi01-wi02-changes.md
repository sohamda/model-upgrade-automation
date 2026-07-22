<!-- markdownlint-disable-file -->
# Release Changes: Phase 2 Live Evaluation (WI-01, WI-02)

**Related Plan**: phase2-quality-safety-eval-plan.instructions.md
**Implementation Date**: 2026-07-22

## Summary

Implemented the live evaluation body of `FoundryQualitySafetyEvalClient` (WI-01), added a
`--live` opt-in path to the benchmark refresh script, created a SHA-pinned OIDC CI workflow
for scheduled/dispatch benchmark refresh (WI-02), and added hermetic unit tests covering all
binding council conditions (C1, C7, C8, C9, C10, C11, C12, C13). No live Azure calls were
made; the stub remains the default and the recommender hot path still imports without the
`[evaluation]` extra.

## Changes

### Added

* .github/workflows/refresh-quality-safety-benchmarks.yml - Scheduled + dispatch benchmark refresh workflow with OIDC azure/login, SHA-pinned actions, opt-in live gating, and auto-PR staging only the benchmark YAML.
* .copilot-tracking/changes/2026-07-22/phase2-live-eval-wi01-wi02-changes.md - This changes log.
* .copilot-tracking/plans/logs/2026-07-22/phase2-live-eval-wi01-wi02-log.md - Planning log for discrepancies and follow-on work.

### Modified

* src/evaluator/quality_safety_eval_client.py - Live `FoundryQualitySafetyEvalClient` body: bounded-param validation before import guard, own-deployment scope lock, content-safety + red-team runs with C11 error→UNSCORED(None) mapping, min-sample-size defect-rate guard, aggregate-only signals with full provenance stamping.
* scripts/refresh_quality_safety_benchmarks.py - `--live`/`--dry-run` mutually exclusive group, `_select_client` live path resolving Foundry project + judge model, candidate/model cap enforcement, live provenance stamping (tuples→lists), seed fallback via `has_safety_signal`.
* config/azure.env.example - Added `FOUNDRY_PROJECT_ENDPOINT=` and `JUDGE_MODEL=` placeholders before the RunContext defaults block.
* tests/unit/test_quality_safety_eval_client.py - Added hermetic tests: import-without-extra guard, owned-target scope lock (no URL leak), defect-rate min-sample None guard, quality-score None exclusion, safety-signal presence, bounded-param ValueErrors, evaluate_model error→None mapping + provenance (class-level method patching for slots dataclass).
* tests/unit/test_refresh_quality_safety_benchmarks.py - Added hermetic tests: `--live`/`--dry-run` mutual exclusion + stub default, candidate cap enforcement, live build provenance stamping + seed fallback.

### Removed

* (none)

## Additional or Deviating Changes

* `mock.patch.object(client, ...)` on a `@dataclass(slots=True)` instance is read-only for methods; switched to class-level `mock.patch.object(FoundryQualitySafetyEvalClient, ...)` in the three `FoundryEvaluateModelTests` methods.
  * Reason: slots prevent per-instance method reassignment; class-level patching is isolated per test and always works.

## Release Summary

Files affected: 6 modified, 3 added.

- Code: `src/evaluator/quality_safety_eval_client.py`, `scripts/refresh_quality_safety_benchmarks.py`, `config/azure.env.example`.
- CI: `.github/workflows/refresh-quality-safety-benchmarks.yml`.
- Tests: `tests/unit/test_quality_safety_eval_client.py`, `tests/unit/test_refresh_quality_safety_benchmarks.py`.

Validation: `pytest tests/unit -q` → 128 passed in ~10s. Recommender hot-path import check → `IMPORT OK` without `[evaluation]` extra. No live Azure calls, no git commit, no `--live` refresh run performed.
