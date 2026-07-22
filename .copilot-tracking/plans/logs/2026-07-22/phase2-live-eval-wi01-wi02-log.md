<!-- markdownlint-disable-file -->
# Planning Log: Phase 2 Live Evaluation (WI-01, WI-02)

**Related Plan**: phase2-quality-safety-eval-plan.instructions.md

## Discrepancy Log

Gaps and deviations identified during implementation.

### Unaddressed Research Items

* DR-01: `_run_quality` and `_run_content_safety` currently return None placeholders when no `probe_prompts` are supplied.
  * Source: src/evaluator/quality_safety_eval_client.py (`_run_quality`, `_run_content_safety`)
  * Reason: Live probe-prompt harness for quality/content-safety evaluators is out of scope for WI-01, which anchored on the RedTeam ASR path and provenance contract. Quality dims fall back to None → curated-seed per C11.
  * Impact: medium

### Implementation Deviations

* DD-01: Method patching in `FoundryEvaluateModelTests`.
  * Plan specifies: patch client methods for hermetic error-injection.
  * Implementation differs: patched at the class level (`FoundryQualitySafetyEvalClient`) rather than the instance.
  * Rationale: `@dataclass(slots=True)` makes instance method attributes read-only; class-level patching is per-test isolated and hermetic.

## Suggested Follow-On Work

Items identified during implementation that fall outside current scope.

* WI-03: Implement live quality + content-safety probe-prompt harness — supply a curated probe-prompt corpus and wire `_run_quality`/`_run_content_safety` to real evaluators. (medium)
  * Source: WI-01 live body
  * Dependency: Requires an approved, non-adversarial probe-prompt set and a Foundry project with judge deployment.
* WI-04: End-to-end `--live` smoke against a scoped test Foundry project in CI (manual dispatch only, opt-in var). (low)
  * Source: WI-02 workflow
  * Dependency: Repo variable enablement + service principal federated credential.

## User Decisions

Decisions recorded from Implementation Decision prompts.

* (none this session)
