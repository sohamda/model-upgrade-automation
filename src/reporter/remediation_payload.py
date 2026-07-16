"""Build local structured payloads for future remediation PR publication."""

from __future__ import annotations

from src.reporter.models import RecommendationDecision, RemediationPayload, RetiringTargetAggregate


def build_remediation_payload(
	target: RetiringTargetAggregate,
	decision: RecommendationDecision,
	*,
	enable_auto_pr: bool,
) -> RemediationPayload:
	"""Build a deferred local remediation payload without mutating GitHub."""

	winner_slug = decision.winner.candidate_slug if decision.winner is not None else None
	winner_model_id = decision.winner.model_id if decision.winner is not None else ""
	winner_version = decision.winner.version if decision.winner is not None else ""
	warnings = sorted(set(target.warnings + decision.global_warnings))
	if not enable_auto_pr:
		warnings.append("Auto remediation PR generation is disabled by local configuration.")
	if decision.winner is None:
		warnings.append("No winning candidate is available for remediation patch generation.")
	return RemediationPayload(
		draft=True,
		enabled_by_config=enable_auto_pr,
		labels=["needs-human-review"],
		target_slug=f"{target.model_id.replace('.', '-')}-{target.version}",
		winner_candidate_slug=winner_slug,
		suggested_parameter_updates={
			"retiring_model_id": target.model_id,
			"retiring_model_version": target.version,
			"replacement_model_id": winner_model_id,
			"replacement_model_version": winner_version,
		},
		warnings=warnings,
	)