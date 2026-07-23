using './main.bicep'

// Target environment (plan-only): subscription 84b82c4c-ae43-4127-8cf6-ecd1c9466830,
// resource group ai-resources, region swedencentral, tenant 1d97ac0b-d548-4256-af90-fdaaac31fbc5.
// NOTE: main.bicep is resource-group scoped. Select the subscription/RG at deploy time
// (az deployment group create --subscription ... --resource-group ai-resources ...).

// Region is set explicitly because the RG default may differ from the intended region.
param location = 'swedencentral'

// Naming inputs. Derived resource names:
//   storage  -> stmuadev003        (Microsoft.Storage, 11 chars, lowercase alphanumeric, OK)
//   keyVault -> kv-mua-dev-003
//   acaEnv   -> acaenv-mua-dev-003
//   acaJob   -> aca-mua-eval        (hard-coded in modules/container-apps.bicep)
//   foundry  -> fnd-mua-dev-003     (NEW Cognitive Services account created by template;
//                                    this is NOT the pre-existing ff-hub-01 hub -- see report)
param workloadPrefix = 'mua'
param environment = 'dev'
param instance = '003'

// OIDC federation inputs for the GitHub Actions principal.
// githubPrincipalObjectId is the Service Principal OBJECT ID (rbac.bicep uses principalType
// 'ServicePrincipal') of app "mua-github-oidc" in the new tenant 1d97ac0b-d548-4256-af90-fdaaac31fbc5.
// Confirm before deploy: az ad sp show --id ea6ff70a-e4fb-48cf-98d9-86dfa3d046db --query id -o tsv
param githubPrincipalObjectId = 'dba88227-a0ce-4b53-b70d-923f0ec64f4f'
param githubRepository = 'sohamda/model-upgrade-automation'
param githubBranchRef = 'refs/heads/main'
