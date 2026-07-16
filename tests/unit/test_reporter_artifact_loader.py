"""Unit tests for TG6 local artifact loading."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.reporter.artifact_loader import load_reporter_run_input


REPO_ROOT = Path(__file__).resolve().parents[2]
HERMETIC_REPO = REPO_ROOT / "tests" / "fixtures" / "hermetic_repo"


class ReporterArtifactLoaderTests(unittest.TestCase):
    def test_given_current_cli_test_run_when_loading_then_dataset_hash_mismatch_is_explicit(self) -> None:
        report_input = load_reporter_run_input(
            HERMETIC_REPO,
            HERMETIC_REPO / "artifacts" / "cli-test-run",
        )

        self.assertEqual(report_input.run_id, "cli-test-run")
        self.assertEqual(len(report_input.targets), 1)
        target = report_input.targets[0]
        self.assertEqual(target.model_id, "gpt-4.1-mini")
        self.assertEqual(len(target.candidates), 2)

        first_candidate = target.candidates[0]
        self.assertFalse(first_candidate.dataset_hash_status.matches_run_context)
        self.assertFalse(first_candidate.dataset_hash_status.matches_aca_job_request)
        self.assertIn(
            "summary.dataset_sha256 differs from dry_run_output.run_context.dataset_sha256",
            first_candidate.dataset_hash_status.mismatch_notes,
        )
        self.assertIn(
            "summary.dataset_sha256 differs from summary.aca_job_request.dataset_sha256",
            first_candidate.dataset_hash_status.mismatch_notes,
        )


if __name__ == "__main__":
    unittest.main()