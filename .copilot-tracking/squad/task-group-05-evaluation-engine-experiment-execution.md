---
title: Task Group 5 Evaluation Engine and Experiment Execution
description: Execution-ready implementation artifact for the TG5 local-first evaluator surface and experiment execution sequencing.
ms.date: 2026-07-15
ms.topic: reference
---
<!-- markdownlint-disable-file -->

## Ownership

* Lead: Wendy (Evaluation + Quality Engineer)
* Support: Kenny (Python Delivery Lead)
* Support: Stan (Platform Reliability + SRE Lead)

## Objective

Deliver the missing `src/evaluator/` execution surface that consumes TG4 dry-run outputs, prepares evaluator job inputs, runs the local-first evaluation path, and freezes the contract for later ACA-hosted Azure execution.

## Local execution status (2026-07-15)

Completed locally in this repository state:

* Slice 0 complete: evaluator package skeleton and TG4 dry-run/history artifact ingestion are implemented under `src/evaluator/`.
* Slice 1 complete: local dataset loading, `dataset_sha256` derivation, and evaluation config projection are implemented and test-covered.
* Slice 2 complete for local-first mode: fake-backed custom and red-team runners execute against staged TG4 artifacts while preserving the target output contract.
* Slice 3 complete: result persistence writes `results/<run_id>/<candidate>/{custom.json,redteam.json,summary.json}`.
* Slice 4 complete at contract level: ACA job adapter and `docker/evaluator/` scaffold exist, but live Azure dispatch remains intentionally deferred.

Still deferred to Azure-live validation:

* Real ACA job invocation, polling, and cleanup proof.
* Managed identity authorization to Foundry, Blob, and Table.
* Private endpoint and private DNS validation from ACA runtime.
* Execution of real `azure-ai-evaluation` and red-team SDK flows against deployed candidates.

TG5 is the first group that turns candidate deployment intent into evaluation-ready experiment inputs and scoring artifacts. It must establish a fully testable local evaluator path now, without re-opening workflow, architecture, or infrastructure decisions already frozen by TG1 through TG4.

## Scope

In scope:

* Create the initial evaluator package structure under `src/evaluator/`.
* Consume TG4 staged artifacts from `artifacts/<run_id>/dry_run_output.json` and `artifacts/<run_id>/history_preview.json`.
* Implement dataset/config loading and experiment request shaping using `config/evaluation.yaml` and local fixtures.
* Implement local-first evaluator orchestration that can score candidate deployment requests without live Azure resources.
* Define result and artifact schemas for `custom.json`, `redteam.json`, and local run summaries.
* Define the ACA job adapter boundary that will later execute the same evaluator flow inside Azure Container Apps.
* Add unit and fixture-based validation so TG6, TG7, and TG8 can integrate against stable evaluation outputs.
* Propose the container surface for evaluator packaging under `docker/evaluator/` if required for later ACA execution.

Out of scope:

* Live ACA job creation, live polling, or teardown execution against Azure.
* Private-endpoint DNS validation, RBAC proof, or managed identity execution proof.
* TG3 workflow authoring changes beyond consuming the frozen handoff contract.
* Foundry deployment creation logic owned by TG4 provisioner beyond reading its emitted plans.
* Reporter ranking policy, GitHub issue publication, or remediation patch generation owned downstream.

## Non-goals

* Do not introduce alternate evaluator architecture outside the TG1 and `requirements/plan.md` contract.
* Do not require Azure credentials, connection strings, or public inference endpoints for the first implementation slices.
* Do not block local evaluator delivery on live candidate deployments when contract-faithful fixture and dry-run inputs already exist.
* Do not couple evaluator business logic directly to GitHub Actions YAML or ACA job plumbing.

## Dependency baseline

### Required upstream inputs already present locally

TG5 is allowed to start because the following dependency surfaces are available in source control and local artifacts:

* `.copilot-tracking/squad/task-group-01-architecture-blueprint.md`
* `.copilot-tracking/squad/task-group-03-cicd-delivery-automation.md`
* `.copilot-tracking/squad/task-group-04-core-pipeline-implementation.md`
* `docs/tg3-handoff-contract.md`
* `requirements/plan.md`
* `config/evaluation.yaml`
* `artifacts/cli-test-run/dry_run_output.json`
* `artifacts/cli-test-run/history_preview.json`
* `tests/fixtures/retirement_signals.yaml`
* `tests/fixtures/candidate_catalog.yaml`
* `tests/unit/test_detector_service.py`
* `tests/unit/test_recommender_service.py`
* `tests/unit/test_provisioner_service.py`
* `tests/unit/test_history_preview.py`
* `tests/unit/test_orchestrator_cli.py`

### Key contract imported from TG1 and requirements

TG5 must preserve these already-defined contracts:

* `src/evaluator` owns custom eval and red-team execution.
* Evaluator input boundary is `DeploymentRef`, dataset manifest, thresholds, and `RunContext`.
* Evaluator output boundary is `custom.json`, `redteam.json`, and metrics events.
* Dataset hash contributes to skip-index identity and artifact naming.
* Azure execution target is ACA job plus private Foundry endpoint, but business logic must remain reusable locally.

## Current handoff status from TG3 and TG4

### TG3 handoff status

The TG3 delivery artifact already freezes the workflow-facing evaluator contract sufficiently for local implementation:

* H-05 satisfied locally: ACA job trigger interface and poll semantics are defined in the TG3 handoff, though not yet runtime-proven against Azure.
* H-06 satisfied locally: dataset and evaluation configuration injection path is documented and can be modeled now.
* H-07 satisfied locally: eval artifact persistence location and naming contract is stable enough to implement against local file outputs first.
* H-08 partially satisfied locally: cleanup guarantees are contractually defined, but only Azure-live execution can fully prove them.

TG5 implication:

* Wendy can implement evaluator request/response shaping, artifact writing, and local orchestration now.
* Wendy should not block on live workflow dispatch or Azure polling proof for the first slices.

### TG4 handoff status

The TG4 core pipeline artifact and staged outputs now provide stable local inputs for evaluator development:

* Dry-run summary exists at `artifacts/<run_id>/dry_run_output.json`.
* History preview exists at `artifacts/<run_id>/history_preview.json`.
* Candidate deployment requests, teardown plans, manifests, skip-index keys, and `RunContext` shape are serialized and test-covered.
* TG4 has already validated the artifact root contract under `artifacts/<run_id>/...` and the coherence between summary, history, and payload artifacts.

TG5 implication:

* Evaluator code can consume real local staged pipeline payloads now instead of inventing new input contracts.
* The first evaluator slice should treat TG4 dry-run artifacts as its canonical fixture baseline.

### Remaining Azure-live only dependency surfaces

These are not blockers for local-first implementation but remain deferred validation gates:

* Live ACA job invocation and poll loop behavior.
* Managed identity authentication from ACA to Foundry, Blob, and Table.
* Private endpoint resolution for Foundry and storage from the ACA subnet.
* Real cleanup confirmation after ephemeral candidate deployment execution.

## Proposed package and support structure

TG5 should create the following initial evaluator surface.

```text
src/
  evaluator/
    __init__.py
    models.py
    dataset_loader.py
    config_loader.py
    input_builder.py
    custom_runner.py
    redteam_runner.py
    result_writer.py
    service.py
    aca_job.py

tests/
  fixtures/
    evaluator/
      dataset.sample.jsonl
      tg4-dry-run.sample.json
      tg4-history-preview.sample.json
      custom-results.sample.json
      redteam-results.sample.json
  unit/
    test_evaluator_dataset_loader.py
    test_evaluator_input_builder.py
    test_evaluator_service.py
    test_evaluator_result_writer.py
    test_evaluator_aca_job.py

docker/
  evaluator/
    Dockerfile
    entrypoint.py
    requirements.txt
```

### Structure notes

* `models.py` should define only evaluator-local request and response models not already owned by `src/shared/contracts.py`.
* `dataset_loader.py` should handle JSONL dataset ingestion, normalization, and `dataset_sha256` derivation.
* `input_builder.py` should translate TG4 dry-run and history artifacts into evaluator work items.
* `custom_runner.py` and `redteam_runner.py` should be pure adapters around the evaluation contract so local tests can replace Azure SDK execution with fakes.
* `result_writer.py` should own the output file naming and directory shaping contract.
* `aca_job.py` should define the live execution boundary only. It must remain injectable and skippable for local validation.
* `docker/evaluator/` is appropriate to plan now because `requirements/plan.md` explicitly places evaluator execution inside an ACA job, but the first implementation slices do not need a working Azure image push.

## Ordered implementation slices

### Slice 0: Evaluator contract skeleton and TG4 artifact ingestion

Goal:

* Establish the evaluator boundary and make TG4 staged outputs readable by evaluator code without Azure dependencies.

Files:

* `src/evaluator/__init__.py`
* `src/evaluator/models.py`
* `src/evaluator/config_loader.py`
* `src/evaluator/input_builder.py`
* `tests/fixtures/evaluator/tg4-dry-run.sample.json`
* `tests/fixtures/evaluator/tg4-history-preview.sample.json`
* `tests/unit/test_evaluator_input_builder.py`

Must implement:

* Typed evaluator request models driven by TG4 `run_context`, provisioner plans, manifests, and skip-index keys.
* Parsing of TG4 staged outputs using the existing `artifacts/<run_id>/...` contract.
* Validation errors for missing manifests, malformed deployment plans, and unsupported artifact types.

Exit criteria:

* TG5 can load existing dry-run artifacts and build deterministic evaluator work items.
* No Azure SDK or network calls are required.

### Slice 1: Dataset loading and local experiment assembly

Goal:

* Turn evaluator config plus dataset fixtures into executable local experiment payloads.

Files:

* `src/evaluator/dataset_loader.py`
* `tests/fixtures/evaluator/dataset.sample.jsonl`
* `tests/unit/test_evaluator_dataset_loader.py`

Must implement:

* JSONL dataset loading.
* Stable `dataset_sha256` derivation from concatenated content.
* Threshold and evaluator-set loading from `config/evaluation.yaml`.
* Experiment payload assembly per candidate deployment.

Exit criteria:

* Local tests prove dataset parsing, hashing, and config binding are deterministic.
* Evaluator work items include enough metadata for later skip-index and reporter consumption.

### Slice 2: Local custom evaluation and red-team adapters

Goal:

* Implement a local execution path that exercises the evaluator orchestration using fake or canned scorers while preserving the future Azure output contract.

Files:

* `src/evaluator/custom_runner.py`
* `src/evaluator/redteam_runner.py`
* `src/evaluator/service.py`
* `tests/unit/test_evaluator_service.py`

Must implement:

* Service orchestration that runs custom and red-team stages for each evaluator work item.
* Fake-runner support so tests can produce realistic `custom.json` and `redteam.json` payloads.
* Stable per-candidate aggregation shape matching `requirements/plan.md` output expectations.

Exit criteria:

* Evaluator service can run locally from staged TG4 artifacts and dataset fixtures.
* Output schemas are stable even when the underlying scorer implementation is still fake-backed.

### Slice 3: Result writing and local artifact persistence

Goal:

* Persist evaluation outputs to the directory structure downstream groups expect.

Files:

* `src/evaluator/result_writer.py`
* `tests/fixtures/evaluator/custom-results.sample.json`
* `tests/fixtures/evaluator/redteam-results.sample.json`
* `tests/unit/test_evaluator_result_writer.py`

Must implement:

* Local output path builder for `results/<run_id>/<candidate>/custom.json` and `results/<run_id>/<candidate>/redteam.json`.
* Optional local manifest/summary object that links evaluator outputs back to TG4 run context and candidate identity.
* Artifact-writing behavior that is deterministic and overwrite-safe for reruns.

Exit criteria:

* Local evaluator execution writes the expected result files under a stable output tree.
* Downstream consumers can discover outputs without inspecting in-memory objects.

### Slice 4: ACA job boundary and container packaging scaffold

Goal:

* Freeze the live Azure execution seam without making Azure-live success a prerequisite for local completion.

Files:

* `src/evaluator/aca_job.py`
* `docker/evaluator/Dockerfile`
* `docker/evaluator/entrypoint.py`
* `docker/evaluator/requirements.txt`
* `tests/unit/test_evaluator_aca_job.py`

Must implement:

* A job-entry adapter that can accept serialized evaluator work items and run the same service entrypoint.
* Container packaging assumptions for ACA execution.
* Clear placeholders for managed identity, private endpoint, and Azure-hosted dataset/blob access.

Exit criteria:

* The ACA execution seam is explicit and test-covered at the contract level.
* Local validation still runs without building or pushing a live image.

### Slice 5: Live-integration validation plan and handoff closure

Goal:

* Package all deferred Azure-live checks as an explicit validation gate rather than hidden implementation debt.

Files:

* This artifact plus any linked implementation notes or test evidence Wendy creates during execution.

Must implement:

* Explicit checklist for ACA trigger, poll, identity, storage, private DNS, and cleanup proof.
* Handoff-ready list for TG6, TG7, and TG8 describing the stable local evaluator outputs.

Exit criteria:

* TG5 local completion status is unambiguous.
* Azure-live only items are clearly deferred and owned.

## What can be fully delivered locally now

The following TG5 outcomes can be fully delivered and validated in the current repository without Azure access:

* Evaluator package skeleton under `src/evaluator/`.
* Parsing of TG4 dry-run and history artifacts into evaluator work items.
* Dataset/config ingestion and `dataset_sha256` derivation.
* Local custom-eval and red-team orchestration using fixture-backed or fake-backed runners.
* Output file generation for `custom.json` and `redteam.json` in stable local paths.
* Unit tests and fixture-driven end-to-end local evaluator execution.
* ACA adapter and container scaffold definitions at the contract level.

These local outcomes are sufficient to unblock:

* TG6 reporting integration against stable evaluator artifact shapes.
* TG7 reliability planning around evaluator lifecycle states and failure surfaces.
* TG8 quality gate expansion against evaluator outputs and experiment metadata.

## What remains Azure-live only

The following TG5 outcomes cannot be considered complete until Azure-hosted validation is performed:

* Actual ACA job trigger and poll behavior through TG3 workflow execution.
* Managed identity authorization to invoke Foundry and write Blob/Table artifacts.
* Private endpoint resolution and private-only data-plane access from the ACA subnet.
* Execution of real `azure-ai-evaluation` and red-team runs against deployed candidates.
* Cleanup proof that ephemeral candidate deployments are torn down or safely recovered after evaluation.

These items must be treated as a separate validation gate, not as blockers for local-first implementation slices 0 through 4.

## Exact acceptance criteria

TG5 local-first implementation is complete when all of the following are true:

1. `src/evaluator/` exists with the initial modules defined in this artifact, or a documented completed subset aligned to the finished slices.
2. Evaluator input models can be constructed directly from TG4 dry-run and history-preview artifacts.
3. Dataset loading and `dataset_sha256` generation are deterministic and test-covered.
4. Evaluator service can execute local custom and red-team flows using non-Azure test doubles while preserving the target output schema.
5. Result writer emits stable local `custom.json` and `redteam.json` paths per candidate.
6. ACA job and container seams are defined without forcing Azure runtime validation into the first implementation pass.
7. No completed local slice requires Azure credentials, public network access, or live deployment resources.
8. Unit tests cover malformed TG4 artifacts, dataset binding, local evaluator execution, and result persistence.

TG5 full end-to-end completion, including Azure-live validation, is complete only when all of the following additional items are true:

1. TG3 workflow can trigger and poll the ACA evaluator job successfully.
2. ACA managed identity can access required Azure dependencies with no keys or connection strings.
3. Evaluator job can read datasets and write artifacts in the live private network path.
4. Cleanup guarantees are proven against real ephemeral candidate deployments.

## Validation plan

### Local validation required now

* Add unit tests for evaluator artifact ingestion using current TG4 sample payloads.
* Add unit tests for dataset parsing and hash derivation.
* Add unit tests for local custom and red-team service orchestration with fake-backed scorers.
* Add unit tests for result writing and path construction.
* Add one local integration-style test that:
  * reads TG4 dry-run artifacts
  * loads evaluator config and dataset fixture
  * assembles evaluator work items
  * runs local evaluator service
  * writes `custom.json` and `redteam.json`

### Deferred Azure-live validation

* `workflow_dispatch` or equivalent live pipeline execution through TG3.
* ACA job image execution with live managed identity.
* Private Foundry invocation and storage persistence.
* Teardown confirmation after evaluator completion or failure.

## Immediate dispatch recommendation

Recommended first implementation ticket:

* **TG5-01**: Create `src/evaluator/models.py`, `src/evaluator/config_loader.py`, `src/evaluator/input_builder.py`, plus `tests/fixtures/evaluator/` sample TG4 payloads and `tests/unit/test_evaluator_input_builder.py`.

Why this first:

* It grounds TG5 on existing repo evidence instead of speculative Azure behavior.
* It freezes the evaluator input contract before Wendy invests in scorer or container code.
* It gives Kenny and Stan a stable artifact shape to review for downstream integration and reliability concerns.

Support engagement for the first dispatch:

* Kenny should confirm the evaluator work-item shape faithfully reflects TG4 provisioner, manifest, and `RunContext` outputs.
* Stan should review failure-state and retry expectations for malformed artifacts or incomplete staged outputs.

## Downstream handoff expectations from TG5

Once slices 0 through 3 are complete, TG5 should hand off the following stable surfaces:

* Local evaluator work-item schema derived from TG4 outputs.
* Stable local result artifact tree and file naming.
* Dataset-hash semantics reused by history and reporter consumers.
* Deferred Azure-live validation checklist with clear ownership boundaries.

At that point, TG6 can aggregate evaluator artifacts, TG7 can attach runtime reliability controls, and TG8 can expand quality gates without re-planning the evaluator business logic surface.