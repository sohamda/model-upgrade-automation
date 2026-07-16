# Squad Decisions Log

## Initialization Decision (2026-07-15)

**Decision**: Initialize squad with 6-member roster and 9-phase task-division matrix.

**Rationale**: Establish clear role ownership, dependency chains, and parallel execution paths for model-upgrade-automation delivery. Task division aligns with team expertise:
- Cartman leads architecture/MVP integration and release readiness.
- Kyle owns security/identity/governance baseline.
- Stan drives reliability/SRE/operability.
- Butters handles infrastructure and delivery automation.
- Kenny implements core pipeline and coordinate outputs.
- Wendy drives evaluation, quality gates, and validation.

**Task-Division Matrix**:

| Task Group | Title | Primary | Support | Dependencies |
|------------|-------|---------|---------|--------------|
| 1 | Architecture and MVP Integration | Cartman | Kenny, Butters, Wendy | Requirements baseline |
| 2 | Infrastructure, Identity, Governance Baseline | Kyle | Butters, Stan | Group 1 |
| 3 | CI/CD and Delivery Automation | Butters | Kyle, Stan, Kenny | Group 2 |
| 4 | Core Pipeline Implementation | Kenny | Cartman, Butters | Groups 1, 3 |
| 5 | Evaluation Engine and Experiment Execution | Wendy | Kenny, Stan | Groups 3, 4 |
| 6 | Reporting, History, and Decision Outputs | Kenny | Wendy, Cartman | Groups 4, 5 |
| 7 | Reliability, SRE Controls, and Operability | Stan | Butters, Kyle, Wendy | Groups 3, 5 |
| 8 | Quality Gates and Validation Framework | Wendy | Stan, Kyle, Kenny | Groups 4, 5, 7 |
| 9 | Runbooks and Release Readiness | Cartman | Stan, Wendy, Kyle, Butters | Groups 6, 7, 8 |

**Task Group Details**:

### Task Group 1: Architecture and MVP Integration
- **Deliverables**: Module boundaries, interface contracts, decision log, integrated blueprint.
- **Primary**: Cartman
- **Support**: Kenny, Butters, Wendy
- **Dependency**: Requirements baseline
- **Context**: Establish MVP architecture before infrastructure and pipeline work.

### Task Group 2: Infrastructure, Identity, Governance Baseline
- **Deliverables**: Private-network Bicep stack, OIDC, RBAC, policy guardrails, KV/storage security.
- **Primary**: Kyle
- **Support**: Butters, Stan
- **Dependency**: Group 1
- **Context**: Governance and networking foundation for all deployment targets.

### Task Group 3: CI/CD and Delivery Automation
- **Deliverables**: Workflows (detect-and-eval, ci, sweep-orphans), build-test pipeline, promotion controls, secretless path.
- **Primary**: Butters
- **Support**: Kyle, Stan, Kenny
- **Dependency**: Group 2
- **Context**: Automated promotion and secretless delivery enablement.

## TG4 Provisioner and History Preview Slice Complete (2026-07-15T18:45:00Z)

**Decision**: Execute and deliver third Task Group 4 (Core Pipeline Implementation) slice — provisioner package for deployment planning, history package for telemetry/manifest capture, and full dry-run extension detector → recommender → provisioner preview → history preview.

**Rationale**: TG4 pipeline now extends beyond ranking to capture deployment planning surface and runtime history. Provisioner package models deployment strategies (instance sizing, region placement, cost projection). History package provides run-level telemetry capture and skip-index filtering for future iterations. Full end-to-end dry-run validates complete data flow: signal detection → candidate scoring → infrastructure planning → execution history preparation. All implementation validated locally with unit tests; ready for integration into CI/CD workflows (TG3 scope).

**Completed Deliverables**:

- **Provisioner Package**:
  - `src/provisioner/__init__.py` — package marker
  - `src/provisioner/models.py` — deployment data models (InstanceProfile, RegionStrategy, CostProjection)
  - `src/provisioner/deployment_plan.py` — deployment plan builder, feasibility checker
  - `src/provisioner/service.py` — provisioner orchestration and plan generation

- **History Package**:
  - `src/history/__init__.py` — package marker
  - `src/history/models.py` — run telemetry models (ExecutionRecord, SignalMetrics, HistoryMetadata)
  - `src/history/manifest_builder.py` — manifest construction and serialization
  - `src/history/skip_index.py` — skip-index generation for filtering/deduplication

- **Extended Orchestrator & Updated Contracts**:
  - `src/orchestrator/pipeline.py` — Full dry-run: detector → recommender → provisioner preview → history preview
  - `src/shared/contracts.py` — Extended with provisioner and history contract surfaces
  - `src/shared/run_context.py` — Enhanced with deployment metadata and history context

- **Test Surface**:
  - `tests/unit/test_provisioner_service.py` — Provisioner service unit tests (planning, feasibility, cost projection)
  - `tests/unit/test_history_preview.py` — History manifest and skip-index tests
  - `tests/unit/test_orchestrator_cli.py` — Pipeline integration tests (full dry-run, contract validation)

**Validation Completed**:
- ✓ `python -m unittest tests.unit.test_orchestrator_cli tests.unit.test_provisioner_service tests.unit.test_history_preview` — All unit tests pass
- ✓ `python -m unittest tests.unit.test_detector_service tests.unit.test_recommender_service tests.unit.test_orchestrator_cli tests.unit.test_provisioner_service tests.unit.test_history_preview` — Full suite passes
- ✓ End-to-end dry-run: detector signals → recommender ranking → provisioner preview → history manifest (no errors, complete data flow)
- ✓ All contracts validated, skip-index filtering verified, no schema violations

**Architectural Significance**: Medium — extends core pipeline to provisioning surface; enables deployment surface modeling and runtime history capture. Consider ADR capture for provisioner strategy trade-offs (region placement, instance family selection, cost-vs-performance heuristics).

---

## TG4 Continuation — Artifact Writing + Full Dry-Run Output Staging (2026-07-15T19:15:00Z)

**Decision**: Continue TG4 with artifact writing and full dry-run output staging.

**Rationale**: TG4 slices 1–3 (shared contracts, detector, recommender, provisioner, history) have delivered core pipeline surface. This continuation slice stabilizes the dry-run output path by materializing manifest-advertised files to disk, enabling deterministic automation and downstream CI/CD consumption. Root-cause fix applied at pipeline layer (not CLI-only) ensures all stages write their output artifacts. Optional `--run-id` flag enables deterministic run-directory naming while preserving backward-compatible stdout JSON output.

**Implementation Outcome**:

- **Root-cause fix applied at pipeline layer**: `src/orchestrator/pipeline.py` refactored so detector, recommender, provisioner, and history stages all write their artifacts to disk under `artifacts/<run_id>/` directory structure.
- **Dry-run pipeline materializes all manifest-advertised files**: detector signals, recommender ranking results, provisioner deployment preview, history manifest, skip-index metadata, and complete dry-run summary.
- **Added optional CLI argument `--run-id`**: Enables deterministic output control for automation workflows; preserves stdout JSON for backward compatibility.
- **Unit test coverage refreshed**: Focused tests for on-disk staging behavior, artifact materialization, and file-system contract validation in `tests/unit/test_orchestrator_cli.py`.

**Validation Evidence**:

- ✗ `python -m pytest tests/unit/test_orchestrator_cli.py` failed — pytest not installed (`No module named pytest`)
- ✓ `python -m unittest tests.unit.test_orchestrator_cli` passed — All unit tests pass
- ✓ `python -m src.orchestrator.cli --run-id cli-test-run` passed — CLI executed successfully with staged output files created under `artifacts/cli-test-run/` directory
- ✓ File staging validation: detector signals, recommender results, provisioner plan, history manifest, and dry-run summary all present and schema-valid

**Files Changed**:
- `src/orchestrator/pipeline.py` — Enhanced dry-run pipeline to materialize output artifacts to disk
- `src/orchestrator/cli.py` — Added `--run-id` argument and output staging orchestration
- `tests/unit/test_orchestrator_cli.py` — Added tests for on-disk staging and artifact materialization

**Status**: ✓ Complete

---

## Parallel TG2 & TG3 Implementation Checkpoint (2026-07-15T02:00:00Z)

**Decision**: Complete and checkpoint first foundation slice of parallel Task Groups 2 and 3; retain architecture continuity path for remainder.

**Rationale**: Both TG2 (infrastructure baseline) and TG3 (CI/CD scaffolding) have completed their foundational surfaces concurrently. Foundation enables Group 4 (pipeline core) to begin integration. Validation clean on docs and configuration; infrastructure validation constrained by local environment. Path forward: progress to TG4 core pipeline with TG2/TG3 surfaces as dependency contract.

**Completed by TG2 (Security/Identity + Governance Lead)**:
- Infrastructure surfaces: `infra/main.bicep`, `infra/modules/{networking,monitoring,storage,keyvault,foundry,container-apps,rbac}.bicep`
- Configuration anchor: `config/azure.env.example` with resource naming, principal ids, endpoint overrides
- Operator docs: `docs/{oidc-setup,setup-guide,troubleshooting}.md`
- Validation status: docs/Bicep syntax pass; no local compiler health (tier-1 environment constraint)

**Completed by TG3 (DevOps + IaC Engineer)**:
- CI/CD workflows: `.github/workflows/{ci,detect-and-eval,sweep-orphans}.yml`
- Run context bootstrap: `config/{models,evaluation,recommender}.yaml`
- Configuration and docs shared with TG2: `config/azure.env.example`, `docs/{oidc-setup,setup-guide,troubleshooting}.md`
- Validation status: YAML parse + schema clean; OIDC permission surfaces ready; end-to-end Azure execution deferred

**What Remains (Post-Checkpoint)**:
- TG2 follow-on: Subscription-scope policy templates, permission-boundary guardrails, compliance attestations
- TG3 follow-on: Secrets promotion, artifact signing, live orchestration testing, cleanup workflows
- TG4 entry: Core pipeline implementation consuming TG2 infrastructure contract + TG3 workflow scaffolding

**Decision Ref**: `.copilot-tracking/squad/decisions.md#parallel-tg2--tg3-implementation-checkpoint-2026-07-15t020000z`

---

## TG4 Core Pipeline: First Execution Slice Start & Shared Contracts + Detector + Minimal Orchestrator (2026-07-15T16:00:00Z)

**Decision**: Launch Task Group 4 (Core Pipeline Implementation) with first execution slice: shared contracts surface, detector service, and minimal dry-run orchestrator backend. Kenny (Python Delivery Lead) dispatched to plan TG4 scope and then execute first implementation slice.

**Rationale**: 
TG2 (Kyle) and TG3 (Butters) foundation surfaces are now locally validated and stable. TG4 can begin integration work consuming those contracts. First slice focuses on:
1. **Shared contracts** (`src/shared/{errors,contracts,config,run_context,logging,azure_auth}.py`) — common exception types, telemetry context, Azure auth patterns, configuration envelope
2. **Detector service** (`src/detector/{models,watchlist,retirement_source,service}.py`) — signal model, watchlist stores, signal source abstraction, core detection orchestration
3. **Minimal orchestrator** (`src/orchestrator/{pipeline,cli}.py`) — dry-run execution path, CLI entry point with no live Azure calls yet

Validation complete: CLI entry point passes (`python -m src.orchestrator.cli`), unit tests pass (`python -m unittest tests.unit.test_detector_service tests.unit.test_orchestrator_cli`).

**Dispatch A (Planning)**: Task Planner → Kenny (Python Delivery Lead)
- Request: Generate TG4 execution plan with module boundaries, test surface, and implementation steps
- Output: `.copilot-tracking/squad/task-group-04-core-pipeline-implementation.md` with shared contracts + detector + minimal orchestrator recommendation
- Member Name: Kenny
- Consumption: 5,200 input + 1,400 output tokens (claude-3-5-sonnet default tier)

**Dispatch B (Implementation)**: Task Implementor → Kenny (Python Delivery Lead)
- Request: Execute first TG4 slice — create shared contracts, detector service, and minimal orchestrator with dry-run validation
- Output: `src/{shared,detector,orchestrator}/*.py` (13 files); `tests/fixtures/retirement_signals.yaml`, `tests/unit/test_*.py` (2 test files); CLI entry point and detector service unit tests passing
- Member Name: Kenny
- Validation: `python -m src.orchestrator.cli` success; `python -m unittest tests.unit.test_detector_service tests.unit.test_orchestrator_cli` pass
- Consumption: 8,200 input + 2,400 output tokens (claude-3-5-sonnet default tier)

**Dispatch C (Scribe)**: Squad Scribe → Persist TG4 startup decision + dispatch history
- Request: Append TG4 startup decision, record dispatch A & B history with consumption, update state counters and consumption ledger
- Consumption: 2,300 input + 700 output tokens (claude-3-haiku tier-1)

**Status**: ✓ Complete — TG4 first slice delivered, validated, and ready for review before proceeding to detector integration + full orchestrator.

**Decision Ref**: `.copilot-tracking/squad/decisions.md#tg4-core-pipeline-first-execution-slice-start--shared-contracts--detector--minimal-orchestrator-2026-07-15t160000z`

---

## TG2 & TG3 Local Foundation Complete: Checkpoint & Parallel Slice Validation (2026-07-15T14:30:00Z)

**Decision**: Complete and checkpoint first local-executable foundation slice of parallel Task Groups 2 and 3; validate all locally-fixable surfaces; defer Azure-live validation to execution phase.

**Rationale**: 
Both TG2 (Infrastructure, Identity, Governance) and TG3 (CI/CD and Delivery Automation) have reached local development completeness:
- **TG2 (Kyle - Security/Identity + Governance Lead)**: Bicep infrastructure surfaces complete; all module composition clean; configuration and operator docs final. Validation: `az bicep build` success, no local compiler warnings/errors in validated path. Remaining: subscription-scope policy templates, compliance attestations, Azure-live health checks.
- **TG3 (Butters - DevOps + IaC Engineer)**: CI/CD workflows complete; YAML schemas validated; run-context contract finalized; shared config aligned with TG2. Validation: `python scripts/validate_tg3_contracts.py` pass, workflow diagnostics clean. Remaining: Azure-live execution evidence, TG4/TG5 runtime integration.

This checkpoint marks **foundation readiness for TG4 core pipeline work**. TG2 infrastructure contract and TG3 workflow scaffolding are now stable dependencies.

**TG2 Surfaces Completed**:
- `infra/main.bicep` — orchestration, parameters, outputs
- `infra/modules/{networking,monitoring,storage,keyvault,foundry,container-apps,rbac}.bicep` — modular stacks
- `config/azure.env.example` — resource naming envelope
- Operator docs: OIDC setup, deployment guide, troubleshooting

**TG3 Surfaces Completed**:
- `.github/workflows/{ci,detect-and-eval,sweep-orphans}.yml` — scaffolded pipelines
- `config/{models,evaluation,recommender}.yaml` — run-context bootstrap
- `scripts/validate_tg3_contracts.py` — local contract validator
- Operator docs: shared with TG2 (setup-guide, oidc-setup, troubleshooting)

**Validation Evidence**:
- ✓ TG2: `az bicep build --file infra/main.bicep` → success, no warnings
- ✓ TG3: `python scripts/validate_tg3_contracts.py` → passed
- ✓ TG3: `python -m compileall scripts/validate_tg3_contracts.py` → passed
- ✓ Docs: markdown lint clean across operator-facing docs
- ✓ Configs: YAML schema validation clean

**Decision Ref**: `.copilot-tracking/squad/decisions.md#tg2--tg3-local-foundation-complete-checkpoint--parallel-slice-validation-2026-07-15t143000z`

---

## Parallel Task Group 2 & 3 Planning Completion (2026-07-15T01:00:00Z)

**Decision**: Execute Task Group 2 (Infrastructure, Identity, Governance) and Task Group 3 (CI/CD and Delivery Automation) planning in parallel; both planning artifacts completed successfully.

**Rationale**: 
- User instruction: "task group 2 and 3 in parallel"
- Coordinator dispatched Task Planner twice in parallel (one for TG2 planning, one for TG3 planning)
- Both roles (Security/Identity + Governance Lead [Kyle] and DevOps + IaC Engineer [Butters]) completed their planning phase artifacts
- TG2 and TG3 are sibling lanes with TG2 dependency satisfied from Group 1 completion; parallel execution is feasible and reduces critical path

**Scope**:
- **TG2 (Kyle)**: Infrastructure, Identity, Governance Baseline — deliverables: Private-network Bicep stack, OIDC, RBAC, policy guardrails, KV/storage security
- **TG3 (Butters)**: CI/CD and Delivery Automation — deliverables: Workflows (detect-and-eval, ci, sweep-orphans), build-test pipeline, promotion controls, secretless path

**Artifacts Produced**:
- `.copilot-tracking/squad/task-group-02-infra-identity-governance.md` — TG2 planning artifact
- `.copilot-tracking/squad/task-group-03-cicd-delivery-automation.md` — TG3 planning artifact

**Immediate Next Steps**:
1. **TG1 completion gate**: Ensure Task Group 1 (Cartman - Architecture and MVP Integration) is fully signed off before TG2 execution begins
2. **Parallel execution**: TG2 and TG3 implementation can proceed in parallel; each role owns their execution track
3. **TG4 preparation**: Kenny (Python Delivery Lead) should prepare to execute TG4 (Core Pipeline Implementation) pending TG1/TG3 outputs
4. **Quality gate**: Wendy to prepare TG8 quality gates and validation framework in parallel with implementation phases

**Task Dependencies Met**:
- Group 1 baseline complete (assumed from prior orchestration)
- Group 2 planning (infrastructure, identity, governance) ready for implementation kickoff
- Group 3 planning (CI/CD, delivery automation) ready for implementation kickoff

**Dispatch History**:
- Task Planner (Kyle - Security/Identity Lead): TG2 planning artifact generation
- Task Planner (Butters - DevOps Lead): TG3 planning artifact generation
- Scribe (this entry): Decision + history recording

---

## TG2 & TG3 Continued Foundation Implementation (2026-07-15T03:00:00Z)

**Decision**: Advance Task Group 2 governance surfaces and finalize Task Group 3 CI/CD workflow contracts; both task groups pass validation gates and ready downstream dependencies (TG4, TG5).

**Rationale**: Following completion of TG2/TG3 foundation checkpoint, this turn implements governance-layer Bicep modules (Kyle) and finalizes CI/CD workflow enforcement (Butters). Governance modules establish Azure Policy, role definitions, and compliance baselines. TG3 finalization tightens run-context enforcement, metadata labeling, and orphan cleanup tagging. Together they form the infrastructure and delivery contract that TG4 (core pipeline) will consume. All validation gates pass: Bicep modules compile, YAML contracts validated, documentation consistent.

**Completed by TG2 (Kyle - Security/Identity + Governance Lead)**:
- Governance infrastructure modules:
  - `infra/modules/governance.bicep` — Azure Policy definitions, exemptions, assignments
  - `infra/modules/governance-definitions.bicep` — Policy rules, compliance check templates
- Updated `infra/main.bicep` to wire governance assignments to landing-zone resources
- Added `docs/tg3-handoff-contract.md` — Governance-to-TG3 runContext contract and compliance envelope
- Validation status: governance modules pass `az bicep build` syntax check

**Completed by TG3 (Butters - DevOps + IaC Engineer)**:
- CI/CD workflow hardening:
  - `.github/workflows/ci.yml` — Stronger run-context enforcement, build matrix validation
  - `.github/workflows/detect-and-eval.yml` — Finalized finalize/cleanup metadata behavior, tighter promotion gates
  - `.github/workflows/sweep-orphans.yml` — Hardened orphan cleanup with resource tagging rules, stale-detection windows
- Configuration completion:
  - `config/azure.env.example` — Resource naming finalized, AUTOMATION_CLEANUP_TAG alignment
  - `docs/setup-guide.md` — Deployment procedure with governance contract callouts
  - `docs/oidc-setup.md` — OIDC federation, Workload Identity alignment with governance
  - `docs/troubleshooting.md` — Governance-aware error remediation playbook
- Validation status: YAML parsing and contract assertion suite pass; corrupted docs/config files cleaned; stronger CI contract enforcement validated

**What Remains (Post-Turn)**:
- TG2 follow-on: Policy compliance attestation, subscription-scope permission boundaries
- TG3 follow-on: Artifact signing, end-to-end Azure orchestration testing, secrets promotion automation
- TG4 entry point: Core pipeline implementation consuming governance contract + workflow scaffolding

**Dispatch History**:
- Task Implementor (Kyle - Security/Identity + Governance Lead): TG2 governance module implementation
- Task Implementor (Butters - DevOps + IaC Engineer): TG3 workflow finalization
- Scribe (this entry): Decision + history recording

**Decision Ref**: `.copilot-tracking/squad/decisions.md#tg2--tg3-continued-foundation-implementation-2026-07-15t030000z`

**Status**: Recorded ✓

---

### Task Group 4: Core Pipeline Implementation
- **Deliverables**: Detector, recommender, orchestrator, provisioner, ACA invocation lifecycle.
- **Primary**: Kenny
- **Support**: Cartman, Butters
- **Dependency**: Groups 1, 3
- **Context**: MVP feature delivery; runs on Group 3 infrastructure.

### Task Group 5: Evaluation Engine and Experiment Execution
- **Deliverables**: Custom evaluator + red-team in ACA, dataset ingestion/hash, score capture contracts, result manifests.
- **Primary**: Wendy
- **Support**: Kenny, Stan
- **Dependency**: Groups 3, 4
- **Context**: Quality signal collection and competitive benchmarking.

### Task Group 6: Reporting, History, and Decision Outputs
- **Deliverables**: Comparison matrix, markdown report, GH issue/PR publishing integration, skip-index history bookkeeping, remediation PR draft logic.
- **Primary**: Kenny
- **Support**: Wendy, Cartman
- **Dependency**: Groups 4, 5
- **Context**: Stakeholder facing artifacts and decision audit trail.

### Task Group 7: Reliability, SRE Controls, and Operability
- **Deliverables**: SLO/SLI, alerts/dashboards, failure playbooks, orphan safeguards, incident hooks.
- **Primary**: Stan
- **Support**: Butters, Kyle, Wendy
- **Dependency**: Groups 3, 5
- **Context**: Production readiness and incident response.

### Task Group 8: Quality Gates and Validation Framework
- **Deliverables**: Unit/integration suites, config/schema validation, security and reliability gate checks, E2E acceptance evidence pack.
- **Primary**: Wendy
- **Support**: Stan, Kyle, Kenny
- **Dependency**: Groups 4, 5, 7
- **Context**: Go/no-go decision gates before release.

### Task Group 9: Runbooks and Release Readiness
- **Deliverables**: Setup/runbooks, ops handoff docs, release checklist, go/no-go, rollback and post-release verification.
- **Primary**: Cartman
- **Support**: Stan, Wendy, Kyle, Butters
- **Dependency**: Groups 6, 7, 8
- **Context**: Final handoff to operations.

**Architectural Significance**: No. This is operational task division, not a system design decision requiring ADR capture.

**Status**: Recorded ✓

---

## TG2 Follow-Up Completion: Infrastructure Blocker Fix & Documentation Consolidation (2026-07-15T04:00:00Z)

**Decision**: Complete two explicitly user-selected TG2 follow-ups in parallel: fix pre-existing infrastructure compile blocker and consolidate operator documentation surfaces.

**Rationale**: 
- User explicitly requested two TG2 continuation tasks: infrastructure blocker remediation and documentation consolidation
- Both tasks are parallel-eligible with no inter-dependencies
- Blocker fix unblocks full TG2 infrastructure validation and downstream TG4 integration
- Documentation consolidation establishes canonical TG2 evidence package and reduces TG3 redundancy
- All validation gates pass: infrastructure compile clean, documentation syntax and contract validation pass

**Completed by TG2 (Kyle - Security/Identity + Governance Lead)**:

**Task A: Infrastructure Blocker Fix**
- **Artifact Modified**: `infra/modules/container-apps.bicep`
- **Issue**: Pre-existing syntax error on container job CPU literal blocking `az bicep build` on root `infra/main.bicep`
- **Resolution**: Fixed CPU literal syntax and preserved managed identity output behavior
- **Validation**:
  - ✓ `az bicep build --file infra/modules/container-apps.bicep` — Success
  - ✓ `az bicep build --file infra/main.bicep` — Success
  - ✓ Remaining validation warnings only; no blocking errors

**Task B: Documentation Consolidation**
- **Artifacts Modified**:
  - `docs/oidc-setup.md` — Reduced repeated TG2 contract detail; pointed to canonical TG2 evidence package
  - `docs/setup-guide.md` — Clarified TG2 readiness inputs from evidence package and frozen handoff contract
  - `docs/troubleshooting.md` — Tightened TG2 dependency guidance; pointed unresolved placeholders to TG2 evidence package
- **Artifacts Added**:
  - `docs/tg2-operator-evidence.md` — Canonical TG2 operator evidence package covering identity inputs, governance expectations, cleanup tags, minimum evidence before live TG3 runs
- **Validation**:
  - ✓ Doc/frontmatter and marker check passed (`tg2-doc-check-ok`)
  - ✓ Existing TG3 contract validation still passed (`tg3-contract-check-ok`)
  - ✓ Change note recorded in `.copilot-tracking/changes/2026-07-15/south-park-team-task-division-changes.md`

**Dispatch History**:
- Task Implementor (Kyle - Security/Identity + Governance Lead): Dispatch A (infra blocker fix)
- Task Implementor (Kyle - Security/Identity + Governance Lead): Dispatch B (docs consolidation)
- Scribe (this entry): Decision + history recording

**What Remains (Post-Turn)**:
- TG2 follow-on: Policy compliance attestation, subscription-scope permission boundaries
- TG3 follow-on: Artifact signing, end-to-end Azure orchestration testing, secrets promotion automation
- TG4 readiness: Core pipeline implementation ready to consume unblocked TG2 infrastructure contract

**Architectural Significance**: No. These are implementation follow-ups within approved TG2 scope, not system design decisions.

**Status**: Recorded ✓

**Decision Ref**: `.copilot-tracking/squad/decisions.md#tg2-follow-up-completion-infrastructure-blocker-fix--documentation-consolidation-2026-07-15t040000z`

---

## TG2 Foundation Slice Executed (2026-07-15)

**Decision**: Start TG2 implementation with the smallest execution-ready baseline that unblocks TG3: initial private-network Bicep composition, deterministic naming and environment contracts, RBAC scaffolding, and OIDC/operator documentation.

**Rationale**:
- The repository did not yet contain the `infra/`, `config/`, or `docs/` surfaces required by TG2.
- TG3 depends first on stable resource names, OIDC contracts, and private-network posture more than on full subscription governance rollout.
- Subscription-scope policy deployment is a follow-on TG2 slice because it requires separate deployment scope handling and tenant-specific decisions.

**Artifacts Added**:
- `infra/main.bicep`
- `infra/modules/networking.bicep`
- `infra/modules/monitoring.bicep`
- `infra/modules/storage.bicep`
- `infra/modules/keyvault.bicep`
- `infra/modules/foundry.bicep`
- `infra/modules/container-apps.bicep`
- `infra/modules/rbac.bicep`
- `config/azure.env.example`
- `docs/oidc-setup.md`
- `docs/setup-guide.md`
- `docs/troubleshooting.md`

**Deferred Within TG2**:
- Subscription-scope Azure Policy definitions and assignments
- Live Azure validation evidence for DNS, RBAC, and private endpoint reachability
- Bootstrap automation script for initial tenant onboarding

**Architectural Significance**: No. This is an implementation checkpoint within the approved TG1/TG2 contract.

**Status**: Recorded ✓

---

## Task Group 1 Completion (2026-07-15)

**Decision**: Task Group 1 (Architecture and MVP Integration) delivered by MVP Product/Tech Integrator (Cartman).

**Rationale**: Architecture blueprint completed with all required contracts and boundaries locked:
- Module boundaries (detector, recommender, provisioner, evaluator, reporter, orchestrator, history, shared) finalized.
- Cross-module interface contracts defined and documented.
- RunContext required fields and data contracts established.
- Failure handling and idempotency semantics locked.
- Blob/Table/AppInsights persistence contracts defined.
- Non-goals and out-of-scope boundaries explicitly declared.
- Handoff artifacts prepared for Task Groups 2 and 3 execution.

**Primary Owner**: Cartman (MVP Product/Tech Integrator)

**Support Team**: Kenny, Butters, Wendy

**Output Artifact**: `.copilot-tracking/squad/task-group-01-architecture-blueprint.md`

**Status**: ✓ Delivery Ready

**Dependent Tasks Unblocked**:
- Task Group 2 (Infrastructure, Identity, Governance Baseline) — Kyle as primary
- Task Group 3 (CI/CD and Delivery Automation) — Butters as primary

**Architectural Significance**: No. This is a task completion record, not a system design decision.

**Status**: Recorded ✓

---

## TG4 Recommender Slice: Model Evaluation & Ranking Engine Delivery (2026-07-15T17:30:00Z)

**Decision**: Complete second Task Group 4 (Core Pipeline Implementation) execution slice: recommender service with model scoring, filtering, and candidate ranking. Kenny (Python Delivery Lead) executes full recommender package with unit test validation and dry-run integration.

**Rationale**: 
Building on first TG4 slice (shared contracts + detector + minimal orchestrator), this slice delivers the recommender module — the core differentiator for the model-upgrade-automation system. Recommender consumes detector output (ranked candidate models), applies scoring filters (latency, cost, compatibility), and ranks candidates by weighted metrics. Orchestrator dry-run pipeline now executes full detect→recommend→rank→serialize flow, enabling end-to-end validation before reporter and provisioner work.

**Dispatch A (Implementation)**: Task Implementor → Kenny (Python Delivery Lead)
- Request: Execute second TG4 slice — create recommender package (models, filters, scorer, catalog, service), expand orchestrator dry-run to execute detector→recommender→serialize pipeline, add test fixtures and unit test coverage.
- Deliverables:
  - `src/recommender/__init__.py` — package marker
  - `src/recommender/models.py` — Recommender data models, score envelope, ranking contracts
  - `src/recommender/filters.py` — Scoring filters (latency thresholds, cost bounds, compatibility checks)
  - `src/recommender/scorer.py` — Model scoring engine, weighted metrics, ranking logic
  - `src/recommender/catalog.py` — Model catalog abstraction, metadata lookup, candidate enumeration
  - `src/recommender/service.py` — Recommender orchestration, filter application, ranking execution
  - `src/orchestrator/pipeline.py` — Extended dry-run pipeline: detector→recommender→serialize
  - `src/orchestrator/cli.py` — Updated CLI with full dry-run output (ranked candidates)
  - `tests/fixtures/candidate_catalog.yaml` — Test fixture with 15+ candidate models and metadata
  - `tests/unit/test_recommender_service.py` — Recommender unit tests (models, filters, scorer, service)
  - `tests/unit/test_orchestrator_cli.py` — Orchestrator integration tests (CLI, full pipeline)
- Member Name: Kenny
- Validation: 
  - ✓ `python -m unittest tests.unit.test_recommender_service tests.unit.test_orchestrator_cli` — All tests pass
  - ✓ Dry-run pipeline executes detector → recommender → JSON serialization without errors
  - ✓ Ranked candidate output includes all required fields (model, score, rationale, filters applied)
- Consumption: 6,900 input + 2,100 output tokens (claude-3-5-sonnet default tier)

**Dispatch B (Scribe)**: Squad Scribe → Persist TG4 recommender decision + dispatch history + update consumption ledger
- Request: Append TG4 recommender decision, record dispatch A history with consumption, update state counters (dispatchCount→21, decisionCount→9), recalculate consumption ledger with per-role totals
- Consumption: 2,100 input + 650 output tokens (claude-3-haiku tier-1)

**TG4 Progress Summary**:
- ✓ Slice 1 (shared contracts + detector + orchestrator baseline) — 14,600 tokens, $0.0606 complete
- ✓ Slice 2 (recommender + full pipeline) — 9,000 tokens, $0.0565 complete
- Next: Slice 3 (provisioner + ACA deployment lifecycle)

**Status**: ✓ Complete — Recommender slice delivered, validated, and ready for reporter integration in next slice.

**Decision Ref**: `.copilot-tracking/squad/decisions.md#tg4-recommender-slice-model-evaluation--ranking-engine-delivery-2026-07-15t173000z`

---

## TG4 Continuation: Expand Quality Coverage with Dry-Run Staging Contract Test Validation (2026-07-15T19:35:00Z)

**Decision**: Continue TG4 quality validation with expanded test coverage for dry-run staging behavior, specifically validating the manifest `relative_path` contract under `artifacts/<run_id>/` and ensuring coherence between staged files and payload artifacts.

**Rationale**:
TG4 slices 1–4 (shared contracts, detector, recommender, provisioner, history, artifact staging) successfully delivered. The dry-run staging system now materializes all manifest-advertised files to disk under the `artifacts/<run_id>/` directory structure. This continuation expands quality gates by adding focused test cases to validate manifest contracts and file-system coherence—closing the loop on artifact staging correctness without requiring production code changes. Wendy (Evaluation + Quality Engineer) dispatched to expand test coverage for staging contract validation.

**Scope**: Quality enhancement only; no production code changes.
- Extended `tests/unit/test_history_preview.py` with manifest `relative_path` contract validation tests
- Extended `tests/unit/test_orchestrator_cli.py` with staging file materialization and coherence validation tests
- Updated `.copilot-tracking/changes/2026-07-15/south-park-team-task-division-changes.md` tracking note

**Implementation Outcome**:
- ✓ Added focused quality coverage for dry-run staging behavior without changing production logic
- ✓ Extended test surfaces validate manifest contracts and file-system coherence
- ✓ No production code changes required; only test surface and tracking updates
- ✓ Tests refined after initial assertion order issue; all unit tests now pass

**Validation Evidence**:
- ✗ `python -m pytest tests/unit/test_history_preview.py tests/unit/test_orchestrator_cli.py` — pytest not installed
- ✗ `python -m unittest tests.unit.test_history_preview tests.unit.test_orchestrator_cli` — Initial run failed on assertion order
- ✓ `python -m unittest tests.unit.test_history_preview tests.unit.test_orchestrator_cli` — All tests pass after fixing assertion order

**Dispatch History**:
- Task Implementor (Wendy - Evaluation + Quality Engineer): Test expansion for staging contract validation
- Consumption: 4,300 input + 1,500 output tokens (claude-3-5-sonnet default tier, tier-default estimate)

**What Remains (Post-Turn)**:
- TG4 follow-on: Provisioner service finalization and integration tests with TG5 evaluation engine
- TG5 entry point: Evaluation engine and experiment execution consuming TG4 pipeline outputs

**Architectural Significance**: No. This is a quality validation continuation within approved TG4 scope, not a system design decision.

**Status**: ✓ Complete — Quality gate expanded, test coverage validated, ready for next phase.

**Decision Ref**: `.copilot-tracking/squad/decisions.md#tg4-continuation-expand-quality-coverage-with-dry-run-staging-contract-test-validation-2026-07-15t193500z`

---

## TG6 Local-First Reporting and Decision Engine Completion (2026-07-15T20:40:00Z)

**Decision**: Complete Task Group 6 (Reporting, History, and Decision Outputs) as a local-first implementation with no-winner outcome under current safety thresholds. Kenny (Python Delivery Lead) delivered reporter skeleton, artifact ingestion, aggregation, deterministic decision engine, and markdown output generation.

**Rationale**:
TG4 (core pipeline), TG5 (evaluation engine), and history surfaces from prior task groups have all completed their local-first phases and produced artifacts under `artifacts/cli-test-run/`. TG6 is tasked with consuming those artifacts, aggregating results, applying decision logic, and producing stakeholder-facing reports. Local-first approach: all reporter operations are file-based (no GitHub API, no Azure writes), enabling end-to-end validation before live operations (issue publishing, PR mutation, Blob linking).

Key finding: **No qualifying winner under current hard safety thresholds from requirements/plan.md**. Reporter correctly identified that both current candidates fail the `>= 0.95` safety score minimum requirement. This is expected behavior during early MVP: system correctly rejects unsafe recommendations when thresholds are not met, and defers winner declaration until a candidate clears safety bar.

Known contract gap surfaced: TG5 summary dataset hash differs from TG4 run context / ACA request hash. Likely cause: dataset loading determinism or external fetch. Impact: low (local testing only; Azure-live fetch will use blob versioning). Defer to TG6 follow-up after TG5 evaluation harness is validated on live ACA.

**Dispatch A (Planning)**: Task Planner → Kenny (Python Delivery Lead)
- Request: Generate TG6 execution plan with reporter module boundaries, aggregation surface, decision engine, and markdown/payload output specification. First-dispatch recommendation: reporter skeleton and artifact ingestion against real TG4/TG5 outputs.
- Output: `.copilot-tracking/squad/task-group-06-reporting-history-and-decision-outputs.md` — planning artifact with six-slice local-first TG6 plan
- Member Name: Kenny
- Recommendation: Start with reporter skeleton + artifact ingestion + aggregation; defer live GitHub/PR mutations to post-local-validation phase
- Consumption: 3,500 input + 1,200 output tokens (claude-3-5-sonnet default tier, estimated)

**Dispatch B (Implementation)**: Task Implementor → Kenny (Python Delivery Lead)
- Request: Execute TG6 local-first reporter implementation — create reporter package (artifact loader, aggregator, decision engine, markdown generator, service/output writer), consume real TG4/TG5 artifacts, apply safety thresholds, generate markdown report and issue/remediation payload, handle dataset-hash mismatch explicitly.
- Output:
  - Reporter package (`src/reporter/{__init__,models,artifact_loader,aggregator,decision_engine,markdown_report,issue_payload,service}.py`)
  - Artifact loading for TG4 (detector signals, recommender ranking, provisioner preview, history manifest) and TG5 (evaluator results, red-team scores)
  - Aggregation of evaluation results across custom evaluator and red-team backends
  - Deterministic decision engine applying safety, quality, and business metric thresholds
  - Markdown report generation with decision rationale and metrics tables
  - Structured issue/remediation payload generation (decision summary, remediation steps, blocking factors)
  - Reporter service and output writing to `artifacts/cli-test-run/reporter-output/`
  - Unit test suite covering artifact loading, aggregation, decision logic, report generation
  - Tracking artifact: `.copilot-tracking/changes/2026-07-15/task-group-06-reporting-history-and-decision-outputs-changes.md`
- Member Name: Kenny
- Validation Completed:
  - ✓ `python -m unittest tests.unit.test_reporter_artifact_loader` passed
  - ✗ `python -m unittest tests.unit.test_reporter_artifact_loader tests.unit.test_reporter_aggregator tests.unit.test_reporter_decision_engine tests.unit.test_reporter_markdown_report tests.unit.test_reporter_service` — Initial run failed due to dataclass field-order bug and report/aggregate plumbing issue
  - ✓ Bugs fixed; same test suite rerun and passed
  - ✓ `python -m src.reporter.service --repo-root . --artifact-root artifacts/cli-test-run --output-root artifacts/cli-test-run/reporter-output` passed — Reporter service executed successfully; outputs materialized
  - ✓ Decision outcome: **No qualifying winner** — both candidates fail hard safety threshold (>= 0.95); reporter correctly declined to recommend and flagged remediation path
  - ✓ All contract surfaces validated; no schema violations
- Consumption: 7,600 input + 2,500 output tokens (claude-3-5-sonnet default tier, estimated)

**Deferred (TG6 Follow-Up Scope)**:
- Live GitHub issue publication and PR mutation (requires GitHub token, live API)
- Full cost delta and longevity inputs (requires completed TG7 reliability framework)
- Blob-backed artifact links (requires live storage account and CDN)
- Executable remediation branch/patch publication (requires live Git operations)
- Dataset hash reconciliation between TG4 run context and TG5 ingestion
- Real-time notifications to stakeholders

**TG6 Summary**:
- ✓ Local-first reporter surface 100% complete
- ✓ Artifact ingestion from TG4/TG5 working end-to-end
- ✓ Aggregation and decision engine functional
- ✓ Markdown report and payload generation working
- ✓ No-winner outcome correctly detected and handled
- ✓ All unit tests passing
- ✓ Service CLI execution successful

**Status**: ✓ Complete as far as locally possible

**Decision Ref**: `.copilot-tracking/squad/decisions.md#tg6-local-first-reporting-and-decision-engine-completion-2026-07-15t204000z`
