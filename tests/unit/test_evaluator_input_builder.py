"""Unit tests for TG5 staged artifact ingestion."""

from __future__ import annotations

from pathlib import Path
import shutil
import unittest

from src.evaluator.config_loader import load_evaluator_config
from src.evaluator.input_builder import build_work_items_from_artifacts
from src.shared.errors import ContractError


REPO_ROOT = Path(__file__).resolve().parents[2]


class EvaluatorInputBuilderTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(REPO_ROOT / "artifacts" / "broken-run", ignore_errors=True)

    def test_given_tg4_staged_artifacts_when_building_work_items_then_candidate_inputs_are_deterministic(self) -> None:
        # Arrange
        artifact_root = REPO_ROOT / "artifacts" / "cli-test-run"
        dataset_path = REPO_ROOT / "tests" / "fixtures" / "evaluator" / "dataset.sample.jsonl"
        evaluator_config = load_evaluator_config(REPO_ROOT)

        # Act
        work_items = build_work_items_from_artifacts(
            REPO_ROOT,
            artifact_root,
            evaluator_config,
            dataset_path,
        )

        # Assert
        self.assertEqual(len(work_items), 2)
        self.assertEqual(work_items[0].run_context.run_id, "cli-test-run")
        self.assertEqual(work_items[0].candidate_slug, "gpt-4-1-2026-01-12")
        self.assertEqual(work_items[0].deployment_ref.deployment_name, "tg4-gpt-4-1-mini-gpt-4-1-2026-01-12")
        self.assertEqual(work_items[0].dataset_sha256, work_items[0].run_context.dataset_sha256)
        self.assertEqual(
            work_items[0].manifest_paths["provisioner-preview"].relative_to(REPO_ROOT).as_posix(),
            "artifacts/cli-test-run/provisioner.json",
        )
        self.assertEqual(work_items[0].recommendation_rationale[0], "quality=0.95*0.50")
        self.assertEqual(work_items[1].candidate_model_id, "gpt-4.1-nano")

    def test_given_missing_required_manifest_when_building_work_items_then_contract_error_is_raised(self) -> None:
        # Arrange
        artifact_root = REPO_ROOT / "artifacts" / "broken-run"
        artifact_root.mkdir(parents=True, exist_ok=True)
        dry_run_source = REPO_ROOT / "tests" / "fixtures" / "evaluator" / "tg4-dry-run.sample.json"
        history_source = REPO_ROOT / "tests" / "fixtures" / "evaluator" / "tg4-history-preview.sample.json"
        dry_run_payload = dry_run_source.read_text(encoding="utf-8")
        broken_history_payload = history_source.read_text(encoding="utf-8").replace(
            '      "artifact_type": "provisioner-preview",\n'
            '      "content_sha256": "provisioner-sha",\n'
            '      "created_at_utc": "2026-07-15T19:10:21.556073+00:00",\n'
            '      "dataset_sha256": "435204ce99306666c9ef05db27ac32076b8d32a5f43198e0e837ec6dfadfd0c6",\n'
            '      "relative_path": "artifacts/cli-test-run/provisioner.json",\n'
            '      "run_id": "cli-test-run"\n',
            "",
        )
        (artifact_root / "dry_run_output.json").write_text(dry_run_payload, encoding="utf-8")
        (artifact_root / "history_preview.json").write_text(broken_history_payload, encoding="utf-8")

        # Act & Assert
        with self.assertRaises(ContractError):
            build_work_items_from_artifacts(
                REPO_ROOT,
                artifact_root,
                load_evaluator_config(REPO_ROOT),
                REPO_ROOT / "tests" / "fixtures" / "evaluator" / "dataset.sample.jsonl",
            )


if __name__ == "__main__":
    unittest.main()