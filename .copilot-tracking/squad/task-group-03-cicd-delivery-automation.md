---
title: Task Group 3 CI/CD and Delivery Automation
description: Execution-ready implementation artifact for CI/CD and delivery automation aligned to TG1 contracts and TG2 dependency surfaces
ms.date: 2026-07-15
ms.topic: reference
---
<!-- markdownlint-disable-file -->

# Task Group 3: CI/CD and Delivery Automation

## Ownership

* Lead: Butters (DevOps + IaC Engineer)
* Support: Kyle (Security/Identity + Governance Lead)
* Support: Stan (Platform Reliability + SRE Lead)
* Support: Kenny (Python Delivery Lead)

## Scope

Task Group 3 implements delivery automation and CI/CD guardrails for model-upgrade-automation without implementing application business logic.

In scope:

* Author GitHub Actions workflows for weekly orchestration, CI, and orphan cleanup.
* Wire OIDC-based secretless authentication for workflow runtime.
* Enforce least-privilege permission boundaries in pipeline jobs.
* Implement run orchestration controls: concurrency, retry boundaries, timeout defaults, and deterministic run context propagation.
* Create artifact publishing flow to support downstream reporting and implementation groups.
* Define promotion controls and gated execution behavior.
* Define rollback and safe-failure behavior for CI/CD operations.

Non-goals:

* No source implementation of detector/recommender/evaluator business logic.
* No Bicep module implementation for TG2 infra baseline.
* No APIM routing changes, production traffic switching, or automatic merges.
* No manual secrets stored in repository files or GitHub Actions secrets when OIDC path is available.

## Dependency Links and Contracts

### TG1 Contract Dependencies (hard)

Source: `.copilot-tracking/squad/task-group-01-architecture-blueprint.md`

TG3 must implement the following TG1 requirements exactly:

* D-01 Trigger contract: weekly cron + manual dispatch.
* D-02 RunContext propagation: deterministic `run_id` and required fields.
* D-03 Orchestration flow: invoke/poll/teardown lifecycle for ACA job + candidate deployment lifecycle.
* D-04 Artifact contract: publish and retain paths compatible with TG1 Blob/Table/report contracts.
* D-05 Failure policy: retries/backoff/jitter and idempotent-safe operation boundaries.
* D-06 Orphan safety net: scheduled stale deployment sweeper.

### TG2 Interface Dependencies (hard but parallel-ready)

TG2 output artifact path is pending at time of writing. Until TG2 artifact is published, TG3 uses these interface placeholders as contracts to unblock parallel planning and partial implementation:

* I-01 Identity contract: OIDC federated credential subject(s), tenant/subscription scope, and principal IDs.
* I-02 RBAC matrix: least-privilege role assignments for workflow principal and ACA managed identity.
* I-03 Resource naming map: Foundry, ACA environment/job, Storage, Key Vault, Resource Group names.
* I-04 Network posture proof: private endpoint DNS and no public data-plane path.

Blocking rule:

* TG3 may implement workflow structure, gating, and CI checks before TG2 completion.
* TG3 may not mark delivery-ready until I-01 through I-04 are resolved by TG2 outputs.

## Deliverables and Acceptance Criteria

### Deliverable A: CI Workflow Baseline

Files:

* `.github/workflows/ci.yml`

Acceptance criteria:

* Pull request validation runs lint, unit tests, and static checks for Python and workflow schema.
* Workflow uses least-permissions by default.
* Required checks are deterministic and fail-fast on config/schema violations.

### Deliverable B: Weekly Detect-and-Eval Workflow

Files:

* `.github/workflows/detect-and-eval.yml`

Acceptance criteria:

* Supports `schedule` (weekly Monday 04:00 UTC default) and `workflow_dispatch`.
* Uses concurrency lock to prevent overlapping runs.
* Generates and propagates deterministic `run_id` across steps/jobs.
* Uses OIDC (`id-token: write`) and no long-lived secrets for Azure auth.
* Implements invoke -> poll -> finalize pattern with explicit timeout and retry settings.

### Deliverable C: Orphan Sweeper Workflow

Files:

* `.github/workflows/sweep-orphans.yml`

Acceptance criteria:

* Scheduled daily orphan scan for stale ephemeral model deployments.
* Deletes only resources tagged with automation ownership marker.
* Dry-run mode supported for validation.
* Emits summary artifact/log for auditable cleanup.

### Deliverable D: Promotion and Governance Gates

Files:

* `.github/workflows/detect-and-eval.yml` (gates section)
* `.github/workflows/ci.yml` (required checks)
* `docs/setup-guide.md` (operator gate behavior)

Acceptance criteria:

* Promotion-relevant steps require successful prior quality gates.
* Auto-remediation PR path remains opt-in and disabled by default.
* Failure conditions exit safely with no dangling deployment activity.

### Deliverable E: Pipeline Runtime Configuration Contract

Files:

* `config/azure.env.example`
* `docs/oidc-setup.md`
* `docs/troubleshooting.md`

Acceptance criteria:

* Required environment variables documented and mapped to RunContext fields.
* Secretless OIDC setup is the default and only recommended auth path.
* Troubleshooting covers auth failures, permission mismatches, timeout failures, and cleanup recovery.

## Detailed Task Breakdown (Owner Per Task)

| Task ID | Task | Primary Owner | Support | Dependencies | Parallelizable | Done When |
|---|---|---|---|---|---|---|
| TG3-01 | Build workflow skeletons (`ci`, `detect-and-eval`, `sweep-orphans`) | Butters | Kenny | TG1 D-01 | Yes | All workflow files exist and parse successfully |
| TG3-02 | Add OIDC login and least-privilege job permissions | Kyle | Butters | TG2 I-01, I-02 | Yes | Workflows authenticate via OIDC, no secret creds required |
| TG3-03 | Implement run context bootstrap (`run_id`, env mapping, metadata) | Butters | Kenny | TG1 D-02 | Yes | Required RunContext fields flow end-to-end in workflow jobs |
| TG3-04 | Add invoke/poll/finalize orchestration blocks with retry/timeout defaults | Butters | Kenny, Stan | TG1 D-03, D-05 | No | Workflow lifecycle aligns with TG1 failure handling contract |
| TG3-05 | Implement orphan sweeper policy and tag-safe cleanup rules | Stan | Butters | TG1 D-06 | Yes | Sweeper deletes only owned stale ephemeral resources |
| TG3-06 | Wire CI quality gates (lint/test/schema) and required-check policy | Kenny | Butters | TG3-01 | Yes | PR checks block invalid pipeline changes |
| TG3-07 | Add promotion controls and rollback-safe failure gates | Stan | Kyle, Butters | TG3-04, TG3-06 | No | Failure path is deterministic and safe; no hidden side effects |
| TG3-08 | Publish operator docs for OIDC, runbook snippets, and troubleshooting | Kyle | Stan, Butters | TG3-02, TG3-04 | Yes | Docs are sufficient for onboarding and incident response |
| TG3-09 | Validate full pipeline in non-prod with evidence pack | Stan | Butters, Kenny | TG3-01..TG3-08 | No | End-to-end execution evidence recorded and reproducible |

## Ordered Implementation Sequence

### Sequence 1: Foundation (parallel)

* TG3-01 workflow skeletons
* TG3-03 run context bootstrap
* TG3-06 CI quality gate scaffold

Rationale: no hard dependency on TG2 interfaces beyond naming placeholders.

### Sequence 2: Identity and safety controls (parallel)

* TG3-02 OIDC + least-privilege
* TG3-05 orphan sweeper safety logic
* TG3-08 docs draft

Rationale: can progress while TG2 final artifact is still being finalized, but cannot close release-readiness until TG2 contracts are linked.

### Sequence 3: Execution path (sequential)

* TG3-04 invoke/poll/finalize orchestration
* TG3-07 promotion controls + rollback gates

Rationale: promotion/rollback logic depends on stable execution path behavior.

### Sequence 4: Validation and closeout (sequential)

* TG3-09 end-to-end validation with evidence
* Link TG2 final interfaces (I-01 through I-04) and mark contract resolved

## Quality Gates and Rollback Expectations

### Quality Gates

* QG-01 Workflow lint and schema validation must pass on every PR.
* QG-02 OIDC auth validation must pass in non-prod before schedule enablement.
* QG-03 RunContext completeness check must pass for required TG1 fields.
* QG-04 Orphan sweeper dry-run then live-run validation must pass with ownership-tag filtering.
* QG-05 End-to-end weekly workflow simulation (`workflow_dispatch`) must pass before enabling cron in production branch.

### Rollback Expectations

* RB-01 Immediate rollback path is workflow-level revert to last known good commit.
* RB-02 If detect-and-eval run fails after provisioning, finalize step must attempt teardown and emit cleanup status.
* RB-03 If teardown fails, orphan sweeper run must be triggered/verified within 24 hours.
* RB-04 Promotion controls must fail closed; no partial promotion state is allowed.
* RB-05 Any auth or RBAC regression reverts to prior workflow revision while preserving OIDC-only posture (no fallback secrets).

## Handoff Contracts

### Handoff to TG4: Core Pipeline Implementation (Kenny)

Contract TG3->TG4:

* H-01 Stable workflow entrypoints and expected environment contracts published.
* H-02 RunContext variable map documented and consumed by orchestrator code.
* H-03 Retry/timeout/concurrency defaults published for orchestrator alignment.
* H-04 Artifact and report staging paths finalized for reporter integration.

Acceptance for handoff:

* TG4 can run core orchestration via `workflow_dispatch` in non-prod with no manual pipeline edits.

### Handoff to TG5: Evaluation Track (Wendy)

Contract TG3->TG5:

* H-05 ACA job trigger interface and poll semantics stabilized.
* H-06 Dataset and eval configuration injection path documented.
* H-07 Eval artifact persistence location and naming contract fixed.
* H-08 Cleanup guarantees for ephemeral candidate deployments validated.

Acceptance for handoff:

* TG5 can execute evaluator job lifecycle from pipeline and retrieve persisted results for scoring/reporting.

## File-Level Target Map (TG3 Create/Change Surface)

Execution planning for TG3 should target the following repository paths:

### Workflows

* `.github/workflows/ci.yml` (create/update)
* `.github/workflows/detect-and-eval.yml` (create/update)
* `.github/workflows/sweep-orphans.yml` (create/update)

### Config and pipeline contracts

* `config/azure.env.example` (update for RunContext and auth mapping)
* `config/evaluation.yaml` (read-only dependency for workflow variable alignment)
* `config/recommender.yaml` (read-only dependency for workflow variable alignment)

### Documentation and runbooks

* `docs/setup-guide.md` (update CI/CD setup and operator controls)
* `docs/oidc-setup.md` (create/update secretless setup steps)
* `docs/troubleshooting.md` (update pipeline failure and rollback playbook)
* `README.md` (update workflow usage and trigger controls)

### Optional support scripts (only if needed by execution plan)

* `scripts/bootstrap.ps1` (update OIDC/bootstrap hints only)
* `scripts/local-dev.py` (update local workflow simulation guidance only)

Out-of-scope change guard:

* Do not modify `src/**` business logic as part of TG3.
* Do not modify `infra/**` implementation logic owned by TG2 except documented contract references.

## Execution Readiness Checklist

* [ ] TG1 dependency contracts D-01 through D-06 are mapped to concrete workflow tasks.
* [ ] TG2 interface placeholders I-01 through I-04 are resolved and linked to final artifact.
* [ ] OIDC-only auth path validated; no long-lived secrets required.
* [ ] Least-privilege permissions set at workflow/job level.
* [ ] Concurrency, retry, timeout, and cleanup controls implemented.
* [ ] Quality gates QG-01 through QG-05 pass in non-prod.
* [ ] Rollback expectations RB-01 through RB-05 validated and documented.
* [ ] Handoff contracts H-01 through H-08 accepted by TG4 and TG5 owners.

