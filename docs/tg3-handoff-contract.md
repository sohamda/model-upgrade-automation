---
title: TG3 Handoff Contract
description: Frozen TG2-to-TG3 resource, identity, network, governance, and validation contract for delivery workflow implementation.
ms.date: 2026-07-15
ms.topic: reference
---

## Purpose

This document freezes the smallest TG2 contract slice that TG3 needs before delivery automation can move from scaffold-only workflows to live Azure operations.

TG3 should consume this file as the source of truth for resource naming, OIDC setup, network restrictions, governance guardrails, and validation gates.

## Resource and identity map

TG3 derives these names from the `infra/main.bicep` outputs and repository variables.

| Contract area | Value source | Notes |
|---|---|---|
| Subscription ID | `AZURE_SUBSCRIPTION_ID` | OIDC control-plane scope |
| Resource group | `RESOURCE_GROUP` | TG2 deployment scope |
| Foundry account | `FOUNDRY_ACCOUNT_NAME` | Private-only data-plane target |
| Foundry project | `FOUNDRY_PROJECT_NAME` | RunContext field required by TG1 |
| ACA environment | `ACA_ENVIRONMENT_NAME` | VNet-integrated evaluator runtime |
| ACA job | `ACA_JOB_NAME` | Invoked by TG3 workflow later |
| Storage account | `STORAGE_ACCOUNT_NAME` | Blob and Table artifact/history store |
| Key Vault | `KEY_VAULT_NAME` | Optional runtime secret retrieval only |
| GitHub workflow identity | `AZURE_CLIENT_ID` | Federated identity, not a secret |

## OIDC contract

TG3 must preserve these identity assumptions:

* Authentication uses GitHub Actions OIDC only.
* No workflow may introduce `AZURE_CREDENTIALS`, client secrets, storage keys, or connection strings for control-plane access.
* Azure login jobs request only:

```yaml
permissions:
  contents: read
  id-token: write
```

Required federated credential values:

| Setting | Value |
|---|---|
| Issuer | `https://token.actions.githubusercontent.com` |
| Audience | `api://AzureADTokenExchange` |
| Subject | `repo:<org>/<repo>:ref:refs/heads/main` |

TG2 RBAC baseline:

* GitHub OIDC principal: `Contributor` scoped to the target resource group.
* ACA managed identity: `Cognitive Services User`, `Storage Blob Data Contributor`, `Storage Table Data Contributor`, `Key Vault Secrets User`, `Monitoring Metrics Publisher`.

## Network contract

The TG2 runtime path is private-only.

| Service | Required state | Connectivity path |
|---|---|---|
| Foundry | `publicNetworkAccess=Disabled`, `disableLocalAuth=true` | ACA subnet -> private endpoint -> `privatelink.cognitiveservices.azure.com` |
| Storage | `publicNetworkAccess=Disabled`, `allowSharedKeyAccess=false`, `allowBlobPublicAccess=false` | ACA subnet -> blob/table private endpoints -> `privatelink.blob.core.windows.net` and `privatelink.table.core.windows.net` |
| Key Vault | `publicNetworkAccess=Disabled`, RBAC mode | ACA subnet -> private endpoint -> `privatelink.vaultcore.azure.net` |

TG3 must not add public fallback logic, public endpoint probes, or secret-based data-plane access patterns.

## Governance contract

TG2 now defines deployable guardrails for the target resource-group scope.

Policy coverage:

* Deny public network access for Azure AI Foundry.
* Deny public network access, shared-key access, and public blob access for Storage.
* Deny public network access for Key Vault.
* Require tags:
  * `workload`
  * `environment`
  * `managedBy=model-upgrade-automation`
  * `taskGroup=tg2`
  * `owner=model-upgrade-automation`
  * `cleanup=ephemeral`

TG3 responsibilities:

* Preserve the required tags on all ephemeral resources it creates.
* Treat policy assignment failures as blocking errors for live runs.
* Avoid changing resource properties that would violate the private-only posture.

## Validation checklist

TG3 should not enable live delivery until all of these checks pass.

### Identity checks

1. `azure/login` succeeds with OIDC and no client secret.
2. The workflow principal can deploy to the target resource group.
3. The ACA managed identity can invoke Foundry and write Blob/Table artifacts without keys or connection strings.

### Network checks

1. Foundry resolves through `privatelink.cognitiveservices.azure.com`.
2. Blob resolves through `privatelink.blob.core.windows.net`.
3. Table resolves through `privatelink.table.core.windows.net`.
4. Key Vault resolves through `privatelink.vaultcore.azure.net`.

### Governance checks

1. Policy assignments for Foundry, Storage, Key Vault, and required tags exist at the target scope.
2. Live TG3 resources include all required tags.
3. No TG3 workflow step depends on public network access or secret-based Azure control-plane authentication.

## What TG3 can assume now

* Resource names and required environment variables are stable enough to wire workflow contracts.
* Identity and RBAC expectations are explicit.
* The private-network stance is non-negotiable.
* Governance enforcement points are defined locally in source control and can be validated before live Azure rollout.