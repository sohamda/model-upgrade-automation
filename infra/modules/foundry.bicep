metadata name = 'foundry'
metadata description = 'Deploys the Azure AI Foundry account baseline with private-only connectivity and a private endpoint contract for evaluator access.'

@description('Azure region for the Foundry resources.')
param location string

@description('Name of the Azure AI Foundry account.')
param foundryAccountName string

@description('Resource ID of the subnet that hosts private endpoints.')
param privateEndpointSubnetResourceId string

@description('Private DNS zone resource IDs keyed by service contract name.')
param privateDnsZoneIds object

@description('Resource tags applied to Foundry resources.')
param tags object

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: foundryAccountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: foundryAccountName
    publicNetworkAccess: 'Disabled'
    disableLocalAuth: true
    networkAcls: {
      defaultAction: 'Deny'
    }
  }
}

resource foundryPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: '${foundryAccountName}-pe'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetResourceId
    }
    privateLinkServiceConnections: [
      {
        name: 'account'
        properties: {
          privateLinkServiceId: foundryAccount.id
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

resource foundryDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: foundryPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'cognitive-services'
        properties: {
          privateDnsZoneId: privateDnsZoneIds.cognitiveServices
        }
      }
    ]
  }
}

@description('Resource ID of the Azure AI Foundry account.')
output foundryAccountResourceId string = foundryAccount.id
