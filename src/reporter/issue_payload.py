"""Build local structured payloads for future GitHub issue publication."""

from __future__ import annotations

from datetime import datetime, timezone

from src.reporter.models import IssuePayload, RecommendationDecision, RetiringTargetAggregate


def build_issue_payload(target: RetiringTargetAggregate, decision: RecommendationDecision) -> IssuePayload:
	"""Build a deferred local payload for the weekly summary issue."""

	week = datetime.now(timezone.utc).isocalendar()
	winner_slug = decision.winner.candidate_slug if decision.winner is not None else None
	summary = (
		f"Retiring model {target.model_id} {target.version} evaluated {len(target.candidates)} candidates; "
		f"winner={winner_slug or 'none'}"
	)
	return IssuePayload(
		week_key=f"{week.year}-W{week.week:02d}",
		title=f"Weekly model upgrade summary - {target.model_id}",
		labels=["model-upgrade", "automated"],
		retiring_model_id=target.model_id,
		retiring_model_version=target.version,
		winner_candidate_slug=winner_slug,
		summary=summary,
		warnings=sorted(set(target.warnings + decision.global_warnings)),
	)