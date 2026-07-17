<!-- markdownlint-disable-file -->
# Implementation Details: GPT-4.1 Retirement Alternatives Live Foundry Flow

## Context Reference

Sources: requirements/plan.md, .copilot-tracking/research/2026-07-17/gpt-41-retirement-alternatives-research.md, .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md

## Implementation Phase 1: Domain Contracts, Config, and Orchestration Modes

<!-- parallelizable: false -->

### Step 1.1: Expand shared contracts for evidence-backed recommendations

Replace fixture-era contract assumptions with explicit fields required for live Azure discovery, recommendation traceability, provisioning state, evaluation manifests, and publication outcomes.

Files:
* src/shared/contracts.py - Add or update dataclasses/models for source provenance, candidate eligibility, deployment operation state, run manifest schema, and report status taxonomy.
* src/reporter/models.py - Align report and decision models with new run statuses and fail-closed states.

Success criteria:
* All recommendation and decision objects include source provenance and freshness metadata.
* Candidate and deployment entities can represent partial provisioning and evaluation failures without collapsing the run.
* Reporter models can express blocked outcomes such as catalog stale, incomplete comparison, and cleanup pending.

Context references:
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 1-241) - Current gaps and required contracts.
* requirements/plan.md (Lines 1-110) - Product behavior and private-network constraints.

Dependencies:
* None.

### Step 1.2: Extend configuration and CLI surface for dual source input

Implement explicit user input for retiring model/version while preserving watch-list and optional Azure deployment discovery.

Files:
* src/shared/config.py - Add model source mode, foundry account scopes, cache policy, candidate policy, and gating policy.
* src/orchestrator/cli.py - Add inputs for retiring model, retiring version, workload, region, run mode, and confirmation/approval IDs.
* config/models.yaml - Add backward-compatible sections for explicit targets and discover-from-azure settings.
* config/evaluation.yaml - Add policy fields for budget cap, minimum successful evaluations, stale-source handling, and approval requirement.
* config/recommender.yaml - Add weights and hard constraints based on documented capabilities and lifecycle.

Success criteria:
* Tool can run with either explicit target input, discovery mode, or both.
* New config fields remain backward compatible with fixture-only defaults.
* CLI enforces explicit model+version requirement for unattended live provisioning.
* Config includes explicit v1 policy defaults: `candidate_scope=azure_openai_only`, `require_baseline_for_winner=true`, `allow_global_residency=false`, `max_cost_per_run_usd=30`, `max_cost_per_target_usd=12`, `max_cost_per_month_usd=250`, `max_replacement_attempts=2`, `min_successful_evaluations_for_winner=2`.

Context references:
* requirements/plan.md (Lines 13-37) - Source behavior and candidate count.
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 241-520) - Configuration expansion recommendations.

Dependencies:
* Step 1.1 completion.

### Step 1.3: Introduce run state machine and fail-closed transitions

Codify allowed orchestration transitions and ensure mutation steps are unreachable without approvals.

Files:
* src/orchestrator/pipeline.py - Add explicit state transitions discover -> research -> ranked -> approval -> provision -> evaluate -> decide -> cleanup -> publish.
* src/shared/run_context.py - Add approval binding, source snapshot hashes, and mode metadata.
* src/orchestrator/main.py or equivalent entrypoint module - Enforce mode semantics consistently.

Success criteria:
* Default mode is research-only with no mutations.
* Provisioning path requires approval token and run-bound plan hash.
* Final report reflects precise terminal state even on partial failures.

Context references:
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 261-379) - State machine and safety gates.

Dependencies:
* Step 1.1 completion.
* Step 1.2 completion.

### Step 1.4: Validate phase changes

Run lint and tests for shared domain and orchestration behavior.

Validation commands:
* python -m pytest -q tests/unit/test_orchestrator_cli.py tests/unit/test_detector_service.py tests/unit/test_recommender_service.py
* python -m pytest -q tests/unit/test_reporter_models.py -k status

## Implementation Phase 2: Live Retirement and Catalog Source Adapters

<!-- parallelizable: true -->

### Step 2.1: Implement retirement schedule adapter with cache and provenance

Add a source adapter that fetches current Microsoft retirement schedule and emits normalized retirement signals with immutable provenance.

Files:
* src/detector/retirement_schedule_source.py - New adapter parsing authoritative retirement schedule pages.
* src/detector/retirement_source.py - Compose fixture and live source implementations.
* src/recommender/catalog_cache.py - Shared source cache helper with ETag/Last-Modified support.

Success criteria:
* Retirement adapter returns normalized entries with source URL, retrieved timestamp, source revision, and content hash.
* Adapter supports cache hits and 304 revalidation.
* Parsing failures are surfaced as explicit run blockers in live mode.

Context references:
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 89-162) - Source URLs and parsing requirements.

Dependencies:
* Step 1.1 completion.

### Step 2.2: Implement Foundry catalog and region availability adapters

Fetch and normalize current model catalog and region availability so eligibility and ranking are based on live documented facts.

Files:
* src/recommender/foundry_catalog_source.py - New adapter for model catalog plus region availability sources.
* src/recommender/catalog.py - Shift from fixture-only source to protocol-based source selection.
* src/recommender/eligibility.py - New hard eligibility rules based on documented capability, lifecycle, and region/deployment support.

Success criteria:
* Catalog records include model id, version, lifecycle, capabilities, and region/deployment availability.
* Eligibility gate excludes retired/stale/incompatible candidates before scoring.
* Adapter emits parser version and source hashes for reproducibility.

Context references:
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 101-162) - Current catalog and region availability sources.

Dependencies:
* Step 2.1 completion.

### Step 2.3: Add Azure deployment inventory discovery for retiring targets

Enable discovery from live Foundry account deployments in addition to user-supplied targets.

Files:
* src/detector/deployed_introspector.py - New SDK adapter using Cognitive Services deployments list/get.
* src/detector/target_resolver.py - New merger of explicit inputs, watch-list targets, and discovered deployment inventory.
* src/detector/service.py - Integrate resolver and horizon filtering.
* src/shared/azure_auth.py - Replace placeholder with credential/client factories.

Success criteria:
* Tool can discover deployed models and map them into retiring targets.
* Explicit user input can bypass watch-list mismatch while still logging warnings.
* Discovery path records account and deployment identity needed for safe provisioning and cleanup.

Context references:
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 163-241) - SDK and discovery details.

Dependencies:
* Step 1.2 completion.
* Step 2.1 completion.

### Step 2.4: Validate phase changes

Run parser and source integration unit tests.

Validation commands:
* python -m pytest -q tests/unit/test_retirement_schedule_source.py tests/unit/test_foundry_catalog_source.py tests/unit/test_catalog_cache.py
* python -m pytest -q tests/unit/test_deployed_introspector.py tests/unit/test_target_resolver.py

## Implementation Phase 3: Candidate Recommendation and Top-3 Selection Policy

<!-- parallelizable: true -->

### Step 3.1: Implement deterministic scoring with documentation-backed factors

Score only eligible candidates and rank based on documented longevity, capability match, regional deployability, and configured cost/quality/safety priorities.

Files:
* src/recommender/scorer.py - Expand score components and emit score breakdown.
* src/recommender/service.py - Enforce top 3 recommendation selection and policy-driven fallback behavior.
* src/recommender/filters.py - Remove fixture-only assumptions and call eligibility rules.

Success criteria:
* Recommendation output includes exactly top 3 candidates when 3+ eligible candidates exist.
* When fewer than 3 qualify, output explicitly marks incomplete comparison and blocks automatic winner.
* Score output is auditable with component-level explanation.
* GPT-4.1 compatibility profile is enforced through required capabilities: `chat_completions`, `responses`, `function_calling`, `structured_outputs`, and text input.

Context references:
* requirements/plan.md (Lines 22-39) - Top 2-3 candidate behavior.
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 379-520) - Ranking and policy recommendations.

Dependencies:
* Step 2.2 completion.

### Step 3.2: Add source freshness and stale-data fail-closed checks

Require current source freshness for live provisioning eligibility and recommendation confidence.

Files:
* src/recommender/service.py - Enforce source freshness policy and run status transitions.
* src/reporter/decision_engine.py - Block recommendations on stale/incomplete evidence.
* src/reporter/aggregator.py - Carry freshness and exclusion reasons into report payload.

Success criteria:
* Live provisioning cannot proceed if retirement or catalog evidence is stale beyond configured threshold.
* Report clearly distinguishes research-only advisory from provision-ready recommendation.

Context references:
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 181-241) - Caching and fallback strategy.

Dependencies:
* Step 3.1 completion.

### Step 3.3: Validate phase changes

Run recommender and reporter decision unit tests.

Validation commands:
* python -m pytest -q tests/unit/test_recommender_service.py tests/unit/test_candidate_eligibility.py
* python -m pytest -q tests/unit/test_reporter_decision_engine.py tests/unit/test_reporter_aggregator.py

## Implementation Phase 4: Safe Provisioning, Teardown, and Operation Ledger

<!-- parallelizable: false -->

### Step 4.1: Implement SDK-based deployment lifecycle adapter

Create, poll, and delete candidate deployments using Azure management SDK with pinned versions and safety tags.

Files:
* src/provisioner/azure_deployments.py - New adapter for list/get/create/delete with long-running operation handling.
* src/provisioner/service.py - Replace planning-only flow with live lifecycle orchestration.
* src/provisioner/deployment_plan.py - Add run-unique naming, explicit version pinning, NoAutoUpgrade, and full cleanup tags.
* pyproject.toml - Add required runtime dependencies.

Success criteria:
* Provisioner creates exactly the approved candidate deployments (up to 3).
* Every create call includes explicit model version and no-auto-upgrade behavior.
* Teardown is idempotent and always attempted in finally block.

Context references:
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 163-241) - Azure APIs and deployment schema.
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 261-379) - Safety gates and cleanup policy.

Dependencies:
* Step 1.3 completion.
* Step 3.2 completion.

### Step 4.2: Implement confirmation and budget gates

Add pre-provision immutable plan approval binding and budget checks before each create operation.

Files:
* src/orchestrator/pipeline.py - Add approval verification and budget policy checks before mutations.
* src/shared/config.py - Add budget policy and required approver mode.
* src/history/table_skip_index.py - New table adapter for operation ledger and skip-index records.
* src/history/blob_artifact_store.py - New blob adapter for immutable plan/evidence artifacts.
* src/history/skip_index.py - Refactor into repository interface plus policy logic.
* src/history/manifest_builder.py - Refactor preview manifest builders to support durable run-manifest composition while preserving pure builder utilities for tests.

Success criteria:
* No mutation occurs without required approval state and plan hash match.
* Budget policy can block create attempts before exceeding configured cost ceilings.
* Operation ledger persists create/evaluate/cleanup state for recovery.
* Confirmation gate behavior is explicit:
	* Scheduled runs default to research-only.
	* Provisioning requires protected-environment approval and immutable plan-hash binding.
	* Approval payload includes run_id, target model/version, 3 planned candidates, and budget envelope.

Context references:
* requirements/plan.md (Lines 40-75) - Cost and control requirements.
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 320-447) - Gating and history model.

Dependencies:
* Step 4.1 completion.

### Step 4.3: Tighten orphan sweeper selection safety

Ensure sweeper can only delete deployment resources created by this tool and this scope.

Files:
* .github/workflows/sweep-orphans.yml - Restrict scope to Cognitive Services deployment resource IDs and strict tag predicates.
* src/provisioner/deployment_plan.py - Emit tags required by sweeper predicate.
* tests/unit/test_sweep_selection.py - New tests for selection logic.

Success criteria:
* Sweeper cannot delete non-tool resources even if tags partially overlap.
* Tag contract between provisioner and sweeper is consistent and tested.

Context references:
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 120-148) - Current sweeper mismatch.

Dependencies:
* Step 4.1 completion.

### Step 4.4: Validate phase changes

Run provisioning and history tests plus optional scratch integration tests.

Validation commands:
* python -m pytest -q tests/unit/test_provisioner_service.py tests/unit/test_azure_deployments.py tests/unit/test_table_skip_index.py tests/unit/test_blob_artifact_store.py
* python -m pytest -q tests/integration/test_foundry_deployment_lifecycle.py -m azure_integration

## Implementation Phase 5: ACA Evaluation Execution and Durable Results

<!-- parallelizable: false -->

### Step 5.1: Implement ACA job dispatch and polling

Replace deferred ACA dispatcher with real start/poll flow and run-manifest-based completion checks.

Files:
* src/evaluator/aca_job.py - Implement start and execution polling through Azure management API.
* src/evaluator/run_manifest.py - New schema and validators for evaluator input/output manifests.
* src/evaluator/input_builder.py - Use real deployment resource IDs and dataset digest.
* src/evaluator/result_writer.py - Persist per-candidate completion manifests and hash-verified result summaries to blob storage.

Success criteria:
* Evaluator dispatch returns execution identity and terminal status.
* Timeout and failure states are captured per candidate without collapsing full run.
* Candidate completion requires validated run manifest written to blob storage.
* Completion manifest records evaluator versions, dataset hash, candidate deployment identity, and result artifact hashes.

Context references:
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 165-180) - ACA APIs.
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 447-520) - Run manifest requirements.

Dependencies:
* Step 4.2 completion.

### Step 5.2: Replace synthetic evaluator runners with Azure-capable runners

Use Azure AI Evaluation-compatible custom and red-team runners in ACA execution environment.

Files:
* src/evaluator/custom_runner.py - Refactor to interface or local stub implementation.
* src/evaluator/redteam_runner.py - Refactor to interface or local stub implementation.
* src/evaluator/azure_custom_runner.py - New live custom evaluation runner.
* src/evaluator/azure_redteam_runner.py - New live red-team runner.
* src/evaluator/service.py - Update orchestration to run live in ACA mode and retain local fixture mode.
* docker/evaluator/requirements.txt - Add runtime packages for live evaluation.
* docker/evaluator/Dockerfile - Build evaluator image for ACA jobs.

Success criteria:
* Live evaluation mode uses real deployed candidates and dataset inputs.
* Local mode remains available for fast developer validation.
* Evaluation results include evaluator versions and dataset hash.

Context references:
* requirements/plan.md (Lines 23-35) - Custom and red-team evaluation requirement.
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 130-148) - Current synthetic behavior.

Dependencies:
* Step 5.1 completion.

### Step 5.3: Validate phase changes

Run evaluator unit/integration tests.

Validation commands:
* python -m pytest -q tests/unit/test_evaluator_aca_job.py tests/unit/test_evaluator_service.py tests/unit/test_run_state_machine.py
* python -m pytest -q tests/integration/test_aca_evaluation_execution.py -m azure_integration

## Implementation Phase 6: Reporting, Publication, and Workflow Wiring

<!-- parallelizable: false -->

### Step 6.1: Implement durable reporting and publication adapters

Produce decision-ready reports from durable artifacts and publish to GitHub with draft-remediation gating.

Files:
* src/reporter/service.py - Read blob/table-backed manifests and generate final report statuses.
* src/reporter/aggregator.py - Aggregate per-candidate evidence and failure reasons.
* src/reporter/decision_engine.py - Fail-closed policy for recommendation readiness.
* src/reporter/github_publisher.py - New issue and draft-PR publication adapter.
* src/reporter/markdown_report.py and src/reporter/remediation_payload.py - Ensure report and remediation payloads include evidence hashes and gating status.

Success criteria:
* Report explicitly states recommendation status and blocking reasons.
* Remediation PR creation is skipped unless policy and approvals allow it.
* Publication is idempotent per run_id.
* Remediation generation is constrained to Bicep IaC files only and explicitly excludes APIM/routing or production traffic-switch edits.

Context references:
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 447-520) - Decision/reporting model requirements.

Dependencies:
* Step 5.2 completion.

### Step 6.2: Wire GitHub workflows to real orchestration path

Replace placeholder workflow steps with orchestrator execution and protected approval boundaries.

Files:
* .github/workflows/detect-and-eval.yml - Replace placeholder logic with research, approval, provision, evaluate, collect, cleanup, and publish jobs.
* .github/workflows/ci.yml - Add unit suite expansion and optional integration matrix separation.
* tests/unit/test_workflow_gate_config.py - Add workflow-configuration tests asserting protected-environment approval and `ENABLE_SCHEDULED_PROVISIONING` guards for live provisioning paths.
* docs/setup-guide.md and docs/troubleshooting.md - Update operational and failure-mode guidance.

Success criteria:
* Scheduled run remains research-only unless explicit scheduled provisioning gate is enabled.
* Live mutation path requires protected environment approval.
* Cleanup runs with if: always() and publishes cleanup evidence.
* Workflow regression tests fail if live provisioning jobs are runnable without protected-environment approval and configured scheduled provisioning gate.

Context references:
* requirements/plan.md (Lines 56-110) - Public control-plane and private evaluation architecture.
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 521-760) - Workflow restructuring guidance.

Dependencies:
* Step 4.2 completion.
* Step 5.2 completion.
* Step 6.1 completion.

### Step 6.3: Validate phase changes

Run reporter and workflow-focused tests.

Validation commands:
* python -m pytest -q tests/unit/test_reporter_service.py tests/unit/test_github_publisher.py tests/unit/test_reporter_decision_engine.py
* python -m pytest -q tests/e2e/test_retirement_alternatives_workflow.py

## Implementation Phase 7: Final Validation and Readiness Review

<!-- parallelizable: false -->

### Step 7.1: Run full project validation

Execute full lint, unit tests, and configured integration/e2e suites.

Validation commands:
* python -m pytest -q
* python -m pytest -q tests/integration -m azure_integration
* python -m pytest -q tests/e2e/test_retirement_alternatives_workflow.py

### Step 7.2: Fix minor validation issues

Apply targeted fixes for straightforward lint/test regressions in modified modules.

### Step 7.3: Report blocking issues and release gates

If unresolved issues remain, publish a release-readiness checklist with unresolved risks and required product decisions before enabling scheduled provisioning.

## Dependencies

* Azure SDK libraries for identity, Cognitive Services, Container Apps management, Blob/Table Storage, and evaluation.
* Existing Azure OIDC GitHub environment wiring.
* Scratch Azure environment for integration test execution.

## Success Criteria

* Tool supports both explicit retiring model input and live Foundry deployment discovery.
* Tool retrieves current retirement/catalog/availability evidence and recommends top 3 candidates from current documented Azure data.
* Provisioning is approval-gated and budget-gated before creating any deployment.
* Tool can provision up to 3 candidates, run evaluations, and publish fail-closed decision reports.
* Cleanup is always attempted and evidence is durable for audit and replay.