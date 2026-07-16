---
title: South Park Team Task Division Details
description: Execution details for the task-division-only ownership plan for model-upgrade-automation
ms.date: 2026-07-15
ms.topic: reference
---
<!-- markdownlint-disable-file -->

## Context Reference

Sources: requirements/plan.md; .copilot-tracking/research/2026-07-15/south-park-team-task-division-research.md

## Implementation Phase 1: Ownership Alignment and Interface Freeze

<!-- parallelizable: false -->

### Step 1.1: Confirm and lock the task division matrix as the implementation authority

Publish and approve the single ownership matrix as the canonical execution contract before implementation begins.

Files:

* .copilot-tracking/plans/2026-07-15/south-park-team-task-division-plan.instructions.md - authoritative table and ownership mapping

Discrepancy references:

* Addresses DR-01 and DR-02 in planning log

Success criteria:

* Every required coverage area is represented in one matrix
* Each task group has exactly one primary owner

Dependencies:

* requirements/plan.md scope is accepted as baseline

### Step 1.2: Finalize inter-group contracts for handoffs and dependency boundaries

Define practical handoff interfaces between task groups to prevent overlap ambiguity during implementation.

Files:

* .copilot-tracking/details/2026-07-15/south-park-team-task-division-details.md - handoff and dependency guidance

Success criteria:

* Dependency chain is explicit for all task groups
* Supporting owners are identified for each handoff boundary

Dependencies:

* Step 1.1 completion

## Implementation Phase 2: Execution and Quality Closure

<!-- parallelizable: true -->

### Step 2.1: Execute task groups under the defined ownership and dependency sequence

Execute each task group according to the matrix while preserving ownership accountability and dependency order.

Files:

* requirements/plan.md - implementation reference for detector/recommender/orchestrator/reporter/evaluator scope

Discrepancy references:

* Addresses DD-01 in planning log

Success criteria:

* Infra/security, CI/CD, core pipeline, evaluator, reporting, reliability, quality, and release-readiness streams are all actively owned
* Dependency prerequisites are completed before downstream execution starts

Dependencies:

* Implementation Phase 1 completion

### Step 2.2: Validate delivery through quality gates and release-readiness checks

Run role-aligned quality and release checks to ensure implementation is deployable and operable.

Validation commands:

* python -m pytest tests/unit - Python unit validation for core modules
* python -m pytest tests/integration - integration gate for pipeline and evaluation paths
* az bicep build --file infra/main.bicep - IaC syntax validation

Success criteria:

* Quality evidence exists for each role-owned stream
* Release readiness artifacts are complete and decision-ready

Dependencies:

* Step 2.1 completion

### Step 2.3: Validate phase changes

Run lint and build commands for files modified in this phase. Skip validation when it conflicts with parallel phases running the same validation scope.

Validation commands:

* python -m pytest tests/unit - Python test suite
* az bicep build --file infra/main.bicep - IaC validation

## Implementation Phase 3: Final Validation

<!-- parallelizable: false -->

### Step 3.1: Run full project validation

Execute all validation commands for the project:

* python -m pytest tests/unit
* python -m pytest tests/integration
* az bicep build --file infra/main.bicep

### Step 3.2: Fix minor validation issues

Iterate on lint errors, build warnings, and test failures. Apply fixes directly when corrections are straightforward and isolated.

### Step 3.3: Report blocking issues

When validation failures require changes beyond minor fixes:

* Document issues and affected files
* Provide next-step recommendations
* Route unresolved blockers into a new planning pass

## Dependencies

* Azure access and OIDC/RBAC setup permissions
* GitHub Actions execution permissions
* Python runtime and required packages

## Success Criteria

* The matrix can be executed directly as a delivery ownership model with no timeline assumptions
* All core coverage areas are owned, dependency-linked, and quality-gated
* Release-readiness ownership is explicit and complete