"""Unit tests for TG6 markdown report rendering."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.reporter.aggregator import aggregate_reporter_run
from src.reporter.artifact_loader import load_reporter_run_input
from src.reporter.decision_engine import decide_recommendation
from src.reporter.markdown_report import render_markdown_report


REPO_ROOT = Path(__file__).resolve().parents[2]
HERMETIC_REPO = REPO_ROOT / "tests" / "fixtures" / "hermetic_repo"


class ReporterMarkdownReportTests(unittest.TestCase):
    def test_given_current_cli_test_run_when_rendering_then_required_sections_are_present(self) -> None:
        report_input = load_reporter_run_input(HERMETIC_REPO, HERMETIC_REPO / "artifacts" / "cli-test-run")
        aggregate = aggregate_reporter_run(report_input)[0]
        decision = decide_recommendation(aggregate)

        report = render_markdown_report(aggregate, decision)

        self.assertIn("## Ranked candidates", report.content)
        self.assertIn("## Per-evaluator score matrix", report.content)
        self.assertIn("## Red-team results", report.content)
        self.assertIn("## Contract warnings", report.content)
        self.assertIn("n/a (local placeholder)", report.content)


if __name__ == "__main__":
    unittest.main()