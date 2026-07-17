"""Unit tests for the dry-run orchestrator output surface."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from src.orchestrator.cli import create_parser, main
from src.orchestrator.pipeline import execute_dry_run


REPO_ROOT = Path(__file__).resolve().parents[2]
HERMETIC_REPO = REPO_ROOT / "tests" / "fixtures" / "hermetic_repo"


class OrchestratorPipelineTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(REPO_ROOT / "artifacts" / "test-run", ignore_errors=True)

    def test_given_default_config_when_executing_dry_run_then_emits_detector_and_recommender_payloads(self) -> None:
        # Act
        result = execute_dry_run(REPO_ROOT, run_id="test-run", config_root=HERMETIC_REPO)

        # Assert
        payload = result.to_dict()
        self.assertEqual(payload["run_context"]["deployment_type"], "DataZoneStandard")
        self.assertEqual(payload["run_context"]["correlation_version"], "tg4-slice-2")
        self.assertEqual(len(payload["detector"]["retiring_targets"]), 1)
        self.assertEqual(len(payload["recommender"]["recommendations"]), 1)
        self.assertEqual(len(payload["provisioner"]["plans"]), 1)
        self.assertEqual(len(payload["history"]["manifests"]), 3)
        self.assertEqual(len(payload["history"]["skip_index_keys"]), 2)
        self.assertEqual(
            payload["recommender"]["recommendations"][0]["ranked_candidates"][0]["candidate"]["model_id"],
            "gpt-4.1",
        )
        self.assertEqual(
            payload["provisioner"]["plans"][0]["provision_requests"][0]["tags"]["managedBy"],
            "model-upgrade-automation",
        )
        self.assertEqual(payload["credential"]["mode"], "oidc-placeholder")

    def test_given_explicit_run_id_when_executing_dry_run_then_stages_manifest_and_summary_files(self) -> None:
        # Arrange
        artifact_root = REPO_ROOT / "artifacts" / "test-run"

        # Act
        result = execute_dry_run(REPO_ROOT, run_id="test-run")
        payload = result.to_dict()

        # Assert
        self.assertEqual(payload["staging"]["artifact_root"], "artifacts/test-run")
        self.assertCountEqual(
            payload["staging"]["files"],
            [
                "artifacts/test-run/detector.json",
                "artifacts/test-run/recommender.json",
                "artifacts/test-run/provisioner.json",
                "artifacts/test-run/history_preview.json",
                "artifacts/test-run/dry_run_output.json",
            ],
        )
        self.assertTrue(artifact_root.exists())
        self.assertEqual(
            json.loads((artifact_root / "detector.json").read_text(encoding="utf-8")),
            payload["detector"],
        )
        self.assertEqual(
            json.loads((artifact_root / "recommender.json").read_text(encoding="utf-8")),
            payload["recommender"],
        )
        self.assertEqual(
            json.loads((artifact_root / "provisioner.json").read_text(encoding="utf-8")),
            payload["provisioner"],
        )
        self.assertEqual(
            json.loads((artifact_root / "history_preview.json").read_text(encoding="utf-8")),
            payload["history"],
        )
        self.assertEqual(
            json.loads((artifact_root / "dry_run_output.json").read_text(encoding="utf-8")),
            {
                "run_context": payload["run_context"],
                "detector": payload["detector"],
                "recommender": payload["recommender"],
                "provisioner": payload["provisioner"],
                "history": payload["history"],
                "credential": payload["credential"],
                "runtime": {
                    "retiring_model": None,
                    "retiring_version": None,
                    "discover_from_azure": False,
                    "live_catalog": False,
                    "provision_candidates": False,
                    "run_evals": False,
                    "top_k": 3,
                    "safety": {
                        "provision_candidates": False,
                        "run_evals": False,
                        "mode": "dry-run",
                    },
                },
            },
        )

    def test_given_staged_output_when_reading_summary_then_manifest_advertised_files_are_exact_and_history_is_coherent(self) -> None:
        # Arrange
        artifact_root = REPO_ROOT / "artifacts" / "test-run"

        # Act
        result = execute_dry_run(REPO_ROOT, run_id="test-run")
        payload = result.to_dict()
        summary_payload = json.loads((artifact_root / "dry_run_output.json").read_text(encoding="utf-8"))
        history_payload = json.loads((artifact_root / "history_preview.json").read_text(encoding="utf-8"))
        staged_files = sorted(path.name for path in artifact_root.iterdir() if path.is_file())
        manifest_relative_paths = sorted(
            Path(manifest["relative_path"]).as_posix() for manifest in history_payload["manifests"]
        )
        manifest_filenames = sorted(Path(relative_path).name for relative_path in manifest_relative_paths)

        # Assert
        self.assertEqual(
            sorted(payload["staging"]["files"]),
            sorted(f"artifacts/test-run/{name}" for name in staged_files),
        )
        self.assertEqual(
            manifest_relative_paths,
            [
                "artifacts/test-run/detector.json",
                "artifacts/test-run/provisioner.json",
                "artifacts/test-run/recommender.json",
            ],
        )
        self.assertEqual(
            staged_files,
            sorted(manifest_filenames + ["dry_run_output.json", "history_preview.json"]),
        )
        self.assertEqual(history_payload, summary_payload["history"])
        self.assertEqual(history_payload, payload["history"])
        self.assertEqual(summary_payload["run_context"], payload["run_context"])
        self.assertEqual(summary_payload["detector"], json.loads((artifact_root / "detector.json").read_text(encoding="utf-8")))
        self.assertEqual(
            summary_payload["recommender"],
            json.loads((artifact_root / "recommender.json").read_text(encoding="utf-8")),
        )
        self.assertEqual(
            summary_payload["provisioner"],
            json.loads((artifact_root / "provisioner.json").read_text(encoding="utf-8")),
        )


class OrchestratorCliTests(unittest.TestCase):
    def test_given_new_flags_when_parsing_then_runtime_options_are_supported(self) -> None:
        # Arrange
        parser = create_parser()

        # Act
        args = parser.parse_args(
            [
                "--retiring-model",
                "gpt-4.1-mini",
                "--retiring-version",
                "2025-04-14",
                "--discover-from-azure",
                "--live-catalog",
                "--provision-candidates",
                "--run-evals",
                "--top-k",
                "2",
            ]
        )

        # Assert
        self.assertEqual(args.retiring_model, "gpt-4.1-mini")
        self.assertEqual(args.retiring_version, "2025-04-14")
        self.assertTrue(args.discover_from_azure)
        self.assertTrue(args.live_catalog)
        self.assertTrue(args.provision_candidates)
        self.assertTrue(args.run_evals)
        self.assertEqual(args.top_k, 2)

    @patch("src.orchestrator.cli.execute_dry_run")
    def test_given_run_evals_without_provision_when_main_then_exits_with_config_error(self, mock_execute) -> None:
        # Arrange
        mock_execute.side_effect = Exception("--run-evals requires --provision-candidates to be enabled.")

        # Act
        with patch("sys.argv", ["prog", "--run-evals"]):
            exit_code = main()

        # Assert
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()