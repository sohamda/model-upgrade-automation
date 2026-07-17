# Squad Azure Architect History

## Dispatch: Core Pipeline Live-Mode Azure Architecture & Source Integration (2026-07-17T21:30:00Z)

**Request**: Design target Azure architecture for core pipeline live-mode execution: Foundry discovery source integration, live catalog fetch from Microsoft.AI SDK, provisioning target (Azure Container Apps), evaluation runner placement, and safe mutation gates with state tracking.

**Context**: Prior TG4 slices used fixture-only (local YAML). Now requires live Foundry integration: retirement-schedule discovery, regional availability lookup, ACA provisioning, and evaluation execution. Stakeholder requirement: end-to-end automation with non-mutating default and explicit opt-in for provisioning and evaluation.

**Design Summary**:

*Data Flow*:
- Input: retiring model name OR discover from Foundry schedule (CLI flag: `--retiring-model` or `--discover-from-azure`)
- Detector: accept retiring model string, query Foundry retirement schedule API via Microsoft.AI SDK
- Recommender: live catalog fetch from Foundry model-catalog API (regional availability, metadata, estimated costs)
- Top-k filtering: filter to top-k candidates (default 3, CLI flag: `--top-k`)
- Provisioner: optional step — deploy top-k to Azure Container Apps (explicit opt-in, CLI flag: `--provision-candidates`)
- Evaluator: optional step — run evaluations on provisioned instances (explicit opt-in, CLI flag: `--run-evals`; requires `--provision-candidates`)
- Reporter: aggregate evaluation results and produce markdown output

*Azure Services Mapping*:
- **Foundry (Azure AI Services)**: Retirement schedule query, model catalog fetch (read-only, no state mutation)
- **Container Apps**: Provisioning target for top-k candidate deployment (mutation only if `--provision-candidates` enabled)
- **Storage Account**: Artifact and evaluation-result persistence
- **Key Vault**: API key and connection-string management
- **Log Analytics**: Provisioning and evaluation telemetry

*Control Flow & Safety Gates*:
- Default behavior: detect → rank → report (no cloud mutations, dry-run only)
- Provisioning gate: explicit flag `--provision-candidates` enables ACA deployment
- Evaluation gate: explicit flag `--run-evals` enables evaluation runner (requires `--provision-candidates` or returns error)
- State tracking: record provision status and evaluation invocation in manifest history

*Source Integration Details*:
- **Foundry Retirement Schedule**: Query via Microsoft.AI SDK (endpoint: `{foundry-resource}/retirements`, expects standard Azure auth + RBAC)
- **Foundry Model Catalog**: Query via Microsoft.AI SDK (endpoint: `{foundry-resource}/models`, returns regional availability + cost + metadata)
- **Provisioning Runner**: Invoke ACA job trigger with top-k candidate images (non-blocking, poll for status)
- **Evaluation Source**: Accept custom evaluator service endpoint or delegate to Foundry red-team API (post-MVP)

*Security & Least Privilege*:
- OIDC token for Foundry API access (pre-configured in infra/TG2)
- Managed identity for ACA provisioning (RBAC role assignment in infra/TG2)
- Storage account access via managed identity (no connection strings in env)
- KV access for Foundry API credentials (decoupled from code)

**Member Name**: Cartman

**Outputs**:
- Azure control-flow diagram and service mapping
- Live retirement source design (Foundry SDK integration)
- Live catalog source design (regional availability fetch)
- Provisioning target architecture (ACA deployment + state tracking)
- Safety-gate contract and CLI flag specification

**Recommendation**: Implement live sources in detector and recommender first (read-only); defer provisioning and evaluation to subsequent slices; establish explicit opt-in contract for any cloud mutation.

**Consumption Block**:
```
model: claude-3-5-sonnet
model_tier: default
input_tokens: 2100
cached_tokens: 0
output_tokens: 1200
input_rate: 3.00
cached_rate: 0.30
output_rate: 15.00
est_cost_usd: 0.0243
est_credits: 2.43
basis: estimated
```

**Status**: ✓ Complete
