---
id: "0003"
title: "Facts-based candidate shortlisting; remove benchmark pre-ranking"
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
tags: ["architecture", "recommender", "simplification", "data-sources"]
supersedes: null
superseded-by: null
related:
  - path: "requirements/plan.md"
    relation: influenced-by
    note: "Supersedes §6 data cascade rows 6-13 and §8.2 recommender benchmark cascade."
asr_triggers:
  - kind: maintainability
    evidence: "Recommender and evaluator both score quality/safety; the recommender consumes borrowed benchmarks the plan itself declares non-authoritative."
  - kind: evolvability
    evidence: "A 627-line offline quality/safety subsystem + refresh script + dedicated workflow exists solely to feed a pre-filter."
---

# Facts-based candidate shortlisting; remove benchmark pre-ranking

## Context and Problem Statement

The recommender currently pre-ranks candidates using curated quality/safety
benchmark scores fed by an offline subsystem
(`evaluator/quality_safety_eval_client.py` ~627 lines,
`recommender/quality_safety_source.py`, `quality_safety_enrichment.py`,
`scripts/refresh_quality_safety_benchmarks.py`,
`.github/workflows/refresh-quality-safety-benchmarks.yml`, and
`config/quality_safety_benchmarks.yaml`). Yet the plan (§6.9 row 13) declares
the tool's **own eval run** the authoritative quality signal. So the recommender
scrapes/curates borrowed benchmark scores to shortlist candidates that are then
evaluated for real — two quality-scoring systems for one decision.

## Decision Drivers

* We only need the **top 2–3** candidates per retiring model.
* The authoritative quality/safety signal comes from the tool's own eval run.
* Deterministic, API-backed facts (availability, price, horizon, family) are
  sufficient to pick a defensible shortlist.
* Every deleted external source (HF Hub, HF leaderboard, curated benchmark file)
  removes a fragility and a maintenance chore.

## Considered Options

* **Option A — Keep benchmark pre-ranking** (offline curated quality/safety +
  optional HF enrichment) before provisioning.
* **Option B — Facts-based shortlisting.** Shortlist using only ARM Models API +
  Azure Retail Prices facts (same/newer family, region + deployment-type
  available, longer retirement horizon, cost delta). Let the real eval be the
  sole quality arbiter.

## Decision Outcome

Chosen option: **Option B — facts-based shortlisting**, because pre-ranking on
non-authoritative benchmark scores adds a whole subsystem to approximate a
signal the pipeline then measures directly. For a shortlist of 2–3, API-backed
facts are enough, and the eval decides quality.

### Consequences

* Good, deletes `quality_safety_eval_client.py`, `quality_safety_source.py`,
  `quality_safety_enrichment.py`, `hf_client.py` (if present),
  `refresh_quality_safety_benchmarks.py`,
  `refresh-quality-safety-benchmarks.yml`, and
  `config/quality_safety_benchmarks.yaml`.
* Good, recommender collapses to filters + a deterministic cost/longevity sort.
* Good, removes HF rate-limit handling and benchmark-staleness concerns.
* Neutral, the recommender's `weights` shrink to fact-based dimensions (e.g.,
  cost, longevity, context, availability); the eval owns quality/safety.
* Bad, loses a cheap pre-eval quality hint → acceptable because the shortlist is
  small and the eval is authoritative; if the candidate universe grows large,
  reintroduce a lightweight, API-only pre-filter (not a benchmark pipeline).

### Confirmation

The recommender module imports no benchmark/HF source. Shortlisting is a pure
function of ARM + pricing facts. The offline quality/safety files and workflow
are removed. Ranking remains deterministic (stable sort with documented tie-breaks).

## Pros and Cons of the Options

### Option A — Keep benchmark pre-ranking

* Good, gives a quality hint before spending eval compute.
* Bad, duplicates the authoritative eval; large offline subsystem to maintain.
* Bad, external sources (HF) are rate-limited and drift.

### Option B — Facts-based shortlisting

* Good, minimal, deterministic, fully API-backed.
* Good, eliminates a second quality-scoring system.
* Bad, no pre-eval quality signal → mitigated by small shortlist + authoritative eval.

## More Information

If future scale makes provisioning the shortlist expensive, add an API-only
pre-filter (e.g., context-window and price thresholds) rather than resurrecting a
benchmark-ingestion pipeline. Pairs with ADR-0004 (single code path) to further
shrink the recommender surface.
