"""Unit tests for TG6 reporter winner selection."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.reporter.aggregator import aggregate_reporter_run
from src.reporter.artifact_loader import load_reporter_run_input
from src.reporter.decision_engine import decide_recommendation


REPO_ROOT = Path(__file__).resolve().parents[2]


class ReporterDecisionEngineTests(unittest.TestCase):
    def test_given_current_cli_test_run_when_deciding_then_hard_safety_threshold_blocks_a_local_winner(self) -> None:
        report_input = load_reporter_run_input(REPO_ROOT, REPO_ROOT / "artifacts" / "cli-test-run")
        aggregate = aggregate_reporter_run(report_input)[0]

        decision = decide_recommendation(aggregate)

        self.assertIsNone(decision.winner)
        self.assertTrue(all(item.verdict == "rejected" for item in decision.ranked_candidates))
        self.assertTrue(
            any("hard safety" in reason for item in decision.ranked_candidates for reason in item.rejection_reasons)
        )
        self.assertTrue(decision.global_warnings)
        self.assertTrue(decision.scoring_notes)


if __name__ == "__main__":
    unittest.main()