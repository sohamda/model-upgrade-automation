metadata name = 'monitoring'
metadata description = 'Deploys the Log Analytics workspace and Application Insights instance used by the TG2 baseline.'

@description('Azure region for monitoring resources.')
param location string

@description('Name of the Log Analytics workspace.')
param logAnalyticsWorkspaceName string

@description('Name of the Application Insights component.')
param appInsightsName string

@description('Resource tags applied to monitoring resources.')
param tags object

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    IngestionMode: 'LogAnalytics'
    DisableLocalAuth: true
    publicNetworkAccessForIngestion: 'Disabled'
    publicNetworkAccessForQuery: 'Disabled'
  }
}

@description('The Log Analytics workspace customer ID used by Container Apps.')
output logAnalyticsWorkspaceCustomerId string = logAnalyticsWorkspace.properties.customerId

@description('The Log Analytics shared key used by Container Apps environment provisioning.')
@secure()
output logAnalyticsWorkspaceSharedKey string = logAnalyticsWorkspace.listKeys().primarySharedKey

@description('The Application Insights connection string for workflow/runtime configuration.')
output appInsightsConnectionString string = appInsights.properties.ConnectionString
