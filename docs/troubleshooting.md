---
title: TG3 Troubleshooting
description: Troubleshooting guidance for TG3 workflows, OIDC auth, and cleanup controls
ms.date: 2026-07-15
ms.topic: troubleshooting
---

## Missing GitHub variables

Symptom:

* `Detect and Evaluate` fails during the preflight validation step.
* `Sweep Orphans` fails before Azure login.

Response:

* Compare repository variables with `config/azure.env.example`.
* Run `python scripts/validate_tg3_contracts.py` locally to catch missing contract files, workflow marker drift, and config mismatches before re-running Actions.
* Keep `dry_run=true` until the TG2 evidence package includes the final resource naming map and identity contract.
* Expect dry-run artifacts to use `tg2-contract-pending` for unresolved TG2 placeholders. Non-dry-run execution must replace every placeholder with a real value.
* Use [docs/tg2-operator-evidence.md](c:\Users\sohadasgupta\IdeaProjects\hve-squad\model-upgrade-automation\docs\tg2-operator-evidence.md) to verify which TG2-owned inputs are still missing.

## OIDC authentication failures

Symptom:

* `azure/login` fails with federation or subject mismatch errors.

Response:

* Reconfirm the Entra application or managed identity client ID.
* Reconfirm the federated credential subject matches the branch or environment pattern used by the workflow.
* Reconfirm that the job requesting Azure access still has `id-token: write`.
* Do not add a fallback client secret. The supported recovery path is to fix federation or RBAC.

## Auto-remediation gate failures

Symptom:

* `Detect and Evaluate` fails during bootstrap when `enable_auto_pr=true` was selected.

Response:

* Set the repository or environment variable `ENABLE_AUTO_PR=true` only when draft remediation PR generation is intentionally enabled.
* Keep the input disabled otherwise. The workflow fails closed by design.

## Scheduled workflows do not run

Symptom:

* A scheduled workflow appears skipped.

Response:

* Set `ENABLE_SCHEDULED_EVALS=true` for `Detect and Evaluate`.
* Set `ENABLE_ORPHAN_SWEEP=true` for `Sweep Orphans`.
* Verify the workflow file exists on the default branch.

## Timeout or finalize failures

Symptom:

* The orchestration job times out or the finalize job reports incomplete cleanup.

Response:

* Review the uploaded artifacts for the affected run.
* Trigger `Sweep Orphans` with `dry_run=true` first, then rerun with `dry_run=false` after confirming the stale resource list.
* Keep rollback at the workflow commit level until TG4 and TG5 replace placeholders with live orchestration.

## Cleanup safety checks

Symptom:

* A resource is not selected for cleanup.

Response:

* Confirm the resource has all required ownership tags:
  * `owner=model-upgrade-automation`
  * `managedBy=model-upgrade-automation`
  * `automation_scope=ephemeral` or `cleanup=ephemeral`
* Confirm `created_at_utc` is present and uses UTC ISO 8601 format.
* Confirm the resource age exceeds the configured `retention_hours` threshold.
