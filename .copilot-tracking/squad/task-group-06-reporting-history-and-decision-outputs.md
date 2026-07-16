---
title: Task Group 6 Reporting History and Decision Outputs
description: Execution-ready implementation artifact for the TG6 local-first reporter surface and decision-output sequencing
ms.date: 2026-07-15
ms.topic: reference
---
<!-- markdownlint-disable-file -->

# Task Group 6: Reporting, History, and Decision Outputs

## Ownership

* Lead: Kenny (Python Delivery Lead)
* Support: Wendy (Evaluation + Quality Engineer)
* Support: Cartman (MVP Product/Tech Integrator)

## Objective

Deliver the missing `src/reporter/` surface that consumes TG4 dry-run and history artifacts plus TG5 evaluator outputs, computes winner decisions deterministically, and produces local-first reporting outputs that are ready for later GitHub publication and release-gated remediation flows.

TG6 is the first group that turns pipeline and evaluator artifacts into stakeholder-facing decision outputs. It must fully separate what can be completed and validated locally now from what remains dependent on Azure-live data access, GitHub publishing, or later release approvals.

## Current local execution baseline (2026-07-15)

Completed locally in this repository state:

* TG4 emits `artifacts/<run_id>/dry_run_output.json` and `artifacts/<run_id>/history_preview.json` with retiring target, ranked candidates, provision plans, artifact manifests, and skip-index keys.
* TG5 emits per-candidate `custom.json`, `redteam.json`, and `summary.json` under `results/<run_id>/<candidate>/`.
* `requirements/plan.md` already freezes reporter responsibilities, winner logic, markdown report shape, and opt-in remediation PR behavior.
* TG1 already freezes the ownership boundary that `src/reporter` owns aggregation, recommendation, markdown, and GitHub outputs.

Still deferred beyond local-first completion:

* GitHub Issue publication, PR creation, and branch mutation against a live repository token or app identity.
* Blob-backed artifact links and any Azure-live history lookup beyond the local preview files.
* Release-gated remediation patch publication and any human approval workflows for rollout.
* Weekly production publishing behavior validation under the real CI workflow.

## Scope

In scope:

* Create the initial `src/reporter/` package and its test surface.
* Read and validate TG4 dry-run artifacts from `artifacts/<run_id>/`.
* Read and validate TG5 evaluator artifacts from `results/<run_id>/<candidate>/`.
* Aggregate candidate-level evaluation results into a comparison matrix per retiring model.
* Implement deterministic winner selection according to `requirements/plan.md`.
* Render a local markdown report with the required sections and recommendation narrative.
* Generate structured local decision-output payloads that later GitHub and remediation publishers can consume.
* Define stable adapter seams for GitHub issue updates, markdown PR publication, and remediation PR drafting without requiring those live integrations now.

Out of scope:

* Any change to TG4 detector, recommender, provisioner, or history contracts unless a hard contract defect is proven.
* Any change to TG5 evaluator scoring logic or ACA execution behavior.
* Live GitHub publication, branch creation, label management, or PR mutation.
* Azure-live Blob/Table reads and writes beyond consuming the already-staged local artifacts.
* Production rollout automation, APIM changes, or automatic model switching.

## Non-goals

* Do not re-open the TG1 reporting architecture or winner-policy decisions.
* Do not couple reporting logic directly to GitHub Actions YAML.
* Do not require Azure credentials or GitHub credentials for local report generation.
* Do not hide deferred publishing work behind incomplete local implementations.

## Dependency baseline

### Required upstream inputs already present locally

TG6 is allowed to start because the following dependency surfaces are already available in source control or local artifacts:

* `.copilot-tracking/squad/task-group-01-architecture-blueprint.md`
* `.copilot-tracking/squad/task-group-04-core-pipeline-implementation.md`
* `.copilot-tracking/squad/task-group-05-evaluation-engine-experiment-execution.md`
* `requirements/plan.md`
* `artifacts/cli-test-run/dry_run_output.json`
* `artifacts/cli-test-run/history_preview.json`
* `results/cli-test-run/gpt-4-1-2026-01-12/custom.json`
* `results/cli-test-run/gpt-4-1-2026-01-12/redteam.json`
* `results/cli-test-run/gpt-4-1-2026-01-12/summary.json`
* `results/cli-test-run/gpt-4-1-nano-2026-02-01/custom.json`
* `results/cli-test-run/gpt-4-1-nano-2026-02-01/redteam.json`
* `results/cli-test-run/gpt-4-1-nano-2026-02-01/summary.json`

### Key contracts imported from TG1 and requirements

TG6 must preserve these already-defined contracts:

* `src/reporter` owns aggregation, recommendation, markdown, and GitHub outputs.
* Winner logic follows the ordered filters and tie-breaks in `requirements/plan.md`:
  1. Filter out candidates below hard safety threshold.
  2. Filter out candidates below minimum red-team block rate.
  3. Score remaining candidates by weighted CE score minus weighted cost.
  4. Tie-break by longevity.
* Markdown report must include retiring model context, ranked candidates table, per-evaluator score matrix, red-team results, cost delta, recommendation rationale, artifact links, and migration checklist.
* Remediation output remains opt-in, draft-only, and never auto-merged.

## Current handoff status from TG4 and TG5

### TG4 handoff status

The TG4 local dry-run outputs already satisfy the minimum reporting input contract for local-first implementation:

* `dry_run_output.json` contains retiring targets, ranked candidates, provision requests, teardown plans, run context, and local history manifest references.
* `history_preview.json` contains manifest metadata and skip-index keys that the reporter can display or echo in local outputs.
* Candidate identity is stable enough locally to join TG4 provision-plan candidates with TG5 result directories by candidate slug or model/version tuple.

TG6 implication:

* Kenny can implement deterministic aggregation and report rendering now without waiting for Azure Blob or Table access.
* Local report generation should treat TG4 staged files as the canonical history source until Azure-backed history adapters are needed.

### TG5 handoff status

The TG5 local evaluator outputs already satisfy the minimum decision-input contract for local-first implementation:

* Each candidate directory contains `custom.json`, `redteam.json`, and `summary.json`.
* `summary.json` contains the immediate winner-decision inputs required for MVP comparison: candidate identity, retiring model identity, aggregate custom score, aggregate red-team block rate, thresholds, run id, and local completion status.
* TG5 explicitly deferred GitHub publication and Azure-live execution, which keeps the reporter free to implement a pure local-first path first.

TG6 implication:

* The first reporting slice should aggregate `summary.json` as the primary decision surface.
* The second reporting slice should enrich that aggregate with details from `custom.json` and `redteam.json` for markdown matrices and diagnostics.

### Known contract gaps and local assumptions

These are not blockers for starting TG6, but they must be called out explicitly:

* `src/reporter/` does not exist yet in the repository and must be created from scratch.
* The current local `summary.json` files contain a `dataset_sha256` value that does not match the `dataset_sha256` stored in TG4 `run_context`, while `aca_job_request.dataset_sha256` still reflects the TG4 value. TG6 must not silently assume those hashes are identical.
* Cost delta and longevity inputs are defined in `requirements/plan.md`, but the currently staged local result summaries do not yet expose a full cost model or explicit longevity field. TG6 should implement the scoring seam and render placeholders or derived local approximations where the inputs are not yet available.

## Proposed package and support structure

TG6 should create the following initial reporter surface.

```text
src/
  reporter/
    __init__.py
    models.py
    artifact_loader.py
    aggregator.py
    decision_engine.py
    markdown_report.py
    issue_payload.py
    remediation_payload.py
    service.py

tests/
  fixtures/
    reporter/
      dry-run.sample.json
      history-preview.sample.json
      summary.gpt-4-1.sample.json
      summary.gpt-4-1-nano.sample.json
      custom.gpt-4-1.sample.json
      redteam.gpt-4-1.sample.json
      expected-report.md
  unit/
    test_reporter_artifact_loader.py
    test_reporter_aggregator.py
    test_reporter_decision_engine.py
    test_reporter_markdown_report.py
    test_reporter_service.py
    test_reporter_issue_payload.py
    test_reporter_remediation_payload.py
```

### Structure notes

* `artifact_loader.py` should own discovery and parsing of TG4 and TG5 local artifacts.
* `aggregator.py` should build retiring-model-scoped comparison datasets from the raw files.
* `decision_engine.py` should hold the deterministic winner logic and produce explicit exclusion reasons.
* `markdown_report.py` should render a local markdown file without assuming GitHub publication.
* `issue_payload.py` should build a pure data payload for the weekly summary issue rather than mutating GitHub directly.
* `remediation_payload.py` should emit a draftable patch/intention payload only, not a live PR.
* `service.py` should orchestrate local loading, aggregation, decisioning, and output writing behind one stable entrypoint.

## Ordered implementation slices

### Slice 0: Reporter contract skeleton and artifact ingestion

Goal:

* Establish the reporter boundary and make TG4 and TG5 local artifacts readable through one consistent contract.

Files:

* `src/reporter/__init__.py`
* `src/reporter/models.py`
* `src/reporter/artifact_loader.py`
* `tests/fixtures/reporter/dry-run.sample.json`
* `tests/fixtures/reporter/history-preview.sample.json`
* `tests/fixtures/reporter/summary.gpt-4-1.sample.json`
* `tests/fixtures/reporter/summary.gpt-4-1-nano.sample.json`
* `tests/unit/test_reporter_artifact_loader.py`

Must implement:

* Typed reporter input models for retiring-model context, candidate summaries, history manifests, and decision-ready aggregates.
* Filesystem discovery of `artifacts/<run_id>/...` and `results/<run_id>/<candidate>/...`.
* Validation errors for missing or mismatched local artifacts, including explicit handling for dataset hash mismatches.

Exit criteria:

* Reporter code can load the current `cli-test-run` artifact set deterministically.
* Failures are explicit and actionable rather than deferred to downstream logic.

### Slice 1: Aggregation and winner-decision engine

Goal:

* Convert loaded artifact sets into retiring-model-scoped comparison datasets and deterministic recommendation decisions.

Files:

* `src/reporter/aggregator.py`
* `src/reporter/decision_engine.py`
* `tests/unit/test_reporter_aggregator.py`
* `tests/unit/test_reporter_decision_engine.py`

Must implement:

* Candidate comparison matrix assembly from `summary.json` plus optional detail enrichment from `custom.json` and `redteam.json`.
* Winner filtering and ranking rules aligned to `requirements/plan.md`.
* Explicit candidate rejection reasons for threshold failures.
* Deterministic behavior when cost delta or longevity inputs are unavailable locally.

Exit criteria:

* The local `cli-test-run` data yields one reproducible recommendation result.
* Every excluded candidate has a machine-readable reason.

### Slice 2: Local markdown report generation

Goal:

* Render the stakeholder-facing markdown report fully locally with no GitHub or Azure dependency.

Files:

* `src/reporter/markdown_report.py`
* `tests/fixtures/reporter/expected-report.md`
* `tests/unit/test_reporter_markdown_report.py`

Must implement:

* Report sections required by `requirements/plan.md`.
* Ranked candidates table, recommendation rationale, red-team summary, migration checklist, and local artifact references.
* Clear local placeholders where Blob URLs or production publication links are not yet available.

Exit criteria:

* A report can be rendered locally for the current run and compared against an expected fixture shape.
* The local report clearly distinguishes decision-ready content from deferred publish-only links.

### Slice 3: Decision-output payloads for GitHub and remediation adapters

Goal:

* Produce publish-ready payloads without performing live publication.

Files:

* `src/reporter/issue_payload.py`
* `src/reporter/remediation_payload.py`
* `tests/unit/test_reporter_issue_payload.py`
* `tests/unit/test_reporter_remediation_payload.py`

Must implement:

* Structured weekly summary issue payload builder.
* Structured remediation draft payload builder for Bicep patch generation inputs.
* Explicit draft-only and later-gate markers on remediation outputs.

Exit criteria:

* TG6 emits stable payload objects that a later publisher can submit without changing decision logic.
* No live GitHub mutation is required for validation.

### Slice 4: Reporter service entrypoint and local output writing

Goal:

* Provide one local-first execution path that writes report and decision artifacts to disk.

Files:

* `src/reporter/service.py`
* `tests/unit/test_reporter_service.py`

Must implement:

* End-to-end orchestration from artifact loading through output writing.
* Local output directory and filename conventions for markdown and decision payloads.
* Stable service return shape that upstream orchestration or future GitHub publishers can consume.

Exit criteria:

* TG6 can run entirely locally against staged TG4 and TG5 outputs.
* One invocation produces deterministic markdown and structured decision outputs.

### Slice 5: Live-publish seam and deferred release-gate checklist

Goal:

* Freeze the deferred boundary so local completion is unambiguous and later GitHub/Azure-live work is not hidden.

Files:

* This artifact plus any linked execution notes created during implementation.

Must implement:

* Explicit checklist for GitHub issue publication, docs PR publication, remediation PR drafting, Blob-backed artifact links, and release approval gates.
* Clear ownership note for which of those deferred items belong to later implementation versus operational validation.

Exit criteria:

* Local-first completion criteria are closed without pretending publish-ready integration has already been proven.
* Deferred items are visible and bounded.

## What can be fully delivered locally now

The following TG6 outcomes can be fully delivered and validated in the current repository without Azure-live or GitHub-live dependencies:

* Full `src/reporter/` package skeleton.
* Local loading of TG4 staged dry-run and history preview artifacts.
* Local loading of TG5 `summary.json`, `custom.json`, and `redteam.json` outputs.
* Deterministic winner selection against current local artifacts.
* Local markdown report rendering to disk.
* Structured issue/remediation payload generation to disk.
* Unit tests and fixture-backed validation for all local decision logic.

## What is explicitly deferred

The following work must be deferred to later implementation or release gates:

* Posting or updating a live GitHub Issue.
* Opening a live docs PR or remediation PR.
* Resolving Blob URLs for raw artifacts from Azure storage instead of local paths.
* Cross-run baseline lookups from Azure Table or Blob history stores instead of TG4 local previews.
* Final release approval that decides whether a remediation payload becomes a human-reviewed PR.

## Exact acceptance criteria

TG6 is complete for local-first delivery when all of the following are true:

1. `src/reporter/` exists with the proposed package structure or an equivalent structure that preserves the same boundaries.
2. Reporter code can ingest `artifacts/cli-test-run/dry_run_output.json` and `artifacts/cli-test-run/history_preview.json`.
3. Reporter code can ingest both candidate result directories under `results/cli-test-run/` and correlate them to the retiring target.
4. Winner logic is implemented exactly once in a dedicated decision component and is unit-tested.
5. Dataset hash mismatches between TG4 and TG5 surfaces are surfaced explicitly in validation or decision metadata.
6. Local markdown output includes retiring model context, ranked candidate table, recommendation rationale, red-team summary, local artifact references, and migration checklist.
7. Structured issue and remediation payloads are generated locally without any live GitHub mutation.
8. Unit tests cover artifact loading, aggregation, decision logic, markdown rendering, and payload generation.
9. The implementation documentation or service output clearly states which publication and release-gate actions are deferred.

## Validation plan

### Local validation required for TG6 completion

* Run reporter unit tests for all new modules.
* Execute one local reporter run against the existing `cli-test-run` artifact set.
* Verify deterministic outputs across repeated runs with no artifact changes.
* Verify failure behavior when a candidate summary is missing or when dataset hashes disagree.

### Deferred validation for later gates

* GitHub issue publication and update behavior against a test repository.
* Markdown PR publication and branch creation in workflow context.
* Remediation payload conversion into a real Bicep patch PR.
* Azure-backed artifact link substitution and baseline history reads.

## Immediate dispatch recommendation

Dispatch Slice 0 first.

Reason:

* It is the narrowest slice with the highest leverage across all later reporting work.
* It validates the real local artifact contract instead of relying on assumed shapes.
* It forces the dataset-hash discrepancy to be handled deliberately at the contract boundary before winner logic and report rendering are built on top of it.

Recommended owner split:

* Kenny leads `src/reporter/{models.py,artifact_loader.py}` and the initial service seam.
* Wendy validates that evaluator summary fields are sufficient and flags any missing score or threshold fields needed for downstream decisions.
* Cartman reviews output shape against the stakeholder-facing recommendation narrative expected in `requirements/plan.md`.

## Blockers and unresolved dependency notes

Current blockers:

* No hard blocker prevents TG6 local-first implementation from starting now.

Unresolved dependency notes:

* The `dataset_sha256` discrepancy between TG4 `run_context` and TG5 local `summary.json` must be resolved or intentionally normalized before Azure-live history comparisons are trusted.
* Cost delta and longevity inputs are specified in `requirements/plan.md` but are not fully represented in the currently staged local summaries, so TG6 should preserve extension points and avoid overcommitting to incomplete local heuristics.
* GitHub publication, remediation PR drafting, and Azure-backed artifact links remain deferred until credentials, release gates, and publisher surfaces are deliberately implemented and validated.