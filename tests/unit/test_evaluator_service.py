"""Unit tests for the end-to-end local evaluator flow."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import unittest

from src.evaluator.service import detect_suspicious_uniformity, execute_local_evaluation


REPO_ROOT = Path(__file__).resolve().parents[2]
HERMETIC_REPO = REPO_ROOT / "tests" / "fixtures" / "hermetic_repo"


class EvaluatorServiceTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(REPO_ROOT / "results" / "cli-test-run", ignore_errors=True)

    def test_given_staged_artifacts_and_dataset_when_executing_then_custom_and_redteam_outputs_are_materialized(self) -> None:
        # Arrange
        artifact_root = HERMETIC_REPO / "artifacts" / "cli-test-run"
        dataset_path = REPO_ROOT / "tests" / "fixtures" / "evaluator" / "dataset.sample.jsonl"

        # Act
        output = execute_local_evaluation(REPO_ROOT, artifact_root, dataset_path)

        # Assert
        self.assertEqual(output["run_id"], "cli-test-run")
        self.assertEqual(output["result_count"], 2)
        self.assertEqual(output["aca_dispatch_status"], "deferred-local-only")
        first_result = output["results"][0]
        custom_payload = json.loads((REPO_ROOT / first_result["custom_path"]).read_text(encoding="utf-8"))
        redteam_payload = json.loads((REPO_ROOT / first_result["redteam_path"]).read_text(encoding="utf-8"))
        summary_payload = json.loads((REPO_ROOT / first_result["summary_path"]).read_text(encoding="utf-8"))
        self.assertIn("rows", custom_payload)
        self.assertIn("attacks", redteam_payload)
        self.assertEqual(summary_payload["status"], "local_complete")
        self.assertEqual(summary_payload["candidate_model"]["deployment_type"], "DataZoneStandard")
        self.assertIn("relative_gate", summary_payload)
        self.assertIn("audit", summary_payload)
        self.assertIn("uniformity_flags", output)

    def test_given_default_non_live_path_when_executing_then_summary_omits_live_only_keys(
        self,
    ) -> None:
        # Arrange
        artifact_root = HERMETIC_REPO / "artifacts" / "cli-test-run"
        dataset_path = REPO_ROOT / "tests" / "fixtures" / "evaluator" / "dataset.sample.jsonl"

        # Act
        output = execute_local_evaluation(REPO_ROOT, artifact_root, dataset_path)

        # Assert: the default (non-live) path never stamps the live-only
        # advisory/promotion_grade fields and never applies redaction, keeping
        # the fake-path summary contract byte-stable (Council DR-03 caveat).
        first_result = output["results"][0]
        summary_payload = json.loads(
            (REPO_ROOT / first_result["summary_path"]).read_text(encoding="utf-8")
        )
        self.assertNotIn("promotion_grade", summary_payload)
        self.assertNotIn("advisory", summary_payload)
        self.assertNotIn("advisory_rationale", summary_payload)


class DetectSuspiciousUniformityTests(unittest.TestCase):
    def test_given_all_candidates_blocked_at_1_0_when_checked_then_flags_constant_block_rate(
        self,
    ) -> None:
        # Arrange
        results = [
            {"redteam_block_rate": 1.0, "custom_overall": 0.8},
            {"redteam_block_rate": 1.0, "custom_overall": 0.9},
        ]

        # Act
        flags = detect_suspicious_uniformity(results)

        # Assert
        self.assertIn("redteam_block_rate_constant_1.0", flags)

    def test_given_varied_block_rates_when_checked_then_no_uniformity_flag(self) -> None:
        # Arrange
        results = [
            {"redteam_block_rate": 1.0, "custom_overall": 0.8},
            {"redteam_block_rate": 0.9, "custom_overall": 0.7},
        ]

        # Act
        flags = detect_suspicious_uniformity(results)

        # Assert
        self.assertNotIn("redteam_block_rate_constant_1.0", flags)

    def test_given_identical_custom_overall_across_multiple_candidates_when_checked_then_flags_it(
        self,
    ) -> None:
        # Arrange
        results = [
            {"redteam_block_rate": 0.9, "custom_overall": 0.8},
            {"redteam_block_rate": 0.85, "custom_overall": 0.8},
        ]

        # Act
        flags = detect_suspicious_uniformity(results)

        # Assert
        self.assertIn("custom_overall_identical_across_candidates", flags)

    def test_given_single_candidate_when_checked_then_no_identical_score_flag(self) -> None:
        # Arrange
        results = [{"redteam_block_rate": 0.9, "custom_overall": 0.8}]

        # Act
        flags = detect_suspicious_uniformity(results)

        # Assert
        self.assertNotIn("custom_overall_identical_across_candidates", flags)


if __name__ == "__main__":
    unittest.main()