---
applyTo: '.copilot-tracking/changes/2026-07-23/real-quality-safety-gates-changes.md'
---
<!-- markdownlint-disable-file -->
# Implementation Plan: Make the Evaluator's Quality + Safety Gates Real

## Overview

Replace the deterministic fake evaluator scores with LIVE, Azure-backed quality judging and red-team ASR routed through the already-validated `src/evaluator/quality_safety_eval_client.py` seam, keeping the fakes as the default and live strictly opt-in, per Council Decision #51's 13 binding conditions.

## Objectives

### User Requirements

* Make the promotion-gate quality + safety signals real (live-backed), not stubbed — Source: user planning request (this session); Council Decision #51 plan-of-record mandate.
* Encode all 13 Council #51 binding conditions before any code is written; produce plan + details only (Kenny/Task Implementor executes) — Source: user planning request.
* Phase 1 = live runners + provider + opt-in; Phase 2 = real adversarial gate (probe set, classifier, relative scoring, canaries, audit, human gate) — Source: user's two verbatim phase specs.

### Derived Objectives

* Reuse the validated seam instead of forking a client — Derived from: Council C1 + Decision #48 de-risker; lowest-risk path.
* Add per-model API shaping additively to config/models.yaml — Derived from: o3 vs gpt-5.1 request differences (no capabilities section exists today).
* Keep results/redteam/ off CI artifact globs — Derived from: verified detect-and-eval.yml uploads only .artifacts/* + run-context/finalize.

## Context Summary

### Project Files

* src/evaluator/service.py - injectable-runner seam (`execute_local_evaluation`); needs `--live` wiring + advisory/relative/audit stamping.
* src/evaluator/quality_safety_eval_client.py - council-blessed live seam; `FoundryQualitySafetyEvalClient.response_provider` is the plug-in point (REUSE, do not fork).
* src/evaluator/custom_runner.py - `LocalCustomRunner` (default); add `LiveCustomRunner`.
* src/evaluator/redteam_runner.py - `LocalRedTeamRunner` (default, has nano rule to remove); add `LiveRedTeamRunner`.
* src/evaluator/models.py - result/work-item contracts consumed by summary.
* src/evaluator/result_writer.py - results/{run_id}/{slug}/*.json writer; extend for audit bundle.
* config/models.yaml - add additive `model_api_shapes`.
* config/evaluation.yaml - add additive `judge_model_version`, `rubric_version`, `relative_gate` keys.
* datasets/general_qa.jsonl - QA set (no gold answers); do NOT reuse for adversarial probes.

### References

* .copilot-tracking/research/2026-07-23/real-quality-safety-gates-research.md - verified facts + condition mapping.
* .copilot-tracking/plans/2026-07-22/phase2-real-eval-quality-safety-plan.instructions.md - prior recommender-cache surface (reuses same seam; different gate).

### Standards References

* /memories/repo/squad-decision-51-council-verdict-eval-runners.md - 13 binding conditions (C1-C13).
* /memories/repo/squad-council-verdict-wi01-wi02-foundry-eval.md - seam posture (import-guard, scope-lock, provenance, no-key).
* .github/copilot-instructions.md - repository conventions.

## Implementation Checklist

### [x] Implementation Phase 1: Live-Backed Runners (Make the Signal Real)

<!-- parallelizable: false -->

* [x] Step 1.1: Add additive `model_api_shapes` to config/models.yaml + loader (C2)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 19-39)
* [x] Step 1.2: Create src/evaluator/aoai_client.py candidate response provider + model_id->deployment adapter (C2, C5, DD-03)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 40-70)
* [x] Step 1.3: Resilience wrapper (backoff+jitter, Retry-After, timeout, UNSCORED) (Architect resilience)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 71-92)
* [x] Step 1.4: Create LiveCustomRunner delegating to the seam (binds DD-03/DD-04 deployment-name closure) (C1, C3, C10)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 93-116)
* [x] Step 1.5: Create LiveRedTeamRunner delegating to the seam (binds DD-04 deployment-name closure) (C1, C3, C11)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 117-139)
* [x] Step 1.6: Wire `--live` / `MUA_EVAL_MODE=live` runner selection in service.py (C4)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 140-159)
* [x] Step 1.7: Enforce independent judge (judge != candidate/family; pinned) (C10)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 160-180)
* [x] Step 1.8: Security redaction + red-team transcript segregation to results/redteam/ (C6, C7, C8, C9)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 181-202)
* [x] Step 1.9: Label live outputs NON-promotion-grade / advisory + thread flag through models.py/aggregator.py into reporter (RAI, C13, DR-03)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 203-226)
* [x] Step 1.10: Validate Phase 1 (guard-import + offline fakes; live smoke opt-in only)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 227-234)

### [x] Implementation Phase 2: Real Adversarial Gate (Judgment Integrity)

<!-- parallelizable: false -->

* [x] Step 2.1: Create versioned SHA-256 adversarial probe set (5 categories, 5-10 each; not general_qa) (C11)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 239-264)
* [x] Step 2.2: Real block-judging (classifier primary + judge; fail-closed; remove nano rule) (C11, C12)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 265-286)
* [x] Step 2.3: Relative-to-retiring scoring (candidate >= retiring - epsilon) + additive config (RAI relative)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 287-307)
* [x] Step 2.4: Anti-regression canaries (poison + discrimination + uniformity flag) (C12)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 308-326)
* [x] Step 2.5: Per-run auditability bundle (both dataset hashes, versions, per-item pass/fail, baseline) (RAI audit)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 327-347)
* [x] Step 2.6: Human-in-the-loop gate (RECOMMENDS; human confirms; versioned rubric; reporter honors advisory) (C13, DR-03)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 348-367)
* [x] Step 2.7: Validate Phase 2 (canaries offline; probe-set + classifier live opt-in)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 368-374)

### [x] Implementation Phase 3: Test Strategy + Full Validation

<!-- parallelizable: false -->

* [x] Step 3.1: Unit tests inject fakes/stubs; no Azure creds in CI
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 379-393)
* [x] Step 3.2: Full validation + opt-in live check (STOP-AND-GATE; tear down deployments after)
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 394-402)
* [x] Step 3.3: Report blocking issues with next steps
  * Details: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Lines 403-405)

## Planning Log

See .copilot-tracking/plans/logs/2026-07-23/real-quality-safety-gates-log.md for discrepancy tracking, implementation paths considered, the condition-to-task traceability table, and suggested follow-on work.

## Dependencies

* Python 3.12 with `.venv` (offline default) and `.venv-live` (`[evaluation]` extra: openai, azure-identity, azure-ai-evaluation).
* Existing validated seam src/evaluator/quality_safety_eval_client.py (Decision #48).
* Two live Azure OpenAI deployments (independent judge + candidate) for opt-in live tests only; torn down after (inference-only; no resource mutation).
* PD-01 resolved (judge deployment source + safety classifier choice) before Step 2.2.

## Success Criteria

* Live runners emit real quality + red-team signals via the reused seam; fakes remain default; live opt-in only — Traces to: C1, C3, C4.
* Keyless AAD, redacted logs/results, segregated red-team transcripts — Traces to: C5, C6, C7, C8, C9.
* Independent judge, real probe set + classifier, relative gate, canaries, audit bundle, human gate — Traces to: C10, C11, C12, C13 + RAI HIGH-risk caveat.
* Offline unit suite green with fakes/stubs; no Azure creds in CI; nothing auto-promotes; no Azure resources mutated — Traces to: user requirement + Council STOP-AND-GATE.
