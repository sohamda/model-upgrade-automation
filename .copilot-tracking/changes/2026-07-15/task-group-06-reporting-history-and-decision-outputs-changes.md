<!-- markdownlint-disable-file -->
# Release Changes: task-group-06-reporting-history-and-decision-outputs

**Related Plan**: task-group-06-reporting-history-and-decision-outputs.md
**Implementation Date**: 2026-07-15

## Summary

Implemented the TG6 local-first reporter path end to end: local artifact loading from TG4/TG5 outputs, deterministic aggregation and winner selection with explicit fallback seams, markdown report rendering, deferred publication payload generation, and a runnable reporter service with focused unit coverage.

## Changes

### Added

* src/reporter/__init__.py - Exported the local reporter service entrypoint
* src/reporter/models.py - Added typed reporter contracts for run inputs, candidates, thresholds, and dataset-hash validation
* src/reporter/artifact_loader.py - Added local TG4/TG5 artifact discovery and parsing with explicit dataset-hash mismatch reporting plus recommender metadata joins
* src/reporter/aggregator.py - Added retiring-target-scoped candidate aggregation with evaluator matrices, red-team breakdowns, and local fallback notes
* src/reporter/decision_engine.py - Added deterministic winner selection with hard safety filtering, block-rate filtering, and explicit cost/longevity fallback seams
* src/reporter/markdown_report.py - Added local markdown report rendering for ranked candidates, evaluator matrices, red-team results, warnings, and migration checklist output
* src/reporter/issue_payload.py - Added structured deferred GitHub issue payload generation
* src/reporter/remediation_payload.py - Added structured deferred remediation payload generation for draft-only publication later
* src/reporter/service.py - Added the end-to-end reporter service and local CLI output writer
* tests/unit/test_reporter_artifact_loader.py - Added a focused loader test for the staged `cli-test-run` artifact set and the known dataset-hash mismatch
* tests/unit/test_reporter_aggregator.py - Added aggregation coverage for evaluator and red-team matrix output
* tests/unit/test_reporter_decision_engine.py - Added winner-selection coverage for the staged local candidate set
* tests/unit/test_reporter_markdown_report.py - Added markdown report coverage for required TG6 sections and placeholders
* tests/unit/test_reporter_service.py - Added end-to-end local service coverage for reporter output writing
* .copilot-tracking/changes/2026-07-15/task-group-06-reporting-history-and-decision-outputs-changes.md - Recorded TG6 implementation progress

### Modified

* None

### Removed

* None

## Additional or Deviating Changes

* Cost delta and longevity remain placeholder seams in the local-first decision engine
  * The currently staged TG4/TG5 artifacts do not expose those inputs, so TG6 records neutral cost fallback and deterministic tie-break fallback notes instead of inventing hidden values
* GitHub issue publication and remediation PR mutation remain deferred
  * TG6 now emits structured local payloads for those operations without requiring live credentials or repository mutation

## Release Summary

TG6 can now load the real local `cli-test-run` dry-run and evaluator artifacts, compute a deterministic winner, surface the known dataset hash mismatch explicitly, render a local markdown report, and write deferred publication payloads under a local output directory. The remaining work is integration-only: wiring these outputs into live GitHub publication, richer cost and longevity sources, and any later Azure-backed artifact links or remediation branch mutation.