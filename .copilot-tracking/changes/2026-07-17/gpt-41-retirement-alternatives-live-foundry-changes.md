<!-- markdownlint-disable-file -->
# Release Changes: GPT-4.1 Retirement Alternatives Live Foundry Flow

**Related Plan**: gpt-41-retirement-alternatives-live-foundry-plan.instructions.md
**Implementation Date**: 2026-07-17

## Summary

Implementing live retirement/candidate discovery, explicit CLI inputs, safe opt-in provisioning and evaluation gates, workflow wiring, and targeted tests/docs updates.

## Changes

### Added

* src/detector/retirement_schedule_source.py - Added live Microsoft Learn retirement schedule adapter with robust table parsing and actionable failures.
* src/detector/deployed_introspector.py - Added Azure CLI based Foundry deployment discovery for `--discover-from-azure` mode.
* src/recommender/foundry_catalog_source.py - Added live Microsoft Learn model catalog adapter for current candidate retrieval.
* tests/unit/test_retirement_schedule_source.py - Added parser unit coverage for retirement adapter.
* tests/unit/test_foundry_catalog_source.py - Added parser unit coverage for live catalog adapter.
* tests/unit/test_deployed_introspector.py - Added discovery adapter normalization test.
* tests/unit/test_pipeline_runtime_gates.py - Added runtime gate tests for top-k and eval/provision safety rules.

### Modified

* src/orchestrator/cli.py - Added required CLI flags for explicit retiring target, live retrieval toggles, safety gates, and top-k selection.
* src/orchestrator/pipeline.py - Added runtime option wiring, live source selection, Azure discovery integration, top-k enforcement, opt-in provisioning/eval execution, and explicit safety payloads.
* src/shared/config.py - Added RuntimeOptions contract for pipeline runtime controls.
* src/shared/contracts.py - Extended CandidateRank for rejection-reason compatibility.
* src/detector/service.py - Enabled explicit CLI target passthrough mode.
* src/recommender/service.py - Fixed candidate limit handling to deterministic integer cap.
* src/provisioner/service.py - Added MVP provisioning execution path and teardown-plan persistence while preserving dry-run plan behavior.
* tests/unit/test_orchestrator_cli.py - Added coverage for new CLI flags and safety-gate failure surface.
* .github/workflows/detect-and-eval.yml - Wired live orchestrator CLI invocation and added explicit live/provision/eval workflow inputs.
* README.md - Added exact commands and required environment variables for safe and live user scenarios.

### Removed

## Additional or Deviating Changes

* MVP live adapters currently parse Learn pages heuristically; parser governance and source-shape hardening remain follow-on work.
	* Enables end-to-end behavior now while preserving fail-closed errors on parse or retrieval failures.

## Release Summary

