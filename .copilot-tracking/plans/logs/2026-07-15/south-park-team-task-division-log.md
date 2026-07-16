---
title: South Park Team Task Division Planning Log
description: Discrepancy tracking and path decisions for the task-division-only plan
ms.date: 2026-07-15
ms.topic: reference
---
<!-- markdownlint-disable-file -->

## Discrepancy Log

Gaps and differences identified between research findings and the implementation plan.

### Unaddressed Research Items

* DR-01: Detailed command-level CI gate definitions per repository language matrix are not expanded in this ownership-only plan
  * Source: .copilot-tracking/research/2026-07-15/south-park-team-task-division-research.md
  * Reason: Request scope is task division only; command matrix belongs to implementation execution
  * Impact: low
* DR-02: Environment-specific RBAC role ID mapping is not expanded by subscription
  * Source: .copilot-tracking/research/2026-07-15/south-park-team-task-division-research.md
  * Reason: Ownership plan intentionally stays environment-agnostic
  * Impact: low
* DR-03: provisioner and history/skip-index responsibilities were initially not named explicitly in the ownership table
  * Source: requirements/plan.md (decisions #12, #13); .copilot-tracking/research/2026-07-15/south-park-team-task-division-research.md (Core Python pipeline components)
  * Reason: Initial grouping used broader labels
  * Impact: resolved (Task Group 4 now names "provisioner deploy/teardown flow"; Task Group 6 now names "skip-index history (Table/Blob artifact bookkeeping)")
* DR-04: fixed teammate role titles were initially implicit only
  * Source: user request team definition; .copilot-tracking/research/2026-07-15/south-park-team-task-division-research.md (Team-to-Domain Fit)
  * Reason: Ownership table encoded roles by ownership, not explicit role listing
  * Impact: resolved (added Team Roles (Fixed) section in plan Context Summary)

### Plan Deviations from Research

* DD-01: Research listed separate detector/recommender/orchestrator/reporter components; plan groups detector/recommender/orchestrator under one core pipeline group and reporter under a dedicated reporting group
  * Research recommends: Keep clear component-level ownership boundaries
  * Plan implements: Consolidated ownership grouping with explicit deliverables and dependency links
  * Rationale: Improves execution clarity for six-person team while preserving all required coverage
* DD-02: Plan's Implementation Phase 3, Step 3.1 still lists `npm run lint` as a validation command (`south-park-team-task-division-plan.instructions.md`, line 94); requirements/plan.md confirms the stack is Python + Bicep + GitHub Actions only, with no Node/JS/TS component anywhere in scope
  * Research recommends: N/A — no research source specifies npm tooling
  * Plan implements: stack-appropriate validation command list in Phase 3 Step 3.1 (`python -m pytest tests/unit`, `python -m pytest tests/integration`, `az bicep build --file infra/main.bicep`)
  * Rationale: removed leftover template boilerplate and aligned plan with actual project stack
  * Impact: resolved

## Reference Integrity

* RI-01: Plan's Implementation Checklist cited Details line ranges that did not align with the actual heading positions in the details file
  * Source: .copilot-tracking/plans/2026-07-15/south-park-team-task-division-plan.instructions.md (Implementation Checklist); actual headings in .copilot-tracking/details/2026-07-15/south-park-team-task-division-details.md at lines 17 (Step 1.1), 38 (Step 1.2), 59 (Step 2.1), 80 (Step 2.2), 99 (Step 2.3), 108 (Phase 3)
  * Citation: verified current citations — Step 1.1 "Lines 17-37", Step 1.2 "Lines 38-54", Step 2.1 "Lines 59-79", Step 2.2 "Lines 80-98" — all now match the details heading boundaries exactly
  * Impact: resolved

## Implementation Paths Considered

### Selected: Single Matrix with Dependency-Linked Ownership

* Approach: One concise table defining task group, deliverables, owner, supporters, and dependencies
* Rationale: Matches user output contract exactly and provides implementation-ready accountability without timeline coupling
* Evidence: user request and research scope constraints

### IP-01: Component-Deep Multi-Table Decomposition

* Approach: Separate tables per component area (infra, pipeline, evaluation, quality, release)
* Trade-offs: More detail but violates the single-table output requirement and adds unnecessary verbosity
* Rejection rationale: Conflicts with explicit requirement for a single task division table

## Suggested Follow-On Work

* WI-01: Environment-specific role binding sheet — Create tenant/subscription-level RBAC assignment manifest and principal mapping (medium)
  * Source: DR-02
  * Dependency: Ownership plan adoption
* WI-02: Command-level quality gate matrix — Add concrete lint/test/build commands per module and workflow path (medium)
  * Source: DR-01
  * Dependency: Ownership plan adoption
* WI-03: Definition of done checklist per task group — Add acceptance criteria template for each owner stream (medium)
  * Source: Implementation readiness hardening
  * Dependency: Task Group 1 lock-in
* WI-04: Live TG3 execution evidence pack — Capture non-dry-run OIDC login, ACA invoke/poll, teardown success, and orphan sweeper recovery evidence once Azure access is available (high)
  * Source: TG3 local-only completion boundary
  * Dependency: TG2 contract inputs resolved in Azure and TG4/TG5 execution entrypoints available

## Implementation Deviations

* DD-03: TG2 infra warning cleanup was implemented directly in the local Bicep source rather than deferred to a later general validation pass
  * Plan specifies: generic execution and validation sequencing only
  * Implementation differs: resolved the current Bicep warning set during TG2 execution to improve downstream TG3 contract confidence
  * Rationale: the warnings were narrow, local, and removable without changing intent, and a clean compile is a stronger handoff artifact for TG3
* DD-04: TG3 contract validation was centralized in a repo-local Python script and invoked from multiple workflows instead of keeping contract logic embedded only in `ci.yml`
  * Plan specifies: CI quality gates and workflow-level validation must exist
  * Implementation differs: the checks now share one executable validator used locally, in CI, and in workflow preflight
  * Rationale: this reduces drift across workflows, strengthens local-only validation, and improves TG3 readiness without adding TG4 business logic