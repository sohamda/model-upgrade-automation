---
id: "0001"
title: "Adopt Architecture C — single-container weekly cron"
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
tags: ["architecture", "simplification", "orchestration"]
supersedes: null
superseded-by: null
related:
  - path: "requirements/plan.md"
    relation: influenced-by
    note: "Supersedes §1 Decision 1 (Architecture B) and the §3 high-level architecture."
  - path: "docs/adrs/0002-evaluate-on-firewalled-public-eval-foundry.md"
    relation: influences
    note: "Enabling networking decision."
asr_triggers:
  - kind: maintainability
    evidence: "~half of infra and a third of orchestration exist only to bridge public GHA runners to a private Foundry endpoint."
  - kind: cost
    evidence: "Persistent VNet + private endpoints baseline (~$15+/mo) exists to serve an eval path carrying no sensitive data."
---

# Adopt Architecture C — single-container weekly cron

## Context and Problem Statement

The original design (plan §1 Decision 1) chose **Architecture B — a GitHub
Actions orchestrator that uses only the Azure control plane (ARM), delegating
all data-plane work to a VNet-integrated Azure Container Apps (ACA) job**. The
sole justification is that the consumer's Foundry is behind a private endpoint
and public GitHub-hosted runners cannot reach it.

This split is the dominant source of complexity in the codebase: it forces a
VNet, private DNS zones, private endpoints, a VNet-integrated ACA environment,
an ARM-based job invoke/poll loop (`orchestrator/invoke_aca_job.py`,
`evaluator/aca_job.py`), and an orphan-sweeper workflow. Is that split
justified by the tool's actual mission?

## Decision Drivers

* The eval path carries **no sensitive data** — it evaluates ephemeral
  candidate deployments the tool creates itself, against golden QA datasets and
  synthetic red-team probes.
* Mission (plan §16) is retirement awareness + data-backed replacement
  recommendations, weekly, unattended, at single-digit-USD cost.
* Fork-to-first-report ≤ 60 minutes (plan §16 criterion 2) — the private
  networking apparatus is explicitly called "the biggest v0.1 hazard."
* Maintainability: fewer moving parts, fewer failure modes to reason about.

## Considered Options

* **Option A — Keep Architecture B** (GHA control plane + VNet-integrated ACA data plane).
* **Option C — Single-container weekly cron.** One GitHub Actions job runs one
  Python process (or one container) that performs detect → shortlist → provision
  → evaluate → report → teardown end-to-end, talking to a firewalled *eval*
  Foundry account (see ADR-0002). No VNet, no ACA, no private DNS.

## Decision Outcome

Chosen option: **Option C — single-container weekly cron**, because the entire
control-plane/data-plane split exists to bridge public runners to a *private*
endpoint that the eval path does not actually require. Removing the private-
network requirement (ADR-0002) collapses the split; once the eval can run
anywhere, running it in-process on the GitHub runner is by far the simplest
option that still satisfies every §16 success criterion.

### Consequences

* Good, deletes `networking.bicep`, all private DNS zones + private endpoints,
  the ACA environment/job, `orchestrator/invoke_aca_job.py`,
  `evaluator/aca_job.py`, and `sweep-orphans.yml`.
* Good, removes the ARM invoke/poll loop and its timeout/failure handling.
* Good, lowers persistent-infra baseline and shortens fork-to-first-report.
* Good, one correlation context (`run_id`) instead of two (GHA + ACA) sides.
* Bad, loses in-VNet execution for consumers with a hard "even synthetic eval
  must stay private" compliance mandate → mitigated by offering an **opt-in
  `private_networking` overlay** rather than making it the default.
* Bad, long red-team runs consume GitHub Actions minutes rather than ACA
  compute → acceptable at the stated scale (2–3 candidates, weekly); revisit if
  runtime exceeds the runner's job limit.

### Confirmation

A run executes end-to-end from a single job with no ACA/VNet resources
provisioned. `infra/` no longer contains `networking.bicep`,
`container-apps.bicep`, or private-endpoint/DNS modules. `grep` for
`invoke_aca_job` / `aca_job` returns no production references.

## Pros and Cons of the Options

### Option A — Keep Architecture B

* Good, keeps all inference inside the VNet — matches the strictest reading of a
  private-network posture.
* Good, offloads compute from the GitHub runner.
* Bad, ~half the infra and a third of the orchestration exist only for the
  runner→private-endpoint bridge.
* Bad, two-sided correlation, ARM polling, orphan sweeping, and private-DNS
  misconfiguration are recurring failure modes.
* Bad, contradicts the ≤60-minute fork-to-first-report goal.

### Option C — Single-container weekly cron

* Good, minimal moving parts; one code path; one correlation context.
* Good, cheapest and fastest to stand up.
* Neutral, compute runs on the GitHub runner (fine at stated scale).
* Bad, requires the eval Foundry to be reachable from the runner (addressed by
  ADR-0002) and an opt-in overlay for strict-compliance consumers.

## More Information

Depends on **ADR-0002** (firewalled public eval Foundry) as the enabling
networking decision. Re-visit if a consumer presents a compliance requirement
that synthetic eval traffic must never traverse a public (even firewalled)
endpoint — in that case ship the `private_networking` overlay, do not revert the
default.
