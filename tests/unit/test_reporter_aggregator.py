"""Unit tests for TG6 reporter aggregation."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.reporter.aggregator import aggregate_reporter_run
from src.reporter.artifact_loader import load_reporter_run_input


REPO_ROOT = Path(__file__).resolve().parents[2]


class ReporterAggregatorTests(unittest.TestCase):
    def test_given_current_cli_test_run_when_aggregating_then_warnings_and_score_matrices_are_materialized(self) -> None:
        report_input = load_reporter_run_input(REPO_ROOT, REPO_ROOT / "artifacts" / "cli-test-run")

        aggregates = aggregate_reporter_run(report_input)

        self.assertEqual(len(aggregates), 1)
        aggregate = aggregates[0]
        self.assertEqual(len(aggregate.candidates), 2)
        self.assertTrue(aggregate.warnings)
        first_candidate = aggregate.candidates[0]
        self.assertIn("coherence", first_candidate.evaluator_scores)
        self.assertIn("prompt_injection", first_candidate.redteam_by_category)
        self.assertIsNone(first_candidate.cost_delta_input)
        self.assertTrue(first_candidate.fallback_notes)


if __name__ == "__main__":
    unittest.main()