---
title: Task Group 8 Quality Gates Validation Framework
description: Execution-ready quality gate framework that operationalizes TG7 reliability controls into repository-level validation and release evidence contracts
ms.date: 2026-07-17
ms.topic: reference
---
<!-- markdownlint-disable-file -->

# Task Group 8: Quality Gates Validation Framework

## Ownership

* Lead: Wendy (Evaluation + Quality)
* Support: Stan (Reliability + Operability)
* Support: Butters (CI/CD Delivery)
* Support: Kyle (Infrastructure + Governance)
* Support: Cartman (MVP Product/Tech Integrator)

## Objective

Define and implement the end-to-end quality gate framework that validates functional correctness, configuration integrity, security posture, and TG7 reliability readiness before release promotion.

TG8 begins immediately after TG7 Gate B PASS and must consume TG7 reliability artifacts as first-class gate inputs, especially the machine-checkable gate script at `scripts/check_tg7_reliability_gate.py`.

## Scope

In scope:

* Define a single quality gate matrix across unit, integration, config, security, reliability, and e2e categories.
* Convert TG7 reliability controls into deterministic PASS/FAIL checks for TG8.
* Standardize evidence outputs so every gate result is auditable and replayable.
* Add validation runners and contracts that can be executed locally and in CI.
* Establish TG8 handoff contract for TG9 release readiness and go/no-go decisions.

Out of scope:

* Re-authoring TG7 reliability baseline, alerts, workbook, or incident playbook content.
* Replacing TG3-TG7 implementation logic.
* Automatic production rollout decisioning.

## Dependency Matrix

| Dependency | Producer | Status | TG8 Usage |
|---|---|---|---|
| `.copilot-tracking/squad/task-group-07-reliability-sre-controls-operability.md` | TG7 | Complete | Reliability ownership boundaries and handoff assumptions |
| `scripts/check_tg7_reliability_gate.py` | TG7 | Complete | Canonical reliability PASS/FAIL evaluator for TG8 reliability gate |
| `docs/tg7-reliability-sli-baseline.md` | TG7 | Complete | SLI/SLO source-of-truth for thresholds and validation semantics |
| `docs/tg7-incident-playbook-gateb.md` | TG7 | Complete | Failure signature triage and remediation routing |
| `config/tg7-reliability-alert-definitions.yaml` | TG7 | Complete | Alert rule contract validation input |
| `config/tg7-reliability-workbook-definitions.yaml` | TG7 | Complete | Dashboard/workbook contract validation input |
| `artifacts/gatea-policy-remediation-20260717/tg7-reliability-baseline.json` | TG7 | Complete | Baseline artifact consumed by reliability gate checker |
| `artifacts/gatea-policy-remediation-20260717/tg7-reliability-latest-evidence.sample.json` | TG7 | Complete | Evidence artifact shape and seed input for reliability gate checker |

## TG7 Integration Points (Explicit)

1. Reliability gate execution in TG8 must invoke:

	 ```powershell
	 python scripts/check_tg7_reliability_gate.py --baseline artifacts/gatea-policy-remediation-20260717/tg7-reliability-baseline.json --evidence <tg8-evidence-path>
	 ```

2. TG8 reliability evidence must include the signal objects required by the TG7 checker:
	 * `signals.workflow_failure`
	 * `signals.oidc_failure`
	 * `signals.sweep_failure`
	 * `signals.latency_breach`
	 * `gate_b_failure_signatures_tracking`

3. TG8 must preserve and validate the two mandatory Gate B signature keys:
	 * `hidden artifact upload mismatch`
	 * `AADSTS700213 OIDC federated subject mismatch`

4. TG8 config/security/reliability checks must cross-reference:
	 * `config/tg7-reliability-alert-definitions.yaml`
	 * `config/tg7-reliability-workbook-definitions.yaml`
	 * `docs/tg7-incident-playbook-gateb.md`

## Concrete Task Plan

### TG8-01 Quality Gate Taxonomy and ID Contract (first implementation slice)

* Owner: Wendy
* Support: Stan
* Goal: Freeze canonical gate IDs, categories, and pass semantics consumed by all TG8 runners.
* Deliverables:
	* Gate ID registry `QG-UNIT-01` .. `QG-E2E-01`
	* Category mapping and mandatory/optional flags
	* Shared PASS/FAIL/ERROR result schema
* Exit criteria:
	* All TG8 tasks reference only registered gate IDs and schema

### TG8-02 Reliability Gate Adapter (TG7 Script Integration)

* Owner: Wendy
* Support: Stan
* Goal: Integrate TG7 reliability checker as mandatory TG8 reliability gate.
* Deliverables:
	* Deterministic runner wrapper for `scripts/check_tg7_reliability_gate.py`
	* Reliability gate result normalization into TG8 gate schema
	* Baseline/evidence path configuration contract
* Exit criteria:
	* Reliability gate PASS/FAIL matches TG7 checker exit status and reason output

### TG8-03 Unit Test Gate Hardening

* Owner: Wendy
* Support: Kenny
* Goal: Ensure module-level correctness for detector, evaluator, reporter, and shared contracts.
* Deliverables:
	* Unit gate command contract
	* Minimum pass thresholds for test count and zero-failure rule
* Exit criteria:
	* Unit gate fails on any test failure or collection error

### TG8-04 Integration Gate for Pipeline and Artifact Contracts

* Owner: Wendy
* Support: Butters
* Goal: Validate cross-module artifact flow from orchestrator through reporter outputs.
* Deliverables:
	* Integration scenarios for dry-run, result aggregation, and summary output
	* Artifact contract validation checks for required files and fields
* Exit criteria:
	* Integration gate fails on missing required artifact contracts

### TG8-05 Configuration Compliance Gate

* Owner: Kyle
* Support: Wendy
* Goal: Validate static config integrity and schema consistency for reliability and evaluation configs.
* Deliverables:
	* Config validation checks for YAML/JSON schema and required keys
	* Explicit checks for TG7 alert/workbook contract consistency
* Exit criteria:
	* Config gate fails if required TG7 signal/rule mappings drift

### TG8-06 Security and Policy Validation Gate

* Owner: Kyle
* Support: Stan
* Goal: Enforce baseline security and policy checks before release progression.
* Deliverables:
	* Security scan command contract and severity threshold mapping
	* Policy compliance checks tied to existing gate evidence folders
* Exit criteria:
	* Security gate fails on Critical findings or policy contract breakage

### TG8-07 Reliability Evidence Freshness and Integrity Gate

* Owner: Stan
* Support: Wendy
* Goal: Ensure reliability evidence is recent, complete, and signature-aware.
* Deliverables:
	* Freshness thresholds for baseline and latest evidence artifacts
	* Integrity checks for required reliability signal keys
* Exit criteria:
	* Reliability evidence gate fails when freshness window or required keys are violated

### TG8-08 End-to-End Scenario Gate

* Owner: Cartman
* Support: Wendy, Butters
* Goal: Validate complete non-prod scenario from trigger to decision artifact output.
* Deliverables:
	* One canonical E2E scenario and expected evidence set
	* E2E gate assertions for workflow execution and final artifact completeness
* Exit criteria:
	* E2E gate produces deterministic PASS/FAIL with evidence references

### TG8-09 Unified Evidence Artifact Contract and Aggregated Gate Report

* Owner: Wendy
* Support: Cartman
* Goal: Standardize all gate outputs into a single machine-readable and human-readable package.
* Deliverables:
	* `gate-results.json` schema contract
	* `gate-summary.md` template and rule set
	* Per-gate evidence index manifest
* Exit criteria:
	* Any gate run can be replayed and audited using only the evidence package

### TG8-10 TG9 Handoff Package (Release Readiness Inputs)

* Owner: Wendy
* Support: Stan, Cartman
* Goal: Deliver a release-readiness handoff contract consumable by TG9 with no re-interpretation.
* Deliverables:
	* TG8 pass/fail scoreboard
	* Open-risk register and release blockers list
	* TG9 intake checklist referencing gate evidence package paths
* Exit criteria:
	* TG9 can perform go/no-go evaluation using TG8 outputs without re-running TG7 semantics design

## Quality Gate Matrix

| Gate ID | Category | Intent | Primary Inputs | Command/Check | Pass Criteria | Fail Criteria | Evidence Output |
|---|---|---|---|---|---|---|---|
| QG-UNIT-01 | unit | Validate module-level correctness | `tests/unit/` | `python -m pytest tests/unit -q` | Exit code 0, no failed tests | Any test failure/error | Unit test result log + junit/json summary |
| QG-INT-01 | integration | Validate cross-module contracts | `artifacts/`, `results/`, `src/` | Targeted integration test run | Required integration scenarios pass | Missing/failed scenario | Integration report + scenario evidence |
| QG-CONFIG-01 | config | Validate config schema and contract consistency | `config/*.yaml`, `infra/*.bicep`, `requirements/plan.md` | Config schema + consistency checks | Required keys and mappings valid | Missing key/schema drift | Config validation report |
| QG-SEC-01 | security | Validate security/policy baseline | Policy outputs + security scan results | Security scan and policy checks | No Critical findings, policy checks pass | Critical findings or policy break | Security gate report + findings index |
| QG-REL-01 | reliability | Enforce TG7 reliability contract | TG7 baseline + latest evidence | `python scripts/check_tg7_reliability_gate.py ...` | Script exit code 0 and no fail reasons | Exit code 1/2 or fail reasons present | Reliability check output + copied input pointers |
| QG-E2E-01 | e2e | Validate end-to-end release candidate path | Workflow runs + final artifacts | E2E scenario validation runner | End-to-end flow and artifacts complete | Any missing mandatory step/artifact | E2E report + artifact manifest |

## Pass/Fail Criteria (Global)

Global PASS:

* All mandatory gates (`QG-UNIT-01`, `QG-INT-01`, `QG-CONFIG-01`, `QG-SEC-01`, `QG-REL-01`, `QG-E2E-01`) are PASS.
* No unresolved Critical findings remain in security or reliability categories.
* Evidence package is complete and schema-valid.

Global FAIL:

* Any mandatory gate is FAIL or ERROR.
* Reliability gate checker returns non-zero.
* Evidence package is incomplete or tampered/unparseable.

## Evidence Artifact Contract

TG8 gate execution must publish evidence under:

* `artifacts/tg8-quality-gates/<run_id>/gate-results.json`
* `artifacts/tg8-quality-gates/<run_id>/gate-summary.md`
* `artifacts/tg8-quality-gates/<run_id>/evidence-index.json`

`gate-results.json` minimum schema fields:

* `schema_version`
* `run_id`
* `generated_at_utc`
* `overall_status`
* `gates[]` with:
	* `gate_id`
	* `category`
	* `status` (`PASS`|`FAIL`|`ERROR`|`SKIP`)
	* `command`
	* `inputs[]`
	* `outputs[]`
	* `reasons[]`
	* `duration_seconds`

Reliability gate evidence (`QG-REL-01`) must additionally capture:

* baseline artifact path
* evidence artifact path
* raw stdout/stderr from `scripts/check_tg7_reliability_gate.py`
* parsed fail reasons when present

## Handoff to TG9 Release Readiness

TG8 delivers the following mandatory handoff bundle to TG9:

1. `gate-results.json` and `gate-summary.md` for the candidate release run.
2. Reliability-specific appendix proving TG7 integration command and result.
3. Open-risk and blocker table with owner, severity, and mitigation state.
4. Release recommendation status:
	 * `RECOMMEND_RELEASE`
	 * `RECOMMEND_HOLD`
	 * `REQUIRES_DECISION`

TG9 acceptance criteria for intake:

* TG8 evidence package is complete and machine-parseable.
* TG8 reliability gate result is PASS and traceable to TG7 artifacts.
* Any remaining non-blocking risks are explicitly documented with owner and due date.

## First Implementation Slice (Execute Immediately in This Session)

Slice ID: TG8-S1

Goal:

* Stand up the minimum runnable TG8 gate skeleton with mandatory TG7 reliability integration.

Actions:

1. Define and freeze gate IDs and mandatory flags for `QG-UNIT-01`..`QG-E2E-01`.
2. Add TG8 evidence folder contract for one session run under `artifacts/tg8-quality-gates/<run_id>/`.
3. Implement reliability gate wrapper command contract that executes:

	 ```powershell
	 python scripts/check_tg7_reliability_gate.py --baseline artifacts/gatea-policy-remediation-20260717/tg7-reliability-baseline.json --evidence artifacts/gatea-policy-remediation-20260717/tg7-reliability-latest-evidence.sample.json
	 ```

4. Capture normalized gate result record (PASS/FAIL/ERROR + reasons).
5. Publish initial `gate-summary.md` with one populated gate (`QG-REL-01`) and placeholders for remaining gates.

Exit criteria:

* TG8 can produce one deterministic gate artifact package with `QG-REL-01` evaluated from TG7 checker output.
* Package is sufficient to unblock TG8-S2 (full multi-category gate runner).

