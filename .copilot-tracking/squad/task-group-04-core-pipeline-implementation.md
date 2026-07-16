---
title: Task Group 4 Core Pipeline Implementation
description: Execution-ready implementation artifact for the TG4 core Python pipeline surface and immediate dispatch sequencing.
ms.date: 2026-07-15
ms.topic: reference
---
<!-- markdownlint-disable-file -->

## Ownership

* Lead: Python Delivery Lead (Kenny)
* Support: MVP Product/Tech Integrator (Cartman)
* Support: DevOps + IaC Engineer (Butters)

## Objective

Deliver the missing `src/` application surface that turns the TG1 architecture contract and TG3 workflow scaffolding into an executable MVP control pipeline.

TG4 is the first implementation group that creates runnable business logic. It must be implementation-ready for immediate dispatch and must avoid re-opening architecture, infra, or workflow decisions already frozen by TG1 through TG3.

## Scope

In scope:

* Create the initial Python package structure under `src/`.
* Implement the shared typed contracts and configuration loaders required by all downstream modules.
* Implement the detector flow for watch-list loading, retirement target normalization, and run-context-aware outputs.
* Implement the recommender flow for deterministic candidate ranking against config-driven constraints.
* Implement the provisioner control-plane client surface for candidate deployment request shaping and teardown planning.
* Implement the orchestrator control flow that stitches detector, recommender, provisioner, and workflow inputs together.
* Implement history hooks required to emit stable artifact and skip-index payloads, even if Azure persistence is initially stubbed behind interfaces.
* Produce local validation surfaces so TG5, TG6, and TG8 can consume stable contracts without waiting for Azure-live execution.

Out of scope:

* ACA evaluator job business logic (`src/evaluator/**`) beyond interface placeholders required for orchestration.
* GitHub workflow authoring or further TG3 pipeline contract changes.
* Bicep, RBAC, private endpoint, or policy implementation changes owned by TG2.
* Report rendering, GitHub Issue publishing, remediation PR authoring, and stakeholder-facing outputs owned by TG6.
* End-to-end Azure execution proof, policy attestation, or private DNS reachability proof; these remain Azure-live validation items.

## Non-goals

* Do not introduce alternate architecture or bypass TG1 contract boundaries.
* Do not add secret-based authentication, connection strings, or public data-plane fallback paths.
* Do not tightly couple business logic to GitHub Actions YAML; TG4 consumes workflow inputs, it does not own workflow structure.
* Do not block initial implementation on Azure-live access when contract-faithful local interfaces can be built first.

## Dependency Baseline

### Required upstream inputs

TG4 is allowed to start because the following upstream planning and foundation artifacts exist locally:

* `requirements/plan.md`
* `.copilot-tracking/squad/task-group-01-architecture-blueprint.md`
* `.copilot-tracking/squad/task-group-03-cicd-delivery-automation.md`
* `docs/tg3-handoff-contract.md`
* `config/azure.env.example`
* `config/models.yaml`
* `config/evaluation.yaml`
* `config/recommender.yaml`
* `.github/workflows/detect-and-eval.yml`
* `.github/workflows/ci.yml`
* `.github/workflows/sweep-orphans.yml`
* `scripts/validate_tg3_contracts.py`

### Key constraint imported from TG1

TG4 must preserve the module contracts defined in TG1:

* `src/detector` owns retirement detection and watch-list intersection.
* `src/recommender` owns candidate filtering and deterministic scoring.
* `src/provisioner` owns ARM deployment lifecycle shaping.
* `src/orchestrator` owns end-to-end run control and state sequencing.
* `src/history` owns artifact manifest and skip-index contract shaping.
* `src/shared` owns auth, config, typed contracts, logging, and reusable utilities.

## Local handoff status from TG2 and TG3

### Satisfied locally now

These handoffs are sufficiently satisfied in source control for TG4 implementation to begin immediately:

| Handoff | Source | Local status | TG4 usage |
|---|---|---|---|
| Resource naming contract | `config/azure.env.example`, `docs/tg3-handoff-contract.md` | Present and stable as placeholders/contracts | Build config models and environment parsing now |
| RunContext contract shape | TG1 blueprint + TG3 workflow artifact requirements | Present and stable | Implement typed `RunContext` and serialization now |
| Workflow entrypoint expectation | `.github/workflows/detect-and-eval.yml` | Present | Align orchestrator CLI/module entrypoint with workflow invocation shape |
| TG3 contract validator | `scripts/validate_tg3_contracts.py` | Present and passing locally | Reuse as evidence that env/config surfaces are stable |
| OIDC-only posture | TG2/TG3 docs and decisions | Present as policy and docs contract | Design auth interfaces around `DefaultAzureCredential`/managed identity only |
| Artifact/report staging expectations | TG1 + TG3 planning artifacts | Present as path and manifest contract | Implement manifest builders and filesystem-safe local staging now |
| Private-only data-plane rule | TG1/TG2/TG3 contracts | Present as invariant | Keep provisioner/orchestrator interfaces control-plane only |

### Still Azure-live and not a blocker for first slice

These handoffs are not fully proven locally and should be treated as integration assumptions until Azure execution validates them:

| Handoff | Source | Current state | TG4 implication |
|---|---|---|---|
| Real OIDC login to Azure | TG2/TG3 | Contracted, not execution-proven here | Keep auth adapter injectable; do not require live auth for unit tests |
| Actual resource IDs and deployed names from Bicep outputs | TG2 | Placeholder/config-driven locally | Read from config/env abstractions, not hard-coded values |
| ACA job invocation and polling against live Azure | TG3 | Workflow shape defined, not runtime-proven | Implement orchestrator/provisioner interfaces with dry-run/test doubles first |
| Private DNS reachability from ACA subnet | TG2 | Documented, not runtime-proven | Out of scope for local TG4 validation; keep evaluator boundary abstract |
| RBAC sufficiency for workflow principal and managed identity | TG2 | Planned/documented, not runtime-proven | Surface explicit permission errors cleanly in auth/provisioner contracts |
| Policy assignment enforcement on live resources | TG2 | Planned/documented, not runtime-proven | Preserve required tagging and non-public defaults in payload builders |

## Target package and module structure for `src/`

TG4 should create the following initial package surface.

```text
src/
  __init__.py
  detector/
    __init__.py
    models.py
    watchlist.py
    retirement_source.py
    service.py
  recommender/
    __init__.py
    models.py
    filters.py
    scorer.py
    catalog.py
    service.py
  provisioner/
    __init__.py
    models.py
    deployment_plan.py
    arm_payloads.py
    service.py
  orchestrator/
    __init__.py
    models.py
    pipeline.py
    cli.py
  history/
    __init__.py
    models.py
    manifest_builder.py
    skip_index.py
  shared/
    __init__.py
    contracts.py
    config.py
    run_context.py
    errors.py
    logging.py
    azure_auth.py
    time.py
```

### Packaging notes

* Keep all cross-module types in `src/shared/contracts.py`, not duplicated per module.
* Keep module-specific request/result wrappers in each module's `models.py` when they are internal to that boundary.
* Expose service-layer pure functions or small service classes from each module's `service.py` so orchestrator code depends on stable interfaces.
* Defer any Azure SDK coupling to `shared/azure_auth.py` and `provisioner/service.py`; do not spread client creation across modules.
* Prefer deterministic, serializable dataclasses or Pydantic models for all boundary objects.

## Ordered implementation slices

The slices below are intentionally ordered to minimize rework and let Kenny dispatch immediately.

### Slice 0: Shared contracts and runtime bootstrap

Goal:

* Establish the contract surface every other slice will compile against.

Files to create first:

* `src/__init__.py`
* `src/shared/__init__.py`
* `src/shared/contracts.py`
* `src/shared/config.py`
* `src/shared/run_context.py`
* `src/shared/errors.py`
* `src/shared/logging.py`
* `src/shared/azure_auth.py`

Must implement:

* `RunContext` typed model with required TG1 fields.
* Config loaders for `models.yaml`, `evaluation.yaml`, `recommender.yaml`, and environment variables from `azure.env.example` shape.
* Shared domain models for `RetiringModel`, `RetiringTarget`, `Candidate`, `CandidateRank`, `ProvisionRequest`, `DeploymentRef`, `ArtifactManifest`, and `SkipIndexKey`.
* Shared error taxonomy aligned to TG1 failure categories.
* Stubbed credential factory that supports import and local tests without requiring live Azure auth.

Exit criteria:

* All downstream slices can import shared models without circular references.
* Local unit tests can instantiate `RunContext` from fixture data.

### Slice 1: Detector

Goal:

* Convert configured watch-list entries and retirement inputs into normalized `RetiringTarget[]` outputs.

Files:

* `src/detector/__init__.py`
* `src/detector/models.py`
* `src/detector/watchlist.py`
* `src/detector/retirement_source.py`
* `src/detector/service.py`

Must implement:

* Watch-list loader and normalization for `config/models.yaml`.
* Retirement-horizon filtering using `RunContext.retirement_horizon_days`.
* Deterministic output model for retiring targets and parse warnings.
* Explicit source abstraction so retirement data can come from static fixtures first and live scraping later.

Exit criteria:

* Detector can run locally against fixture retirement input and configured models.
* Output is deterministic and serializable.

### Slice 2: Recommender

Goal:

* Produce deterministic candidate ranking from retiring targets without requiring Azure deployment.

Files:

* `src/recommender/__init__.py`
* `src/recommender/models.py`
* `src/recommender/filters.py`
* `src/recommender/scorer.py`
* `src/recommender/catalog.py`
* `src/recommender/service.py`

Must implement:

* Config-driven weight loading from `config/recommender.yaml`.
* Hard filters for region, deployment type preference, and basic capability matching.
* Deterministic scoring with stable sort behavior.
* Fixture-friendly catalog source abstraction for local development.

Exit criteria:

* Given fixture targets and catalog data, recommender returns the top N candidates with stable scores.
* Weight sum and hard-filter validation failures are explicit and test-covered.

### Slice 3: Provisioner

Goal:

* Build control-plane deployment and teardown request objects without requiring live Azure execution in the first pass.

Files:

* `src/provisioner/__init__.py`
* `src/provisioner/models.py`
* `src/provisioner/deployment_plan.py`
* `src/provisioner/arm_payloads.py`
* `src/provisioner/service.py`

Must implement:

* `ProvisionRequest` shaping from `CandidateRank[]` and `RunContext`.
* Idempotency key generation consistent with TG1 format.
* Required tag set injection from TG2/TG3 governance contract.
* Teardown plan builder for every generated deployment request.
* Service boundary that can run in dry-run mode and later bind to Azure SDK/CLI execution.

Exit criteria:

* Provisioner can emit deployment and teardown plans locally for top-ranked candidates.
* No live Azure dependency is required for unit-level correctness.

### Slice 4: Orchestrator

Goal:

* Stitch the first three slices into one runnable pipeline entrypoint compatible with TG3 workflow expectations.

Files:

* `src/orchestrator/__init__.py`
* `src/orchestrator/models.py`
* `src/orchestrator/pipeline.py`
* `src/orchestrator/cli.py`

Must implement:

* Pipeline sequencing: load config -> build `RunContext` -> detector -> recommender -> provisioner.
* Dry-run mode that writes a local pipeline summary instead of touching Azure.
* Exit codes aligned to success, config failure, and contract failure categories.
* Serialization of outputs to a staging directory that TG6 can later consume.

Exit criteria:

* A local CLI invocation can produce detector, ranking, and provision-plan outputs end-to-end.
* Orchestrator does not depend on evaluator or reporter implementations.

### Slice 5: History hooks

Goal:

* Emit stable artifact and skip-index payloads so TG5/TG6/TG8 can integrate without revisiting data shape.

Files:

* `src/history/__init__.py`
* `src/history/models.py`
* `src/history/manifest_builder.py`
* `src/history/skip_index.py`

Must implement:

* Local manifest generation matching TG1 blob contract fields.
* Skip-index key builder using retiring model, candidate model/version, and dataset hash shape.
* Storage adapter interface with local in-memory/file implementation first.
* Reporter-facing summary object for downstream aggregation.

Exit criteria:

* Orchestrator dry-run can emit manifest and skip-index preview artifacts locally.
* No Azure Table or Blob runtime requirement exists for first-pass validation.

## Exact handoff expectations into TG4 implementation

### From TG2

Cartman and Butters should treat these as frozen contracts, not discovery tasks:

* Use only the environment names and resource aliases documented in `config/azure.env.example` and `docs/tg3-handoff-contract.md`.
* Preserve required tags: ownership, managed-by, cleanup scope, and task group markers in any deployment payload builders.
* Treat all live Azure identities as externally provisioned. TG4 consumes them through config and auth adapters only.

Still not satisfied by TG2 locally:

* Real subscription/resource-group outputs bound to a deployed environment.
* Runtime proof that RBAC and private networking work in Azure.

### From TG3

TG4 may depend on these workflow contracts now:

* Workflows exist and reserve the orchestration lane.
* OIDC-only pipeline stance is fixed.
* Contract validator and config surfaces are stable.
* The pipeline expects a deterministic `run_id` and run-context artifact behavior.

Still not satisfied by TG3 locally:

* End-to-end `workflow_dispatch` execution against Azure.
* Live ACA invoke/poll/finalize behavior.

## Minimal first implementation slice recommendation

Recommended first slice:

**Slice 0 + Slice 1 together, with orchestrator stub wiring only for local dry-run.**

Why this first:

* It establishes the shared contract surface before any downstream module branches.
* It produces the first business-meaningful output (`RetiringTarget[]`) without waiting on Azure.
* It gives TG3 a concrete Python entrypoint shape to wire later without blocking on recommender/provisioner completion.
* It creates the fixture and test patterns the later slices will reuse.

Concrete first-dispatch target:

* Create `src/shared/**` and `src/detector/**`.
* Add a minimal `src/orchestrator/cli.py` that loads config, builds `RunContext`, runs detector only, and writes a JSON preview artifact.

Definition of done for the first slice:

* A local command can load configured watch-list data and emit normalized retiring targets from fixture retirement input.
* All outputs are strongly typed and JSON-serializable.
* No Azure credentials or network calls are required.

## Acceptance criteria

TG4 is implementation-complete only when all of the following are true:

1. The repository has the full initial `src/` package surface defined in this artifact, or a documented subset corresponding to completed slices.
2. Shared contracts define a stable `RunContext` and boundary models that match TG1 contract names and semantics.
3. Detector and recommender both run locally with fixture-based inputs and deterministic outputs.
4. Provisioner generates idempotent deployment and teardown plans with required governance tags.
5. Orchestrator dry-run executes end-to-end without evaluator/reporter dependencies.
6. History hooks emit manifest and skip-index preview artifacts with the required TG1 fields.
7. No implemented module requires long-lived secrets, public data-plane access, or direct workflow-YAML coupling.
8. Local tests and static validation cover config parsing, contract shape, deterministic ranking, and idempotency key generation.

## Validation plan

### Local validation required before Azure-live integration

* Add unit tests for:
  * `RunContext` construction and validation.
  * Detector watch-list normalization and retirement horizon filtering.
  * Recommender hard filters and deterministic scoring.
  * Provisioner idempotency key and required tag generation.
  * History manifest and skip-index key generation.
* Add a local dry-run execution test for orchestrator:
  * loads config fixtures
  * creates `RunContext`
  * runs detector + recommender + provisioner
  * writes summary JSON artifacts
* Add lightweight static checks:
  * Python compile/import validation
  * Config fixture validation against existing YAML contract surfaces

### Azure-live validation deferred to later execution phases

These checks are intentionally deferred and should be planned, not blocked on, for TG4 initial delivery:

* OIDC login against target Azure tenant/subscription
* Real Foundry candidate deployment creation and teardown
* Real ACA job invocation and polling
* Private endpoint DNS and RBAC validation in deployed environment

## Immediate dispatch recommendation

Kenny should start with one implementation ticket only:

* **TG4-01**: Create `src/shared/**`, `src/detector/**`, and a detector-only `src/orchestrator/cli.py` dry-run path.

Support engagement for the first slice:

* Cartman: confirm detector output shape matches TG1 `RetiringTarget` contract and does not drift from architecture intent.
* Butters: confirm CLI/run-context output shape is easy for TG3 workflow integration to call later.

## Exit handoff from TG4 to downstream groups

TG4 should hand off the following once the first two slices are complete:

* Stable Python package layout under `src/`
* Shared contract models for TG5/TG6/TG8 reuse
* Dry-run orchestration path and fixture-driven example outputs
* Provisioner payload and teardown plan contract
* History manifest/skip-index preview contract

At that point, TG5 can attach evaluator execution, TG6 can attach reporting/output generation, and TG8 can attach broader validation gates without re-planning the core pipeline surface.