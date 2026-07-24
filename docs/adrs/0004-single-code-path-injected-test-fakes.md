---
id: "0004"
title: "Single production code path with injected test fakes"
status: "accepted"
date: "2026-07-24"
deciders:
  - "Repository maintainer"
decision-makers:
  - "Repository maintainer"
consulted:
  - "Design review (2026-07-24)"
informed:
  - "Contributors"
tags: ["architecture", "testability", "simplification", "orchestration"]
supersedes: null
superseded-by: null
related:
  - path: "requirements/plan.md"
    relation: influenced-by
    note: "Supersedes the §14 local-first dry-run pattern and the multi-toggle runtime model."
asr_triggers:
  - kind: maintainability
    evidence: "Every component ships Local/Live variants wrapped in fallback dataclasses gated by 6 runtime toggles; a test seam became the dominant production motif."
  - kind: availability
    evidence: "Source fallback chains (ARM -> Learn -> fixture) can silently serve stale fixtures in production, masking a real failure as resilience."
---

# Single production code path with injected test fakes

## Context and Problem Statement

The "local-first dry-run" testability strategy has leaked into the production
architecture. Components ship paired `Local*`/`Live*` implementations
(`LocalCustomRunner`/`LiveCustomRunner`, `LocalRedTeamRunner`/`LiveRedTeamRunner`),
sources are wrapped in `_FallbackRetirementSource`/`_FallbackCatalogSource`
dataclasses, behavior is gated by a `use_official_sources` flag, and the pipeline
reasons about **six runtime toggles** (`live_catalog`, `discover_from_azure`,
`use_official_sources`, `provision_candidates`, `run_evals`, `top_k`). The
`ARM → Learn → fixture` fallback chains mean a parser regression can silently
degrade to stale fixtures in production and be reported as success.

## Decision Drivers

* Tests must stay fast and hermetic — a real need.
* Production should have **one** predictable path per source, and fail loudly
  when a live dependency is unavailable.
* Toggle combinatorics are a reasoning and testing burden.

## Considered Options

* **Option A — Keep Local/Live variants + fallback chains + toggles.**
* **Option B — Single production path + dependency-injected fakes in tests.**
  Each source/runner has one production implementation. Tests inject fakes at the
  seam. Replace the six toggles with a single `--mode {plan, run}` flag
  (`plan` = read-only detect+recommend+report; `run` = also provision+eval).
  Live-source unavailability raises loudly instead of cascading to fixtures.

## Decision Outcome

Chosen option: **Option B — single path + injected test fakes**, because
dependency injection at test time delivers the same hermetic safety without
three layers of production indirection, and failing loud on missing live sources
turns a hidden reliability risk into an observable error.

### Consequences

* Good, removes `Local*`/`Live*` duplication and the `_Fallback*` wrappers.
* Good, one `--mode` flag replaces six interacting booleans.
* Good, production failures surface instead of silently degrading to fixtures.
* Good, smaller pipeline (`orchestrator/pipeline.py`) with fewer branches.
* Bad, tests must wire fakes explicitly via DI → standard, well-understood cost.
* Bad, loses "always produces some output" behavior → intended; a real outage
  should fail the run, not emit a stale-fixture report.

### Confirmation

`grep` for `Local*Runner` / `Live*Runner` / `_Fallback` returns only test
scaffolding or nothing. The CLI exposes `--mode` instead of the six toggles.
Unit tests pass by injecting fakes; a simulated live-source outage raises a
typed error rather than returning fixture data.

## Pros and Cons of the Options

### Option A — Keep variants + fallbacks + toggles

* Good, runs "offline" with zero configuration.
* Bad, test concerns dominate production structure.
* Bad, silent fixture fallback hides outages; toggle matrix is hard to test.

### Option B — Single path + injected fakes

* Good, clean production code; explicit, observable failures.
* Good, one mental model; smaller surface.
* Bad, requires DI wiring in tests (routine).

## More Information

Pairs with ADR-0001 (single container) and ADR-0003 (smaller recommender). The
`plan`/`run` split preserves the valuable safety property (default is read-only)
without the six-toggle combinatorics.
