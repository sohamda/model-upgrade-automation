---
applyTo: '.copilot-tracking/changes/2026-07-17/gpt-41-retirement-alternatives-live-foundry-changes.md'
---
<!-- markdownlint-disable-file -->
# Implementation Plan: GPT-4.1 Retirement Alternatives Live Foundry Flow

## Overview

Implement a production-ready retirement-alternatives workflow that supports explicit retiring-model input or live Foundry deployment discovery, fetches current Azure documentation/catalog evidence, recommends top 3 alternatives, safely provisions and evaluates candidates, and produces fail-closed decision reports.

## Objectives

### User Requirements

* Support either user-supplied retiring model input or Foundry deployment discovery. - Source: user request in current planning session.
* Fetch current Azure documentation/catalog information and recommend top 3 alternatives from current evidence. - Source: user request and requirements/plan.md.
* Provision the 3 candidates, run evaluations, and produce results. - Source: user request and requirements/plan.md.
* Include clear confirmation gates before any deployment mutations. - Source: user request and requirements/plan.md.

### Derived Objectives

* Preserve fixture-based deterministic mode for local development and CI while adding live adapters. - Derived from: existing architecture and test coverage in current repository.
* Add fail-closed evidence freshness, approval, and budget gates prior to provisioning. - Derived from: identified gaps and safety requirements in research.
* Introduce durable run manifest and operation ledger for reproducibility and cleanup recovery. - Derived from: current local-only artifact and history preview limitations.

## Context Summary

### Project Files

* requirements/plan.md - Product behavior, architecture expectations, and deployment/evaluation constraints.
* src/orchestrator/pipeline.py - Current dry-run orchestration path and control-flow seam.
* src/detector/service.py - Current watch-list matching and horizon filtering behavior.
* src/detector/retirement_source.py - Fixture-only retirement source.
* src/recommender/catalog.py - Fixture-only candidate catalog source.
* src/recommender/service.py - Current ranking and truncation behavior.
* src/provisioner/service.py - Current provisioning-plan-only behavior.
* src/evaluator/aca_job.py - Current deferred ACA dispatch behavior.
* src/evaluator/service.py - Current synthetic local evaluation behavior.
* src/reporter/service.py - Current local report and deferred publication payload behavior.
* .github/workflows/detect-and-eval.yml - Current placeholder workflow orchestration.
* .github/workflows/sweep-orphans.yml - Current orphan cleanup safety net and tag predicates.
* tests/unit/ - Existing fixture/local behavior assertions that must be evolved.

### References

* .copilot-tracking/research/2026-07-17/gpt-41-retirement-alternatives-research.md - Existing repository-level research summary.
* .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md - Detailed architecture and gap analysis with API/source recommendations.
* https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule - Retirement lifecycle source.
* https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure - Current Azure model catalog source.
* https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability - Regional availability source.
* https://learn.microsoft.com/en-us/python/api/azure-mgmt-cognitiveservices/azure.mgmt.cognitiveservices.operations.deploymentsoperations?view=azure-python - Foundry deployment API surface.
* https://learn.microsoft.com/en-us/azure/container-apps/jobs - ACA jobs execution model.

### Standards References

* vscode-userdata:/c%3A/Users/sohadasgupta/AppData/Roaming/Code/User/prompts/azurecosmosdb.instructions.md - Global agent instructions loaded in session.
* c:\Users\sohadasgupta\IdeaProjects\hve-squad\model-upgrade-automation\.github\instructions\hve-core-location.instructions.md - Repository location fallback guidance.

### Planning Defaults (v1 Policy)

* Candidate scope: Azure OpenAI models sold by Azure only.
* Compatibility policy for GPT-4.1 retirement: required capabilities are chat completions, responses API, function calling, structured outputs, and text input. Optional capabilities are image input and fine-tuning.
* Baseline policy: recommendation requires baseline comparison. If baseline unavailable, emit advisory-only report and block automatic winner.
* Candidate fallback policy: attempt provisioning of top 3 ranked candidates, with up to 2 replacement attempts for quota/access failures.
* Minimum evaluation policy: if fewer than 2 candidates finish evaluation successfully, output `incomplete_comparison` and do not recommend a winner.
* Residency policy: exact-region residency required by default; Global deployments blocked unless explicitly enabled with approval.
* Budget defaults: per-run USD 30, per-target USD 12, monthly USD 250.
* Provisioning authority: protected GitHub Environment approval required for any create/delete deployment action; scheduled provisioning disabled unless explicitly enabled.

## Implementation Checklist

### [ ] Implementation Phase 1: Domain Contracts, Config, and Orchestration Modes

<!-- parallelizable: false -->

* [ ] Step 1.1: Expand shared contracts for evidence-backed recommendation, provisioning, evaluation, and reporting states.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 12-31)
* [ ] Step 1.2: Extend config and CLI for explicit target input plus live discovery modes.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 32-55)
* [ ] Step 1.3: Implement run state machine with fail-closed transitions and no-mutation default.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 56-76)
* [ ] Step 1.4: Validate phase changes.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 77-84)

### [ ] Implementation Phase 2: Live Retirement and Catalog Source Adapters

<!-- parallelizable: true -->

* [ ] Step 2.1: Add retirement schedule adapter with cache and provenance.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 89-108)
* [ ] Step 2.2: Add Foundry catalog and region availability adapters with eligibility rules.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 109-128)
* [ ] Step 2.3: Add deployment inventory discovery and target resolver.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 129-150)
* [ ] Step 2.4: Validate phase changes.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 151-158)

### [ ] Implementation Phase 3: Candidate Recommendation and Top-3 Selection Policy

<!-- parallelizable: true -->

* [ ] Step 3.1: Implement deterministic documented-evidence scoring and top-3 output policy.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 163-184)
* [ ] Step 3.2: Implement stale-source fail-closed checks before provisioning eligibility.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 185-203)
* [ ] Step 3.3: Validate phase changes.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 204-211)

### [ ] Implementation Phase 4: Safe Provisioning, Teardown, and Operation Ledger

<!-- parallelizable: false -->

* [ ] Step 4.1: Implement SDK-based deployment create/get/delete lifecycle with pinned versions.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 216-238)
* [ ] Step 4.2: Implement approval and budget gates with durable operation ledger.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 239-266)
* [ ] Step 4.3: Tighten orphan sweeper selection predicates and tag contract.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 267-285)
* [ ] Step 4.4: Validate phase changes.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 286-293)

### [ ] Implementation Phase 5: ACA Evaluation Execution and Durable Results

<!-- parallelizable: false -->

* [ ] Step 5.1: Implement ACA job dispatch/polling and completion-manifest checks.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 298-320)
* [ ] Step 5.2: Replace synthetic evaluators with Azure-capable runners in ACA image.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 321-345)
* [ ] Step 5.3: Validate phase changes.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 346-353)

### [ ] Implementation Phase 6: Reporting, Publication, and Workflow Wiring

<!-- parallelizable: false -->

* [ ] Step 6.1: Implement durable aggregation, decision engine, and publication adapters.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 358-380)
* [ ] Step 6.2: Replace workflow placeholders with protected live orchestration jobs.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 381-405)
* [ ] Step 6.3: Validate phase changes.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 406-413)

### [ ] Implementation Phase 7: Validation

<!-- parallelizable: false -->

* [ ] Step 7.1: Run full project validation
  * Execute all lint commands and full test suites, including integration/e2e where environment is available.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 418-426)
* [ ] Step 7.2: Fix minor validation issues
  * Iterate on straightforward test/lint failures in modified scopes.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 427-430)
* [ ] Step 7.3: Report blocking issues
  * Document unresolved release gates and required product decisions.
  * Details: .copilot-tracking/details/2026-07-17/gpt-41-retirement-alternatives-live-foundry-details.md (Lines 431-435)

## Planning Log

See .copilot-tracking/plans/logs/2026-07-17/gpt-41-retirement-alternatives-live-foundry-log.md for discrepancy tracking, implementation paths considered, and suggested follow-on work.

## Dependencies

* Azure SDK libraries for identity, Cognitive Services deployments, Container Apps jobs, Blob/Table storage, and evaluation.
* GitHub OIDC environment configuration and protected-approval environments for provisioning and remediation publication.
* Scratch Azure environment for safe integration tests.

## Success Criteria

* Tool accepts either direct retiring model input or discovered deployment targets from Foundry resources.
* Tool uses current Azure documentation/catalog evidence and outputs top 3 alternatives with audit-ready rationale.
* Provisioning path includes explicit user confirmation and budget gates before any deployment create operation.
* Tool provisions candidate deployments, runs evaluations, and publishes durable fail-closed results.
* Cleanup is always attempted with strict selection safety and observable cleanup status in the final report.
* Default policies in Planning Defaults are implemented and enforced in config, eligibility, and workflow gates.