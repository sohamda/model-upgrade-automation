---
title: Azure AI Foundry Sweden Central Model Pricing Research
description: Live retail-pricing and billing research for GPT-5.1, O3, and Codestral-2501
ms.date: 2026-07-23
ms.topic: reference
---
<!-- markdownlint-disable-file -->

## Research Scope

* Obtain Azure Retail Prices API consumption pricing for GPT-5.1 and O3 in `swedencentral`
* Determine whether Codestral-2501 is offered through Azure AI Foundry or Azure OpenAI in that region
* Confirm model-deployment provisioning, idle, and teardown billing behavior

## Questions

1. Which token-consumption meters for GPT-5.1 and O3 are listed for Sweden Central?
2. Is Codestral-2501 available and, if so, what are its input/output prices?
3. Does provisioning, idle standard deployment capacity, or deletion incur a separate fee?

## Evidence Log

### Retrieval Context

* Retrieval date: 2026-07-23
* Currency: USD retail prices. Actual invoices can vary with agreement-specific pricing,
  currency conversion, credits, and taxes.
* Azure Retail Prices API service filter: `serviceName eq 'Foundry Models'` and
  `armRegionName eq 'swedencentral'`. Historical filters such as `Azure OpenAI` returned
  no current results, so they must not be used for these price lookups.

### GPT-5.1 Consumption Meters

The live catalog returns 18 `Azure OpenAI GPT5` items for Sweden Central. The on-demand
meters are global or EU Data Zone rather than a separately named regional Standard meter:

| Deployment scope | Input | Cached input | Output |
| --- | ---: | ---: | ---: |
| Global | $1.25 per 1M tokens | $0.125 per 1M tokens | $10.00 per 1M tokens |
| Data Zone | $1.375 per 1M tokens | $0.1375 per 1M tokens | $11.00 per 1M tokens |

The catalog labels these records `type: Consumption` and `unitOfMeasure: 1M`; the
relevant SKU names are `GPT 5.1 inp Gl`, `GPT 5.1 cd inp Gl`, `GPT 5.1 opt Gl`,
`GPT 5.1 inp Dz`, `GPT 5.1 cd inp Dz`, and `GPT 5.1 opt Dz`.

Source: [Azure Retail Prices API, GPT-5.1 Sweden Central](https://prices.azure.com/api/retail/prices?$filter=serviceName%20eq%20%27Foundry%20Models%27%20and%20armRegionName%20eq%20%27swedencentral%27%20and%20contains%28skuName%2C%27GPT%205.1%27%29), retrieved 2026-07-23.

### O3 Consumption Meters

The live catalog returns `o3 0416` consumption meters for Sweden Central:

| Deployment scope | Input | Cached input | Output |
| --- | ---: | ---: | ---: |
| Global | $0.002 per 1K tokens | $0.0005 per 1K tokens | $0.008 per 1K tokens |
| Data Zone | $0.0022 per 1K tokens | $0.00055 per 1K tokens | $0.0088 per 1K tokens |
| Regional | $0.00242 per 1K tokens | $0.000605 per 1K tokens | $0.00968 per 1K tokens |

The catalog labels the records `type: Consumption` and `unitOfMeasure: 1K`. Relevant
regional SKU names are `o3 0416 Inp regnl`, `o3 0416 cached Inp regnl`, and
`o3 0416 Outp regnl`.

Source: [Azure Retail Prices API, O3 Sweden Central](https://prices.azure.com/api/retail/prices?$filter=serviceName%20eq%20%27Foundry%20Models%27%20and%20armRegionName%20eq%20%27swedencentral%27%20and%20contains%28skuName%2C%27o3%200416%27%29), retrieved 2026-07-23.

### Codestral and Codestral-2501

The Sweden Central catalog returns six `Azure Mistral Models` `Codestral` token meters:

| Deployment scope | Input | Output |
| --- | ---: | ---: |
| Global | $0.0003 per 1K tokens | $0.0009 per 1K tokens |
| Data Zone | $0.00033 per 1K tokens | $0.00099 per 1K tokens |
| Regional | $0.000363 per 1K tokens | $0.001089 per 1K tokens |

The catalog proves that generic `Codestral` is billed through Foundry Models in Sweden
Central, but does not publish a model-version identifier. A targeted `2501` catalog
search returned zero records. Mistral's official model list identifies `CODESTRAL-2501`
as a legacy/deprecated Codestral model. Therefore, the generic Azure meter must not be
treated as proof that exact version `Codestral-2501` remains deployable in Azure AI
Foundry. Confirm the version in the Foundry model catalog for the subscription and
region before choosing it.

Sources: [Azure Retail Prices API, Codestral Sweden Central](https://prices.azure.com/api/retail/prices?$filter=serviceName%20eq%20%27Foundry%20Models%27%20and%20armRegionName%20eq%20%27swedencentral%27%20and%20contains%28skuName%2C%27Codestral%27%29), [Azure Retail Prices API, `2501` search](https://prices.azure.com/api/retail/prices?$filter=serviceName%20eq%20%27Foundry%20Models%27%20and%20armRegionName%20eq%20%27swedencentral%27%20and%20contains%28meterName%2C%272501%27%29), and [Mistral Models Overview](https://docs.mistral.ai/getting-started/models/), retrieved 2026-07-23.

### Provisioning, Idle, and Deletion Charges

Microsoft Foundry defines Standard deployments as pay-per-token: "You pay only for what
you consume." A Standard deployment with zero requests therefore has no model-inference
or capacity charge from the Standard deployment itself. Provisioned deployment types are
different: they reserve a fixed number of provisioned throughput units (PTUs), so their
capacity remains billable while allocated, including idle time.

Neither the live Foundry Models retail catalog slices nor the Microsoft pricing and
deployment documentation list a separate one-time model-deployment creation/provisioning
fee or a deletion/teardown fee. The defensible conclusion is that no separate fee is
listed, not a contractual guarantee that an Azure invoice can never contain other costs.
Deleting a deployment stops future Standard request charges and releases its allocated
capacity; it does not reverse usage already incurred, and associated Azure resources can
have their own meters. Cost Management retains usage for deleted resources and billing
data can arrive after usage occurs.

Sources: [Understanding deployment types in Microsoft Foundry Models](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/deployment-types), [Azure OpenAI Service pricing](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/), and [Understand Cost Management data](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/understand-cost-mgt-data), retrieved 2026-07-23.

### Conclusions

1. GPT-5.1 and O3 have active Sweden Central Foundry Models price meters. GPT-5.1 uses
	global or EU Data Zone token meters in the catalog; O3 additionally has regional
	token meters.
2. Generic Codestral token pricing is available through Foundry Models in Sweden Central,
	but exact Codestral-2501 deployment availability is unproven and requires an
	entitlement-aware Foundry catalog check.
3. Standard deployments have no hourly idle charge at zero inference because they are
	pay-per-token.
4. Provisioned deployments have capacity-based PTU billing while capacity is allocated.
5. No distinct one-time deployment provisioning or teardown fee is listed in the checked
	official price catalog and documentation. Already-incurred usage and separate resource
	charges still remain payable.

## Follow-On Questions

None identified.
