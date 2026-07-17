---
title: Task Group 7 Reliability SRE Controls and Operability
description: Execution-ready reliability and operability plan grounded on 002 slice infrastructure and Gate B PASS evidence
ms.date: 2026-07-17
ms.topic: reference
---
<!-- markdownlint-disable-file -->

# Task Group 7: Reliability, SRE Controls, and Operability

## Ownership

* Lead: Stan (Reliability + Operability Lead)
* Support: Butters (CI/CD Delivery)
* Support: Kyle (Infrastructure + Governance)
* Support: Wendy (Evaluation + Quality)

## Objective

Define and implement the minimum production-safe reliability layer for the model-upgrade-automation system so failures are detected quickly, triaged consistently, cleaned safely, and handed off to TG8/TG9 with measurable operational controls.

TG7 starts immediately after Gate B PASS and uses the 002 slice as the ground truth for reliability signals, alert contracts, and operability workflows.

## Evidence Baseline and Execution Context (2026-07-17)

### Proven gate status

* Gate A: PASS (002 infrastructure slice validated)
* Gate B: PASS (post-remediation)
  * `detect-and-eval.yml` successful run: `29577754373`
  * `sweep-orphans.yml` successful run: `29577762865`

### Gate B reliability-relevant evidence

From `.copilot-tracking/squad/azure-gate-b-2026-07-17.md`:

* OIDC login succeeded in both workflows after federated credential remediation.
* Lifecycle execution succeeded end-to-end in `detect-and-eval`:
  * bootstrap run context
  * invoke/poll placeholder
  * finalize and cleanup handoff
* Artifact persistence succeeded for run-context, orchestration artifacts, finalize summary, and sweep summary.
* Orphan sweep dry-run executed successfully with tagging query and summary upload.

### 002 slice operating surfaces

* Resource group: `rg-mua-dev-001`
* Foundry account: `fnd-mua-dev-002`
* ACA environment: `acaenv-mua-dev-002`
* ACA job: `aca-mua-eval`
* Storage account: `stmuadev002`
* Key Vault: `kv-mua-dev-002`
* Ownership/cleanup tags:
  * `owner=model-upgrade-automation`
  * `managedBy=model-upgrade-automation`
  * `cleanup=ephemeral`
  * `scope=ephemeral`

## Scope

In scope:

* SLI/SLO definition for detect/evaluate/sweep lifecycle.
* Alert and dashboard contracts for pipeline reliability and cleanup safety.
* Failure playbooks for known failure modes (OIDC, artifact persistence, invoke/poll, sweep).
* Orphan safeguards and escalation triggers.
* Incident hooks and event taxonomy for downstream quality/release gates.
* Reliability validation gates and evidence package for TG8/TG9 handoff.

Out of scope:

* Re-implementing TG3 workflows from scratch.
* Changing TG4/TG5 business logic.
* Automatic production cutover decisions.
* Human pager/on-call tooling onboarding outside repository-managed hooks.

## Dependency Matrix

| Dependency | Producer | Status | TG7 Usage |
|---|---|---|---|
| TG3 workflow contracts (`detect-and-eval`, `sweep-orphans`) | TG3 | Ready + Gate B proven | Primary reliability signal source |
| TG4 run context + orchestration artifacts | TG4 | Ready | SLI input for lifecycle completeness |
| TG5 evaluator outputs | TG5 | Local-first ready | Signal for evaluation success/failure ratios |
| TG6 reporter outputs and no-winner behavior | TG6 | Local-first complete | Incident hooks and remediation escalation triggers |
| TG2 governance/tagging contract | TG2 | Ready | Orphan sweep safety guardrails |

## Concrete Task Plan

### TG7-01 Reliability Signal Contract and Baseline SLI Extractor (first implementation slice)

* Owner: Stan
* Support: Butters
* Goal: Freeze a canonical reliability signal schema and produce first computed SLI snapshot from proven Gate B runs.
* Inputs:
  * Run `29577754373` (`detect-and-eval`)
  * Run `29577762865` (`sweep-orphans`)
  * Existing artifact directories under `artifacts/`
* Deliverables:
  * Reliability signal schema (workflow/job/step/event/severity/recovery metadata)
  * Baseline SLI snapshot (`mttr_seed`, `success_ratio_seed`, `artifact_persistence_ratio_seed`, `orphan_sweep_success_seed`)
  * Contract doc for TG8 gate consumption
* Exit criteria:
  * Schema versioned and checked into repo docs
  * Baseline SLI snapshot reproducible from command line

### TG7-02 SLI/SLO Policy Definition

* Owner: Stan
* Support: Wendy
* Goal: Define measurable reliability objectives aligned to current architecture and known failure patterns.
* Deliverables:
  * SLI formulas and data-source mapping
  * SLO targets and burn thresholds
  * Error budget policy draft for release gating
* Exit criteria:
  * Each SLI has one primary source and one fallback source
  * Every SLO has severity threshold and action owner

### TG7-03 Alert Routing Contract (Pipeline + Cleanup)

* Owner: Butters
* Support: Stan
* Goal: Add deterministic alert rules for critical reliability events.
* Deliverables:
  * Alert rules catalog (critical/high/medium)
  * Mapping from workflow failure states to incident categories
  * Alert payload schema for incident hook integration
* Exit criteria:
  * All high-severity failure modes produce one canonical alert payload

### TG7-04 Dashboard Surfaces (Ops Read Model)

* Owner: Stan
* Support: Wendy
* Goal: Define and bootstrap dashboard views for fast triage.
* Deliverables:
  * Dashboard panel list with queries/data adapters
  * Reliability trend panel specs (24h/7d/30d)
  * Candidate-eval health panel specs
* Exit criteria:
  * Dashboard contract references all SLI metrics and alert states

### TG7-05 Failure Playbooks

* Owner: Stan
* Support: Kyle, Butters
* Goal: Write deterministic runbooks for top failure categories.
* Deliverables:
  * OIDC federation mismatch playbook
  * Artifact upload/path regression playbook
  * Invoke/poll timeout or partial-completion playbook
  * Sweep-orphans query or deletion guardrail playbook
* Exit criteria:
  * Every playbook includes detect, contain, recover, verify, and prevent sections

### TG7-06 Orphan Safeguards Hardening

* Owner: Kyle
* Support: Butters
* Goal: Enforce safe cleanup boundaries and prevent destructive drift.
* Deliverables:
  * Required-tag enforcement checklist before sweep
  * Dry-run-first and max-delete guardrails
  * Protected-resource deny list contract
* Exit criteria:
  * Sweep action cannot proceed to destructive mode without safety predicates

### TG7-07 Incident Hook Integration Points

* Owner: Stan
* Support: Wendy
* Goal: Define repository-level incident event hooks usable by TG8/TG9.
* Deliverables:
  * Incident event taxonomy (`reliability.alert.raised`, `reliability.incident.opened`, `reliability.incident.resolved`)
  * Hook payload schemas and storage path conventions
  * Correlation ID contract (`run_id`, `resource_slice`, `retiring_model`, `candidate_model`)
* Exit criteria:
  * Hook schema is consumable without additional transformation by TG8 validation jobs

### TG7-08 Reliability Validation Gate Suite

* Owner: Wendy
* Support: Stan
* Goal: Introduce pass/fail checks for reliability controls before release validation.
* Deliverables:
  * Gate definitions: RG-01..RG-05
  * Minimal automated checks for SLI freshness, alert firing, and playbook coverage
  * Evidence bundle format for gate outcomes
* Exit criteria:
  * Reliability gate produces deterministic PASS/FAIL with evidence links

### TG7-09 Handoff Package to TG8

* Owner: Stan
* Support: Wendy
* Goal: Provide TG8 with reliability signals and gate contracts.
* Deliverables:
  * Reliability evidence pack manifest
  * Gate input mappings and test fixtures
  * Open risk register for unresolved reliability debt
* Exit criteria:
  * TG8 can execute quality gate expansion without re-specifying reliability semantics

### TG7-10 Handoff Package to TG9

* Owner: Stan
* Support: Cartman
* Goal: Provide TG9 with operability-ready runbooks and escalation model.
* Deliverables:
  * Runbook set with release-day triage flow
  * On-call/event routing matrix
  * Post-release reliability verification checklist
* Exit criteria:
  * TG9 can publish final runbook/release readiness artifacts without re-planning TG7

## SLI and SLO Proposal (Initial)

| ID | SLI | Formula | Initial SLO Target | Severity Trigger |
|---|---|---|---|---|
| SLI-01 | Detect-and-eval success ratio | successful runs / total runs (rolling 7d) | >= 99% | Critical if < 95% over 24h |
| SLI-02 | Sweep-orphans success ratio | successful sweeps / total sweeps (rolling 7d) | >= 99.5% | High if < 98% over 24h |
| SLI-03 | Run-context artifact persistence ratio | runs with uploaded run-context / detect runs | 100% | Critical if < 99% |
| SLI-04 | Orchestration lifecycle completeness | runs with bootstrap+invoke/poll+finalize success / detect runs | >= 99% | High if < 97% |
| SLI-05 | Alert acknowledgment latency | median time from alert emission to ack | <= 10 minutes | High if > 20 minutes |
| SLI-06 | Mean time to recovery (MTTR) | mean incident recovery duration | <= 60 minutes | Critical if > 120 minutes |
| SLI-07 | Orphan protection precision | correctly identified orphan resources / total flagged resources | >= 99% | Critical if protected resource flagged |

Notes:

* SLI-01 through SLI-04 are immediately seedable from Gate B run evidence.
* SLI-05 and SLI-06 begin with manual timestamps, then migrate to hook-driven telemetry.
* SLI-07 requires TG7-06 safeguard instrumentation.

## Alerting Surfaces

### Critical alerts

* `ALERT-CRIT-01`: OIDC login failure in `detect-and-eval` or `sweep-orphans`
* `ALERT-CRIT-02`: Run-context artifact upload missing
* `ALERT-CRIT-03`: Protected resource flagged for orphan cleanup
* `ALERT-CRIT-04`: Lifecycle finalization not reached after successful invoke

### High alerts

* `ALERT-HIGH-01`: Invoke/poll timeout or partial completion
* `ALERT-HIGH-02`: Sweep summary missing after workflow success
* `ALERT-HIGH-03`: Repeated no-winner outcomes exceeding configured threshold window

### Medium alerts

* `ALERT-MED-01`: Elevated retry count in workflow bootstrap
* `ALERT-MED-02`: Dashboard data freshness older than 30 minutes

## Dashboard Surfaces

### Dashboard D1: Pipeline Reliability

Panels:

* Detect-and-eval success rate trend
* Stage-level failure heatmap (bootstrap / invoke-poll / finalize)
* Artifact persistence ratio
* MTTR and incident count trend

### Dashboard D2: Cleanup Safety and Orphan Control

Panels:

* Sweep success ratio
* Dry-run vs enforce-mode counts
* Resources flagged vs resources protected by deny-list
* Cleanup action age and unresolved orphan backlog

### Dashboard D3: Evaluation and Decision Operability

Panels:

* Evaluator run completion status by candidate
* No-winner frequency and threshold causes
* Reliability incident overlays on recommendation windows

## Failure Playbooks

### FP-01 OIDC Federation Failure

* Detect: Azure login step fails with AADSTS federation/subject mismatch.
* Contain: Block downstream mutation steps; force dry-run mode.
* Recover: Validate federated credentials for both standard and encoded subject forms.
* Verify: Re-run target workflow and confirm login success + downstream stage execution.
* Prevent: Add preflight credential subject validation check before run kickoff.

### FP-02 Artifact Persistence Failure

* Detect: `Upload run context artifact` or summary artifact step fails.
* Contain: Mark run as non-promotable; skip release-affecting actions.
* Recover: Validate artifact path existence (`.artifacts` and `artifacts`), hidden file handling.
* Verify: Ensure run-context + orchestration + finalize/sweep artifacts are present.
* Prevent: Enforce artifact path contract test in TG8 gate suite.

### FP-03 Invoke/Poll Partial Completion

* Detect: Bootstrap success but invoke or finalize missing/skipped.
* Contain: Raise high-severity alert and open incident hook record.
* Recover: Replay workflow with same run context and compare stage transitions.
* Verify: Lifecycle completeness SLI returns to threshold.
* Prevent: Add state-transition invariant checks and timeout budget alarms.

### FP-04 Orphan Sweep Safety Violation

* Detect: Sweep flags protected/non-ephemeral resources or skips summary generation.
* Contain: Force dry-run-only fallback and freeze destructive sweep mode.
* Recover: Recompute candidate resources using tag envelope and deny-list filter.
* Verify: Zero protected resources in actionable list.
* Prevent: Mandatory pre-sweep guardrail check with explicit approval artifact.

## Orphan Safeguards

Required controls:

* Dry-run default: all sweeps begin in dry-run mode.
* Required tags gate: only resources with expected ownership/cleanup tags are eligible.
* Deny-list protection: block resources lacking exact `owner`/`managedBy` contract.
* Max-delete threshold: hard cap per run to avoid blast radius.
* Safety artifact: generate sweep intent artifact before enforce-mode execution.
* Post-sweep verification: ensure summary artifact and residual-resource diff are produced.

## Incident Hooks

Event classes:

* `reliability.alert.raised`
* `reliability.incident.opened`
* `reliability.incident.updated`
* `reliability.incident.resolved`
* `reliability.safeguard.blocked_action`

Required payload fields:

* `event_id`
* `event_class`
* `severity`
* `run_id`
* `workflow_name`
* `resource_slice` (fixed value now: `002`)
* `resource_group`
* `summary`
* `recommended_action`
* `correlation_id`
* `occurred_at_utc`

Storage and routing contract:

* Persist incident hook payloads as JSON artifacts under `artifacts/<run_id>/incident-hooks/`.
* Emit one markdown summary entry per incident for operator timeline consumption.
* TG8 consumes hook artifacts as quality gate evidence.
* TG9 consumes hook artifacts for release runbook and post-release review.

## Reliability Validation Gates

### RG-01 Baseline Evidence Gate

* Criteria:
  * Gate A PASS evidence linked
  * Gate B PASS evidence linked with run IDs `29577754373` and `29577762865`
  * 002 resource map validated against current config contracts
* Result: required before any SLO claim is accepted

### RG-02 SLI Computation Gate

* Criteria:
  * SLI-01..SLI-04 computable from current artifacts
  * Calculation script/check produces deterministic output
* Result: required before dashboard baseline publication

### RG-03 Alert Contract Gate

* Criteria:
  * Critical and high alerts mapped to explicit failure modes
  * Alert payload contains required incident hook fields
* Result: required before TG8 validation integration

### RG-04 Safeguard Gate

* Criteria:
  * Orphan safety predicates validated
  * Enforce-mode path blocked when guardrails fail
* Result: required before non-dry-run cleanup promotion

### RG-05 Operability Handoff Gate

* Criteria:
  * Failure playbooks complete for FP-01..FP-04
  * TG8 and TG9 handoff packages produced and accepted
* Result: TG7 completion gate

## Handoff Contract to TG8 (Quality Gates)

TG7 -> TG8 required package:

* Reliability signal schema and SLI formulas (versioned)
* Baseline SLI snapshot from Gate B proven runs
* Alert rule catalog and payload contract
* Incident hook event schema + example artifacts
* RG-01..RG-04 gate definitions and expected evidence format

TG8 acceptance criteria:

* TG8 quality gate jobs can parse TG7 reliability artifacts without custom transforms.
* TG8 can assert fail/pass for reliability regressions using TG7 contracts only.

## Handoff Contract to TG9 (Runbooks and Release Readiness)

TG7 -> TG9 required package:

* FP-01..FP-04 playbooks with clear escalation paths
* Dashboard panel definitions and interpretation notes
* Orphan safeguard operating checklist and emergency stop procedure
* Incident hook-to-release-checklist mapping
* RG-05 completion evidence

TG9 acceptance criteria:

* TG9 can assemble release readiness and rollback runbooks without redefining reliability controls.
* Post-release verification checklist includes TG7 SLO and incident criteria.

## First Implementation Slice to Execute Next (explicit and executable now)

Slice ID: `TG7-01`

Execution intent:

* Build the first reliability baseline artifact set directly from already-successful Gate B runs on 002.

Concrete outputs to produce in the next implementation action:

1. `docs/tg7-reliability-sli-baseline.md`
   * Contains SLI definitions, formulas, data-source mapping, and initial seed values.
2. `artifacts/gatea-policy-remediation-20260717/tg7-reliability-baseline.json`
   * Machine-readable baseline snapshot including run IDs, stage outcomes, and seeded SLI values.
3. `scripts/validate_tg7_reliability_baseline.py`
   * Validation script that asserts required fields and deterministic recomputation from baseline inputs.

Executable command sequence (next step):

```powershell
python scripts/validate_tg7_reliability_baseline.py --input artifacts/gatea-policy-remediation-20260717/tg7-reliability-baseline.json
```

Definition of done for this slice:

* Baseline JSON validates successfully.
* Baseline document links both Gate B run IDs and 002 resources explicitly.
* TG8 can consume the baseline JSON without schema changes.

## Completion Criteria for TG7

TG7 is complete when all of the following are true:

* TG7-01 through TG7-10 are completed or explicitly deferred with owner and due trigger.
* RG-01 through RG-05 gates all PASS.
* SLO policy and alert contracts are published and tied to incident hooks.
* Failure playbooks are validated against at least one replay or simulated failure scenario per class.
* TG8 and TG9 have accepted handoff packages and no unresolved critical reliability blockers remain.
