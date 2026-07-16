metadata name = 'rbac'
metadata description = 'Assigns least-privilege roles to the GitHub OIDC principal and the Container Apps managed identity.'

@description('Object ID of the Microsoft Entra application or service principal used by GitHub Actions OIDC federation.')
param githubPrincipalObjectId string

@description('Principal ID of the Container Apps managed identity.')
param containerAppsManagedIdentityPrincipalId string

@description('Resource ID of the Azure AI Foundry account.')
param foundryAccountResourceId string

@description('Resource ID of the storage account.')
param storageAccountResourceId string

@description('Resource ID of the Key Vault.')
param keyVaultResourceId string

var contributorRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')
var storageBlobDataContributorRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
var storageTableDataContributorRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
var keyVaultSecretsUserRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
var cognitiveServicesUserRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
var monitoringMetricsPublisherRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')
var foundryAccountName = last(split(foundryAccountResourceId, '/'))
var storageAccountName = last(split(storageAccountResourceId, '/'))
var keyVaultName = last(split(keyVaultResourceId, '/'))

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: foundryAccountName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: storageAccountName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource githubContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, githubPrincipalObjectId, contributorRoleDefinitionId)
  properties: {
    principalId: githubPrincipalObjectId
    principalType: 'ServicePrincipal'
    roleDefinitionId: contributorRoleDefinitionId
  }
}

resource acaFoundryUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryAccountResourceId, containerAppsManagedIdentityPrincipalId, cognitiveServicesUserRoleDefinitionId)
  scope: foundryAccount
  properties: {
    principalId: containerAppsManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cognitiveServicesUserRoleDefinitionId
  }
}

resource acaBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountResourceId, containerAppsManagedIdentityPrincipalId, storageBlobDataContributorRoleDefinitionId)
  scope: storageAccount
  properties: {
    principalId: containerAppsManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataContributorRoleDefinitionId
  }
}

resource acaTableContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid('${storageAccountResourceId}/table', containerAppsManagedIdentityPrincipalId, storageTableDataContributorRoleDefinitionId)
  scope: storageAccount
  properties: {
    principalId: containerAppsManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageTableDataContributorRoleDefinitionId
  }
}

resource acaKeyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultResourceId, containerAppsManagedIdentityPrincipalId, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: {
    principalId: containerAppsManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
  }
}

resource acaMetricsPublisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, containerAppsManagedIdentityPrincipalId, monitoringMetricsPublisherRoleDefinitionId)
  properties: {
    principalId: containerAppsManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: monitoringMetricsPublisherRoleDefinitionId
  }
}

@description('Role names assigned by the TG2 baseline.')
output roleAssignments object = {
  githubPrincipal: [
    'Contributor (resource group scoped)'
  ]
  containerAppsManagedIdentity: [
    'Cognitive Services User'
    'Storage Blob Data Contributor'
    'Storage Table Data Contributor'
    'Key Vault Secrets User'
    'Monitoring Metrics Publisher'
  ]
}
