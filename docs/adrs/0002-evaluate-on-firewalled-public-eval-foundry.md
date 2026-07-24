---
id: "0002"
title: "Evaluate on a firewalled public eval Foundry account"
status: "accepted"
date: "2026-07-24"
deciders:
  - "Repository maintainer"
decision-makers:
  - "Repository maintainer"
consulted:
  - "Design review (2026-07-24)"
informed:
  - "Downstream template consumers"
tags: ["architecture", "networking", "security", "simplification"]
supersedes: null
superseded-by: null
related:
  - path: "requirements/plan.md"
    relation: influenced-by
    note: "Supersedes §1 Decision 14 (Nothing public) and §4 persistent private-network infra."
  - path: "docs/adrs/0001-adopt-architecture-c-single-container-cron.md"
    relation: influenced-by
    note: "This is the enabling networking decision for Architecture C."
asr_triggers:
  - kind: security
    evidence: "Private-endpoint requirement was inherited from the consumer's production posture, not from any data-sensitivity on the eval path."
  - kind: cost
    evidence: "VNet + 4 private DNS zones + 4+ private endpoints exist to protect non-sensitive synthetic eval traffic."
---

# Evaluate on a firewalled public eval Foundry account

## Context and Problem Statement

Plan §1 Decision 14 ("Nothing public") mandates that Foundry, Storage, and Key
Vault all sit behind private endpoints, and that the eval runner be
VNet-integrated. This requirement is the root cause of the ACA/VNet/DNS
apparatus (see ADR-0001). But the "nothing public" posture was inherited from
the consumer's **production** environment. The tool does not evaluate on the
consumer's production Foundry — it **creates its own ephemeral candidate
deployments** and probes them with **golden QA datasets and synthetic red-team
prompts**. What sensitive data is actually on this path? None.

## Decision Drivers

* No production traffic and no customer data ever touch the eval path.
* The strict private-network model imposes high setup and maintenance cost and
  is the top stated deployment hazard.
* Security must remain real: candidate endpoints still need auth and network
  scoping, just proportionate to the (low) sensitivity of the data.

## Considered Options

* **Option A — Private endpoints + VNet** (plan default).
* **Option B — Firewalled public eval Foundry.** A dedicated eval Foundry
  account with a **public endpoint restricted by IP allowlist / service firewall**
  and **Entra ID auth (managed identity, no keys)**. The eval runs directly from
  the GitHub runner against this account. The consumer's production Foundry is
  never touched.
* **Option C — Reuse the consumer's private production Foundry** for eval
  (rejected on both security and complexity grounds).

## Decision Outcome

Chosen option: **Option B — firewalled public eval Foundry**, because it removes
the entire VNet/private-endpoint/DNS/ACA burden while keeping proportionate
controls (network allowlist + keyless Entra auth + a scope lock to the owned
eval project) for a path that carries no sensitive data. The strict private
model becomes an **opt-in overlay** for consumers with a hard compliance mandate.

### Consequences

* Good, unblocks ADR-0001; deletes the private-networking infra.
* Good, keeps zero long-lived secrets (OIDC + managed identity retained).
* Good, an isolated eval account contains blast radius — it is not the prod resource.
* Bad, introduces a public (though firewalled) inference endpoint → mitigated by
  IP allowlist, Entra-only auth, and the existing own-deployment scope lock in
  `assert_owned_target`.
* Bad, consumers under strict mandates must enable the `private_networking`
  overlay → documented as a supported, non-default path.

### Confirmation

The eval Foundry account is provisioned with `publicNetworkAccess: Enabled` plus
an IP allowlist and no API keys. A run authenticates via managed identity/OIDC
only. NSG/private-endpoint resources are absent unless the overlay is enabled.
The scope lock (`assert_owned_target`) still refuses any target outside the
owned eval project.

## Pros and Cons of the Options

### Option A — Private endpoints + VNet

* Good, maximal network isolation.
* Bad, disproportionate to the eval path's (nil) data sensitivity.
* Bad, drives the majority of infra and orchestration complexity.

### Option B — Firewalled public eval Foundry

* Good, proportionate controls; drastically simpler.
* Good, isolated blast radius; keyless auth preserved.
* Neutral, still a public endpoint but firewalled and Entra-gated.
* Bad, needs an opt-in overlay for strict-compliance forks.

### Option C — Reuse consumer's private prod Foundry

* Bad, couples eval to production; worst security posture.
* Bad, reintroduces the private-network bridge.

## More Information

Enables **ADR-0001**. The `private_networking` overlay should be a self-
contained Bicep module set (VNet + private endpoints + DNS + ACA) that a fork
opts into via one config flag, so the default path stays simple.
