---
title: TG9 Release Readiness Runbook
description: Operator runbook for producing and reviewing the TG9 go/no-go decision packet from TG8 and TG9 slice1 evidence
sidebar_position: 9
ms.date: 2026-07-17
ms.topic: how-to
keywords:
  - tg9
  - release readiness
  - go no-go
  - operations
---

## Purpose

Use this runbook to generate an operator-facing TG9 release decision packet from:

* TG8 quality gate evidence
* TG9 slice1 intake outputs

The process is non-destructive. It generates documentation and evidence artifacts only.

## Inputs

Required inputs:

* TG8 run folder under `artifacts/tg8-quality-gates/<tg8_run_id>/`
* TG9 slice1 folder under `artifacts/tg9-release-readiness/<tg9_slice1_run_id>/`

Expected TG8 files:

* `gate-results.json`
* `gate-summary.md`
* `evidence-index.json`
* `tg9-handoff.md`

Expected TG9 slice1 files:

* `intake-payload.json`
* `provisional-decision.md`
* `evidence-index.json`

## Generate TG9 Full Packet

Run the full packet generator:

```bash
python scripts/run_tg9_full.py --tg8-run-id <tg8_run_id> --tg9-slice1-run-id <tg9_slice1_run_id> --run-id <tg9_full_run_id>
```

Example:

```bash
python scripts/run_tg9_full.py --tg8-run-id tg8-full-20260717 --tg9-slice1-run-id tg9-slice1-20260717 --run-id tg9-full-20260717
```

## Generated Outputs

The command writes a packet to `artifacts/tg9-release-readiness/<run_id>/`.

Required outputs:

* `final-decision.json`
* `release-checklist.md`
* `rollback-plan.md`
* `post-release-verification.md`
* `open-risks.md`
* `evidence-index.json`

## Decision Semantics

The final decision honors TG8 recommendation and gate states.

* `GO`: Mandatory gates pass and TG8 recommends release.
* `NO_GO`: Any mandatory gate fails or TG8 recommendation is hold.
* `REQUIRES_DECISION`: Manual adjudication required due to mixed signals.

Release posture is captured separately in `final-decision.json`.

* `RELEASE_READY`
* `CONDITIONAL_GO`
* `HOLD`

## Operator Review Checklist

Before approval, confirm:

1. `final-decision.json` is parseable JSON.
2. `evidence-index.json` is parseable JSON and lists packet artifacts.
3. `release-checklist.md` and `rollback-plan.md` reflect current release scope.
4. `open-risks.md` is explicit, even when no open risks exist.

## Escalation Guidance

Escalate to release owners when:

* Decision status is not `GO`.
* Any blocker is unresolved.
* Any parse validation fails.
* Evidence links are stale or missing for mandatory gates.
