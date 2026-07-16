---
title: South Park Team Task Division Research
description: Source-backed research summary for a no-timeline ownership plan for model-upgrade-automation
ms.date: 2026-07-15
ms.topic: overview
---
<!-- markdownlint-disable-file -->

## Scope

Create a task-division-only plan for the exact six-person team:

* Cartman: MVP Product/Tech Integrator
* Kyle: Security/Identity + Governance Lead
* Stan: Platform Reliability + SRE Lead
* Butters: DevOps + IaC Engineer
* Kenny: Python Delivery Lead (Core pipeline)
* Wendy: Evaluation + Quality Engineer

## Primary Source

* requirements/plan.md

## Confirmed Project Coverage Required for Planning

* Infra and security foundation:
  * Persistent private networking, private endpoints, RBAC/OIDC, Key Vault, storage, monitoring
* CI/CD and orchestration:
  * Weekly orchestration workflow, orphan sweeper, PR gates, control-plane orchestration and ACA job triggering
* Core Python pipeline components:
  * detector, recommender, orchestrator, provisioner, history, reporter
* Evaluator implementation:
  * custom evaluator + red team execution path in ACA job, telemetry and result artifact handling
* Quality gates:
  * unit/integration testing, policy and config validation, release checks
* Operationalization:
  * runbooks, troubleshooting, release readiness, handoff artifacts

## Constraints For This Planning Request

* No timeline, no week-by-week or sprint breakdown
* Output requires a single task division table with these columns exactly:
  * Task Group
  * Key Deliverables
  * Primary Owner
  * Supporting Owner(s)
  * Depends On
* Must remain concise but implementation-ready

## Team-to-Domain Fit

* Cartman owns cross-cutting integration, scope decisions, and release/no-release coordination
* Kyle owns identity, least privilege, governance controls, and security acceptance gates
* Stan owns reliability targets, SRE controls, observability, and operational safety
* Butters owns IaC, CI/CD plumbing, environment automation, and delivery mechanics
* Kenny owns Python service/module implementation across the core execution pipeline
* Wendy owns model-eval quality, validation suites, and release-quality evidence