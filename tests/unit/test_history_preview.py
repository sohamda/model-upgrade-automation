"""Unit tests for manifest and skip-index preview generation."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.history.manifest_builder import build_history_preview
from src.provisioner.service import plan_provisioning
from src.shared.config import load_app_config
from src.shared.contracts import Candidate, CandidateRank, RetiringTarget, to_serializable_dict
from src.shared.run_context import build_run_context


REPO_ROOT = Path(__file__).resolve().parents[2]


class HistoryPreviewTests(unittest.TestCase):
    def test_given_pipeline_outputs_when_building_preview_then_manifest_contains_expected_fields(self) -> None:
        # Arrange
        config = load_app_config(REPO_ROOT)
        run_context = build_run_context(config, run_id="test-run", dataset_sha256="abc123")
        target = RetiringTarget(
            model_id="gpt-4.1-mini",
            current_version="2025-04-14",
            region="swedencentral",
            workload="general_qa",
            retirement_date="2026-08-15",
            days_until_retirement=31,
            source="fixture",
            replacement_family="gpt-4.1",
        )
        ranked_candidates = [
            CandidateRank(
                candidate=Candidate(
                    model_id="gpt-4.1",
                    version="2026-01-12",
                    region="swedencentral",
                    deployment_types=["DataZoneStandard"],
                ),
                score=0.99,
                rationale=["fixture"],
            )
        ]
        provision_result = plan_provisioning(config, run_context, target, ranked_candidates)

        # Act
        preview = build_history_preview(
            run_context,
            [target],
            [
                {
                    "retiring_target": to_serializable_dict(target),
                    "ranked_candidates": [
                        {
                            "candidate": to_serializable_dict(ranked_candidates[0].candidate),
                            "score": ranked_candidates[0].score,
                            "rationale": list(ranked_candidates[0].rationale),
                        }
                    ],
                    "parse_warnings": [],
                }
            ],
            [
                {
                    "retiring_target": to_serializable_dict(target),
                    "provision_requests": [
                        to_serializable_dict(item) for item in provision_result.provision_requests
                    ],
                    "teardown_plans": [
                        to_serializable_dict(item) for item in provision_result.teardown_plans
                    ],
                }
            ],
        )

        # Assert
        self.assertEqual(len(preview["manifests"]), 3)
        self.assertEqual(preview["manifests"][0]["run_id"], "test-run")
        self.assertEqual(preview["manifests"][0]["dataset_sha256"], "abc123")
        self.assertTrue(preview["manifests"][0]["content_sha256"])
        self.assertEqual(len(preview["skip_index_keys"]), 1)
        self.assertEqual(preview["skip_index_keys"][0]["model_id"], "gpt-4.1-mini")
        self.assertEqual(preview["skip_index_keys"][0]["candidate_model_id"], "gpt-4.1")

    def test_given_preview_when_serialized_then_manifest_relative_paths_match_expected_artifact_contract(self) -> None:
        # Arrange
        config = load_app_config(REPO_ROOT)
        run_context = build_run_context(config, run_id="test-run", dataset_sha256="abc123")
        target = RetiringTarget(
            model_id="gpt-4.1-mini",
            current_version="2025-04-14",
            region="swedencentral",
            workload="general_qa",
            retirement_date="2026-08-15",
            days_until_retirement=31,
            source="fixture",
            replacement_family="gpt-4.1",
        )
        ranked_candidates = [
            CandidateRank(
                candidate=Candidate(
                    model_id="gpt-4.1",
                    version="2026-01-12",
                    region="swedencentral",
                    deployment_types=["DataZoneStandard"],
                ),
                score=0.99,
                rationale=["fixture"],
            )
        ]
        provision_result = plan_provisioning(config, run_context, target, ranked_candidates)
        preview = build_history_preview(
            run_context,
            [target],
            [
                {
                    "retiring_target": to_serializable_dict(target),
                    "ranked_candidates": [
                        {
                            "candidate": to_serializable_dict(ranked_candidates[0].candidate),
                            "score": ranked_candidates[0].score,
                            "rationale": list(ranked_candidates[0].rationale),
                        }
                    ],
                    "parse_warnings": [],
                }
            ],
            [
                {
                    "retiring_target": to_serializable_dict(target),
                    "provision_requests": [
                        to_serializable_dict(item) for item in provision_result.provision_requests
                    ],
                    "teardown_plans": [
                        to_serializable_dict(item) for item in provision_result.teardown_plans
                    ],
                }
            ],
        )

        # Act
        serialized_preview = json.loads(json.dumps(preview))
        manifest_pairs = {
            manifest["artifact_type"]: manifest["relative_path"]
            for manifest in serialized_preview["manifests"]
        }

        # Assert
        self.assertEqual(
            manifest_pairs,
            {
                "detector-preview": "artifacts/test-run/detector.json",
                "recommender-preview": "artifacts/test-run/recommender.json",
                "provisioner-preview": "artifacts/test-run/provisioner.json",
            },
        )
        self.assertTrue(
            all(Path(relative_path).parts[:2] == ("artifacts", "test-run") for relative_path in manifest_pairs.values())
        )


if __name__ == "__main__":
    unittest.main()
