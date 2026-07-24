# Architecture Decision Records

This directory records architecture decisions for the Model Upgrade Automation tool.
The ADRs below capture a deliberate **simplification pass** over the original
`requirements/plan.md`, driven by a design review on 2026-07-24 that found the
planned design substantially over-scoped for the tool's actual mission
(weekly, unattended, data-backed awareness of retiring Azure Foundry models).

Format: [MADR v4.0.0](https://adr.github.io/madr/) with hve-core frontmatter extensions.

## Index

| ADR | Title | Status | Supersedes (plan decision) |
|---|---|---|---|
| [0001](0001-adopt-architecture-c-single-container-cron.md) | Adopt Architecture C — single-container weekly cron | accepted | §1 Decision 1 (Architecture B) |
| [0002](0002-evaluate-on-firewalled-public-eval-foundry.md) | Evaluate on a firewalled public eval Foundry account | accepted | §1 Decision 14 (nothing public / private endpoints) |
| [0003](0003-facts-based-candidate-shortlisting.md) | Facts-based candidate shortlisting; remove benchmark pre-ranking | accepted | §1 Decision 7 (recommender), §6 data cascade |
| [0004](0004-single-code-path-injected-test-fakes.md) | Single production code path with injected test fakes | accepted | §14 local-first dry-run pattern |
| [0005](0005-blob-only-history.md) | Blob-only history; drop Table Storage skip-index | accepted | §1 Decision 12 (hybrid history) |
| [0006](0006-trim-mvp-scope-and-remove-platform-scaffolding.md) | Trim MVP outputs; remove TG7–TG9 platform scaffolding | accepted | §1 Decision 15 (report delivery), §5 scope |

## Reading order

Start with **0001** (the umbrella architecture change). ADRs 0002–0005 are the
enabling decisions that make Architecture C viable. **0006** removes accreted
scope that is not part of the core mission.

## Relationship to `requirements/plan.md`

`requirements/plan.md` remains the historical record of the original intent.
Where an ADR here conflicts with the plan, **the ADR wins**. A future revision
of the plan should fold these decisions in; until then, treat this directory as
the current source of truth for architecture.
