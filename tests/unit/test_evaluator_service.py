"""Unit tests for the end-to-end local evaluator flow."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import unittest

from src.evaluator.service import execute_local_evaluation


REPO_ROOT = Path(__file__).resolve().parents[2]


class EvaluatorServiceTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(REPO_ROOT / "results" / "cli-test-run", ignore_errors=True)

    def test_given_staged_artifacts_and_dataset_when_executing_then_custom_and_redteam_outputs_are_materialized(self) -> None:
        # Arrange
        artifact_root = REPO_ROOT / "artifacts" / "cli-test-run"
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


if __name__ == "__main__":
    unittest.main()