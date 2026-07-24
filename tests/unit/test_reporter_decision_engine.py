"""Unit tests for TG6 reporter winner selection."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.reporter.aggregator import aggregate_reporter_run
from src.reporter.artifact_loader import load_reporter_run_input
from src.reporter.decision_engine import decide_recommendation
from src.reporter.models import (
    CandidateComparison,
    DatasetHashStatus,
    ReporterThresholds,
    RetiringTargetAggregate,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
HERMETIC_REPO = REPO_ROOT / "tests" / "fixtures" / "hermetic_repo"


def _dataset_hash_status() -> DatasetHashStatus:
    return DatasetHashStatus(
        run_context_dataset_sha256="abc",
        aca_job_dataset_sha256="abc",
        summary_dataset_sha256="abc",
        matches_run_context=True,
        matches_aca_job_request=True,
    )


def _candidate(
    slug: str,
    *,
    advisory: bool,
    promotion_grade: bool,
    custom_overall: float | None,
    redteam_block_rate: float | None,
) -> CandidateComparison:
    return CandidateComparison(
        candidate_slug=slug,
        model_id="gpt-4.1-mini",
        version="2025-04-14",
        deployment_name=f"{slug}-deployment",
        deployment_type="DataZoneStandard",
        custom_overall=custom_overall,
        redteam_block_rate=redteam_block_rate,
        minimum_safety_score=1.0,
        evaluator_scores={},
        redteam_by_category={},
        thresholds=ReporterThresholds(minimum_custom_score=0.75, minimum_redteam_block_rate=0.95),
        dataset_hash_status=_dataset_hash_status(),
        recommender_score=None,
        recommender_rank=None,
        promotion_grade=promotion_grade,
        advisory=advisory,
    )


def _target(candidates: list[CandidateComparison]) -> RetiringTargetAggregate:
    return RetiringTargetAggregate(
        model_id="gpt-4.1",
        version="2025-04-14",
        region="swedencentral",
        workload="test-workload",
        retirement_date="2026-01-01",
        days_until_retirement=90,
        replacement_family="gpt-4.1",
        dry_run_output_path="results/dry-run.json",
        history_preview_path="results/history.json",
        candidates=candidates,
    )


class ReporterDecisionEngineTests(unittest.TestCase):
    def test_given_current_cli_test_run_when_deciding_then_hard_safety_threshold_blocks_a_local_winner(self) -> None:
        report_input = load_reporter_run_input(HERMETIC_REPO, HERMETIC_REPO / "artifacts" / "cli-test-run")
        aggregate = aggregate_reporter_run(report_input)[0]

        decision = decide_recommendation(aggregate)

        self.assertIsNone(decision.winner)
        self.assertTrue(all(item.verdict == "rejected" for item in decision.ranked_candidates))
        self.assertTrue(
            any("hard safety" in reason for item in decision.ranked_candidates for reason in item.rejection_reasons)
        )
        self.assertTrue(decision.global_warnings)
        self.assertTrue(decision.scoring_notes)


class ReporterDecisionEngineAdvisoryFlowTests(unittest.TestCase):
    def test_given_advisory_and_promotable_candidates_when_deciding_then_advisory_never_wins(self) -> None:
        advisory_candidate = _candidate(
            "advisory-candidate",
            advisory=True,
            promotion_grade=False,
            custom_overall=None,
            redteam_block_rate=None,
        )
        promotable_candidate = _candidate(
            "promotable-candidate",
            advisory=False,
            promotion_grade=True,
            custom_overall=0.9,
            redteam_block_rate=0.97,
        )

        decision = decide_recommendation(_target([advisory_candidate, promotable_candidate]))

        advisory_decision = next(
            item for item in decision.ranked_candidates if item.candidate_slug == "advisory-candidate"
        )
        self.assertEqual(advisory_decision.verdict, "needs_human_review")
        self.assertIsNone(advisory_decision.weighted_score)
        self.assertEqual(advisory_decision.rejection_reasons, [])

        self.assertIsNotNone(decision.winner)
        self.assertEqual(decision.winner.candidate_slug, "promotable-candidate")

    def test_given_only_advisory_candidates_when_deciding_then_no_winner_and_no_crash(self) -> None:
        advisory_candidate = _candidate(
            "advisory-only",
            advisory=True,
            promotion_grade=False,
            custom_overall=None,
            redteam_block_rate=None,
        )

        decision = decide_recommendation(_target([advisory_candidate]))

        self.assertIsNone(decision.winner)
        self.assertEqual(decision.ranked_candidates[0].verdict, "needs_human_review")


if __name__ == "__main__":
    unittest.main()