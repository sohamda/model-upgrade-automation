---
title: Task Group 1 Architecture Blueprint
description: Implementation-ready architecture contract for model-upgrade-automation Task Group 1
ms.date: 2026-07-15
ms.topic: reference
---
<!-- markdownlint-disable-file -->

## Scope

Task Group 1 defines the implementation contracts for MVP architecture only. It does not implement code or infrastructure.

This blueprint aligns with requirements/plan.md decisions:

* Private networking for Foundry, Storage, and Key Vault data plane access
* OIDC from GitHub Actions to Azure with no long-lived repo secrets
* ARM control plane operations from GitHub Actions
* ACA job data plane execution inside VNet-integrated environment
* No public data plane path

## Module Boundaries (src/*)

| Module | Owns | Inputs | Outputs | Out of Scope |
|---|---|---|---|---|
| src/detector | Retirement detection and watch-list intersection | config/models.yaml, retirement docs, optional ARM deployment inventory | RetiringModel[] | Candidate ranking, provisioning, evaluation |
| src/recommender | Candidate discovery, filtering, deterministic scoring | RetiringModel[], model catalog docs, pricing data, config/recommender.yaml, config/evaluation.yaml | CandidateRank[] per retiring model | Resource creation, model invocation |
| src/provisioner | Candidate deployment lifecycle via ARM | CandidateRank, RunContext | DeploymentRef, teardown result | Data plane inference and scoring |
| src/evaluator | Custom eval and red-team execution in ACA job | DeploymentRef, datasets, thresholds, RunContext | custom.json, redteam.json, metrics events | Ranking policy and report publishing |
| src/reporter | Aggregation, recommendation, markdown and GitHub outputs | Evaluation artifacts, skip/history records, baseline context | docs report, issue payload, optional remediation patch payload | Infra mutation beyond optional draft patch |
| src/orchestrator | End-to-end control flow and run coordination | Full config, module contracts, RunContext | RunState transitions, workflow status, final summary | Model-scoring internals |
| src/history | Skip-index and artifact persistence contract | RunContext, evaluation summaries, raw files | Table entities, blob manifests | Recommendation logic |
| src/shared | Auth, config, logging, typed contracts, error taxonomy | environment and config | Reusable clients, models, utilities | Business decisions per module |

## Interface Contracts

### Detector -> Recommender

Input contract:

* retiring_models: RetiringModel[]
* watched_models: WatchedModel[]
* retirement_horizon_days: int
* run_context: RunContext

Output contract:

* retiring_targets: RetiringTarget[]
* parse_warnings: Warning[]

### Recommender -> Provisioner

Input contract:

* retiring_target: RetiringTarget
* ranked_candidates: CandidateRank[] (already hard-filtered)
* candidates_per_retiring_model: int
* deployment_type_preference: string[]
* allowed_regions: string[]

Output contract:

* provision_requests: ProvisionRequest[] with deterministic idempotency_key

### Provisioner -> Evaluator

Input contract:

* deployment_ref: DeploymentRef (resource_id, deployment_name, region, deployment_type)
* dataset_manifest: DatasetManifest
* eval_thresholds: EvalThresholds
* run_context: RunContext

Output contract:

* eval_job_request: EvalJobRequest
* teardown_plan: TeardownPlan

### Evaluator -> History

Input contract:

* candidate_eval_result: CandidateEvalResult
* dataset_sha256: string
* verdict: winner | rejected | incomplete
* run_context: RunContext

Output contract:

* blob_artifact_manifest: ArtifactManifest
* skip_index_entity: SkipIndexEntity
* metric_batch: AppInsightsMetric[]

### History -> Reporter

Input contract:

* artifact_manifest_list: ArtifactManifest[]
* skip_index_snapshot: SkipIndexEntity[]
* prior_baseline_refs: BaselineRef[]

Output contract:

* report_ready_dataset: ReportDataset

### Reporter -> Orchestrator

Input contract:

* report_dataset: ReportDataset
* recommendation: RecommendationDecision
* publishing_config: PublishingConfig

Output contract:

* report_outputs: ReportOutput[]
* publish_status: PublishStatus
* optional_remediation_pr_payload: RemediationPayload?

### Shared cross-cutting contract

Shared provides:

* Typed models for all interface payloads
* OIDC-authenticated ARM client factory
* Managed identity data plane client factory for ACA runtime
* Correlated structured logging with run_id
* Error taxonomy and retry policy primitives

## Run Context Contract (required fields)

Every module boundary call carries RunContext. Required fields:

| Field | Type | Required | Purpose |
|---|---|---|---|
| run_id | string | Yes | Global correlation key across workflow, ACA, blobs, table, telemetry |
| trigger_type | cron \| workflow_dispatch | Yes | Audit and execution policy |
| started_at_utc | datetime | Yes | Latency and timeout windows |
| github_repo | string | Yes | Publishing target and provenance |
| github_run_id | string | Yes | CI traceability |
| azure_tenant_id | string | Yes | Auth boundary |
| azure_subscription_id | string | Yes | ARM scope |
| resource_group | string | Yes | Resource addressing |
| foundry_account_name | string | Yes | Deployment target |
| foundry_project_name | string | Yes | Deployment namespace |
| aca_environment_name | string | Yes | Eval execution plane |
| aca_job_name | string | Yes | Eval job invocations |
| storage_account_name | string | Yes | Blob/Table persistence |
| key_vault_name | string | Yes | Optional secrets retrieval |
| deployment_type | DataZoneStandard \| GlobalStandard \| Regional \| PTU | Yes | Candidate compatibility and reporting |
| allowed_regions | string[] | Yes | Hard region guardrail |
| retirement_horizon_days | int | Yes | Detection gate |
| dataset_sha256 | string | Yes | Skip-index key component |
| correlation_version | string | Yes | Contract evolution control |

## Failure-Handling Contract

### Error categories

| Category | Examples | Handling | Reported as |
|---|---|---|---|
| transient_control_plane | ARM 429/5xx, ACA start poll timeout windows | Retry with backoff and jitter | warning unless retries exhausted |
| transient_data_plane | temporary model endpoint errors from ACA side | Retry inside evaluator job | warning unless retries exhausted |
| deterministic_config | invalid yaml, missing required field, invalid threshold | Fail fast, no retry | error |
| deterministic_contract | missing required RunContext field, schema mismatch | Fail fast, no retry | error |
| dependency_unavailable | pricing/catalog/doc fetch unavailable | Continue with degraded path when safe, otherwise mark candidate incomplete | warning or error based on impact |
| safety_gate_failure | score below hard threshold or block rate below minimum | No retry, mark rejected | informational rejection |

### Retry policy

* Max attempts for transient classes: 3
* Backoff: exponential, capped
* Jitter: required
* Retry scope:
  * Orchestrator retries control plane operations
  * Evaluator retries data plane operations

### Idempotency policy

* Idempotency key format: run_id + retiring_model_id + candidate_model_id + candidate_version + dataset_sha256
* Provisioner create/delete operations must be safe on repeated calls
* History upsert must be key-stable and overwrite-safe
* Reporter publish must support retry-safe upsert/update semantics for weekly issue and branch commits

## Data Artifact Contract

### Blob contract

Container: eval-artifacts
Path: run_id/retiring_model/candidate_model/version/
Required blobs:

* custom.json
* redteam.json
* manifest.json
* logs.jsonl

manifest.json required fields:

* run_id
* retiring_model_id
* candidate_model_id
* candidate_version
* deployment_type
* region
* dataset_sha256
* custom_score_summary
* redteam_block_rate
* verdict
* created_at_utc

### Table contract

Table: evalhistory

* PartitionKey: retiring_model_id
* RowKey: candidate_model_id__candidate_version__dataset_sha256_first16

Required properties:

* RunId
* EvaluatedAt
* DatasetSha256
* DeploymentType
* Region
* BlobArtifactUrl
* CustomScoreSummary
* RedTeamBlockRate
* OverallVerdict
* TtlDays

### App Insights contract

Required metric:

* mua.eval.score with dimensions run_id, retiring_model, candidate_model, candidate_version, evaluator, deployment_type, region

Required event:

* mua.run.completed with run duration, cost estimate, and verdict summary

Required trace property:

* run_id on every orchestrator and evaluator trace record

## Non-goals and Out-of-Scope Boundaries

* No APIM routing changes as part of MVP automation
* No production traffic switching automation
* No model fine-tuning or training pipeline
* No generalized model benchmark platform beyond retirement-driven replacement flow
* No multi-tenant control plane in MVP
* No public data plane fallback path
* No irreversible auto-remediation merge behavior

## Dependency Handoff Notes

### Handoff to Task Group 2 (Infrastructure, Identity, Governance)

Task Group 2 must implement infrastructure and identity exactly against this contract:

* Private endpoints and private DNS for Foundry, Blob, Table, Key Vault
* VNet-integrated ACA environment for evaluator job
* OIDC federated identity for GitHub Actions ARM control plane access
* Managed identity RBAC for ACA data plane access
* ARM-only orchestration permissions for pipeline identity

Task Group 2 output needed by Task Group 1 consumers:

* Final resource naming map and resource IDs
* RBAC matrix mapped to run context fields
* Network validation proof that data plane stays private

### Handoff to Task Group 3 (CI/CD and Delivery Automation)

Task Group 3 must wire workflows to this orchestration contract:

* Weekly cron plus manual dispatch trigger support
* Concurrency guard to prevent overlapping runs
* Deterministic run_id generation and propagation into RunContext
* Reliable invoke/poll/teardown flow for ACA job and candidate deployments
* Required artifact publishing paths and report generation trigger

Task Group 3 output needed by downstream implementation:

* Workflow variable mapping to RunContext fields
* Retry and timeout defaults consistent with failure-handling contract
* Orphan sweep job for stale ephemeral deployments

## Implementation Readiness Notes

This blueprint is contract-complete for downstream module implementation by Task Groups 2 and 3 and for feature delivery by later groups. Any contract change must be appended to squad decisions before implementation divergence.
