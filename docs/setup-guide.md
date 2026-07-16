---
title: TG3 Setup Guide
description: Operator setup for the TG3 CI/CD foundation of model-upgrade-automation
ms.date: 2026-07-15
ms.topic: how-to
---

## Overview

This repository now includes the TG3 delivery foundation:

* `.github/workflows/ci.yml` validates workflow, config, and documentation contracts.
* `.github/workflows/detect-and-eval.yml` establishes the weekly orchestration entrypoint.
* `.github/workflows/sweep-orphans.yml` provides the stale-resource cleanup safety net.

These workflows are intentionally scaffold-first. They create stable entrypoints, run-context propagation, OIDC authentication posture, and cleanup boundaries without introducing application business logic.

## Required repository variables

Create the variables documented in `config/azure.env.example` as repository or environment variables.

Use [docs/tg2-operator-evidence.md](c:\Users\sohadasgupta\IdeaProjects\hve-squad\model-upgrade-automation\docs\tg2-operator-evidence.md) together with [docs/tg3-handoff-contract.md](c:\Users\sohadasgupta\IdeaProjects\hve-squad\model-upgrade-automation\docs\tg3-handoff-contract.md) to confirm that TG2 has published the final identity, naming, and governance inputs for those variables.

Minimum required variables for non-dry-run execution:

* `AZURE_CLIENT_ID`
* `AZURE_TENANT_ID`
* `AZURE_SUBSCRIPTION_ID`
* `RESOURCE_GROUP`
* `FOUNDRY_ACCOUNT_NAME`
* `FOUNDRY_PROJECT_NAME`
* `ACA_ENVIRONMENT_NAME`
* `ACA_JOB_NAME`
* `STORAGE_ACCOUNT_NAME`
* `KEY_VAULT_NAME`

Optional workflow gates:

* `ENABLE_SCHEDULED_EVALS=true` enables the weekly cron job.
* `ENABLE_ORPHAN_SWEEP=true` enables the daily orphan sweeper.

## Workflow usage

Use `workflow_dispatch` first.

Recommended sequence:

1. Run `CI` after workflow or config edits.
2. Run `python scripts/validate_tg3_contracts.py` locally before pushing workflow-only changes.
2. Run `Detect and Evaluate` with `dry_run=true` to confirm run-context generation and artifact flow.
3. After TG2 resource and RBAC contracts are available, rerun `Detect and Evaluate` with `dry_run=false`.
4. Run `Sweep Orphans` with `dry_run=true` before allowing live cleanup.

## Operator controls

The TG3 foundation fails closed.

* Scheduled jobs do not run unless the corresponding enablement variable is set.
* Non-dry-run detect-and-eval execution stops if required Azure variables are missing.
* `enable_auto_pr=true` is rejected unless the repository variable `ENABLE_AUTO_PR=true` is also present.
* Cleanup only targets resources tagged with `owner=model-upgrade-automation` and `automation_scope=ephemeral`.
* The orphan sweeper also recognizes the TG2 placeholder cleanup tag `cleanup=ephemeral` when `managedBy=model-upgrade-automation` is present.
* The detect-and-eval finalize phase always emits a cleanup handoff artifact even when no teardown is attempted.

## Validation limits

This slice does not execute detector, recommender, provisioner, evaluator, or reporter code.

Those implementations remain with TG4 and TG5. The current foundation validates repository contracts, workflow structure, run-context completeness, and Azure-auth-ready orchestration boundaries only.
