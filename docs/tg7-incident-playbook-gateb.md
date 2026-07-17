---
title: TG7 Incident Playbook Gate B Failure Signatures
description: Deterministic triage and recovery playbook for TG7 reliability incidents tied to known Gate B failure signatures
ms.date: 2026-07-17
ms.topic: reference
---

## Purpose

This playbook defines operator triage paths for TG7 reliability signals and binds each path to known Gate B failure signatures.

Known Gate B signatures:

* hidden artifact upload mismatch
* AADSTS700213 OIDC federated subject mismatch

## Triage Decision Tree

1. Identify the active signal from alert payload: workflow_failure, oidc_failure, sweep_failure, or latency_breach.
2. Match any failure signature from workflow logs.
3. Execute the corresponding path below.
4. Record incident evidence and resolution outcome under artifacts run evidence.

## Workflow Failure Path

### Detect Workflow Failure

* Alert: ALERT-CRIT-WORKFLOW-FAILURE
* Common signature: hidden artifact upload mismatch

### Contain Workflow Failure

* Mark run non-promotable.
* Block release-affecting workflow stages.

### Recover Workflow Failure

* Validate artifact path handling for both artifacts and .artifacts conventions.
* Re-run the failing workflow with unchanged inputs.

### Verify Workflow Failure

* Confirm workflow returns success.
* Confirm run-context and summary artifacts are uploaded.

### Prevent Workflow Failure

* Keep artifact contract checks in reliability gate validation.

## OIDC Failure Path

### Detect OIDC Failure

* Alert: ALERT-CRIT-OIDC-FAILURE
* Required signature: AADSTS700213 OIDC federated subject mismatch

### Contain OIDC Failure

* Stop all mutation-capable steps in the workflow.
* Force dry-run-only mode.

### Recover OIDC Failure

* Validate federated credential subjects for exact branch and encoded branch forms.
* Re-run OIDC login steps in detect-and-eval and sweep-orphans.

### Verify OIDC Failure

* Login succeeds in both workflows.
* Downstream stages run without auth errors.

### Prevent OIDC Failure

* Keep subject preflight checks in gate prerequisites.

## Sweep Failure Path

### Detect Sweep Failure

* Alert: ALERT-HIGH-SWEEP-FAILURE
* Related signature: hidden artifact upload mismatch or missing sweep summary

### Contain Sweep Failure

* Freeze enforce-mode cleanup.
* Permit dry-run sweep only.

### Recover Sweep Failure

* Recompute orphan candidates from required ownership tags.
* Re-run sweep-orphans in dry-run mode and validate summary generation.

### Verify Sweep Failure

* Sweep summary artifact exists.
* No protected resources enter actionable list.

### Prevent Sweep Failure

* Keep deny-list and max-delete guardrails active.

## Latency Breach Path

### Detect Latency Breach

* Alert: ALERT-HIGH-LATENCY-BREACH
* Trigger: end_to_end_gate_completion_latency > 1800 seconds

### Contain Latency Breach

* Pause candidate promotion decisions.
* Open reliability incident entry with impacted run IDs.

### Recover Latency Breach

* Inspect stage timings for bootstrap, invoke/poll, and finalize.
* Replay workflow once to distinguish transient latency from systemic regression.

### Verify Latency Breach

* Latest run latency is within SLO threshold.
* No active high/critical reliability alerts remain.

### Prevent Latency Breach

* Track trend panel for latency and enforce alert acknowledgments within operational budget.

## Operator Commands

```powershell
python scripts/check_tg7_reliability_gate.py --baseline artifacts/gatea-policy-remediation-20260717/tg7-reliability-baseline.json --evidence artifacts/gatea-policy-remediation-20260717/tg7-reliability-latest-evidence.sample.json
```

```powershell
python -m json.tool artifacts/gatea-policy-remediation-20260717/tg7-reliability-latest-evidence.sample.json > $null
```
