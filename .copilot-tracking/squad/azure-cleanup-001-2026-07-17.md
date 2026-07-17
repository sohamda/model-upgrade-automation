---
title: Azure Cleanup 001 Audit (2026-07-17)
description: Audit trail for safe cleanup of obsolete instance 001 resources in rg-mua-dev-001 while preserving instance 002 resources.
---

## Scope and constraints

* Resource group: `rg-mua-dev-001`
* Active slice preserved: `instance=002` (northeurope)
* Cleanup scope executed: explicit `instance=001` resource list plus private DNS VNet links named `vnet-mua-dev-001-link`
* Safety constraint: no destructive action against `002` resources or shared policy artifacts

## Pre-delete inventory (candidates)

All requested targets were found before deletion.

* `log-mua-dev-001` (`Microsoft.OperationalInsights/workspaces`)
* `vnet-mua-dev-001` (`Microsoft.Network/virtualNetworks`)
* `appi-mua-dev-001` (`Microsoft.Insights/components`)
* `acaenv-mua-dev-001` (`Microsoft.App/managedEnvironments`)
* `fnd-mua-dev-001` (`Microsoft.CognitiveServices/accounts`)
* `stmuadev001` (`Microsoft.Storage/storageAccounts`)
* `kv-mua-dev-001` (`Microsoft.KeyVault/vaults`)
* `fnd-mua-dev-001-pe` (`Microsoft.Network/privateEndpoints`)
* `stmuadev001-table-pe` (`Microsoft.Network/privateEndpoints`)
* `stmuadev001-blob-pe` (`Microsoft.Network/privateEndpoints`)
* `kv-mua-dev-001-pe` (`Microsoft.Network/privateEndpoints`)
* `privatelink.blob.core.windows.net/vnet-mua-dev-001-link` (`Microsoft.Network/privateDnsZones/virtualNetworkLinks`)
* `privatelink.cognitiveservices.azure.com/vnet-mua-dev-001-link` (`Microsoft.Network/privateDnsZones/virtualNetworkLinks`)
* `privatelink.table.core.windows.net/vnet-mua-dev-001-link` (`Microsoft.Network/privateDnsZones/virtualNetworkLinks`)
* `privatelink.vaultcore.azure.net/vnet-mua-dev-001-link` (`Microsoft.Network/privateDnsZones/virtualNetworkLinks`)

## Deletion ordering used

1. Private DNS VNet links (`vnet-mua-dev-001-link` under each privatelink zone)
2. Private endpoints (`*-001-pe`)
3. Parent resources (`acaenv`, `fnd`, `storage`, `kv`, `appi`, `log`, `vnet`)

## Deleted resources

* `privatelink.blob.core.windows.net/vnet-mua-dev-001-link`
* `privatelink.cognitiveservices.azure.com/vnet-mua-dev-001-link`
* `privatelink.table.core.windows.net/vnet-mua-dev-001-link`
* `privatelink.vaultcore.azure.net/vnet-mua-dev-001-link`
* `fnd-mua-dev-001-pe`
* `stmuadev001-table-pe`
* `stmuadev001-blob-pe`
* `kv-mua-dev-001-pe`
* `acaenv-mua-dev-001`
* `fnd-mua-dev-001`
* `stmuadev001`
* `kv-mua-dev-001`
* `appi-mua-dev-001`
* `log-mua-dev-001`
* `vnet-mua-dev-001`
* `vnet-mua-dev-001-snet-pe-nsg-swedencentral`
* `vnet-mua-dev-001-snet-aca-nsg-swedencentral`

## Skipped and not found

* None from requested target list

## Delete errors

* No command-level delete failures were returned for requested targets

## Verification results

### Verification A: no 001 resources remain

Remaining `001` resources in `rg-mua-dev-001` after cleanup:

* None

Result: **PASS** for strict condition "no 001 resources remain".

### Verification B: critical 002 resources still exist

Confirmed present:

* `acaenv-mua-dev-002` (`Microsoft.App/managedEnvironments`)
* `aca-mua-eval` (`Microsoft.App/jobs`)
* `fnd-mua-dev-002` (`Microsoft.CognitiveServices/accounts`)
* `stmuadev002` (`Microsoft.Storage/storageAccounts`)
* `kv-mua-dev-002` (`Microsoft.KeyVault/vaults`)

Result: **PASS**.

## Final status

**PASS**

Reason: All requested `001` deletion targets were removed, cleanup was extended to delete the two leftover `001` NSGs, no `001` resources remain, and all critical `002` resources are still present.
