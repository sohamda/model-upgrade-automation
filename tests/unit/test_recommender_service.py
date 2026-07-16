"""Unit tests for deterministic recommender behavior."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.recommender.catalog import FixtureCandidateCatalog
from src.recommender.service import recommend_candidates
from src.shared.config import load_app_config
from src.shared.contracts import RetiringTarget
from src.shared.run_context import build_run_context


REPO_ROOT = Path(__file__).resolve().parents[2]


class RecommenderServiceTests(unittest.TestCase):
    def test_given_matching_catalog_when_recommending_then_returns_stable_ranked_candidates(self) -> None:
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
        catalog = FixtureCandidateCatalog(
            REPO_ROOT / "tests" / "fixtures" / "candidate_catalog.yaml"
        )

        # Act
        result = recommend_candidates(config, run_context, target, catalog)

        # Assert
        self.assertEqual(len(result.ranked_candidates), 2)
        self.assertEqual(result.ranked_candidates[0].candidate.model_id, "gpt-4.1")
        self.assertEqual(result.ranked_candidates[1].candidate.model_id, "gpt-4.1-nano")
        self.assertGreater(result.ranked_candidates[0].score, result.ranked_candidates[1].score)

    def test_given_no_matching_catalog_when_recommending_then_returns_warning(self) -> None:
        # Arrange
        config = load_app_config(REPO_ROOT)
        run_context = build_run_context(config, run_id="test-run")
        target = RetiringTarget(
            model_id="gpt-4.1-mini",
            current_version="2025-04-14",
            region="westus",
            workload="general_qa",
            retirement_date="2026-08-15",
            days_until_retirement=31,
            source="fixture",
            replacement_family="gpt-4.1",
        )
        catalog = FixtureCandidateCatalog(
            REPO_ROOT / "tests" / "fixtures" / "candidate_catalog.yaml"
        )

        # Act
        result = recommend_candidates(config, run_context, target, catalog)

        # Assert
        self.assertEqual(result.ranked_candidates, [])
        self.assertEqual(len(result.parse_warnings), 1)


if __name__ == "__main__":
    unittest.main()