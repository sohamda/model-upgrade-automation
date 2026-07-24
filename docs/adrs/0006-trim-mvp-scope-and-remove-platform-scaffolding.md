---
id: "0006"
title: "Trim MVP outputs; remove TG7–TG9 platform scaffolding"
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
tags: ["architecture", "scope", "simplification", "reporting"]
supersedes: null
superseded-by: null
related:
  - path: "requirements/plan.md"
    relation: influenced-by
    note: "Supersedes §1 Decision 15 (four output channels) and trims scope beyond §5."
asr_triggers:
  - kind: maintainability
    evidence: "TG7-TG9 reliability workbooks, release-readiness gates, and governance policy were added around a weekly single-digit-dollar cron and are absent from the plan."
---

# Trim MVP outputs; remove TG7–TG9 platform scaffolding

## Context and Problem Statement

Two forms of scope have accreted beyond the tool's mission:

1. **Output channels.** Plan §1 Decision 15 defines four delivery paths — GitHub
   Issue, report PR, Teams webhook, and an auto-remediation Bicep-patch PR.
2. **Platform scaffolding not in the plan.** The repo has grown TG7–TG9
   apparatus: reliability workbooks and alert definitions
   (`config/tg7-reliability-*.yaml`), release-readiness gates and driver scripts
   (`scripts/run_tg8_*`, `scripts/run_tg9_*`, `scripts/check_tg7_*`,
   `scripts/validate_tg7_*`), associated `docs/tg*` runbooks, and Azure Policy
   modules (`infra/modules/governance*.bicep`). None of this is in
   `requirements/plan.md`.

For a weekly, single-digit-USD internal eval job, this is enterprise-platform
tooling wrapped around a cron script.

## Decision Drivers

* MVP needs exactly one durable, reviewable output.
* Speculative channels and platform gates increase surface without validated need.
* Keeping the core repo focused improves the template's forkability (§16).

## Considered Options

* **Option A — Keep all four output channels and the TG7–TG9 platform layer.**
* **Option B — One MVP output + defer/extract the rest.** Ship a single **report
  PR** (markdown report as the PR body/file) as the MVP output. Defer Teams and
  the auto-remediation Bicep PR to a post-MVP milestone (retain the existing
  `remediation_payload`/`teams_notifier` code as opt-in, off by default). Remove
  the TG7–TG9 reliability/release-gate/governance scaffolding from the core repo,
  or extract it into a separate ops repo if still wanted.

## Decision Outcome

Chosen option: **Option B — one MVP output + defer/extract the rest**, because a
single report PR satisfies the "reports drive real decisions" success criterion,
and the platform scaffolding is not part of the mission and is not in the plan.

### Consequences

* Good, MVP surface is one output channel; less to build, test, and document.
* Good, removes TG7–TG9 config, scripts, runbooks, and governance Bicep from the
  core repo (or relocates them to an ops repo).
* Good, Teams + auto-remediation remain available as opt-in, keeping the code
  already written without making it default scope.
* Neutral, a rolling weekly GitHub Issue can be reintroduced later if a summary
  view is wanted; the report PR is sufficient for MVP.
* Bad, loses the pre-built reliability/release gates from the default repo →
  intended; reintroduce only if the tool graduates to a platform.

### Confirmation

The default workflow produces a report PR and no other channel unless opt-in
flags are set. `config/tg7-*`, `scripts/*tg7*|*tg8*|*tg9*`, `docs/tg*`, and
`infra/modules/governance*` are removed from the core repo (or moved to an
`ops/` repo). CI still lints and tests the core pipeline.

## Pros and Cons of the Options

### Option A — Keep everything

* Good, feature-rich out of the box.
* Bad, four output channels and a platform layer for a weekly cron; large
  maintenance surface; diverges from the plan.

### Option B — One output + defer/extract

* Good, focused MVP; faster forking; matches the mission.
* Good, retains opt-in code for Teams/remediation without default cost.
* Bad, fewer built-in ops features by default → deliberate.

## More Information

Revisit once the tool has real adoption and a validated need for richer delivery
or platform-grade reliability gates. Pairs with ADR-0001 and ADR-0005 to keep the
default footprint minimal.
