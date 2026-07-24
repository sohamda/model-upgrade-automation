<!-- markdownlint-disable-file -->
# Planning Log: Live `--live` evaluator validation on ff-hub-01

**Related Plan**: real-quality-safety-gates-plan.instructions.md (2026-07-23)

## Discrepancy Log

Gaps and deviations identified during the live validation.

### Unaddressed Research Items

* DR-01: Relative-to-retiring gate cannot exercise on this staged artifact-root.
  * Source: src/evaluator/input_builder.py (`build_work_items_from_artifacts` supplies no retiring baseline scores → `retiring_custom_overall`/`retiring_redteam_block_rate` = None)
  * Reason: staged dry-run artifacts carry no baseline eval scores; gate is skipped, not fabricated.
  * Impact: low — advisory run routes every candidate to needs_human_review regardless.

### Implementation Deviations

* DD-01: The quality judge seam builds a plain judge config with no reasoning-model handling.
  * Plan specifies: use an independent judge to produce real quality scores.
  * Implementation differs: `_judge_config` = `{azure_endpoint, azure_deployment: judge_model, api_version}` (quality_safety_eval_client.py) sends default `temperature`/`max_tokens`, which o-series reasoning judges reject → each dimension errors → quality UNSCORED.
  * Rationale: this is existing seam behavior; validating live surfaced it. No fabrication occurs — UNSCORED is the honest fail-safe.

* DD-02: On the custom path, the seam's side-effect `_run_red_team` targets the bare model_id (`"gpt-5.1"`/`"o3"`), which is not a real deployment name → the scan fails fast to UNSCORED.
  * Impact: harmless — the authoritative red-team signal comes from `LiveRedTeamRunner` (own classifier + judge path), not this seam fold. No hidden red-team cost/time on the custom path.

## Suggested Follow-On Work

* WI-01: Add `is_reasoning_model` support to the quality judge config so o-series independent judges (o1/o4-mini) can produce real quality scores. (medium)
  * Source: PD-01 analysis
  * Dependency: none; additive to `_judge_config` / `_run_quality`.
* WI-02: Wire retiring-baseline scores into `build_work_items_from_artifacts` so the relative-to-retiring gate can exercise live. (low)

## User Decisions

Decisions recorded from Implementation Decision prompts.

* PD-01: Independent quality judge for the candidates — **awaiting user decision** (presented 2026-07-24, $0 spent).
