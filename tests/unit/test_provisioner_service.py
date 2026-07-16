"""Unit tests for local provisioner request shaping."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.provisioner.deployment_plan import build_idempotency_key, build_required_tags
from src.provisioner.service import plan_provisioning
from src.shared.config import load_app_config
from src.shared.contracts import Candidate, CandidateRank, RetiringTarget
from src.shared.run_context import build_run_context


REPO_ROOT = Path(__file__).resolve().parents[2]


class ProvisionerServiceTests(unittest.TestCase):
    def test_given_same_inputs_when_building_idempotency_key_then_key_is_stable(self) -> None:
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
        ranked_candidate = CandidateRank(
            candidate=Candidate(
                model_id="gpt-4.1",
                version="2026-01-12",
                region="swedencentral",
                deployment_types=["DataZoneStandard"],
            ),
            score=0.99,
            rationale=["fixture"],
        )

        # Act
        left = build_idempotency_key(run_context, target, ranked_candidate)
        right = build_idempotency_key(run_context, target, ranked_candidate)

        # Assert
        self.assertEqual(left, right)
        self.assertEqual(len(left), 64)

    def test_given_config_when_planning_then_requests_include_required_tags(self) -> None:
        # Arrange
        config = load_app_config(REPO_ROOT)
        run_context = build_run_context(config, run_id="test-run")
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

        # Act
        result = plan_provisioning(config, run_context, target, ranked_candidates)
        tags = build_required_tags(config, run_context)

        # Assert
        self.assertEqual(len(result.provision_requests), 1)
        self.assertEqual(result.provision_requests[0].tags, tags)
        self.assertEqual(result.provision_requests[0].tags["taskGroup"], "tg4")
        self.assertEqual(result.provision_requests[0].tags["managedBy"], "model-upgrade-automation")


if __name__ == "__main__":
    unittest.main()
