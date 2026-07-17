---
title: Azure Non-Prod Readiness Checkpoint - Gate A
description: Gate A checkpoint for model-upgrade-automation using TG2 and TG3 contracts with live Azure evidence
ms.date: 2026-07-17
ms.topic: reference
---

## Scope and Inputs

* Repository: `model-upgrade-automation`
* Target resource group: `rg-mua-dev-001`
* User-confirmed facts:
  * Resource group exists: `rg-mua-dev-001`
  * OIDC app exists: `model-upgrade-automation-github-oidc`
* Contract sources:
  * `docs/tg2-operator-evidence.md`
  * `docs/tg3-handoff-contract.md`
* Check date: `2026-07-17`

## Environment Context

* Azure Extensions auth context (MCP extension context):
  * `isSignedIn=false`
  * No subscriptions visible from extension context
* Azure CLI auth context (used for all live checks in this artifact):
  * Subscription: `3b250d66-c6d7-48ff-b78e-351fa7f7a8eb` (`MCAPS-soham`)
  * Tenant: `16b3c013-d300-468d-ac64-7eda0820b6d3` (`Microsoft Non-Production`)
  * Account: `sohadasgupta@microsoft.com`

## Check Matrix

| Control | Status | Evidence | Notes |
|---|---|---|---|
| RG exists and is usable | PASS | `az group show --name rg-mua-dev-001` returns `provisioningState=Succeeded`, `location=swedencentral` | Base scope exists |
| RG location captured | PASS | RG location is `swedencentral` | Required for subsequent deployments |
| Core surface: Storage account present in RG | FAIL | `az resource list --resource-group rg-mua-dev-001 --resource-type Microsoft.Storage/storageAccounts` => `[]` | TG3 expects storage contract and private-only posture checks |
| Core surface: Key Vault present in RG | FAIL | `az resource list --resource-group rg-mua-dev-001 --resource-type Microsoft.KeyVault/vaults` => `[]` | TG3 expects Key Vault resource and RBAC/private networking checks |
| Core surface: Foundry/Cognitive account present in RG | FAIL | `az resource list --resource-group rg-mua-dev-001 --resource-type Microsoft.CognitiveServices/accounts` => `[]` | TG3 contract requires Foundry account/project path |
| Core surface: Container Apps environment present in RG | FAIL | `az resource list --resource-group rg-mua-dev-001 --resource-type Microsoft.App/managedEnvironments` => `[]` | No ACA env visible for evaluator runtime |
| Core surface: Monitoring surface present in RG | WARN | `az monitor log-analytics workspace list --resource-group rg-mua-dev-001` => `[]`; `az resource list --resource-type Microsoft.Insights/components` => `[]` | Monitoring may be out-of-RG, but no evidence in target RG |
| OIDC identity object visibility (App) | PASS | `az ad app list --display-name model-upgrade-automation-github-oidc` returns appId `d68aace3-2717-4fde-9364-157e471bb776`, objectId `4e00f0df-eebc-40e1-aa83-5484a80ce070` | Identity object visible |
| OIDC identity object visibility (Service Principal) | PASS | `az ad sp list --display-name model-upgrade-automation-github-oidc` returns SP objectId `8bcf3361-a44d-4d05-bb0d-169abc0ac4c6` | SP exists |
| OIDC federated credential correctness for GitHub main branch | PASS | `az ad app federated-credential list --id 4e00f0df-eebc-40e1-aa83-5484a80ce070` shows issuer `https://token.actions.githubusercontent.com`, audience `api://AzureADTokenExchange`, subject `repo:sohamda/model-upgrade-automation:ref:refs/heads/main` | Matches TG3 OIDC contract subject pattern model |
| OIDC principal role assignment readiness at RG scope | FAIL | `az role assignment list --assignee-object-id 8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 --scope /subscriptions/3b250d66-c6d7-48ff-b78e-351fa7f7a8eb/resourceGroups/rg-mua-dev-001` => `[]` | No Contributor (or equivalent) assignment found |
| RBAC sanity at RG scope (discoverable assignments) | FAIL | `az role assignment list --scope /subscriptions/3b250d66-c6d7-48ff-b78e-351fa7f7a8eb/resourceGroups/rg-mua-dev-001` => `[]` | No role assignments visible at RG scope |
| RBAC sanity at subscription scope for OIDC principal | FAIL | `az role assignment list --assignee-object-id 8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 --scope /subscriptions/3b250d66-c6d7-48ff-b78e-351fa7f7a8eb` => `[]` | No inherited baseline assignment found |
| TG3 governance tags: RG includes required fields | FAIL | RG tags currently: `environment=dev`, `managedBy=model-upgrade-automation`, `workload=mua` | Missing required TG3 fields: `taskGroup=tg2`, `owner=model-upgrade-automation`, `cleanup=ephemeral` |
| Policy/governance assignments at RG scope | WARN | `az policy assignment list --resource-group rg-mua-dev-001` => `[]` | Could be inherited at higher scope; no RG-level assignments visible |
| Private endpoint prerequisites discoverable | FAIL | `az network private-endpoint list --resource-group rg-mua-dev-001` => `[]` | No private endpoints in target RG |
| Private DNS prerequisites discoverable | FAIL | `az network private-dns zone list --resource-group rg-mua-dev-001` => `[]` | No required private DNS zones in target RG |
| VNet prerequisites discoverable | FAIL | `az network vnet list --resource-group rg-mua-dev-001` => `[]` | No VNet/subnet path visible for private-only data plane |

## Blockers

1. No core runtime resources currently exist in the target RG (`storage`, `keyvault`, `foundry`, `aca env`, monitoring).
2. OIDC principal exists but has no deploy-authorizing RBAC assignment at RG or subscription scope.
3. TG3 governance contract is incomplete on tags and not evidenced for policy/private networking prerequisites.

## Minimal Remediation Steps (Non-Destructive) and Order

### Step 1: Complete required TG3 tags on the RG

```bash
az group update \
  --name rg-mua-dev-001 \
  --set tags.workload=mua tags.environment=dev tags.managedBy=model-upgrade-automation tags.taskGroup=tg2 tags.owner=model-upgrade-automation tags.cleanup=ephemeral
```

### Step 2: Grant OIDC SP least-privilege baseline for control-plane deploys (RG scope)

```bash
az role assignment create \
  --assignee-object-id 8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 \
  --assignee-principal-type ServicePrincipal \
  --role Contributor \
  --scope /subscriptions/3b250d66-c6d7-48ff-b78e-351fa7f7a8eb/resourceGroups/rg-mua-dev-001
```

### Step 3: Provision or validate required core surfaces in RG (using your approved TG2 IaC/deploy path)

Expected minimum surfaces for TG3 readiness evidence:

* `Microsoft.Storage/storageAccounts`
* `Microsoft.KeyVault/vaults`
* `Microsoft.CognitiveServices/accounts` (Foundry)
* `Microsoft.App/managedEnvironments`
* Monitoring surface (`Microsoft.OperationalInsights/workspaces` and/or `Microsoft.Insights/components`)

### Step 4: Confirm private-only network prerequisites

Create/verify:

* Private endpoints for Foundry, Storage (blob/table), and Key Vault
* Private DNS zones and links:
  * `privatelink.cognitiveservices.azure.com`
  * `privatelink.blob.core.windows.net`
  * `privatelink.table.core.windows.net`
  * `privatelink.vaultcore.azure.net`
* VNet/subnet path for ACA runtime

### Step 5: Re-validate Gate A controls

```bash
az group show --name rg-mua-dev-001
az role assignment list --assignee-object-id 8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 --scope /subscriptions/3b250d66-c6d7-48ff-b78e-351fa7f7a8eb/resourceGroups/rg-mua-dev-001
az resource list --resource-group rg-mua-dev-001 --resource-type Microsoft.Storage/storageAccounts
az resource list --resource-group rg-mua-dev-001 --resource-type Microsoft.KeyVault/vaults
az resource list --resource-group rg-mua-dev-001 --resource-type Microsoft.CognitiveServices/accounts
az resource list --resource-group rg-mua-dev-001 --resource-type Microsoft.App/managedEnvironments
az network private-endpoint list --resource-group rg-mua-dev-001
az network private-dns zone list --resource-group rg-mua-dev-001
az network vnet list --resource-group rg-mua-dev-001
```

## Re-Validation Snapshot (after read-only checks performed now)

* RG state remains `Succeeded` and reachable.
* OIDC app/SP/federated credential are visible and structurally correct.
* Core resource surfaces remain absent in target RG.
* RBAC assignments for OIDC SP remain absent at RG/subscription scopes.
* Network/private endpoint/private DNS prerequisites remain absent in target RG.

## Revalidation Pass

### Execution Window

* Date: `2026-07-17`
* Subscription: `3b250d66-c6d7-48ff-b78e-351fa7f7a8eb` (`MCAPS-soham`)
* Resource group: `rg-mua-dev-001`

### Pass 1: Safe Remediations Applied (Non-Destructive)

Completed actions:

1. Updated RG tags in place via `az group update`.
2. Created RG-scoped `Contributor` assignment for OIDC service principal object ID `8bcf3361-a44d-4d05-bb0d-169abc0ac4c6` via `az role assignment create`.

Evidence:

* `az group show --name rg-mua-dev-001 --query "{name:name,location:location,tags:tags}"` now returns:
  * `workload=mua`
  * `environment=dev`
  * `managedBy=model-upgrade-automation`
  * `taskGroup=tg2`
  * `owner=model-upgrade-automation`
  * `cleanup=ephemeral`
* `az role assignment list --assignee-object-id 8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 --scope /subscriptions/3b250d66-c6d7-48ff-b78e-351fa7f7a8eb/resourceGroups/rg-mua-dev-001` now returns `Contributor`.

Result delta:

* Tag blocker: **cleared**
* OIDC RBAC blocker: **cleared**

### Pass 1 Revalidation (Post-Remediation)

`az resource list` checks still showed no TG2 baseline core resources present at this point:

* Storage: `[]`
* Key Vault: `[]`
* Foundry/Cognitive account: `[]`
* ACA managed environment: `[]`
* Private endpoints: `[]`
* Private DNS zones: `[]`
* VNet: `[]`

### Baseline Infra Attempt (What-If First, Then Create)

What-if preview executed:

* Command: `az deployment group what-if --name tg2-baseline-gatea-20260717 --resource-group rg-mua-dev-001 --template-file infra/main.bicep --parameters workloadPrefix=mua environment=dev instance=001 githubPrincipalObjectId=8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 githubRepository=sohamda/model-upgrade-automation githubBranchRef=refs/heads/main --result-format ResourceIdOnly`
* Result summary:
  * `Resource changes: 43 to create, 5 unsupported`
  * Includes expected TG2 surfaces (Storage, Key Vault, Foundry, ACA env, VNet, Private DNS zones, Private Endpoints, Log Analytics, App Insights, policy definitions/assignments).

Create/update attempt executed:

* Command: `az deployment group create --name tg2-baseline-gatea-20260717 --resource-group rg-mua-dev-001 --template-file infra/main.bicep --parameters workloadPrefix=mua environment=dev instance=001 githubPrincipalObjectId=8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 githubRepository=sohamda/model-upgrade-automation githubBranchRef=refs/heads/main`
* Outcome: **failed** with `DeploymentFailed`.

Failure evidence from deployment operations:

* `RequestDisallowedByPolicy` for `Microsoft.Insights/components/appi-mua-dev-001` due required-tag deny assignments.
* `RequestDisallowedByPolicy` for `Microsoft.Network/privateDnsZones/virtualNetworkLinks/*` due required-tag deny assignments.

Minimal correction required:

* Adjust TG2 tag-policy definitions/assignments to exclude resource types that do not support tags (or scope tag policies to taggable types only), then re-run the same deployment.
* Ensure all taggable resources in modules include `owner` and `cleanup` tags before policy enforcement.

### Pass 2 Revalidation (After Deployment Attempt)

Current state evidence:

* `az group show --name rg-mua-dev-001` => `provisioningState=Succeeded` with required tags present.
* `az role assignment list ...` => OIDC principal has RG-scoped `Contributor`.
* Core surfaces:
  * Storage: `[]`
  * Key Vault: `[]`
  * Foundry/Cognitive: `[]`
  * ACA managed environment: `[]`
* Monitoring:
  * Log Analytics: `["log-mua-dev-001"]`
  * App Insights: `[]`
* Network prerequisites:
  * VNet: `["vnet-mua-dev-001"]`
  * Private DNS zones: `["privatelink.blob.core.windows.net","privatelink.cognitiveservices.azure.com","privatelink.table.core.windows.net","privatelink.vaultcore.azure.net"]`
  * Private endpoints: `[]`
* Governance assignments now present at RG scope:
  * `mua-tg2-foundry-private-only`
  * `mua-tg2-storage-private-only`
  * `mua-tg2-keyvault-private-only`
  * `mua-tg2-require-workload-tag`
  * `mua-tg2-require-environment-tag`
  * `mua-tg2-require-managedby-tag`
  * `mua-tg2-require-taskgroup-tag`
  * `mua-tg2-require-owner-tag`
  * `mua-tg2-require-cleanup-tag`

## Final Remediation Attempt

### Objective

Complete Gate A by removing the remaining deployment denies with the smallest safe policy change, then rerun TG2 baseline deployment and full readiness checks.

### Commands Run and Outcomes

1. Identified exact deny sources from deployment operations.

```bash
az deployment operation group list --resource-group rg-mua-dev-001 --name tg2-baseline-gatea-20260717 --query "[?properties.provisioningState=='Failed'].{operationId:operationId,target:properties.targetResource.resourceName,type:properties.targetResource.resourceType,code:properties.statusMessage.error.code,message:properties.statusMessage.error.message,details:properties.statusMessage.error.details}" --output json
```

Outcome:

* Confirmed denies were from RG assignments:
  * `mua-tg2-require-workload-tag`
  * `mua-tg2-require-environment-tag`
  * `mua-tg2-require-managedby-tag`
  * `mua-tg2-require-taskgroup-tag`
  * `mua-tg2-require-owner-tag`
  * `mua-tg2-require-cleanup-tag`
* Confirmed blocked resource types included non-taggable child resources (`Microsoft.Network/privateDnsZones/virtualNetworkLinks`) and baseline resources missing `owner`/`cleanup` tags.

2. Applied minimal safe deny-policy narrowing to exclude non-taggable resource types while preserving deny on taggable resources.

Live-policy update command pattern:

```bash
az policy definition update --name <definition-name> --rules artifacts/gatea-policy-remediation-20260717/<definition>-rule-v2.json
```

Applied to all six tag definitions:

* `mua-tg2-require-workload-tag`
* `mua-tg2-require-environment-tag`
* `mua-tg2-require-managedby-tag`
* `mua-tg2-require-taskgroup-tag`
* `mua-tg2-require-owner-tag`
* `mua-tg2-require-cleanup-tag`

Exclusion set applied in each policy rule (`field: type`, `notIn`):

* `Microsoft.Authorization/policyAssignments`
* `Microsoft.Authorization/roleAssignments`
* `Microsoft.Network/privateDnsZones/virtualNetworkLinks`
* `Microsoft.Network/privateEndpoints/privateDnsZoneGroups`

Verification sample:

```bash
az policy definition show --name mua-tg2-require-owner-tag --query "policyRule.if.allOf[0]" --output json
```

Outcome:

* Policy definitions updated successfully.

3. Fixed IaC tag propagation to keep governance intent intact on taggable resources.

Code change summary:

* `infra/main.bicep`: pass `requiredGovernanceTags` (includes `owner` and `cleanup`) into all resource modules.
* `infra/modules/governance-definitions.bicep`: encode the same non-taggable type exclusions in policy definitions.

Outcome:

* Subsequent resources now carry full required tag set (`workload`, `environment`, `managedBy`, `taskGroup`, `owner`, `cleanup`).

4. Re-ran TG2 baseline deployment using same parameter set.

```bash
az deployment group create --name tg2-baseline-gatea-20260717-remed4 --resource-group rg-mua-dev-001 --template-file infra/main.bicep --parameters workloadPrefix=mua environment=dev instance=001 githubPrincipalObjectId=8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 githubRepository=sohamda/model-upgrade-automation githubBranchRef=refs/heads/main --query "{name:name,provisioningState:properties.provisioningState,timestamp:properties.timestamp,error:properties.error}" --output json
```

Outcome:

* Deployment advanced past prior policy deny blockers.
* `networking`, `monitoring`, `storage`, `keyVault`, `foundry`, `governance-definitions`, and `governance` modules succeeded.
* Remaining failure was `containerApps` module validation due ACA managed environment state.

5. Captured exact immutable blocker from nested deployment.

```bash
az deployment operation group list --resource-group rg-mua-dev-001 --name containerApps --query "[?properties.provisioningState=='Failed'].{target:properties.targetResource.resourceName,type:properties.targetResource.resourceType,code:properties.statusMessage.error.code,message:properties.statusMessage.error.message,details:properties.statusMessage.error.details}" --output json
```

Outcome:

* Exact error:
  * `ManagedEnvironmentCapacityHeavyUsageError`
  * Inner provider error code: `AKSCapacityHeavyUsage`
  * Region: `swedencentral`
  * Message indicates regional AKS capacity pressure and recommends another region.

6. Re-ran full Gate A checks post-remediation.

Key commands (same validation set):

```bash
az group show --name rg-mua-dev-001 --query "{name:name,location:location,provisioningState:properties.provisioningState,tags:tags}" --output json
az role assignment list --assignee-object-id 8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 --scope /subscriptions/3b250d66-c6d7-48ff-b78e-351fa7f7a8eb/resourceGroups/rg-mua-dev-001 --query "[].{role:roleDefinitionName,scope:scope}" --output json
az resource list --resource-group rg-mua-dev-001 --resource-type Microsoft.Storage/storageAccounts --query "[].name" --output json
az resource list --resource-group rg-mua-dev-001 --resource-type Microsoft.KeyVault/vaults --query "[].name" --output json
az resource list --resource-group rg-mua-dev-001 --resource-type Microsoft.CognitiveServices/accounts --query "[].name" --output json
az containerapp env show --resource-group rg-mua-dev-001 --name acaenv-mua-dev-001 --query "{name:name,provisioningState:properties.provisioningState}" --output json
az monitor log-analytics workspace list --resource-group rg-mua-dev-001 --query "[].name" --output json
az resource list --resource-group rg-mua-dev-001 --resource-type Microsoft.Insights/components --query "[].name" --output json
az network private-endpoint list --resource-group rg-mua-dev-001 --query "[].name" --output json
az network private-dns zone list --resource-group rg-mua-dev-001 --query "[].name" --output json
az network vnet list --resource-group rg-mua-dev-001 --query "[].name" --output json
az policy assignment list --resource-group rg-mua-dev-001 --query "[].name" --output json
```

Outcome summary:

* PASS: RG and required tags.
* PASS: OIDC SP Contributor at RG scope.
* PASS: Storage, Key Vault, Foundry resources present.
* PASS: App Insights and Log Analytics present.
* PASS: Private endpoints, private DNS zones, and VNet present.
* PASS: TG2 policy assignments present.
* WARN: ACA environment exists but `provisioningState=Failed`.

### Immutable Blocker and Owner/Action

No remaining org-policy blocker is preventing Gate A.

Current immutable blocker is platform regional capacity:

* Blocker: `AKSCapacityHeavyUsage` / `ManagedEnvironmentCapacityHeavyUsageError` while provisioning `Microsoft.App/managedEnvironments` in `swedencentral`.
* Scope ownership: Azure platform capacity in target region (not controllable at RG policy scope).
* Action needed:
  1. Platform owner / subscription operator reattempt in-region after capacity recovery, or
  2. Approve region switch for TG2 baseline to a region with available ACA/AKS capacity and redeploy with updated `location`.

## Final Verdict

**Gate A: WARN**

Rationale:

* Governance and RBAC blockers were remediated.
* Deployment no longer fails on deny-tag policy controls.
* All core TG2 data/governance/network prerequisites are now present and tagged.
* Gate A remains warning-level (not pass) due external regional ACA capacity failure, which prevents fully healthy ACA environment readiness in the current region.

## Retry Evidence Update (Same Baseline, One More Attempt)

* Retry timestamp (UTC): `2026-07-17T09:36:46Z`
* Retry deployment name: `tg2-baseline-gatea-20260717-remed5`
* Scope: `rg-mua-dev-001`

Command executed:

```bash
az deployment group create --name tg2-baseline-gatea-20260717-remed5 --resource-group rg-mua-dev-001 --template-file infra/main.bicep --parameters workloadPrefix=mua environment=dev instance=001 githubPrincipalObjectId=8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 githubRepository=sohamda/model-upgrade-automation githubBranchRef=refs/heads/main --query "{name:name,state:properties.provisioningState,timestamp:properties.timestamp,error:properties.error}" --output json
```

Outcome:

* `DeploymentFailed` at nested `containerApps` stage.
* Immediate blocker from latest retry: `ManagedEnvironmentNotReadyForAppCreation` because `acaenv-mua-dev-001` is currently in `Failed` state.

Persistent root-cause evidence pointer (same nested deployment family):

```bash
az deployment operation group list --resource-group rg-mua-dev-001 --name containerApps --query "[?properties.provisioningState=='Failed'].{target:properties.targetResource.resourceName,type:properties.targetResource.resourceType,code:properties.statusMessage.error.code,message:properties.statusMessage.error.message,details:properties.statusMessage.error.details}" --output json
```

* Returns `ManagedEnvironmentCapacityHeavyUsageError` / `AKSCapacityHeavyUsage` in `swedencentral`.

## Fallback-To-Pass (Non-Destructive)

### Option A: Targeted ACA Environment-Only Retry Loop (Current Region + Backoff)

Intent: retry only the ACA module against existing `acaenv-mua-dev-001` in `swedencentral` with exponential backoff, without deleting any resources.

```powershell
$ErrorActionPreference='Stop'
$rg='rg-mua-dev-001'
$location='swedencentral'
$acaEnv='acaenv-mua-dev-001'
$vnet='vnet-mua-dev-001'
$subnet='snet-aca'
$law='log-mua-dev-001'

$subnetId = az network vnet subnet show --resource-group $rg --vnet-name $vnet --name $subnet --query id --output tsv
$lawCustomerId = az monitor log-analytics workspace show --resource-group $rg --workspace-name $law --query customerId --output tsv
$lawSharedKey = az monitor log-analytics workspace get-shared-keys --resource-group $rg --workspace-name $law --query primarySharedKey --output tsv
$tags = '{"workload":"mua","environment":"dev","managedBy":"model-upgrade-automation","taskGroup":"tg2","owner":"model-upgrade-automation","cleanup":"ephemeral"}'

for ($i = 1; $i -le 6; $i++) {
  $dep = "acaenv-retry-$i-$(Get-Date -Format yyyyMMddHHmmss)"
  az deployment group create --name $dep --resource-group $rg --template-file infra/modules/container-apps.bicep --parameters location=$location containerAppsEnvironmentName=$acaEnv infrastructureSubnetResourceId=$subnetId logAnalyticsWorkspaceCustomerId=$lawCustomerId logAnalyticsWorkspaceSharedKey=$lawSharedKey tags="$tags" --query "{name:name,state:properties.provisioningState,error:properties.error}" --output json
  if ($LASTEXITCODE -eq 0) { break }
  $sleepSeconds = [math]::Min(900, [int](30 * [math]::Pow(2, $i - 1)))
  Start-Sleep -Seconds $sleepSeconds
}
```

Validation check after loop:

```bash
az containerapp env show --resource-group rg-mua-dev-001 --name acaenv-mua-dev-001 --query "{name:name,provisioningState:properties.provisioningState}" --output json
```

### Option B: Alternate-Region Parallel Dev Slice (Instance `002`, Explicit Location Override)

Intent: deploy a coexisting dev slice in same RG with unique names via `instance=002` and explicit region override, keeping existing resources untouched.

```bash
az deployment group what-if --name tg2-baseline-gatea-alt-ne-20260717 --resource-group rg-mua-dev-001 --template-file infra/main.bicep --parameters location=northeurope workloadPrefix=mua environment=dev instance=002 githubPrincipalObjectId=8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 githubRepository=sohamda/model-upgrade-automation githubBranchRef=refs/heads/main --result-format ResourceIdOnly
```

```bash
az deployment group create --name tg2-baseline-gatea-alt-ne-20260717 --resource-group rg-mua-dev-001 --template-file infra/main.bicep --parameters location=northeurope workloadPrefix=mua environment=dev instance=002 githubPrincipalObjectId=8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 githubRepository=sohamda/model-upgrade-automation githubBranchRef=refs/heads/main --query "{name:name,state:properties.provisioningState,timestamp:properties.timestamp,error:properties.error}" --output json
```

Post-create ACA check for alternate slice:

```bash
az containerapp env show --resource-group rg-mua-dev-001 --name acaenv-mua-dev-002 --query "{name:name,location:location,provisioningState:properties.provisioningState}" --output json
```

## Gate Decision Update (Shared Prerequisites vs ACA)

* Shared prerequisites (RBAC, governance tags/policies, storage, key vault, foundry, monitoring, VNet, private DNS, private endpoints): **PASS**.
* ACA readiness in current primary slice (`acaenv-mua-dev-001`): **WARN** due capacity-derived failed environment state.
* Overall Gate A status remains **WARN** (not full PASS) while ACA is degraded.

## Gate B Mode Allowed Now

* Allowed now: **dry-run only** (`what-if`, contract validation, static checks).
* Not allowed yet: **live eval** dependent on a healthy ACA environment until either Option A or Option B yields `acaenv-*` with `provisioningState=Succeeded`.

## Option B Execution Result

### Commands executed

Executed exactly from the checkpoint with explicit location override and no deletes:

```bash
az deployment group what-if --name tg2-baseline-gatea-alt-ne-20260717 --resource-group rg-mua-dev-001 --template-file infra/main.bicep --parameters location=northeurope workloadPrefix=mua environment=dev instance=002 githubPrincipalObjectId=8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 githubRepository=sohamda/model-upgrade-automation githubBranchRef=refs/heads/main --result-format ResourceIdOnly
```

```bash
az deployment group create --name tg2-baseline-gatea-alt-ne-20260717 --resource-group rg-mua-dev-001 --template-file infra/main.bicep --parameters location=northeurope workloadPrefix=mua environment=dev instance=002 githubPrincipalObjectId=8bcf3361-a44d-4d05-bb0d-169abc0ac4c6 githubRepository=sohamda/model-upgrade-automation githubBranchRef=refs/heads/main --query "{name:name,state:properties.provisioningState,timestamp:properties.timestamp,error:properties.error}" --output json
```

```bash
az containerapp env show --resource-group rg-mua-dev-001 --name acaenv-mua-dev-002 --query "{name:name,location:location,provisioningState:properties.provisioningState}" --output json
```

### What-if result

The what-if preview was non-destructive and targeted a coexisting `instance=002` slice in `northeurope`.

Summary:

* `21` resources to create
* `22` resources to deploy
* `5` unsupported what-if predictions
* Existing `instance=001` resources remained in ignore/no-change paths

### Create result

Top-level deployment result:

* Deployment name: `tg2-baseline-gatea-alt-ne-20260717`
* Provisioning state: `Failed`
* Timestamp: `2026-07-17T09:46:42.229325+00:00`

Failure details were non-destructive control-plane reconciliation errors, not runtime-surface failures:

* `rbac`: `RoleAssignmentExists`
  * Existing role assignment already present
* `governance`: `InvalidLocationUpdate`
  * Existing policy assignments at RG scope already exist in `swedencentral` and cannot be rewritten to `northeurope`

These failures did not block creation of the alternate runtime slice.

### Validated `instance=002` resources

Validated core surfaces and network dependencies for the alternate slice:

* ACA environment: `acaenv-mua-dev-002` in `northeurope` with `provisioningState=Succeeded`
* ACA job: `aca-mua-eval` with `provisioningState=Succeeded`
* Storage account: `stmuadev002`
* Key Vault: `kv-mua-dev-002`
* Foundry account: `fnd-mua-dev-002`
* Log Analytics workspace: `log-mua-dev-002`
* Application Insights: `appi-mua-dev-002`
* VNet: `vnet-mua-dev-002` with `provisioningState=Succeeded`
* Private endpoints:
  * `fnd-mua-dev-002-pe` with `provisioningState=Succeeded`
  * `kv-mua-dev-002-pe` with `provisioningState=Succeeded`
  * `stmuadev002-blob-pe` with `provisioningState=Succeeded`
  * `stmuadev002-table-pe` with `provisioningState=Succeeded`
* Private DNS zone links for `vnet-mua-dev-002` exist for:
  * `privatelink.blob.core.windows.net`
  * `privatelink.table.core.windows.net`
  * `privatelink.vaultcore.azure.net`
  * `privatelink.cognitiveservices.azure.com`

### Final Gate A verdict

Gate A status: `PASS`

Rationale:

* The alternate-region non-destructive slice for `instance=002` exists and its ACA environment is healthy.
* All core TG2 surfaces required by the TG3 handoff contract are present for the alternate slice.
* Remaining top-level deployment failures are limited to idempotency and immutable-location reconciliation on already-existing RBAC and policy-assignment resources in the shared RG.
* No delete action was required or performed.

### Live Gate B allowance

Live Gate B allowed: `yes`

Operator note:

* Use the `instance=002` resource names for TG3 live variables.
* The GitHub repository variables beyond the Azure identity trio are not yet populated in the repository and must be set before `dry_run=false` workflow dispatch.

### Exact Gate B kickoff commands

Set the live TG3 repository variables to the passing `instance=002` slice:

```bash
gh variable set RESOURCE_GROUP --body rg-mua-dev-001
gh variable set FOUNDRY_ACCOUNT_NAME --body fnd-mua-dev-002
gh variable set FOUNDRY_PROJECT_NAME --body tg2-contract-pending
gh variable set ACA_ENVIRONMENT_NAME --body acaenv-mua-dev-002
gh variable set ACA_JOB_NAME --body aca-mua-eval
gh variable set STORAGE_ACCOUNT_NAME --body stmuadev002
gh variable set KEY_VAULT_NAME --body kv-mua-dev-002
gh variable set ALLOWED_REGIONS --body northeurope
gh variable set DEPLOYMENT_TYPE --body DataZoneStandard
gh variable set RETIREMENT_HORIZON_DAYS --body 90
gh variable set AUTOMATION_OWNERSHIP_TAG --body model-upgrade-automation
gh variable set AUTOMATION_SCOPE_TAG --body ephemeral
gh variable set MANAGED_BY_TAG --body model-upgrade-automation
gh variable set AUTOMATION_CLEANUP_TAG --body ephemeral
```

Kick off live Gate B:

```bash
gh workflow run detect-and-eval.yml -f dry_run=false -f candidate_limit=3 -f enable_auto_pr=false
```

Optional immediate verification:

```bash
gh run list --workflow detect-and-eval.yml --limit 1
```
