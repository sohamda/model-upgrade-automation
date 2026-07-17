---
title: Demo Results Snapshot
description: Committed sample of workflow run outcomes and gate decisions for quick inspection.
sidebar_position: 90
keywords: [demo, results, gates, release readiness, workflow summary]
tags: [demo, quality-gates, release-readiness]
---

# Demo Results Snapshot

This page is a committed, human-readable sample of what you should expect to see from workflow runs.

For live runs, use the Actions run **Summary** tab and downloaded artifacts.

## Example Run Signals

Source run IDs used for this snapshot:

1. Detect and Evaluate: `29577754373`
2. Sweep Orphans (dry-run): `29577762865`

## TG8 Quality Gates (Example)

Example overall gate result:

1. `overall_status`: `PASS`
2. Mandatory gates:
   1. `QG-UNIT-01`: `PASS`
   2. `QG-INT-01`: `PASS`
   3. `QG-CONFIG-01`: `PASS`
   4. `QG-SEC-01`: `PASS`
   5. `QG-REL-01`: `PASS`
   6. `QG-E2E-01`: `PASS`

Interpretation:

1. All mandatory quality gates succeeded.
2. The release-readiness stage can proceed.

## TG9 Release Readiness (Example)

Example decision result:

1. `decision.status`: `GO`
2. `decision.release_posture`: `CONDITIONAL_GO`
3. `blockers.open_count`: `0`

Interpretation:

1. Release is approved with documented residual conditions.
2. No open blocking items remain.

## How To Read Live Results

1. Open the workflow run page in GitHub Actions.
2. Read the run **Summary** section for compact report output.
3. Download artifacts for raw JSON evidence.
4. Confirm gate status and release decision fields above.

## Notes

This file is intentionally committed under `docs/` so repository readers can view an example even though runtime `artifacts/` paths are gitignored.
