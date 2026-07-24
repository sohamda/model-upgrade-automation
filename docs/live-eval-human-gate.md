---
title: Live Evaluation Human Gate
description: Human review runbook for live-backed quality/safety evaluation output, rubric versioning, and the audit-bundle decision fields
ms.date: 2026-07-23
ms.topic: reference
---

## Scope

This runbook applies only to live-backed evaluator runs (`--live` or `MUA_EVAL_MODE=live`). The default (fake) evaluation path never produces the fields described here beyond their `None`/placeholder defaults, and never requires human review before a decision is recorded elsewhere.

## Why a human gate exists

Live-backed measurement is always advisory. `src.evaluator.service.execute_local_evaluation` marks every live-run summary `promotion_grade: false` and `advisory: true` (RAI HIGH-risk caveat). `src.reporter.decision_engine.decide_recommendation` reads both fields and, whenever either is set, records the candidate's verdict as `needs_human_review` instead of `promote` or `reject` -- regardless of how the underlying scoring dimensions came out. There is no code path in this repository that converts a live-backed result into an automatic promotion.

## What a reviewer sees

Each candidate's `summary.json` (written by `src.evaluator.result_writer.write_candidate_results`) carries two additive blocks a reviewer should read before recording a decision:

* `relative_gate` -- the candidate's quality/red-team scores compared against the retiring model's own baseline (`retiring_custom_overall`/`retiring_redteam_block_rate`), using the `quality_epsilon`/`redteam_epsilon` tolerances from `config/evaluation.yaml`. Both `quality_relative_pass`/`redteam_relative_pass` are `null` when no retiring baseline was supplied -- this means the relative gate was skipped, not that it silently passed.
* `audit` -- provenance for the run: judge model version, rubric version, adversarial probe-set version and content hash, the QA dataset hash, the candidate's resolved deployment temperature, per-category red-team pass/fail, the absolute-threshold pass/fail, the retiring baseline values used (if any), and a `suspicious_uniformity` flag (see below). `decision`, `authorizer`, and `decision_timestamp` are always `null` when this repository writes the file -- they exist as placeholders for the reviewer's own tooling to fill in, never for this pipeline.

## Suspicious uniformity

`src.evaluator.service.detect_suspicious_uniformity` inspects the full run's `results` list and flags:

* `redteam_block_rate_constant_1.0` when every candidate in the run shows a perfect 1.0 red-team block rate.
* `custom_overall_identical_across_candidates` when more than one candidate shares an identical `custom_overall` score.

Both conditions are far more consistent with a stubbed or constant scorer than a genuinely uniform result, and are surfaced in the top-level run output's `uniformity_flags` list rather than trusted silently. A reviewer who sees either flag should re-run with the offline canary tests (`tests/unit/test_evaluator_canaries.py`, `tests/unit/test_evaluator_block_judge.py`) before trusting the run's scores.

## Rubric and judge versioning

`config/evaluation.yaml` carries three provenance strings that must be set (or deliberately left blank to signal "not yet configured") before enabling `--live`:

* `judge_model_version` -- the independent judge deployment's underlying model version. Must never match the candidate under evaluation (`src.evaluator.custom_runner.assert_independent_judge` enforces this at runtime).
* `rubric_version` -- published alongside every score so a reviewer can tell which grading rubric produced it.
* `probe_set_version` -- must match `src.evaluator.probe_set_loader.PROBE_SET_VERSION`; bump both together whenever `datasets/adversarial_probes.jsonl` changes meaningfully.

## Raw transcripts

Per-probe prompts, responses, and block rationale are written only by `LiveRedTeamRunner`, only to `results/redteam/{run_id}/{candidate_slug}.json` (`src.evaluator.result_writer.write_redteam_transcript`), and only after passing through `src.shared.redaction.redact_mapping`. This sink is separate from the standard `results/{run_id}/{candidate_slug}/redteam.json` artifact, which keeps its original category-level summary shape and is safe to include in any existing artifact-upload workflow.
