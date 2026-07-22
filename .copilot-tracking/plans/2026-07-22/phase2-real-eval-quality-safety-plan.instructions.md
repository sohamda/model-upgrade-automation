---
applyTo: '.copilot-tracking/changes/2026-07-22/phase2-real-eval-quality-safety-changes.md'
---
<!-- markdownlint-disable-file -->
# Implementation Plan: Phase 2 — Real Eval Producer for Quality/Safety Benchmarks (Offline Seam)

## Overview

Build an offline, import-guarded evaluator-client seam plus a local refresh script that derives quality/safety scores and rewrites the cached `config/quality_safety_benchmarks.yaml`, keeping the recommender runtime pyyaml-only and the consumer contract unchanged.

## Objectives

### User Requirements

* Build the refresh tool + an injectable eval-client seam now; DEFER live Azure wiring — Source: user locked decision 1.
* Scope model seed to the current 8 models in `config/quality_safety_benchmarks.yaml` — Source: user locked decision 2.
* Execution surface = local manual script only (`scripts/refresh_quality_safety_benchmarks.py`); NO CI — Source: user locked decision 3.
* Keep runtime deps pyyaml-only; put eval/red-team deps in a new `[evaluation]` optional extra, import-guarded — Source: user hard constraints + research "Offline ≠ Air-Gapped".
* Preserve the runtime consumer contract (`QualitySafetyBenchmarkSource`, `enrich_quality_safety`) reading cached YAML unchanged; only the producer changes — Source: user hard constraints.
* Write provenance into YAML additively without breaking the existing parser — Source: user hard constraints.
* Add root `tests/conftest.py` clearing ambient config env vars first — Source: user must-include work item 0 + research Q6.

### Derived Objectives

* Place the new seam in `src/evaluator/` alongside existing local-fake runners — Derived from: repo layout (`src/evaluator/redteam_runner.py`, `service.py`) already hosts evaluator adapters; no `azure-ai-evaluation` import exists anywhere in `src` (verified).
* Keep score derivation as pure, injected-client-free functions — Derived from: user requirement that helpers be unit-testable with no network.
* Add additive-only YAML keys (`source`, `run_id`, `evaluator_version`, `sdk_version`) — Derived from: parser reads only 5 keys via `.get()`; extra keys are ignored (verified in `quality_safety_source.py`).

## Context Summary

### Project Files

* config/quality_safety_benchmarks.yaml - 8-model curated seed; top-level `benchmarks:` list; producer target of this phase.
* src/recommender/quality_safety_source.py - `QualitySafetyBenchmarkSource` parser; reads only model_id/quality_score/safety_score/provenance/as_of_date via `.get()`; UNCHANGED.
* src/recommender/quality_safety_enrichment.py - `enrich_quality_safety` consumer; UNCHANGED.
* src/shared/errors.py - `DependencyUnavailableError` to raise for missing optional deps.
* src/shared/config.py - `load_app_config` reads config env vars via `_resolve_env_value` (OS overrides file default).
* src/shared/run_context.py - reads `GITHUB_*` and `RUN_ID`.
* src/evaluator/models.py - existing evaluator dataclass conventions to mirror (`@dataclass(slots=True)`).
* pyproject.toml - runtime deps = pyyaml only; `[project.optional-dependencies]` has `test` only.
* tests/unit/test_quality_safety_source.py - unittest.TestCase style + tmp-dir YAML fixtures to mirror.

### References

* .copilot-tracking/research/2026-07-22/phase2-real-eval-quality-safety-research.md - formulas, dependency footprint, offline architecture, open decisions.
* .copilot-tracking/research/subagents/2026-07-22/pytest-env-isolation-conftest.md - autouse env-clearing fixture pattern.

### Standards References

* .github/copilot-instructions.md - repo code style (`from __future__ import annotations`, `@dataclass(slots=True)`, type hints, module docstrings, hermetic tests).

### Verified Ambient Config Env Vars (work item 0 evidence)

`load_app_config` (`src/shared/config.py`, OS env overrides `azure.env.example` defaults): `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `RESOURCE_GROUP`, `FOUNDRY_ACCOUNT_NAME`, `FOUNDRY_PROJECT_NAME`, `ACA_ENVIRONMENT_NAME`, `ACA_JOB_NAME`, `STORAGE_ACCOUNT_NAME`, `KEY_VAULT_NAME`, `DEPLOYMENT_TYPE`, `ALLOWED_REGIONS`, `RETIREMENT_HORIZON_DAYS`, `CANDIDATES_PER_RETIRING_MODEL`, `ENABLE_AUTO_PR`, `AUTOMATION_OWNERSHIP_TAG`, `AUTOMATION_SCOPE_TAG`, `MANAGED_BY_TAG`, `AUTOMATION_CLEANUP_TAG`. `build_run_context` (`src/shared/run_context.py`): `GITHUB_REPOSITORY`, `GITHUB_EVENT_NAME`, `RUN_ID`, `GITHUB_RUN_ID`. Only `DEPLOYMENT_TYPE` and `ALLOWED_REGIONS` are read WITHOUT a fallback (raise `ConfigurationError` when absent) and are the confirmed polluters (terminal evidence + research Q6). No root `tests/conftest.py` currently exists (only skill-scoped ones under `.agents/skills/`).

## Implementation Checklist

### [x] Implementation Phase 1: Test Env Isolation

<!-- parallelizable: true -->

* [x] Step 1.1: Create root `tests/conftest.py` with autouse fixture clearing `DEPLOYMENT_TYPE` + `ALLOWED_REGIONS`
  * Details: .copilot-tracking/details/2026-07-22/phase2-real-eval-quality-safety-details.md (Lines 12-40)
* [x] Step 1.2: Validate phase changes
  * Run `.venv/Scripts/python.exe -m pytest tests/unit -q` with `DEPLOYMENT_TYPE`/`ALLOWED_REGIONS` set in shell; expect green (isolation works)

### [x] Implementation Phase 2: Optional Evaluation Extra

<!-- parallelizable: true -->

* [x] Step 2.1: Add `[project.optional-dependencies] evaluation` to `pyproject.toml`; leave runtime deps untouched
  * Details: .copilot-tracking/details/2026-07-22/phase2-real-eval-quality-safety-details.md (Lines 42-64)

### [x] Implementation Phase 3: Eval Client Seam + Score Helpers

<!-- parallelizable: true -->

* [x] Step 3.1: Create `src/evaluator/quality_safety_eval_client.py` (interface + raw-signals dataclass + real impl + stub impl)
  * Details: .copilot-tracking/details/2026-07-22/phase2-real-eval-quality-safety-details.md (Lines 66-120)
* [x] Step 3.2: Add pure score-derivation helpers (`clamp01`, `derive_quality_score`, `derive_safety_score`) in the same module
  * Details: .copilot-tracking/details/2026-07-22/phase2-real-eval-quality-safety-details.md (Lines 122-150)

### [x] Implementation Phase 4: Refresh Script

<!-- parallelizable: false -->

* [x] Step 4.1: Create `scripts/refresh_quality_safety_benchmarks.py` (argparse, injected client, `--dry-run` stub, provenance-stamped YAML writer)
  * Details: .copilot-tracking/details/2026-07-22/phase2-real-eval-quality-safety-details.md (Lines 152-210)

### [x] Implementation Phase 5: Hermetic Tests

<!-- parallelizable: false -->

* [x] Step 5.1: `tests/unit/test_quality_safety_eval_client.py` — helper formulas, clamping, worst-of-signals, missing-dep raises
  * Details: .copilot-tracking/details/2026-07-22/phase2-real-eval-quality-safety-details.md (Lines 212-244)
* [x] Step 5.2: `tests/unit/test_refresh_quality_safety_benchmarks.py` — stub-client run asserts YAML shape + provenance + 8 entries
  * Details: .copilot-tracking/details/2026-07-22/phase2-real-eval-quality-safety-details.md (Lines 246-274)
* [x] Step 5.3: Backward-compat test — `QualitySafetyBenchmarkSource` parses YAML carrying new additive provenance fields
  * Details: .copilot-tracking/details/2026-07-22/phase2-real-eval-quality-safety-details.md (Lines 276-300)

### [x] Implementation Phase 6: Validation

<!-- parallelizable: false -->

* [x] Step 6.1: Run full unit suite: `.venv/Scripts/python.exe -m pytest tests/unit -q` — expect green
* [x] Step 6.2: Smoke the refresh script: `.venv/Scripts/python.exe scripts/refresh_quality_safety_benchmarks.py --dry-run` — writes/echoes 8 provenance-stamped entries, no Azure
* [x] Step 6.3: Report any blocking issue requiring further research; avoid large-scale fixes inline

## Planning Log

See .copilot-tracking/plans/logs/2026-07-22/phase2-real-eval-quality-safety-log.md for discrepancy tracking, implementation paths considered, and suggested follow-on work.

## Dependencies

* Python 3.12 venv at `.venv` with editable install and `[test]` extra (existing).
* `[evaluation]` extra is NOT installed for unit tests; the seam must import-guard it.

## Success Criteria

* Root `tests/conftest.py` isolates `DEPLOYMENT_TYPE`/`ALLOWED_REGIONS`; suite green with those vars set — Traces to: user work item 0.
* `[evaluation]` extra added; runtime deps remain pyyaml-only — Traces to: user hard constraints.
* Eval-client seam is injectable; real impl raises `DependencyUnavailableError` without the extra; recommender hot path imports none of it — Traces to: user work item 2.
* Refresh script rewrites the 8 entries with additive provenance; `--dry-run` needs no Azure — Traces to: user work items 3.
* `QualitySafetyBenchmarkSource` still parses the new YAML; existing `tests/unit` stay green — Traces to: user work items 4-5.
