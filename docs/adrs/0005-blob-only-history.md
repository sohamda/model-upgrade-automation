---
id: "0005"
title: "Blob-only history; drop Table Storage skip-index"
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
tags: ["architecture", "storage", "simplification"]
supersedes: null
superseded-by: null
related:
  - path: "requirements/plan.md"
    relation: influenced-by
    note: "Supersedes §1 Decision 12 (hybrid Blob + Table + App Insights) and §9 data model."
asr_triggers:
  - kind: cost
    evidence: "A Table Storage skip-index behind a private endpoint stores sub-kilobyte data at a cardinality of dozens of rows per year."
  - kind: scalability
    evidence: "Point-read skip-index scaling was designed for a workload that produces tens of records annually."
---

# Blob-only history; drop Table Storage skip-index

## Context and Problem Statement

Plan §1 Decision 12 specifies a **hybrid** history store: Blob for raw
artifacts, Table Storage for the skip-index (composite key
`model_id/version/dataset_sha256`), and App Insights for score telemetry. At the
tool's actual cardinality — 2–3 candidates per model, weekly, i.e. tens of rows
per year — a dedicated Table Storage index (with its own private endpoint under
the old model) is infrastructure weight for sub-kilobyte data. The current
`history/skip_index.py` is already only 16 lines.

## Decision Drivers

* Skip-index cardinality is tiny and grows slowly.
* Fewer storage services = fewer endpoints, roles, and failure modes.
* Telemetry should be justified by an actual consumer (a dashboard), not shipped
  speculatively.

## Considered Options

* **Option A — Hybrid Blob + Table + App Insights** (plan default).
* **Option B — Blob-only history.** Raw artifacts in Blob as today; the
  skip-index becomes a single `index.json` object in the same container
  (read-modify-write per run). App Insights becomes **optional**, enabled only
  when a consumer wires a dashboard.

## Decision Outcome

Chosen option: **Option B — Blob-only history**, because a JSON index in the
existing container serves the skip-lookup need at this scale with one storage
service, one role assignment, and (post ADR-0002) no private endpoint. The
markdown report is the primary human-facing telemetry; App Insights is opt-in.

### Consequences

* Good, removes the Table Storage resource, its role assignment, and (with
  ADR-0002) its private endpoint.
* Good, one storage surface for artifacts + index; simpler `history/` module.
* Good, App Insights cost/ingestion is incurred only when actually used.
* Neutral, `index.json` read-modify-write is safe under the single-writer weekly
  cron (no concurrent runs; concurrency group already enforced).
* Bad, loses O(1) point-read semantics → irrelevant at tens-of-rows scale;
  revisit only if annual volume reaches thousands of records.
* Bad, loses always-on score telemetry → intended; re-enable via the opt-in path
  when a dashboard exists.

### Confirmation

`infra/` contains no Table Storage resource or table private endpoint. The
skip-index is a Blob object; a run reads it, decides skips, and writes it back.
App Insights is gated behind a config flag and absent by default.

## Pros and Cons of the Options

### Option A — Hybrid Blob + Table + App Insights

* Good, scales to very high cardinality with fast point reads.
* Bad, three storage services for a tens-of-rows-per-year workload.
* Bad, extra endpoints, roles, and telemetry cost shipped ahead of need.

### Option B — Blob-only history

* Good, one storage service; minimal roles/endpoints; opt-in telemetry.
* Neutral, JSON index is trivial to inspect and diff.
* Bad, not built for thousands of rows → not the current workload.

## More Information

If a consumer later needs high-cardinality history or cross-run analytics,
promote the index to Table Storage or a small database at that point. Pairs with
ADR-0002 (no private endpoints) and ADR-0006 (scope trim).
