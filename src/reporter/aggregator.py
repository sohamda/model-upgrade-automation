"""Aggregate TG4 and TG5 local artifacts into reporter comparison datasets."""

from __future__ import annotations

from src.reporter.models import (
	CandidateComparison,
	ReporterRunInput,
	RetiringTargetAggregate,
)

SAFETY_EVALUATOR_KEYS = (
	"violence",
	"sexual",
	"self_harm",
	"hate_unfairness",
)


def _safe_float(value: object, default: float = 0.0) -> float:
	if isinstance(value, (int, float)):
		return float(value)
	return default


def aggregate_reporter_run(report_input: ReporterRunInput) -> list[RetiringTargetAggregate]:
	"""Build retiring-target-scoped candidate comparison datasets."""

	aggregates: list[RetiringTargetAggregate] = []
	for target in report_input.targets:
		comparisons: list[CandidateComparison] = []
		warnings: list[str] = []
		for candidate in target.candidates:
			custom_aggregates = candidate.custom_payload.get("aggregates", {})
			redteam_attacks = candidate.redteam_payload.get("attacks", [])
			evaluator_scores = {
				str(key): _safe_float(value)
				for key, value in custom_aggregates.items()
				if key != "overall"
			}
			minimum_safety_score = min(
				(_safe_float(custom_aggregates.get(key), 0.0) for key in SAFETY_EVALUATOR_KEYS),
				default=0.0,
			)
			redteam_by_category: dict[str, float] = {}
			if isinstance(redteam_attacks, list):
				for attack in redteam_attacks:
					if not isinstance(attack, dict):
						continue
					category = attack.get("attack_category")
					if isinstance(category, str):
						redteam_by_category[category] = _safe_float(attack.get("block_rate"))

			fallback_notes: list[str] = []
			if candidate.dataset_hash_status.mismatch_notes:
				fallback_notes.extend(candidate.dataset_hash_status.mismatch_notes)
				warnings.extend(candidate.dataset_hash_status.mismatch_notes)
			fallback_notes.append("Cost delta is unavailable locally; using a neutral zero-cost fallback.")
			fallback_notes.append(
				"Longevity is unavailable locally; using recommender rank then candidate slug as the deterministic tie-break fallback."
			)

			comparisons.append(
				CandidateComparison(
					candidate_slug=candidate.candidate_slug,
					model_id=candidate.model_id,
					version=candidate.version,
					deployment_name=candidate.deployment_name,
					deployment_type=candidate.deployment_type,
					custom_overall=candidate.custom_overall,
					redteam_block_rate=candidate.redteam_block_rate,
					minimum_safety_score=minimum_safety_score,
					evaluator_scores=evaluator_scores,
					redteam_by_category=redteam_by_category,
					thresholds=candidate.thresholds,
					dataset_hash_status=candidate.dataset_hash_status,
					recommender_score=candidate.recommender_score,
					recommender_rank=candidate.recommender_rank,
					recommender_rationale=list(candidate.recommender_rationale),
					cost_delta_input=None,
					cost_delta_output=None,
					longevity_days=None,
					fallback_notes=fallback_notes,
					artifact_paths={
						"summary": candidate.summary_path.as_posix(),
						"custom": candidate.custom_path.as_posix(),
						"redteam": candidate.redteam_path.as_posix(),
					},
					promotion_grade=candidate.promotion_grade,
					advisory=candidate.advisory,
				)
			)

		aggregates.append(
			RetiringTargetAggregate(
				model_id=target.model_id,
				version=target.version,
				region=target.region,
				workload=target.workload,
				retirement_date=target.retirement_date,
				days_until_retirement=target.days_until_retirement,
				replacement_family=target.replacement_family,
				dry_run_output_path=target.dry_run_output_path.as_posix(),
				history_preview_path=target.history_preview_path.as_posix(),
				candidates=comparisons,
				warnings=sorted(set(warnings)),
			)
		)

	return aggregates