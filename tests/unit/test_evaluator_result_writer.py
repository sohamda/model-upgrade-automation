"""Unit tests for evaluator artifact persistence."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import unittest

from src.evaluator.models import (
    CandidateEvaluationArtifacts,
    CustomEvaluationResult,
    RedTeamEvaluationResult,
)
from src.evaluator.result_writer import write_candidate_results


REPO_ROOT = Path(__file__).resolve().parents[2]


class EvaluatorResultWriterTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(REPO_ROOT / "results" / "test-run", ignore_errors=True)

    def test_given_candidate_results_when_written_then_expected_json_files_exist(self) -> None:
        # Arrange
        artifacts = CandidateEvaluationArtifacts(
            candidate_slug="gpt-4-1-2026-01-12",
            custom=CustomEvaluationResult(
                candidate_slug="gpt-4-1-2026-01-12",
                dataset_sha256="dataset-sha",
                rows=[{"row_id": "row-1", "scores": {"overall": 0.91}}],
                aggregates={"overall": 0.91},
            ),
            redteam=RedTeamEvaluationResult(
                candidate_slug="gpt-4-1-2026-01-12",
                dataset_sha256="dataset-sha",
                attacks=[{"attack_category": "jailbreak", "block_rate": 1.0}],
                block_rate=1.0,
                aggregates={"overall_block_rate": 1.0},
            ),
            summary={"status": "local_complete"},
        )

        # Act
        output_paths = write_candidate_results(REPO_ROOT, "test-run", artifacts)

        # Assert
        self.assertEqual(
            sorted(path.name for path in output_paths.values()),
            ["custom.json", "redteam.json", "summary.json"],
        )
        self.assertEqual(
            json.loads(output_paths["custom"].read_text(encoding="utf-8"))["aggregates"]["overall"],
            0.91,
        )
        self.assertEqual(
            json.loads(output_paths["redteam"].read_text(encoding="utf-8"))["block_rate"],
            1.0,
        )
        self.assertEqual(
            json.loads(output_paths["summary"].read_text(encoding="utf-8"))["status"],
            "local_complete",
        )


if __name__ == "__main__":
    unittest.main()