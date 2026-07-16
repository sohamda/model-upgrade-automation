metadata name = 'governance-definitions'
metadata description = 'Defines the TG2 custom policy definitions for private-only services and required tags.'

targetScope = 'subscription'

@description('Tag names and expected values enforced by the TG2 baseline.')
param requiredTags object

var foundryType = 'Microsoft.CognitiveServices/accounts'
var storageType = 'Microsoft.Storage/storageAccounts'
var keyVaultType = 'Microsoft.KeyVault/vaults'

resource enforcePrivateOnlyFoundry 'Microsoft.Authorization/policyDefinitions@2023-04-01' = {
  name: 'mua-tg2-enforce-foundry-private-only'
  properties: {
    policyType: 'Custom'
    mode: 'Indexed'
    displayName: 'TG2 Require private-only Azure AI Foundry'
    description: 'Denies Azure AI Foundry accounts that enable public network access or local key-based auth.'
    metadata: {
      category: 'model-upgrade-automation'
      version: '1.0.0'
      taskGroup: 'tg2'
    }
    policyRule: {
      if: {
        allOf: [
          {
            field: 'type'
            equals: foundryType
          }
          {
            anyOf: [
              {
                field: 'Microsoft.CognitiveServices/accounts/publicNetworkAccess'
                notEquals: 'Disabled'
              }
              {
                field: 'Microsoft.CognitiveServices/accounts/disableLocalAuth'
                notEquals: true
              }
            ]
          }
        ]
      }
      then: {
        effect: 'deny'
      }
    }
  }
}

resource enforcePrivateOnlyStorage 'Microsoft.Authorization/policyDefinitions@2023-04-01' = {
  name: 'mua-tg2-enforce-storage-private-only'
  properties: {
    policyType: 'Custom'
    mode: 'Indexed'
    displayName: 'TG2 Require private-only Storage'
    description: 'Denies storage accounts that expose public network access, shared keys, or public blob access.'
    metadata: {
      category: 'model-upgrade-automation'
      version: '1.0.0'
      taskGroup: 'tg2'
    }
    policyRule: {
      if: {
        allOf: [
          {
            field: 'type'
            equals: storageType
          }
          {
            anyOf: [
              {
                field: 'Microsoft.Storage/storageAccounts/publicNetworkAccess'
                notEquals: 'Disabled'
              }
              {
                field: 'Microsoft.Storage/storageAccounts/allowBlobPublicAccess'
                notEquals: false
              }
              {
                field: 'Microsoft.Storage/storageAccounts/allowSharedKeyAccess'
                notEquals: false
              }
            ]
          }
        ]
      }
      then: {
        effect: 'deny'
      }
    }
  }
}

resource enforcePrivateOnlyKeyVault 'Microsoft.Authorization/policyDefinitions@2023-04-01' = {
  name: 'mua-tg2-enforce-keyvault-private-only'
  properties: {
    policyType: 'Custom'
    mode: 'Indexed'
    displayName: 'TG2 Require private-only Key Vault'
    description: 'Denies Key Vaults that expose public network access.'
    metadata: {
      category: 'model-upgrade-automation'
      version: '1.0.0'
      taskGroup: 'tg2'
    }
    policyRule: {
      if: {
        allOf: [
          {
            field: 'type'
            equals: keyVaultType
          }
          {
            field: 'Microsoft.KeyVault/vaults/publicNetworkAccess'
            notEquals: 'Disabled'
          }
        ]
      }
      then: {
        effect: 'deny'
      }
    }
  }
}

resource requireWorkloadTag 'Microsoft.Authorization/policyDefinitions@2023-04-01' = {
  name: 'mua-tg2-require-workload-tag'
  properties: {
    policyType: 'Custom'
    mode: 'Indexed'
    displayName: 'TG2 Require workload tag'
    description: 'Requires the workload tag with the TG2 baseline value.'
    metadata: {
      category: 'model-upgrade-automation'
      version: '1.0.0'
      taskGroup: 'tg2'
    }
    parameters: {
      expectedValue: {
        type: 'String'
        defaultValue: string(requiredTags.workload)
      }
    }
    policyRule: {
      if: {
        anyOf: [
          {
            field: 'tags[\'workload\']'
            exists: false
          }
          {
            field: 'tags[\'workload\']'
            notEquals: '[parameters(\'expectedValue\')]'
          }
        ]
      }
      then: {
        effect: 'deny'
      }
    }
  }
}

resource requireEnvironmentTag 'Microsoft.Authorization/policyDefinitions@2023-04-01' = {
  name: 'mua-tg2-require-environment-tag'
  properties: {
    policyType: 'Custom'
    mode: 'Indexed'
    displayName: 'TG2 Require environment tag'
    description: 'Requires the environment tag with the TG2 baseline value.'
    metadata: {
      category: 'model-upgrade-automation'
      version: '1.0.0'
      taskGroup: 'tg2'
    }
    parameters: {
      expectedValue: {
        type: 'String'
        defaultValue: string(requiredTags.environment)
      }
    }
    policyRule: {
      if: {
        anyOf: [
          {
            field: 'tags[\'environment\']'
            exists: false
          }
          {
            field: 'tags[\'environment\']'
            notEquals: '[parameters(\'expectedValue\')]'
          }
        ]
      }
      then: {
        effect: 'deny'
      }
    }
  }
}

resource requireManagedByTag 'Microsoft.Authorization/policyDefinitions@2023-04-01' = {
  name: 'mua-tg2-require-managedby-tag'
  properties: {
    policyType: 'Custom'
    mode: 'Indexed'
    displayName: 'TG2 Require managedBy tag'
    description: 'Requires the managedBy tag with the TG2 baseline value.'
    metadata: {
      category: 'model-upgrade-automation'
      version: '1.0.0'
      taskGroup: 'tg2'
    }
    parameters: {
      expectedValue: {
        type: 'String'
        defaultValue: string(requiredTags.managedBy)
      }
    }
    policyRule: {
      if: {
        anyOf: [
          {
            field: 'tags[\'managedBy\']'
            exists: false
          }
          {
            field: 'tags[\'managedBy\']'
            notEquals: '[parameters(\'expectedValue\')]'
          }
        ]
      }
      then: {
        effect: 'deny'
      }
    }
  }
}

resource requireTaskGroupTag 'Microsoft.Authorization/policyDefinitions@2023-04-01' = {
  name: 'mua-tg2-require-taskgroup-tag'
  properties: {
    policyType: 'Custom'
    mode: 'Indexed'
    displayName: 'TG2 Require taskGroup tag'
    description: 'Requires the taskGroup tag with the TG2 baseline value.'
    metadata: {
      category: 'model-upgrade-automation'
      version: '1.0.0'
      taskGroup: 'tg2'
    }
    parameters: {
      expectedValue: {
        type: 'String'
        defaultValue: string(requiredTags.taskGroup)
      }
    }
    policyRule: {
      if: {
        anyOf: [
          {
            field: 'tags[\'taskGroup\']'
            exists: false
          }
          {
            field: 'tags[\'taskGroup\']'
            notEquals: '[parameters(\'expectedValue\')]'
          }
        ]
      }
      then: {
        effect: 'deny'
      }
    }
  }
}

resource requireOwnerTag 'Microsoft.Authorization/policyDefinitions@2023-04-01' = {
  name: 'mua-tg2-require-owner-tag'
  properties: {
    policyType: 'Custom'
    mode: 'Indexed'
    displayName: 'TG2 Require owner tag'
    description: 'Requires the owner tag used by the orphan sweep contract.'
    metadata: {
      category: 'model-upgrade-automation'
      version: '1.0.0'
      taskGroup: 'tg2'
    }
    parameters: {
      expectedValue: {
        type: 'String'
        defaultValue: string(requiredTags.owner)
      }
    }
    policyRule: {
      if: {
        anyOf: [
          {
            field: 'tags[\'owner\']'
            exists: false
          }
          {
            field: 'tags[\'owner\']'
            notEquals: '[parameters(\'expectedValue\')]'
          }
        ]
      }
      then: {
        effect: 'deny'
      }
    }
  }
}

resource requireCleanupTag 'Microsoft.Authorization/policyDefinitions@2023-04-01' = {
  name: 'mua-tg2-require-cleanup-tag'
  properties: {
    policyType: 'Custom'
    mode: 'Indexed'
    displayName: 'TG2 Require cleanup tag'
    description: 'Requires the cleanup tag used by ephemeral resource sweeps.'
    metadata: {
      category: 'model-upgrade-automation'
      version: '1.0.0'
      taskGroup: 'tg2'
    }
    parameters: {
      expectedValue: {
        type: 'String'
        defaultValue: string(requiredTags.cleanup)
      }
    }
    policyRule: {
      if: {
        anyOf: [
          {
            field: 'tags[\'cleanup\']'
            exists: false
          }
          {
            field: 'tags[\'cleanup\']'
            notEquals: '[parameters(\'expectedValue\')]'
          }
        ]
      }
      then: {
        effect: 'deny'
      }
    }
  }
}

@description('Custom policy definition names created by the TG2 governance baseline.')
output policyDefinitionNames object = {
  foundryPrivateOnly: enforcePrivateOnlyFoundry.name
  storagePrivateOnly: enforcePrivateOnlyStorage.name
  keyVaultPrivateOnly: enforcePrivateOnlyKeyVault.name
  workloadTag: requireWorkloadTag.name
  environmentTag: requireEnvironmentTag.name
  managedByTag: requireManagedByTag.name
  taskGroupTag: requireTaskGroupTag.name
  ownerTag: requireOwnerTag.name
  cleanupTag: requireCleanupTag.name
}

@description('Policy definition IDs consumed by the TG2 assignment bundle.')
output foundryPrivateOnlyPolicyDefinitionId string = enforcePrivateOnlyFoundry.id

@description('Policy definition IDs consumed by the TG2 assignment bundle.')
output storagePrivateOnlyPolicyDefinitionId string = enforcePrivateOnlyStorage.id

@description('Policy definition IDs consumed by the TG2 assignment bundle.')
output keyVaultPrivateOnlyPolicyDefinitionId string = enforcePrivateOnlyKeyVault.id

@description('Policy definition IDs consumed by the TG2 assignment bundle.')
output workloadTagPolicyDefinitionId string = requireWorkloadTag.id

@description('Policy definition IDs consumed by the TG2 assignment bundle.')
output environmentTagPolicyDefinitionId string = requireEnvironmentTag.id

@description('Policy definition IDs consumed by the TG2 assignment bundle.')
output managedByTagPolicyDefinitionId string = requireManagedByTag.id

@description('Policy definition IDs consumed by the TG2 assignment bundle.')
output taskGroupTagPolicyDefinitionId string = requireTaskGroupTag.id

@description('Policy definition IDs consumed by the TG2 assignment bundle.')
output ownerTagPolicyDefinitionId string = requireOwnerTag.id

@description('Policy definition IDs consumed by the TG2 assignment bundle.')
output cleanupTagPolicyDefinitionId string = requireCleanupTag.id
