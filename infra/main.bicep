metadata name = 'model-upgrade-automation-tg2-baseline'
metadata description = 'Composes the TG2 infrastructure, identity, and governance baseline for private-networked Foundry evaluation workloads.'

targetScope = 'resourceGroup'

@description('Azure region for all resource group-scoped resources.')
param location string = resourceGroup().location

@description('Short workload prefix used to construct resource names.')
param workloadPrefix string

@description('Deployment environment name.')
@allowed([
  'dev'
  'test'
  'prod'
])
param environment string

@description('Instance suffix used to keep resource names unique within the environment.')
param instance string = '001'

@description('Object ID of the Microsoft Entra application or service principal used by GitHub Actions OIDC federation.')
param githubPrincipalObjectId string

@description('The GitHub repository that is allowed to federate into Azure. Format: org/repo.')
param githubRepository string

@description('The GitHub branch ref that is allowed to federate into Azure. Example: refs/heads/main.')
param githubBranchRef string = 'refs/heads/main'

@description('Resource tags applied to all resources deployed by this baseline.')
param tags object = {
  workload: workloadPrefix
  environment: environment
  managedBy: 'model-upgrade-automation'
  taskGroup: 'tg2'
}

var resourceSuffix = '${workloadPrefix}-${environment}-${instance}'
var acaSubnetName = 'snet-aca'
var privateEndpointSubnetName = 'snet-pe'
var virtualNetworkName = 'vnet-${resourceSuffix}'
var storageAccountName = take(replace('st${workloadPrefix}${environment}${instance}', '-', ''), 24)
var keyVaultName = 'kv-${resourceSuffix}'
var containerAppsEnvironmentName = 'acaenv-${resourceSuffix}'
var foundryAccountName = 'fnd-${resourceSuffix}'
var logAnalyticsWorkspaceName = 'log-${resourceSuffix}'
var appInsightsName = 'appi-${resourceSuffix}'
var requiredGovernanceTags = union(tags, {
  owner: 'model-upgrade-automation'
  cleanup: 'ephemeral'
})

/* Networking */

module networking './modules/networking.bicep' = {
  name: 'networking'
  params: {
    location: location
    virtualNetworkName: virtualNetworkName
    acaSubnetName: acaSubnetName
    privateEndpointSubnetName: privateEndpointSubnetName
    tags: requiredGovernanceTags
  }
}

/* Monitoring */

module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    appInsightsName: appInsightsName
    tags: requiredGovernanceTags
  }
}

/* Data plane resources */

module storage './modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    storageAccountName: storageAccountName
    privateEndpointSubnetResourceId: networking.outputs.privateEndpointSubnetResourceId
    privateDnsZoneIds: networking.outputs.privateDnsZoneIds
    tags: requiredGovernanceTags
  }
}

module keyVault './modules/keyvault.bicep' = {
  name: 'keyVault'
  params: {
    location: location
    keyVaultName: keyVaultName
    privateEndpointSubnetResourceId: networking.outputs.privateEndpointSubnetResourceId
    privateDnsZoneIds: networking.outputs.privateDnsZoneIds
    tags: requiredGovernanceTags
  }
}

module foundry './modules/foundry.bicep' = {
  name: 'foundry'
  params: {
    location: location
    foundryAccountName: foundryAccountName
    privateEndpointSubnetResourceId: networking.outputs.privateEndpointSubnetResourceId
    privateDnsZoneIds: networking.outputs.privateDnsZoneIds
    tags: requiredGovernanceTags
  }
}

/* Compute plane */

module containerApps './modules/container-apps.bicep' = {
  name: 'containerApps'
  params: {
    location: location
    containerAppsEnvironmentName: containerAppsEnvironmentName
    infrastructureSubnetResourceId: networking.outputs.acaSubnetResourceId
    logAnalyticsWorkspaceCustomerId: monitoring.outputs.logAnalyticsWorkspaceCustomerId
    logAnalyticsWorkspaceSharedKey: monitoring.outputs.logAnalyticsWorkspaceSharedKey
    tags: requiredGovernanceTags
  }
}

/* Identity and governance */

module rbac './modules/rbac.bicep' = {
  name: 'rbac'
  params: {
    githubPrincipalObjectId: githubPrincipalObjectId
    containerAppsManagedIdentityPrincipalId: containerApps.outputs.managedIdentityPrincipalId
    foundryAccountResourceId: foundry.outputs.foundryAccountResourceId
    storageAccountResourceId: storage.outputs.storageAccountResourceId
    keyVaultResourceId: keyVault.outputs.keyVaultResourceId
  }
}

module governanceDefinitions './modules/governance-definitions.bicep' = {
  name: 'governance-definitions'
  scope: subscription()
  params: {
    requiredTags: requiredGovernanceTags
  }
}

module governance './modules/governance.bicep' = {
  name: 'governance'
  params: {
    location: location
    foundryPrivateOnlyPolicyDefinitionId: governanceDefinitions.outputs.foundryPrivateOnlyPolicyDefinitionId
    storagePrivateOnlyPolicyDefinitionId: governanceDefinitions.outputs.storagePrivateOnlyPolicyDefinitionId
    keyVaultPrivateOnlyPolicyDefinitionId: governanceDefinitions.outputs.keyVaultPrivateOnlyPolicyDefinitionId
    workloadTagPolicyDefinitionId: governanceDefinitions.outputs.workloadTagPolicyDefinitionId
    environmentTagPolicyDefinitionId: governanceDefinitions.outputs.environmentTagPolicyDefinitionId
    managedByTagPolicyDefinitionId: governanceDefinitions.outputs.managedByTagPolicyDefinitionId
    taskGroupTagPolicyDefinitionId: governanceDefinitions.outputs.taskGroupTagPolicyDefinitionId
    ownerTagPolicyDefinitionId: governanceDefinitions.outputs.ownerTagPolicyDefinitionId
    cleanupTagPolicyDefinitionId: governanceDefinitions.outputs.cleanupTagPolicyDefinitionId
  }
}

@description('Resource name map that TG3 uses to hydrate RunContext and workflow environment variables.')
output resourceNameMap object = {
  virtualNetworkName: virtualNetworkName
  acaSubnetName: acaSubnetName
  privateEndpointSubnetName: privateEndpointSubnetName
  storageAccountName: storageAccountName
  keyVaultName: keyVaultName
  containerAppsEnvironmentName: containerAppsEnvironmentName
  foundryAccountName: foundryAccountName
  appInsightsName: appInsightsName
  logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
}

@description('OIDC contract inputs for TG3 workflow authoring.')
output oidcContract object = {
  githubRepository: githubRepository
  githubBranchRef: githubBranchRef
  githubPrincipalObjectId: githubPrincipalObjectId
  azureResourceGroup: resourceGroup().name
  azureSubscriptionId: subscription().subscriptionId
}

@description('Private DNS zones created for private-only data-plane access.')
output privateDnsZones object = networking.outputs.privateDnsZoneIds

@description('Network contract consumed by TG3 for private-only runtime validation.')
output networkContract object = {
  virtualNetworkName: virtualNetworkName
  acaSubnetName: acaSubnetName
  privateEndpointSubnetName: privateEndpointSubnetName
  acaSubnetResourceId: networking.outputs.acaSubnetResourceId
  privateEndpointSubnetResourceId: networking.outputs.privateEndpointSubnetResourceId
  privateDnsZones: networking.outputs.privateDnsZoneIds
  privateOnlyServices: [
    foundryAccountName
    storageAccountName
    keyVaultName
  ]
}

@description('Governance guardrails and validation targets that TG3 must preserve.')
output governanceContract object = {
  policyDefinitionNames: governance.outputs.policyDefinitionNames
  policyAssignmentNames: governance.outputs.policyAssignmentNames
  policyScopeResourceId: resourceGroup().id
  requiredTags: requiredGovernanceTags
  requiredServiceStates: {
    foundryPublicNetworkAccess: 'Disabled'
    storagePublicNetworkAccess: 'Disabled'
    keyVaultPublicNetworkAccess: 'Disabled'
    storageAllowSharedKeyAccess: false
    foundryDisableLocalAuth: true
  }
}

@description('TG3 validation checklist anchors derived from the TG2 baseline.')
output validationChecklist object = {
  dns: [
    'Resolve Foundry through privatelink.cognitiveservices.azure.com from the ACA subnet path.'
    'Resolve Blob through privatelink.blob.${az.environment().suffixes.storage} from the ACA subnet path.'
    'Resolve Table through privatelink.table.${az.environment().suffixes.storage} from the ACA subnet path.'
    'Resolve Key Vault through privatelink.vaultcore.azure.net from the ACA subnet path.'
  ]
  identity: [
    'GitHub Actions authenticates with OIDC only and uses no client secret.'
    'The GitHub principal retains only resource-group-scoped Contributor access unless replaced by a narrower custom role.'
    'The ACA managed identity can invoke Foundry and write Blob/Table history without storage keys or connection strings.'
  ]
  governance: [
    'Tagged resources include workload, environment, managedBy, taskGroup, owner, and cleanup.'
    'Public network access remains disabled for Foundry, Storage, and Key Vault.'
    'Private endpoint guardrails are assigned at the deployment scope before TG3 enables live runs.'
  ]
}
