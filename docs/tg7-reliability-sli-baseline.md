---
title: TG7 Reliability SLI Baseline
description: TG7 first-slice reliability baseline grounded on Gate B pass evidence runs for 002 context
ms.date: 2026-07-17
ms.topic: reference
---

## Scope

This document defines the TG7 first implementation slice baseline for reliability signals, seed SLI values, and initial SLO targets.

The baseline is grounded on Gate B pass evidence from:

* `detect-and-eval` run `29577754373`
* `sweep-orphans` run `29577762865`

## Environment Context

The reliability baseline is anchored to the 002 deployment slice and its validated runtime contract.

| Field | Value |
| --- | --- |
| Environment | `dev` |
| Instance | `002` |
| Resource group | `rg-mua-dev-001` |
| Foundry account | `fnd-mua-dev-002` |
| ACA environment | `acaenv-mua-dev-002` |
| ACA job | `aca-mua-eval` |
| Storage account | `stmuadev002` |
| Key Vault | `kv-mua-dev-002` |

## SLI Definitions and Initial SLO Targets

| SLI | Definition | Seed Value | Initial SLO |
| --- | --- | --- | --- |
| Workflow success ratio | Successful workflow runs divided by total baseline workflows (`detect-and-eval` + `sweep-orphans`) | `2/2 = 1.00` | `>= 0.99` rolling 7d |
| Run context artifact availability | Detect runs with successful run-context upload divided by detect runs observed | `1/1 = 1.00` | `>= 0.99` rolling 7d |
| OIDC login success | Runs with successful Azure OIDC login divided by total baseline workflows | `2/2 = 1.00` | `>= 0.995` rolling 7d |
| Cleanup sweep execution success | Successful sweep-orphans runs divided by total sweep runs observed | `1/1 = 1.00` | `>= 0.995` rolling 7d |
| End-to-end gate completion latency | Gate completion elapsed time from workflow start to workflow completion | Seed not captured in the Gate B evidence document | `<= 1800` seconds per run |

## Artifact Contract

Canonical machine-readable baseline artifact:

* `artifacts/gatea-policy-remediation-20260717/tg7-reliability-baseline.json`

Validation command:

```bash
python scripts/validate_tg7_reliability_baseline.py --baseline artifacts/gatea-policy-remediation-20260717/tg7-reliability-baseline.json
```

The validator enforces schema and value bounds and exits non-zero on errors.

## Assumptions

* Gate B evidence captures pass/fail outcomes for reliability-critical steps, but does not include normalized run-duration fields for latency seed extraction.
* Latency SLO target is initialized as an operational budget target and remains pending first measured seed capture from workflow timing fields.
