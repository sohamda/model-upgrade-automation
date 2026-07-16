---
title: TG2 Operator Evidence Package
description: Canonical TG2 operator contract for identity, governance, evidence, and handoff inputs consumed by TG3 delivery workflows
ms.date: 2026-07-15
ms.topic: reference
---

## Purpose

This document centralizes the TG2-owned operator evidence that the TG3 workflow package depends on.

Use it as the single reference for:

* OIDC identity inputs and subject patterns
* Required resource and naming contract values
* Governance and cleanup tag expectations
* The minimum evidence set that should exist before live TG3 runs

TG3-facing documents should point here for TG2-owned details instead of restating the contract in multiple places.

## Source-controlled local evidence

The following local artifacts now provide a source-controlled TG2 baseline that downstream groups can validate without Azure access:

| Evidence area | Local artifact | What it proves locally |
|---|---|---|
| Resource naming contract | `infra/main.bicep` output `resourceNameMap` | TG3 variable names and resource naming stay aligned with the deployed baseline shape |
| Workflow identity contract | `infra/main.bicep` output `oidcContract` | TG3 OIDC inputs remain part of the TG2 source contract |
| Private network contract | `infra/main.bicep` output `networkContract` | Private subnet, DNS zone, and private-only service expectations are modeled in source |
| Governance contract | `infra/main.bicep` output `governanceContract` | Policy assignment names, required tags, and required service states are defined locally |
| Validation anchors | `infra/main.bicep` output `validationChecklist` | TG3 runtime validation expectations derive from TG2 source instead of ad hoc operator notes |
| Compile validation | `az bicep build --file infra/main.bicep` | The full TG2 main/module graph compiles locally with no current Bicep warnings or errors |

Use these artifacts as the local readiness package when Azure-side evidence has not yet been collected.

## TG2-owned contract inputs

TG2 is responsible for publishing the final values for these inputs before TG3 moves beyond scaffold-first execution:

* Tenant ID
* Subscription ID
* Application or user-assigned managed identity client ID used by GitHub Actions
* Federated credential subject pattern
* Least-privilege RBAC assignments for the workflow principal
* Resource group name
* Foundry account and project names
* ACA environment and ACA job names
* Storage account name
* Key Vault name

The matching repository variable names remain defined in [docs/tg3-handoff-contract.md](c:\Users\sohadasgupta\IdeaProjects\hve-squad\model-upgrade-automation\docs\tg3-handoff-contract.md).

## OIDC posture

Authentication uses GitHub Actions workload identity federation only.

No client secret is required or recommended.

Expected placeholder subjects until TG2 publishes the final identity artifact:

* `repo:<org>/<repo>:ref:refs/heads/main`
* `repo:<org>/<repo>:environment:production`

Jobs that authenticate to Azure should request `id-token: write`. Other jobs should remain at `contents: read` unless a stronger permission is explicitly justified.

## Governance and cleanup expectations

TG2 establishes the baseline tag and policy posture that TG3 automation must preserve.

Required ownership and cleanup tags for ephemeral resources:

* `owner=model-upgrade-automation`
* `managedBy=model-upgrade-automation`
* `automation_scope=ephemeral`
* `cleanup=ephemeral`
* `taskGroup=tg2`

Required time metadata for stale-resource evaluation:

* `created_at_utc` in UTC ISO 8601 format

The orphan sweeper accepts the TG2 placeholder cleanup posture when `managedBy=model-upgrade-automation` is present with `cleanup=ephemeral`.

## Required TG2 evidence before live TG3 runs

TG3 can stay in `dry_run=true` mode without the full evidence package. Before `dry_run=false`, operators should be able to point to all of the following:

1. A published identity contract showing the workflow principal, issuer, audience, and approved subject pattern.
2. A published resource naming map matching the repository variables in `config/azure.env.example`.
3. Confirmation of least-privilege RBAC assignments for the GitHub workflow principal.
4. Confirmation that private-only network posture remains in force for Foundry, Storage, and Key Vault.
5. Confirmation that required tags and deny policies are active at the target deployment scope.

If any item is missing, keep TG3 in scaffold or dry-run mode and use the placeholder marker `tg2-contract-pending` where the workflow expects unresolved TG2 data.

## What is complete locally vs. what still requires Azure

Locally complete now:

* TG2 Bicep source compiles cleanly from `infra/main.bicep`.
* Main-to-module contract wiring for naming, identity, network, and governance is source-controlled.
* TG3 handoff documents can reference a single canonical evidence package.

Still requires live Azure execution or inspection:

* Verifying actual federated credential creation and issuer or subject correctness in Microsoft Entra.
* Verifying real RBAC assignments on the workflow principal and ACA managed identity.
* Verifying policy assignments exist and enforce correctly at the intended scope.
* Verifying private endpoint DNS resolution and data-plane connectivity from the ACA subnet path.

## Relationship to TG3 documents

Use the TG3 documents for these purposes:

* [docs/setup-guide.md](c:\Users\sohadasgupta\IdeaProjects\hve-squad\model-upgrade-automation\docs\setup-guide.md): operator entry sequence and workflow controls
* [docs/oidc-setup.md](c:\Users\sohadasgupta\IdeaProjects\hve-squad\model-upgrade-automation\docs\oidc-setup.md): GitHub-side OIDC variable and permission setup
* [docs/troubleshooting.md](c:\Users\sohadasgupta\IdeaProjects\hve-squad\model-upgrade-automation\docs\troubleshooting.md): failure handling for TG3 runs
* [docs/tg3-handoff-contract.md](c:\Users\sohadasgupta\IdeaProjects\hve-squad\model-upgrade-automation\docs\tg3-handoff-contract.md): frozen TG2-to-TG3 contract consumed by delivery automation