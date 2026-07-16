metadata name = 'networking'
metadata description = 'Deploys the private-network baseline for model-upgrade-automation, including the VNet, delegated subnets, and private DNS zones.'

@description('Azure region for the networking resources.')
param location string

@description('Virtual network name.')
param virtualNetworkName string

@description('Delegated subnet for the internal Container Apps environment.')
param acaSubnetName string

@description('Subnet dedicated to private endpoints.')
param privateEndpointSubnetName string

@description('Resource tags applied to the networking resources.')
param tags object

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: virtualNetworkName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.40.0.0/16'
      ]
    }
    subnets: [
      {
        name: acaSubnetName
        properties: {
          addressPrefix: '10.40.0.0/24'
          delegations: [
            {
              name: 'containerApps'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: privateEndpointSubnetName
        properties: {
          addressPrefix: '10.40.1.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

var acaSubnetResourceId = resourceId('Microsoft.Network/virtualNetworks/subnets', virtualNetworkName, acaSubnetName)
var privateEndpointSubnetResolvedResourceId = resourceId('Microsoft.Network/virtualNetworks/subnets', virtualNetworkName, privateEndpointSubnetName)

resource cognitiveServicesPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.cognitiveservices.azure.com'
  location: 'global'
  tags: tags
}

resource blobPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.blob.${az.environment().suffixes.storage}'
  location: 'global'
  tags: tags
}

resource tablePrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.table.${az.environment().suffixes.storage}'
  location: 'global'
  tags: tags
}

resource vaultPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.vaultcore.azure.net'
  location: 'global'
  tags: tags
}

resource cognitiveServicesDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: cognitiveServicesPrivateDnsZone
  name: '${virtualNetworkName}-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource blobDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: blobPrivateDnsZone
  name: '${virtualNetworkName}-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource tableDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: tablePrivateDnsZone
  name: '${virtualNetworkName}-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource vaultDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: vaultPrivateDnsZone
  name: '${virtualNetworkName}-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

@description('The resource ID of the delegated ACA subnet.')
output acaSubnetResourceId string = acaSubnetResourceId

@description('The resource ID of the private endpoint subnet.')
output privateEndpointSubnetResourceId string = privateEndpointSubnetResolvedResourceId

@description('Private DNS zones keyed by service contract name.')
output privateDnsZoneIds object = {
  cognitiveServices: cognitiveServicesPrivateDnsZone.id
  blob: blobPrivateDnsZone.id
  table: tablePrivateDnsZone.id
  vault: vaultPrivateDnsZone.id
}
