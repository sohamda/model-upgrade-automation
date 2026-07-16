metadata name = 'container-apps'
metadata description = 'Deploys the internal Container Apps environment that hosts the evaluator job definition and managed identity contract.'

@description('Azure region for the Container Apps resources.')
param location string

@description('Name of the Container Apps environment.')
param containerAppsEnvironmentName string

@description('Resource ID of the delegated subnet used by the internal Container Apps environment.')
param infrastructureSubnetResourceId string

@description('Log Analytics workspace customer ID used to connect diagnostics.')
param logAnalyticsWorkspaceCustomerId string

@description('Log Analytics workspace shared key used to connect diagnostics.')
@secure()
param logAnalyticsWorkspaceSharedKey string

@description('Resource tags applied to Container Apps resources.')
param tags object

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvironmentName
  location: location
  tags: tags
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnetResourceId
      internal: true
    }
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspaceCustomerId
        sharedKey: logAnalyticsWorkspaceSharedKey
      }
    }
  }
}

resource evaluatorJob 'Microsoft.App/jobs@2024-03-01' = {
  name: 'aca-mua-eval'
  location: location
  tags: union(tags, {
    owner: 'model-upgrade-automation'
    cleanup: 'ephemeral'
  })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    configuration: {
      triggerType: 'Manual'
      replicaRetryLimit: 3
      replicaTimeout: 1800
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'evaluator'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
    }
  }
}

@description('Resource ID of the Container Apps environment.')
output containerAppsEnvironmentResourceId string = containerAppsEnvironment.id

@description('Principal ID of the evaluator job managed identity.')
output managedIdentityPrincipalId string = evaluatorJob.identity.principalId
