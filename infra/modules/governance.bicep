metadata name = 'governance'
metadata description = 'Assigns the TG2 governance guardrails at the target resource-group scope.'

targetScope = 'resourceGroup'

@description('Azure region used for policy assignment metadata.')
param location string

@description('Policy definition ID for the Foundry private-only guardrail.')
param foundryPrivateOnlyPolicyDefinitionId string

@description('Policy definition ID for the Storage private-only guardrail.')
param storagePrivateOnlyPolicyDefinitionId string

@description('Policy definition ID for the Key Vault private-only guardrail.')
param keyVaultPrivateOnlyPolicyDefinitionId string

@description('Policy definition ID for the workload tag requirement.')
param workloadTagPolicyDefinitionId string

@description('Policy definition ID for the environment tag requirement.')
param environmentTagPolicyDefinitionId string

@description('Policy definition ID for the managedBy tag requirement.')
param managedByTagPolicyDefinitionId string

@description('Policy definition ID for the taskGroup tag requirement.')
param taskGroupTagPolicyDefinitionId string

@description('Policy definition ID for the owner tag requirement.')
param ownerTagPolicyDefinitionId string

@description('Policy definition ID for the cleanup tag requirement.')
param cleanupTagPolicyDefinitionId string

resource assignPrivateOnlyFoundry 'Microsoft.Authorization/policyAssignments@2024-04-01' = {
  name: 'mua-tg2-foundry-private-only'
  location: location
  identity: {
    type: 'None'
  }
  properties: {
    displayName: 'TG2 Foundry private-only guardrail'
    description: 'Applies the TG2 private-only guardrail for Azure AI Foundry.'
    policyDefinitionId: foundryPrivateOnlyPolicyDefinitionId
    enforcementMode: 'Default'
  }
}

resource assignPrivateOnlyStorage 'Microsoft.Authorization/policyAssignments@2024-04-01' = {
  name: 'mua-tg2-storage-private-only'
  location: location
  identity: {
    type: 'None'
  }
  properties: {
    displayName: 'TG2 Storage private-only guardrail'
    description: 'Applies the TG2 private-only guardrail for Storage.'
    policyDefinitionId: storagePrivateOnlyPolicyDefinitionId
    enforcementMode: 'Default'
  }
}

resource assignPrivateOnlyKeyVault 'Microsoft.Authorization/policyAssignments@2024-04-01' = {
  name: 'mua-tg2-keyvault-private-only'
  location: location
  identity: {
    type: 'None'
  }
  properties: {
    displayName: 'TG2 Key Vault private-only guardrail'
    description: 'Applies the TG2 private-only guardrail for Key Vault.'
    policyDefinitionId: keyVaultPrivateOnlyPolicyDefinitionId
    enforcementMode: 'Default'
  }
}

resource assignWorkloadTag 'Microsoft.Authorization/policyAssignments@2024-04-01' = {
  name: 'mua-tg2-require-workload-tag'
  location: location
  identity: {
    type: 'None'
  }
  properties: {
    displayName: 'TG2 workload tag requirement'
    description: 'Requires the workload tag for TG2-managed resources.'
    policyDefinitionId: workloadTagPolicyDefinitionId
    enforcementMode: 'Default'
  }
}

resource assignEnvironmentTag 'Microsoft.Authorization/policyAssignments@2024-04-01' = {
  name: 'mua-tg2-require-environment-tag'
  location: location
  identity: {
    type: 'None'
  }
  properties: {
    displayName: 'TG2 environment tag requirement'
    description: 'Requires the environment tag for TG2-managed resources.'
    policyDefinitionId: environmentTagPolicyDefinitionId
    enforcementMode: 'Default'
  }
}

resource assignManagedByTag 'Microsoft.Authorization/policyAssignments@2024-04-01' = {
  name: 'mua-tg2-require-managedby-tag'
  location: location
  identity: {
    type: 'None'
  }
  properties: {
    displayName: 'TG2 managedBy tag requirement'
    description: 'Requires the managedBy tag for TG2-managed resources.'
    policyDefinitionId: managedByTagPolicyDefinitionId
    enforcementMode: 'Default'
  }
}

resource assignTaskGroupTag 'Microsoft.Authorization/policyAssignments@2024-04-01' = {
  name: 'mua-tg2-require-taskgroup-tag'
  location: location
  identity: {
    type: 'None'
  }
  properties: {
    displayName: 'TG2 taskGroup tag requirement'
    description: 'Requires the taskGroup tag for TG2-managed resources.'
    policyDefinitionId: taskGroupTagPolicyDefinitionId
    enforcementMode: 'Default'
  }
}

resource assignOwnerTag 'Microsoft.Authorization/policyAssignments@2024-04-01' = {
  name: 'mua-tg2-require-owner-tag'
  location: location
  identity: {
    type: 'None'
  }
  properties: {
    displayName: 'TG2 owner tag requirement'
    description: 'Requires the owner tag for ephemeral-resource ownership tracking.'
    policyDefinitionId: ownerTagPolicyDefinitionId
    enforcementMode: 'Default'
  }
}

resource assignCleanupTag 'Microsoft.Authorization/policyAssignments@2024-04-01' = {
  name: 'mua-tg2-require-cleanup-tag'
  location: location
  identity: {
    type: 'None'
  }
  properties: {
    displayName: 'TG2 cleanup tag requirement'
    description: 'Requires the cleanup tag for ephemeral-resource sweep contracts.'
    policyDefinitionId: cleanupTagPolicyDefinitionId
    enforcementMode: 'Default'
  }
}

@description('Policy assignment names that TG3 must validate before enabling live delivery runs.')
output policyAssignmentNames object = {
  foundryPrivateOnly: assignPrivateOnlyFoundry.name
  storagePrivateOnly: assignPrivateOnlyStorage.name
  keyVaultPrivateOnly: assignPrivateOnlyKeyVault.name
  workloadTag: assignWorkloadTag.name
  environmentTag: assignEnvironmentTag.name
  managedByTag: assignManagedByTag.name
  taskGroupTag: assignTaskGroupTag.name
  ownerTag: assignOwnerTag.name
  cleanupTag: assignCleanupTag.name
}

@description('Policy definition names referenced by the TG2 assignment bundle.')
output policyDefinitionNames object = {
  foundryPrivateOnly: last(split(foundryPrivateOnlyPolicyDefinitionId, '/'))
  storagePrivateOnly: last(split(storagePrivateOnlyPolicyDefinitionId, '/'))
  keyVaultPrivateOnly: last(split(keyVaultPrivateOnlyPolicyDefinitionId, '/'))
  workloadTag: last(split(workloadTagPolicyDefinitionId, '/'))
  environmentTag: last(split(environmentTagPolicyDefinitionId, '/'))
  managedByTag: last(split(managedByTagPolicyDefinitionId, '/'))
  taskGroupTag: last(split(taskGroupTagPolicyDefinitionId, '/'))
  ownerTag: last(split(ownerTagPolicyDefinitionId, '/'))
  cleanupTag: last(split(cleanupTagPolicyDefinitionId, '/'))
}
