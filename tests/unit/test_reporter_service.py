"""Unit tests for the end-to-end local TG6 reporter service."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from src.reporter.service import execute_local_report


REPO_ROOT = Path(__file__).resolve().parents[2]
HERMETIC_REPO = REPO_ROOT / "tests" / "fixtures" / "hermetic_repo"


class ReporterServiceTests(unittest.TestCase):
    def test_given_current_cli_test_run_when_executing_then_report_and_payload_files_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "reporter-output"

            result = execute_local_report(
                HERMETIC_REPO,
                HERMETIC_REPO / "artifacts" / "cli-test-run",
                output_root,
            )

            self.assertEqual(result.run_id, "cli-test-run")
            self.assertEqual(len(result.report_paths), 1)
            self.assertTrue(result.report_paths[0].exists())
            self.assertTrue(result.decision_paths[0].exists())
            self.assertTrue(result.issue_payload_paths[0].exists())
            self.assertTrue(result.remediation_payload_paths[0].exists())
            self.assertIsNone(result.winners["gpt-4-1-mini-2025-04-14"])
            self.assertTrue(result.warnings)


if __name__ == "__main__":
    unittest.main()