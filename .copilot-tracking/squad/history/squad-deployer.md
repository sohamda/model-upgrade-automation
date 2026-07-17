<!-- markdownlint-disable-file -->
# Squad Deployer Operations

## 2026-07-17T16:30:00Z: Azure Cleanup Completion for Instance 001

**Request**: User requested removal of obsolete instance 001 resources from rg-mua-dev-001.

**Cleanup Executed**:
- Deleted all requested -001 resources
- Removed leftover NSGs:
  - vnet-mua-dev-001-snet-pe-nsg-swedencentral
  - vnet-mua-dev-001-snet-aca-nsg-swedencentral

**Verification**:
- Command: `az resource list --resource-group rg-mua-dev-001 --query "[?contains(name, '001')].[name, type]" -o tsv`
- Result: Zero remaining resources with '001' in name

**Integrity Check**: Critical 002 resources verified intact:
- acaenv-mua-dev-002
- aca-mua-eval
- fnd-mua-dev-002
- stmuadev002
- kv-mua-dev-002

**Audit Artifact**: `.copilot-tracking/squad/azure-cleanup-001-2026-07-17.md` — PASS

**Outcome**: ✓ Complete

**Consumption Block**:
| Model | Model Tier | Input Tokens | Cached Tokens | Output Tokens | Input Rate | Cached Rate | Output Rate | Est Cost USD | Est Credits | Basis |
|---|---|---|---|---|---|---|---|---|---|---|
| tier-1 | fast | 400 | 0 | 150 | 0.80 | 0.08 | 4.00 | 0.00104 | 0.104 | tier-default |

## 2026-07-17T20:45:00Z: Azure Readiness Gate B – Pass After Remediation

**Request**: User initiated Azure Readiness Gate B validation with OIDC federation and artifact staging prerequisites.

**Gate B Initial Status**: ✗ FAILED
- **Artifact Upload Issue**: Hidden-path handling in GitHub workflow artifact upload step prevented manifest checkpoint from staging
- **OIDC Subject Mismatch**: Federated credential configuration did not include `repo:sohamda/model-upgrade-automation:environment:main` subject variant required for environment-scoped deployments

**Remediation Applied**:
- **Workflow Fixes**: Updated `.github/workflows/detect-and-eval.yml` and `.github/workflows/sweep-orphans.yml` to correct artifact upload path handling and add nested directory support
- **OIDC Federated Credential Update**: Added environment-scoped federated credential variant (`repo:sohamda/model-upgrade-automation:environment:main`) to existing Azure AD app registration—additive update preserving prior subject variants

**Gate B Revalidation**: ✓ PASSED

**Successful Reruns**:
- Run 29577754373 (`detect-and-eval`): ✓ Success — Detection and evaluation pipeline executed without errors; artifacts staged correctly
- Run 29577862865 (`sweep-orphans`): ✓ Success — Orphan cleanup and resource validation executed without errors

**Checkpoint Artifact**: `.copilot-tracking/squad/azure-gate-b-2026-07-17.md` — **PASS**

**Status Notes**:
- All primary validation gates passed
- Additional local tracking and infrastructure changes remain in working tree and were intentionally not modified in this remediation step
- Downstream Gate C execution eligible

**Outcome**: ✓ PASS — Gated prerequisites satisfied; downstream validation unblocked

**Consumption Block**:
| Model | Model Tier | Input Tokens | Cached Tokens | Output Tokens | Input Rate | Cached Rate | Output Rate | Est Cost USD | Est Credits | Basis |
|---|---|---|---|---|---|---|---|---|---|---|
| tier-1 | fast | 520 | 0 | 180 | 0.80 | 0.08 | 4.00 | 0.00134 | 0.134 | tier-default |
