"""Unit tests for recommender hard filters."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.recommender.filters import filter_candidates
from src.recommender.models import CatalogCandidate
from src.shared.config import load_app_config
from src.shared.contracts import RetiringTarget
from src.shared.run_context import build_run_context


REPO_ROOT = Path(__file__).resolve().parents[2]
HERMETIC_REPO = REPO_ROOT / "tests" / "fixtures" / "hermetic_repo"


class FilterCandidatesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_app_config(HERMETIC_REPO)
        self.run_context = build_run_context(self.config, run_id="test-run")
        self.deployment_type = self.run_context.deployment_type

    def _target(self, model_id: str, version: str) -> RetiringTarget:
        return RetiringTarget(
            model_id=model_id,
            current_version=version,
            region="swedencentral",
            workload="general_qa",
            retirement_date="2026-08-15",
            days_until_retirement=31,
            source="fixture",
            replacement_family="gpt-4.1",
        )

    def _candidate(self, model_id: str, version: str) -> CatalogCandidate:
        return CatalogCandidate(
            model_id=model_id,
            version=version,
            region="swedencentral",
            deployment_types=[self.deployment_type],
            workloads=["general_qa"],
            replacement_families=[],
        )

    def test_given_candidate_identical_to_target_when_filtering_then_excluded(self) -> None:
        # Arrange: same model_id and version is not a migration.
        target = self._target("gpt-4o", "2024-05-13")
        candidates = [
            self._candidate("gpt-4o", "2024-05-13"),
            self._candidate("gpt-4o", "2024-11-20"),
        ]

        # Act
        result = filter_candidates(target, candidates, self.config, self.run_context)

        # Assert: identical self excluded; newer version of same family kept.
        result_keys = {(item.model_id, item.version) for item in result}
        self.assertNotIn(("gpt-4o", "2024-05-13"), result_keys)
        self.assertIn(("gpt-4o", "2024-11-20"), result_keys)

    def test_given_empty_families_candidate_for_gpt4o_target_when_filtering_then_passes(self) -> None:
        # Arrange: a different GA chat model with empty families must pass even
        # though the target is gpt-4o (arbitrary retiring model support).
        target = self._target("gpt-4o", "2024-05-13")
        candidates = [self._candidate("gpt-4.1", "2026-01-12")]

        # Act
        result = filter_candidates(target, candidates, self.config, self.run_context)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model_id, "gpt-4.1")


if __name__ == "__main__":
    unittest.main()
