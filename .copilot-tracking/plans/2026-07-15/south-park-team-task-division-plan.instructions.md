---
applyTo: '.copilot-tracking/changes/2026-07-15/south-park-team-task-division-changes.md'
description: Task-division-only ownership plan for model-upgrade-automation using the six-person South Park team
title: South Park Team Task Division Plan
ms.date: 2026-07-15
ms.topic: how-to
---
<!-- markdownlint-disable-file -->

## Overview

Implementation-ready task division for model-upgrade-automation using the exact six-person team, without any timeline or sprint schedule.

## Objectives

### User Requirements

* Provide exactly one task division table with required columns and team mapping — Source: user request
* Keep the plan concise and implementation-ready — Source: user request
* Exclude any week-by-week or sprint breakdown — Source: user request
* Cover infra/security, CI/CD, detector/recommender/orchestrator/reporter, evaluator, quality gates, runbooks, and release readiness — Source: user request

### Derived Objectives

* Define explicit ownership and dependency flow so implementation can start immediately without extra planning rounds — Derived from delivery readiness goal
* Keep one primary owner per task group while preserving cross-functional support visibility — Derived from team-accountability clarity

## Context Summary

### Team Roles (Fixed)

* Cartman: MVP Product/Tech Integrator
* Kyle: Security/Identity + Governance Lead
* Stan: Platform Reliability + SRE Lead
* Butters: DevOps + IaC Engineer
* Kenny: Python Delivery Lead (Core pipeline)
* Wendy: Evaluation + Quality Engineer

### Project Files

* requirements/plan.md - canonical project scope, architecture, component boundaries, and operational expectations

### References

* .copilot-tracking/research/2026-07-15/south-park-team-task-division-research.md - planning evidence and constraints capture

### Standards References

* .github/instructions/copilot-tracking.instructions.md - tracking artifact placement and naming
* .github/instructions/markdown.instructions.md - markdown authoring constraints

## Task Division Table

| Task Group | Key Deliverables | Primary Owner | Supporting Owner(s) | Depends On |
|---|---|---|---|---|
| 1. Architecture and MVP Integration | Finalized module boundaries, interface contracts, decision log, integrated execution blueprint across detector/recommender/orchestrator/evaluator/reporter | Cartman | Kenny, Butters, Wendy | requirements/plan.md baseline |
| 2. Infrastructure, Identity, and Governance Baseline | Private-network Bicep stack, OIDC federation wiring, RBAC role assignments, policy guardrails, Key Vault and storage security posture | Kyle | Butters, Stan | Task Group 1 |
| 3. CI/CD and Delivery Automation | GitHub workflows (detect-and-eval, ci, sweep-orphans), build/test pipeline, environment promotion controls, secure secretless deployment path | Butters | Kyle, Stan, Kenny | Task Group 2 |
| 4. Core Pipeline Implementation (Detector, Recommender, Orchestrator, Provisioner) | Production-ready Python modules for detector, recommender scoring/filtering, orchestration runner, provisioner deploy/teardown flow, ACA invocation and lifecycle handling | Kenny | Cartman, Butters | Task Group 1, Task Group 3 |
| 5. Evaluation Engine and Experiment Execution | Custom evaluator and red-team execution path in ACA job, dataset ingestion/hash handling, score capture contracts, evaluation result manifests | Wendy | Kenny, Stan | Task Group 3, Task Group 4 |
| 6. Reporting, History, and Decision Outputs | Aggregated comparison matrix, markdown report generator, GitHub issue/PR publishing integration, skip-index history (Table/Blob artifact bookkeeping), remediation PR draft logic (flag-gated) | Kenny | Wendy, Cartman | Task Group 4, Task Group 5 |
| 7. Reliability, SRE Controls, and Operability | SLO/SLI set, run-time alerts/dashboards, failure-mode handling playbooks, orphan sweep safeguards, incident response hooks | Stan | Butters, Kyle, Wendy | Task Group 3, Task Group 5 |
| 8. Quality Gates and Validation Framework | Unit/integration test suites, config/schema validation, security and reliability gate checks, end-to-end acceptance criteria and evidence pack | Wendy | Stan, Kyle, Kenny | Task Group 4, Task Group 5, Task Group 7 |
| 9. Runbooks and Release Readiness | Setup/runbook package, operations handoff docs, release checklist, go/no-go criteria, rollback and post-release verification checklist | Cartman | Stan, Wendy, Kyle, Butters | Task Group 6, Task Group 7, Task Group 8 |

## Implementation Checklist

### [ ] Implementation Phase 1: Ownership Alignment and Interface Freeze

<!-- parallelizable: false -->

* [ ] Step 1.1: Confirm and lock the task division matrix as the implementation authority
  * Details: .copilot-tracking/details/2026-07-15/south-park-team-task-division-details.md (Lines 17-37)
* [ ] Step 1.2: Finalize inter-group contracts for handoffs and dependency boundaries
  * Details: .copilot-tracking/details/2026-07-15/south-park-team-task-division-details.md (Lines 38-54)

### [ ] Implementation Phase 2: Execution and Quality Closure

<!-- parallelizable: true -->

* [ ] Step 2.1: Execute task groups under the defined ownership and dependency sequence
  * Details: .copilot-tracking/details/2026-07-15/south-park-team-task-division-details.md (Lines 59-79)
* [ ] Step 2.2: Validate delivery through quality gates and release-readiness checks
  * Details: .copilot-tracking/details/2026-07-15/south-park-team-task-division-details.md (Lines 80-98)
* [ ] Step 2.3: Validate phase changes
  * Run lint and build commands for modified files
  * Skip if validation conflicts with parallel phases

### [ ] Implementation Phase 3: Final Validation

<!-- parallelizable: false -->

* [ ] Step 3.1: Run full project validation
  * Execute stack-appropriate validation commands (`python -m pytest tests/unit`, `python -m pytest tests/integration`, `az bicep build --file infra/main.bicep`)
  * Execute build scripts for all modified components
  * Run test suites covering modified code
* [ ] Step 3.2: Fix minor validation issues
  * Iterate on lint errors and build warnings
  * Apply fixes directly when corrections are straightforward
* [ ] Step 3.3: Report blocking issues
  * Document issues requiring additional research
  * Provide user with next steps and recommended planning
  * Avoid large-scale fixes within this phase

## Planning Log

See .copilot-tracking/plans/logs/2026-07-15/south-park-team-task-division-log.md for discrepancy tracking, implementation paths considered, and suggested follow-on work.

## Dependencies

* Azure subscription access and existing baseline privileges for OIDC + RBAC setup
* GitHub Actions permissions for workflow execution and PR/Issue reporting
* Python toolchain and package dependencies for evaluation and orchestration components

## Success Criteria

* Single ownership table is complete, dependency-aware, and covers all required core workstreams — Traces to: user-required coverage list
* Each task group has one primary owner with explicit supporting owners and dependency chain — Traces to: team task division requirement
* Plan remains timeline-free and can be executed directly as a role-based implementation guide — Traces to: no timeline constraint