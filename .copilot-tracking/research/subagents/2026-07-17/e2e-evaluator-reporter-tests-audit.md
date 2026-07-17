<!-- markdownlint-disable-file -->
---
title: E2E Evaluator Reporter Tests Audit
description: Read-only audit of the provisioned-suggestions evaluation and reporting path
ms.date: 2026-07-17
---

## Scope

Audit the end-to-end requested flow: provisioned suggestions are evaluated and the
results are reported. The audit covers `src/evaluator`, `src/reporter`, adjacent
orchestration and provisioning code, relevant tests, and the existing validation
scripts.

## Research Questions

1. Which evaluation and reporting capabilities are implemented, with exact source
   locations?
2. Which tests validate detector, recommender, provisioner, evaluator, and reporter
   integration?
3. Which gaps block an end-to-end run for the top three recommendations?
4. Which existing scripts or commands validate the partial and full paths today?

## Initial Hypothesis

`src/evaluator.service.execute_local_evaluation` can consume the TG4 provisioner
preview artifacts and persist TG5 results, and `src/reporter.service.execute_local_report`
can consume both artifacts. The main pipeline likely stops after provision-plan staging,
so no single supported command executes detector through reporter in one run.

## Implemented Evaluation and Reporting Capabilities

The source implements an artifact-driven local sequence. `execute_dry_run` invokes
detector, recommender, and provisioner services for every retiring target, then stages
the detector, recommender, provisioner, manifest, and combined dry-run artifacts.
The evaluator derives one work item per provision request and writes custom, red-team,
and summary results. The reporter rehydrates the TG4 and TG5 artifacts, aggregates
scores, makes a deterministic decision, and writes a Markdown report plus three JSON
payload types.

| Capability | Evidence |
|---|---|
| Detector through recommender through provision-plan orchestration | `src/orchestrator/pipeline.py:97` calls detector, recommender, and provisioner at `src/orchestrator/pipeline.py:107-142` |
| TG4 artifact staging | `src/orchestrator/pipeline.py:50-94` writes the component artifacts, `history_preview.json`, and `dry_run_output.json` |
| Candidate-count configuration | `config/evaluation.yaml:2` sets `candidates_per_retiring_model: 3`; `src/recommender/service.py:15-49` ranks then limits candidates |
| Provision request and teardown creation | `src/provisioner/service.py:12-26` creates one provision request and teardown plan for every ranked candidate |
| TG4-to-TG5 work-item construction | `src/evaluator/input_builder.py:112-216` loads dry-run/history artifacts, validates manifests and skip-index keys, and maps provision requests to evaluator work items |
| Local custom evaluation | `src/evaluator/custom_runner.py:9-68` generates deterministic per-row quality/safety scores and aggregates |
| Local red-team evaluation | `src/evaluator/redteam_runner.py:9-57` generates deterministic attack-category block rates |
| Evaluator orchestration and result summary | `src/evaluator/service.py:25-109` runs both local evaluators, records an ACA request shape, and writes one result set per work item |
| TG5 result persistence | `src/evaluator/result_writer.py:11-51` writes `custom.json`, `redteam.json`, and `summary.json` under `results/<run-id>/<candidate-slug>/` |
| TG5-to-TG6 artifact loading | `src/reporter/artifact_loader.py:53-218` joins each provision request with TG5 result files and recommender rank/rationale |
| Aggregate score and warning construction | `src/reporter/aggregator.py:25-108` builds per-candidate evaluator/red-team matrices and surfaces local fallbacks |
| Hard-threshold decision and ranking | `src/reporter/decision_engine.py:7-118` rejects candidates below safety, block-rate, or custom-score thresholds and selects a winner from passing candidates |
| Human-readable report rendering | `src/reporter/markdown_report.py:18-131` renders ranking, evaluator/red-team matrices, warnings, artifact paths, and checklist |
| TG6 report and structured payload persistence | `src/reporter/service.py:35-93` writes Markdown, decision, issue-payload, and remediation-payload files |

## Integration Test Map

| Stage boundary | Existing test evidence | Coverage assessment |
|---|---|---|
| Detector | `tests/unit/test_detector_service.py:20-57` validates fixture normalization and unmatched-signal warning | Unit only |
| Recommender | `tests/unit/test_recommender_service.py:20-65` validates deterministic ranking and no-match warning | Unit only; fixture has two candidates |
| Provisioner | `tests/unit/test_provisioner_service.py:19-101` validates stable idempotency and required tags | Unit only |
| Detector to recommender to provisioner | `tests/unit/test_orchestrator_cli.py:21-127` calls `execute_dry_run` and validates staged detector/recommender/provisioner/history artifacts | This is the only direct integration test across the first three stages |
| Provisioned suggestions to evaluator results | `tests/unit/test_evaluator_service.py:21-47` consumes a prebuilt TG4 fixture and materializes two TG5 result sets | Does not invoke detector, recommender, or provisioner in the test |
| Evaluated results to reporter outputs | `tests/unit/test_reporter_service.py:17-39` consumes prebuilt TG4/TG5 fixtures and checks Markdown/JSON output files | Does not invoke evaluator in the test |
| Reporter artifact/aggregation/decision behavior | `tests/unit/test_reporter_aggregator.py:17-34` and `tests/unit/test_reporter_decision_engine.py:18-36` validate the two-candidate fixture and its no-winner result | Reporter-only integration slice |
| Fixture contract load | `scripts/run_tg8_full.py:200-255` invokes `load_reporter_run_input` over static fixture artifacts as `QG-INT-01` | Verifies read compatibility, not detector through reporter execution |

No existing test invokes `execute_dry_run`, `execute_local_evaluation`, and
`execute_local_report` in a single test run. No workflow calls any of these service or
CLI entry points.

## Exact Gaps Blocking an End-to-End Top-Three Run

1. The GitHub Actions entry workflow is still a placeholder. Although it accepts a
   `candidate_limit` with default `3` at `.github/workflows/detect-and-eval.yml:13-18`
   and resolves it at `.github/workflows/detect-and-eval.yml:99-100`, its only
   orchestration step writes `placeholder-complete` JSON at
   `.github/workflows/detect-and-eval.yml:323-358`. It does not call the TG4, TG5, or
   TG6 CLIs. This blocks scheduled/manual end-to-end execution.
2. The evaluator does not provision a real deployment or run an Azure-backed
   evaluation. `src/evaluator/service.py:45-107` only builds an ACA request and returns
   `aca_dispatch_status: deferred-local-only`; `src/evaluator/aca_job.py:21-40`
   explicitly throws if dispatch is attempted. The current custom/red-team adapters are
   fake-backed deterministic generators at `src/evaluator/custom_runner.py:9-68` and
   `src/evaluator/redteam_runner.py:9-57`. This blocks a real evaluation of provisioned
   suggestions.
3. The canonical local end-to-end fixture contains only two recommendations and two
   provision requests, not three. See
   `tests/fixtures/hermetic_repo/artifacts/cli-test-run/dry_run_output.json:90-174` and
   `tests/fixtures/hermetic_repo/artifacts/cli-test-run/dry_run_output.json:177-231`.
   Reporter and evaluator service tests therefore validate two candidates only. The
   configuration can request three, but no three-candidate fixture/test demonstrates
   correct top-three construction, result persistence, thresholding, or reporting.
4. Report publication is local-only. `src/reporter/models.py:161-190` labels issue and
   remediation payloads `deferred-local-only`; `src/reporter/service.py:58-75` writes
   them to disk and never creates an issue or pull request. This does not block local
   report generation but blocks the requested flow if "reported" includes external
   publication.
5. Decision quality remains intentionally incomplete for local runs. The aggregation
   uses neutral cost and deterministic rank/slug fallback for longevity at
   `src/reporter/aggregator.py:52-59`, and the decision engine repeats that fallback at
   `src/reporter/decision_engine.py:45-54`. The result is auditable but not a complete
   cost/longevity-backed production recommendation.

## Minimum Existing Validation Commands

These commands were identified but not run because this was a read-only audit and the
service commands write under `artifacts/` or `results/`.

| Scope | Existing command | What it validates |
|---|---|---|
| Broadest automated regression check | `python -m pytest -q tests/unit` | The CI command at `.github/workflows/ci.yml:69-76`; includes all evaluator/reporter unit and service-slice tests |
| TG4 partial path | `python -m src.orchestrator.cli --run-id <run-id>` | Detector, recommender, provisioner, history, and dry-run artifact staging; CLI at `src/orchestrator/cli.py:19-76` |
| TG5 partial path | `python -m src.evaluator.service --artifact-root artifacts/<run-id> --dataset tests/fixtures/evaluator/dataset.sample.jsonl` | Local evaluator result materialization; CLI at `src/evaluator/service.py:112-163` |
| TG6 partial path | `python -m src.reporter.service --artifact-root artifacts/<run-id> --output-root artifacts/<run-id>/reporter` | Local report, decision, issue payload, and remediation payload generation; CLI at `src/reporter/service.py:97-167` |
| Fixture integration contract | `python scripts/run_tg8_full.py --skip-gh-check` | TG8 `QG-INT-01` rehydrates the static reporter fixture; it does not execute TG4/TG5 |
| Static prerequisite check | `python scripts/validate_tg3_contracts.py` | Workflow/configuration contract validation, not evaluator/reporter behavior |

For a current local artifact-driven sequence, run the TG4, TG5, and TG6 commands in
that order using the same `<run-id>`. There is no existing one-command full-path
runner, and a generated top-three run requires a catalog that yields three eligible
candidates plus real evaluator/provisioning implementations for production fidelity.

## Validation Status

The research artifact was created and checked with workspace diagnostics, which
reported no errors. No runtime commands were executed in this read-only audit because
the available tool surface does not expose a terminal runner and the mutation-free
scope excludes creating generated artifacts.

## References

* Codebase evidence is cited inline as workspace-relative `path:line` references.
* No external sources were used; the audit concerns repository implementation and
  existing fixtures only.
