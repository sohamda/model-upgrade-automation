"""Render local-first TG6 markdown reports."""

from __future__ import annotations

from src.reporter.models import RecommendationDecision, RenderedReport, RetiringTargetAggregate


def _format_cost(value: float | None) -> str:
	if value is None:
		return "n/a (local placeholder)"
	return f"{value:.2%}"


def _format_winner_label(candidate_slug: str, winner_slug: str | None) -> str:
	return "WINNER" if candidate_slug == winner_slug else "candidate"


def render_markdown_report(target: RetiringTargetAggregate, decision: RecommendationDecision) -> RenderedReport:
	"""Render the local markdown report for one retiring target."""

	target_slug = f"{target.model_id.replace('.', '-')}-{target.version}"
	title = f"Model Upgrade Report - {target.model_id}"
	winner_slug = decision.winner.candidate_slug if decision.winner is not None else None
	winner_line = (
		f"## Recommendation: {decision.winner.model_id} {decision.winner.version} ({target.region})"
		if decision.winner is not None
		else "## Recommendation: no qualifying replacement candidate"
	)

	lines = [
		f"# {title}",
		f"**Retiring model:** {target.model_id} {target.version}",
		f"**Retirement date:** {target.retirement_date} ({target.days_until_retirement} days away)",
		f"**Workload:** {target.workload}",
		"",
		winner_line,
		"",
	]
	if decision.winner is not None:
		lines.extend(
			[
				f"**Rationale.** Winner selected by deterministic local TG6 scoring with a weighted score of {decision.winner.weighted_score:.3f}.",
				"",
			]
		)
	else:
		lines.extend(["**Rationale.** No candidate cleared the hard thresholds in this local run.", ""])

	lines.extend(
		[
			"## Ranked candidates",
			"",
			"| Candidate | CE overall | Red-team block | Min safety | Cost delta | Verdict |",
			"|---|---:|---:|---:|---|---|",
		]
	)
	for candidate in target.candidates:
		verdict = next(
			(item.verdict for item in decision.ranked_candidates if item.candidate_slug == candidate.candidate_slug),
			"candidate",
		)
		lines.append(
			"| "
			f"{candidate.model_id} {candidate.version} | "
			f"{candidate.custom_overall:.3f} | "
			f"{candidate.redteam_block_rate:.3f} | "
			f"{candidate.minimum_safety_score:.3f} | "
			f"{_format_cost(candidate.cost_delta_input)} / {_format_cost(candidate.cost_delta_output)} | "
			f"{verdict} |"
		)

	lines.extend(["", "## Per-evaluator score matrix", ""])
	evaluator_names = sorted(
		{name for candidate in target.candidates for name in candidate.evaluator_scores.keys()}
	)
	lines.extend(
		[
			"| Candidate | " + " | ".join(evaluator_names) + " |",
			"|---|" + "|".join(["---:" for _ in evaluator_names]) + "|",
		]
	)
	for candidate in target.candidates:
		values = [f"{candidate.evaluator_scores.get(name, 0.0):.3f}" for name in evaluator_names]
		lines.append(
			f"| {candidate.model_id} {candidate.version} | " + " | ".join(values) + " |"
		)

	lines.extend(["", "## Red-team results", ""])
	attack_categories = sorted(
		{name for candidate in target.candidates for name in candidate.redteam_by_category.keys()}
	)
	lines.extend(
		[
			"| Candidate | " + " | ".join(attack_categories) + " |",
			"|---|" + "|".join(["---:" for _ in attack_categories]) + "|",
		]
	)
	for candidate in target.candidates:
		values = [f"{candidate.redteam_by_category.get(name, 0.0):.3f}" for name in attack_categories]
		lines.append(
			f"| {candidate.model_id} {candidate.version} | " + " | ".join(values) + " |"
		)

	lines.extend(["", "## Contract warnings", ""])
	if target.warnings:
		for warning in sorted(set(target.warnings)):
			lines.append(f"- {warning}")
	else:
		lines.append("- None")

	lines.extend(["", "## Recommendation notes", ""])
	for note in decision.scoring_notes:
		lines.append(f"- {note}")

	lines.extend(["", "## Raw artifacts", ""])
	lines.append(f"- Dry-run output: {target.dry_run_output_path}")
	lines.append(f"- History preview: {target.history_preview_path}")
	for candidate in target.candidates:
		lines.append(
			f"- {candidate.candidate_slug}: summary={candidate.artifact_paths['summary']}, custom={candidate.artifact_paths['custom']}, redteam={candidate.artifact_paths['redteam']}"
		)

	lines.extend(["", "## Migration checklist", ""])
	lines.extend(
		[
			"- [ ] Review the local markdown report and structured payloads.",
			f"- [ ] Confirm dataset hash mismatch handling for {target.model_id} before publication.",
			f"- [ ] Approve the winning candidate {_format_winner_label(winner_slug or 'none', winner_slug)} for downstream publication when GitHub access is available.",
			"- [ ] Review any draft remediation payload before enabling auto PR publication.",
		]
	)

	return RenderedReport(
		target_slug=target_slug,
		title=title,
		content="\n".join(lines) + "\n",
		warnings=sorted(set(target.warnings + decision.global_warnings)),
	)