---
title: Task Group 2 Infrastructure Identity Governance Baseline
description: Execution-ready implementation artifact for private-network, secretless OIDC, RBAC, and governance baseline
ms.date: 2026-07-15
ms.topic: reference
---
<!-- markdownlint-disable-file -->

## Objective

Deliver Task Group 2 baseline for infrastructure, identity, and governance so Task Group 3 can wire CI/CD safely in parallel without violating the private-network and secretless OIDC contracts.

Primary owner: Kyle (Security/Identity + Governance Lead)
Support owners: Butters (DevOps + IaC Engineer), Stan (Platform Reliability + SRE Lead)

## Scope

In scope:

- Provision and harden persistent Azure infrastructure modules defined by TG1 contracts: VNet, subnets, private DNS zones, Foundry private endpoint, Storage private endpoints (Blob and Table), Key Vault private endpoint, ACA environment with VNet integration, monitoring.
- Establish secretless OIDC federation from GitHub Actions to Azure ARM control plane.
- Define and apply RBAC matrix for pipeline principal and ACA managed identity.
- Establish governance guardrails (policy assignments and baseline controls) to enforce private networking and no public data-plane exposure.
- Produce validation evidence proving data-plane isolation and identity least privilege.

Out of scope:

- Implementing application modules in src/ (detector, recommender, evaluator, reporter, orchestrator).
- Authoring TG3 workflows in .github/workflows.
- APIM routing, production traffic switching, and auto-remediation behavior.
- Any direct deployment automation beyond baseline IaC and identity/governance foundations.

## Non-goals

- No long-lived credentials in repository, workflow secrets, or source files.
- No public network access enablement for Foundry, Storage, or Key Vault.
- No public data-plane fallback path.

## TG1 Dependency Links (Contract Anchors)

This TG2 artifact implements the following TG1 contract sections from .copilot-tracking/squad/task-group-01-architecture-blueprint.md:

- Module boundaries and handoff: "Handoff to Task Group 2 (Infrastructure, Identity, Governance)"
- RunContext required fields used for infra identity bindings
- Data artifact contract (Blob/Table) and App Insights contract
- Failure/idempotency contract (safe retries and idempotent resource operations)

Hard dependency assumptions imported from requirements/plan.md and decisions.md:

- Private endpoint posture for Foundry/Storage/KV with private DNS resolution.
- OIDC federated identity from GitHub Actions to Azure.
- ACA job data-plane execution inside VNet-integrated environment.
- ARM control-plane operations from GitHub Actions only.

## Deliverables and Acceptance Criteria

### D1. Private Network Baseline

Deliverables:

- infra/modules/networking.bicep (VNet, snet-aca, snet-pe, private DNS zones)
- infra/modules/foundry.bicep (private endpoint wiring, publicNetworkAccess disabled)
- infra/modules/storage.bicep (blob/table private endpoints, publicNetworkAccess disabled)
- infra/modules/keyvault.bicep (private endpoint, RBAC mode)
- infra/main.bicep composition updates

Acceptance criteria:

- Foundry, Storage, and Key Vault resolve through private DNS from ACA subnet.
- publicNetworkAccess is Disabled for Foundry, Storage, Key Vault.
- No NSG or route path exposes data-plane resources publicly.

### D2. Identity and Access Baseline

Deliverables:

- Federated credential definition and setup procedure (GitHub Actions OIDC -> Azure principal)
- infra/modules/rbac.bicep role assignments for:
  - GitHub OIDC principal (ARM control-plane only)
  - ACA managed identity (Foundry invoke + Blob/Table write + KV read as required)
- docs/oidc-setup.md updates (if missing or incomplete)

Acceptance criteria:

- GitHub workflow identity can execute ARM create/read/update/delete for scoped resources without secrets.
- ACA identity can perform required data-plane actions and cannot perform broad subscription management.
- No key-based auth required for pipeline execution.

### D3. Governance Guardrails Baseline

Deliverables:

- Policy assignment definitions and parameterization for:
  - Deny public network access for scoped services
  - Require private endpoints for data-plane services
  - Enforce tags for ephemeral resource ownership and cleanup traceability
- Baseline governance evidence document in .copilot-tracking/squad/history/ (new TG2 evidence note)

Acceptance criteria:

- Policy assignments are deployable and scoped to target subscription/resource group.
- Non-compliant public exposure attempts are blocked or flagged per policy effect.
- Required tags are enforced on ephemeral resources used by pipeline runs.

### D4. Validation and Evidence Pack

Deliverables:

- Connectivity and identity validation checklist for TG3 consumption
- Test evidence summary for DNS, RBAC, and private endpoint behavior

Acceptance criteria:

- Evidence explicitly maps each test to TG1 contract requirement.
- TG3 can execute workflow authoring without re-deciding infra/identity controls.

## Detailed Task Breakdown (Owner per Task)

### Phase 1. Baseline Contract Mapping and Design Lock

- TG2-01 Contract extraction and control matrix generation
  - Owner: Kyle
  - Support: Stan
  - Output: TG2 control matrix mapping TG1 clauses to concrete IaC/policy tasks
- TG2-02 Resource naming and ID schema alignment with RunContext fields
  - Owner: Butters
  - Support: Kyle
  - Output: naming map and parameter schema for infra modules

### Phase 2. Network and Private Endpoint Foundation

- TG2-03 Build/adjust networking.bicep for VNet/subnets/private DNS zones
  - Owner: Butters
  - Support: Stan
- TG2-04 Build/adjust foundry.bicep private endpoint and DNS links
  - Owner: Butters
  - Support: Kyle
- TG2-05 Build/adjust storage.bicep for blob/table private endpoints and disable public access
  - Owner: Butters
  - Support: Kyle
- TG2-06 Build/adjust keyvault.bicep private endpoint and RBAC mode
  - Owner: Butters
  - Support: Kyle

### Phase 3. Identity and RBAC Foundation

- TG2-07 OIDC federation setup and trust policy definition for GitHub Actions
  - Owner: Kyle
  - Support: Butters
- TG2-08 RBAC least-privilege mapping and module implementation in rbac.bicep
  - Owner: Kyle
  - Support: Butters
- TG2-09 ACA managed identity permissions validation design
  - Owner: Stan
  - Support: Kyle

### Phase 4. Governance Guardrails

- TG2-10 Policy assignment bundle for private-network and tagging guardrails
  - Owner: Kyle
  - Support: Stan
- TG2-11 Governance rollout plan by scope (subscription vs RG)
  - Owner: Kyle
  - Support: Butters

### Phase 5. Validation Evidence and TG3 Handoff

- TG2-12 Private DNS and endpoint reachability validation checklist
  - Owner: Stan
  - Support: Butters
- TG2-13 Identity/RBAC validation checklist and negative test set
  - Owner: Kyle
  - Support: Stan
- TG2-14 Publish TG3 handoff contract and dependency package
  - Owner: Kyle
  - Support: Butters, Stan

## Ordered Implementation Sequence (Parallelizable Steps Marked)

Execution order:

1. TG2-01, TG2-02 (sequential start; establishes control and naming contract)
2. TG2-03, TG2-04, TG2-05, TG2-06 (parallelizable after TG2-02)
3. TG2-07 and TG2-08 (parallelizable with end of Phase 2 once resource scopes are stable)
4. TG2-09 (after TG2-08 draft role map exists)
5. TG2-10 and TG2-11 (parallelizable after TG2-01 and TG2-08)
6. TG2-12 and TG2-13 (parallelizable after Phases 2-4 outputs exist)
7. TG2-14 final handoff package (after TG2-12 and TG2-13)

Parallelization map:

- Parallel Set A: TG2-03 + TG2-04 + TG2-05 + TG2-06
- Parallel Set B: TG2-07 + TG2-08
- Parallel Set C: TG2-10 + TG2-11
- Parallel Set D: TG2-12 + TG2-13

Sequence constraints:

- TG2-04/05/06 must follow final naming and subnet/DNS decisions from TG2-02.
- TG2-08 role assignments must complete before TG2-13 validation can be finalized.
- TG2-14 cannot start until validation evidence from TG2-12 and TG2-13 is complete.

## Risk Register and Mitigations

| Risk ID | Risk | Impact | Likelihood | Mitigation | Owner |
|---|---|---|---|---|---|
| R-02-01 | Private DNS misconfiguration breaks ACA to Foundry/Storage/KV connectivity | High | Medium | Add explicit DNS zone-link validation and nslookup-style evidence in TG2-12 | Stan |
| R-02-02 | Over-privileged RBAC assignments violate least privilege | High | Medium | Role matrix review gate in TG2-08 and negative permission tests in TG2-13 | Kyle |
| R-02-03 | OIDC federation mis-scoped audience/subject prevents workflow auth | High | Medium | Standardized federation template + dry-run auth validation before TG3 | Butters |
| R-02-04 | Policy effects block legitimate deployment operations unexpectedly | Medium | Medium | Stage policy rollout with audit-then-enforce path and exemption process | Kyle |
| R-02-05 | Parallel TG3 assumptions drift from TG2 final contracts | Medium | Medium | Publish versioned TG2 handoff contract artifact and freeze keys/IDs | Kyle |
| R-02-06 | Public access accidentally re-enabled by later changes | High | Low | Deny policies + CI policy compliance checks in TG3 gates | Stan |
| R-02-07 | Tagging not enforced on ephemeral resources, reducing cleanup traceability | Medium | Medium | Mandatory tag policy and validation in teardown prechecks | Butters |
| R-02-08 | Identity dependency on secrets reintroduced in workflow setup | High | Low | Explicit secretless OIDC checklist and block non-compliant workflow templates | Kyle |

## Handoff Contracts

### Handoff Contract to TG3 (CI/CD and Delivery Automation)

TG2 -> TG3 required handoff package:

- HC-03-01 Resource and identity map
  - Subscription, RG, Foundry account/project names, ACA env/job names, storage account, KV names
  - Required RunContext field mappings
- HC-03-02 OIDC setup contract
  - Federated credential subject/audience configuration
  - Required role assignments for workflow principal
- HC-03-03 Network access contract
  - Confirmation that data-plane endpoints are private-only
  - DNS zones and links required for ACA runtime
- HC-03-04 Governance contract
  - Policy assignments that TG3 workflows must honor
  - Required resource tags and naming constraints
- HC-03-05 Validation evidence package
  - DNS/RBAC/policy test results and known limitations

TG3 acceptance of handoff:

- TG3 workflows can authenticate via OIDC without static secrets.
- TG3 can trigger ARM control-plane operations and ACA job invocations without policy violations.
- TG3 can enforce orphan sweep and tagging constraints with no contract ambiguity.

### Handoff Contract to Downstream Implementation (TG4+)

TG2 baseline guarantees for downstream teams:

- Stable private-network foundation for evaluator data-plane access.
- Stable identity model for orchestrator and job execution.
- Policy and RBAC constraints documented as non-negotiable guardrails.

Downstream dependency obligations:

- All module implementations must consume RunContext identifiers as provisioned by TG2.
- No downstream workflow or code may bypass private endpoint path or add secret-based auth.
- Any required exception to policies/RBAC must be routed through decision log update in .copilot-tracking/squad/decisions.md.

## File-Level Target Map (TG2 Planned Changes Only)

Primary target files/folders to create or update during TG2 execution:

- infra/main.bicep
- infra/modules/networking.bicep
- infra/modules/foundry.bicep
- infra/modules/storage.bicep
- infra/modules/keyvault.bicep
- infra/modules/container-apps.bicep
- infra/modules/monitoring.bicep
- infra/modules/rbac.bicep
- docs/oidc-setup.md
- docs/setup-guide.md
- docs/troubleshooting.md
- .copilot-tracking/squad/decisions.md (TG2 decision checkpoints)
- .copilot-tracking/squad/history/kyle.md
- .copilot-tracking/squad/history/butters.md
- .copilot-tracking/squad/history/stan.md
- .copilot-tracking/squad/task-group-02-infra-identity-governance.md (this artifact)

Validation/tooling touchpoints expected by TG2 implementation execution:

- .github/workflows/ci.yml (policy and IaC validation gates consumed by TG3)
- scripts/bootstrap.ps1 (OIDC/bootstrap alignment)

## Execution Kickoff Checklist

- Confirm TG1 contract version lock and freeze referenced clauses.
- Start TG2-01 and TG2-02 to finalize control matrix and naming map.
- Launch Parallel Set A (network/private endpoint module implementation).
- Launch Parallel Set B (OIDC + RBAC implementation).
- Launch Parallel Set C (policy assignment bundle and rollout plan).
- Run Parallel Set D validations (DNS/private endpoint + RBAC/negative tests).
- Publish TG3 handoff package (HC-03-01..05) with evidence links.
- Record TG2 completion checkpoint in decisions.md.
