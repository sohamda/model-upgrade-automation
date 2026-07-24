<!-- markdownlint-disable-file -->
# Release Changes: Live `--live` evaluator validation on ff-hub-01

**Related Plan**: real-quality-safety-gates-plan.instructions.md (2026-07-23)
**Implementation Date**: 2026-07-24

## Summary

Live end-to-end validation of the `--live` evaluator path (real judge-scored
quality + Content-Safety-gated red-team) against the two candidate deployments
already live on `ff-hub-01`, with an audit bundle and teardown of any ephemeral
resources. Cost-gated authorized run (hard cap $130, self-STOP at $20). No code
under `src/` is modified by this validation; only tracking artifacts and
possibly additive audit config (`config/evaluation.yaml judge_model_version`)
may change.

## Changes

### Added

* .copilot-tracking/changes/2026-07-24/real-quality-safety-gates-live-validation-changes.md - this changes log
* .copilot-tracking/plans/logs/2026-07-24/real-quality-safety-gates-live-validation-log.md - planning/discrepancy log for the live run

### Modified

* (none yet)

### Removed

* (none yet)

## Additional or Deviating Changes

* Pre-flight verification completed with $0 spend (all read-only Azure calls):
  * Identity: user `iam.soham@...` (redacted), tenant `1d97...` (redacted), sub `84b8...` (redacted).
  * ff-hub-01 verified: AIServices, publicNetworkAccess Enabled, project ff-proj-001.
  * Both candidate deployments live at DataZoneStandard cap 1: gpt-5.1 (`tg4-...-gpt-5-1-2025-11-13`) and o3 (`tg4-...-o3-2025-04-16`).
  * Baseline gpt-5.6-sol (cap 238) and gpt-4.1 (cap 1496) also live.
  * Staged artifact-root `artifacts/mua-30008492713-1/` confirmed → exactly 2 work items; Codestral excluded (provision failed); relative-to-retiring gate will be SKIPPED (input_builder supplies no baseline scores).
  * Data-plane RBAC on ff-hub-01 confirmed: Cognitive Services OpenAI User, Azure AI Developer, Foundry Account Owner, Foundry Owner (+ Owner at subscription).
  * Content Safety data plane available on the ff-hub-01 account host — no ephemeral Content Safety resource required.
* BLOCKER surfaced as PD-01 (see planning log): the quality seam cannot drive an o-series reasoning judge, and the only OpenAI-format non-gpt/non-o3 chat models on ff-hub-01 are reasoning models (o1, o4-mini). This threatens "REAL judge-scored quality" for the gpt-5.1 candidate. Paused for user decision before any spend.

## Release Summary

_Pending — populated after the live run and teardown complete._
