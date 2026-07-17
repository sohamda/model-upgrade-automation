---
title: Azure Gate B Checkpoint - Detect and Eval
description: Gate B live non-prod detect-and-eval execution evidence for 002 slice
ms.date: 2026-07-17
ms.topic: reference
---

## Inputs and Environment

* Repository: `sohamda/model-upgrade-automation`
* Branch: `main`
* Slice: `002`
* Azure subscription: `3b250d66-c6d7-48ff-b78e-351fa7f7a8eb`
* Azure tenant: `16b3c013-d300-468d-ac64-7eda0820b6d3`
* Execution date: `2026-07-17`

### Gate B Required Variables

* `RESOURCE_GROUP=rg-mua-dev-001`
* `FOUNDRY_ACCOUNT_NAME=fnd-mua-dev-002`
* `FOUNDRY_PROJECT_NAME=tg2-contract-pending`
* `ACA_ENVIRONMENT_NAME=acaenv-mua-dev-002`
* `ACA_JOB_NAME=aca-mua-eval`
* `STORAGE_ACCOUNT_NAME=stmuadev002`
* `KEY_VAULT_NAME=kv-mua-dev-002`
* `ALLOWED_REGIONS=northeurope`
* `DEPLOYMENT_TYPE=DataZoneStandard`
* `RETIREMENT_HORIZON_DAYS=90`
* `AUTOMATION_OWNERSHIP_TAG=model-upgrade-automation`
* `AUTOMATION_SCOPE_TAG=ephemeral`
* `MANAGED_BY_TAG=model-upgrade-automation`
* `AUTOMATION_CLEANUP_TAG=ephemeral`

Notes:

* Existing repository variable values were updated and verified by `gh variable list`.
* A real Foundry project resource was not discoverable in `rg-mua-dev-001`; fallback value `tg2-contract-pending` was used as requested.

## Workflow Attempts and Outcomes

### 1) Detect and Eval

* Trigger command:

```bash
gh workflow run detect-and-eval.yml -f dry_run=false -f candidate_limit=3 -f enable_auto_pr=false
```

* Run ID: `29577119705`
* Run URL: <https://github.com/sohamda/model-upgrade-automation/actions/runs/29577119705>
* Terminal state: `completed`
* Conclusion: `failure`
* Failed job: `Bootstrap Run Context` (`87874016628`)
* Failed step: `Upload run context artifact`
* Key log evidence:
  * `No files were found with the provided path: .artifacts/run-context.*. No artifacts will be uploaded.`
* Downstream jobs:
  * `Invoke and Poll Placeholder`: `skipped`
  * `Finalize and Cleanup Handoff`: `skipped`

### 2) Sweep Orphans Dry-Run

* Trigger command:

```bash
gh workflow run sweep-orphans.yml -f dry_run=true -f retention_hours=24
```

* Run ID: `29577150939`
* Run URL: <https://github.com/sohamda/model-upgrade-automation/actions/runs/29577150939>
* Terminal state: `completed`
* Conclusion: `failure`
* Failed job: `Sweep Tagged Ephemeral Resources` (`87874113961`)
* Failed step: `Azure login with OIDC`
* Key log evidence:
  * `AADSTS700213: No matching federated identity record found for presented assertion subject 'repo:sohamda@1938772/model-upgrade-automation@1302868165:ref:refs/heads/main'`
  * Issuer shown by workflow: `https://token.actions.githubusercontent.com`
  * Audience shown by workflow: `api://AzureADTokenExchange`

## Gate B Check Matrix

| Check | Status | Evidence | Notes |
|---|---|---|---|
| GitHub repo variables set for 002 slice | PASS | `gh variable list` shows required names and values | Complete for this gate run |
| OIDC auth succeeded | FAIL | `sweep-orphans` run `29577150939`, step `Azure login with OIDC` failed with `AADSTS700213` | Federated credential subject mismatch |
| Invoke and poll lifecycle executed | FAIL | `detect-and-eval` run `29577119705`, `Invoke and Poll Placeholder` job skipped | Upstream bootstrap failure prevented execution |
| Artifact persistence evidence available | FAIL | `detect-and-eval` failed at `Upload run context artifact`: missing `.artifacts/run-context.*` | No run-context artifact uploaded |
| Cleanup behavior evidence available | WARN | `sweep-orphans` workflow was triggered and reached sweep stage gate, but `Sweep tagged resources` step skipped due OIDC failure | Attempt evidence exists, behavior execution evidence missing |

## Remediation Executed (2026-07-17)

### A) Workflow Fixes Applied

Changed files:

* `.github/workflows/detect-and-eval.yml`
  * Added `include-hidden-files: true` to all `actions/upload-artifact` steps.
  * Hardened run-context upload by mirroring bootstrap outputs to non-hidden `artifacts/` and uploading from both:
    * `.artifacts/run-context.*`
    * `artifacts/run-context.*`
* `.github/workflows/sweep-orphans.yml`
  * Added `include-hidden-files: true` on sweep artifact upload.
  * Fixed `az resource list` usage by replacing invalid `--tag` + `--resource-group` combination with JMESPath query:
    * `--query "[?tags.owner=='${OWNERSHIP_TAG}']"`
  * Corrected Python indentation in sweep filter loop.

### B) OIDC Fix in Azure (Additive and Safe)

Application ID: `4e00f0df-eebc-40e1-aa83-5484a80ce070`

Inspected credentials:

```bash
az ad app federated-credential list --id 4e00f0df-eebc-40e1-aa83-5484a80ce070
```

Result before create:

* Existing subject already present:
  * `repo:sohamda/model-upgrade-automation:ref:refs/heads/main`

Created additional exact encoded subject credential:

* Name: `github-main-encoded-gateb`
* Issuer: `https://token.actions.githubusercontent.com`
* Audience: `api://AzureADTokenExchange`
* Subject: `repo:sohamda@1938772/model-upgrade-automation@1302868165:ref:refs/heads/main`

Verified final state includes both required subjects.

### C) Local Validation

Workflow YAML parse sanity checks passed for both updated workflow files.

## Gate B Re-Run Evidence (Post-Remediation)

### 1) Detect and Eval (live)

Trigger command:

```bash
gh workflow run detect-and-eval.yml -f dry_run=false -f candidate_limit=3 -f enable_auto_pr=false
```

Run ID: `29577754373`
Run URL: <https://github.com/sohamda/model-upgrade-automation/actions/runs/29577754373>
Terminal state: `completed`
Conclusion: `success`

Key successful steps:

* `Bootstrap Run Context` job:
  * `Upload run context artifact`: success
* `Invoke and Poll Placeholder` job:
  * `Azure login with OIDC`: success
  * `Orchestrate foundation placeholder`: success
  * `Upload orchestration artifacts`: success
* `Finalize and Cleanup Handoff` job:
  * `Upload finalize summary`: success

### 2) Sweep Orphans (dry-run)

Trigger command:

```bash
gh workflow run sweep-orphans.yml -f dry_run=true -f retention_hours=24
```

Run ID: `29577762865`
Run URL: <https://github.com/sohamda/model-upgrade-automation/actions/runs/29577762865>
Terminal state: `completed`
Conclusion: `success`

Key successful steps:

* `Azure login with OIDC`: success
* `Sweep tagged resources`: success
* `Upload sweep summary`: success

## Updated Gate B Check Matrix

| Check | Status | Evidence | Notes |
|---|---|---|---|
| GitHub repo variables set for 002 slice | PASS | Existing variable set remained valid | No additional variable drift observed |
| OIDC auth succeeded | PASS | `detect-and-eval` run `29577754373`; `sweep-orphans` run `29577762865` | Both workflows passed Azure login |
| Invoke and poll lifecycle executed | PASS | `detect-and-eval` run `29577754373`, `Invoke and Poll Placeholder` job success | Lifecycle executed end-to-end |
| Artifact persistence evidence available | PASS | `Upload run context artifact`, `Upload orchestration artifacts`, `Upload finalize summary`, `Upload sweep summary` all succeeded | Hidden/non-hidden artifact path hardening effective |
| Cleanup behavior evidence available | PASS | `sweep-orphans` run `29577762865`, dry-run sweep step success | Cleanup sweep execution validated |

## Final Gate B Verdict

**Gate B: PASS**

Gate B blockers were remediated and both required workflows completed successfully with expected evidence.
