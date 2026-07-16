"""Unit tests for the ACA job adapter seam."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.evaluator.aca_job import AcaJobAdapter
from src.evaluator.config_loader import load_evaluator_config
from src.evaluator.input_builder import build_work_items_from_artifacts
from src.shared.errors import DependencyUnavailableError


REPO_ROOT = Path(__file__).resolve().parents[2]


class EvaluatorAcaJobTests(unittest.TestCase):
    def test_given_work_item_when_building_aca_request_then_contract_fields_are_preserved(self) -> None:
        # Arrange
        evaluator_config = load_evaluator_config(REPO_ROOT)
        work_item = build_work_items_from_artifacts(
            REPO_ROOT,
            REPO_ROOT / "artifacts" / "cli-test-run",
            evaluator_config,
            REPO_ROOT / "tests" / "fixtures" / "evaluator" / "dataset.sample.jsonl",
        )[0]
        adapter = AcaJobAdapter()

        # Act
        request = adapter.build_request(work_item)

        # Assert
        self.assertEqual(request.run_id, "cli-test-run")
        self.assertEqual(request.candidate_slug, "gpt-4-1-2026-01-12")
        self.assertEqual(request.deployment_name, work_item.deployment_ref.deployment_name)
        self.assertEqual(request.dataset_sha256, work_item.dataset_sha256)

    def test_given_local_only_mode_when_dispatching_then_live_execution_is_explicitly_deferred(self) -> None:
        # Arrange
        adapter = AcaJobAdapter()

        # Act & Assert
        with self.assertRaises(DependencyUnavailableError):
            adapter.dispatch(
                adapter.build_request(
                    build_work_items_from_artifacts(
                        REPO_ROOT,
                        REPO_ROOT / "artifacts" / "cli-test-run",
                        load_evaluator_config(REPO_ROOT),
                        REPO_ROOT / "tests" / "fixtures" / "evaluator" / "dataset.sample.jsonl",
                    )[0]
                )
            )


if __name__ == "__main__":
    unittest.main()