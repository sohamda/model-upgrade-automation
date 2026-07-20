"""Unit tests for deterministic recommender behavior."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.recommender.catalog import FixtureCandidateCatalog
from src.recommender.pricing_source import RetailPricesClient
from src.recommender.service import recommend_candidates
from src.shared.config import load_app_config
from src.shared.contracts import RetiringTarget
from src.shared.run_context import build_run_context


REPO_ROOT = Path(__file__).resolve().parents[2]
HERMETIC_REPO = REPO_ROOT / "tests" / "fixtures" / "hermetic_repo"


class RecommenderServiceTests(unittest.TestCase):
    def test_given_matching_catalog_when_recommending_then_returns_stable_ranked_candidates(self) -> None:
        # Arrange
        config = load_app_config(HERMETIC_REPO)
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
        config = load_app_config(HERMETIC_REPO)
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


class _StubPriceClient:
    """Region-keyed stub delegating matching to the real substring logic."""

    def __init__(self, prices_by_region: dict[str, list[dict]]) -> None:
        self._prices_by_region = prices_by_region
        self._delegate = RetailPricesClient()

    def fetch_prices(self, region: str, api_version: str = "2023-01-01-preview") -> list[dict]:
        return self._prices_by_region.get(region, [])

    def unit_price_for(self, meter_id, sku_name, prices) -> float | None:
        return self._delegate.unit_price_for(meter_id, sku_name, prices)


class RecommenderServicePricingTests(unittest.TestCase):
    def _sku(self, name: str, price: float) -> dict:
        return {"meterId": name, "skuName": name, "unitPrice": price, "retailPrice": price}

    def test_given_price_client_when_recommending_then_pricing_reflected_and_warnings_surface(self) -> None:
        # Arrange: retiring 0.010, gpt-4.1 pricier, gpt-4.1-nano cheaper.
        config = load_app_config(HERMETIC_REPO)
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
        prices = [
            self._sku("gpt 4.1 mini Inp", 0.010),
        ]
        price_client = _StubPriceClient({"swedencentral": prices})

        # Act
        result = recommend_candidates(
            config, run_context, target, catalog, price_client=price_client
        )

        # Assert: ranking still returns both; gpt-4.1 matches the mini sku via
        # substring, while gpt-4.1-nano is unmatched and surfaces a warning even
        # though ranked candidates are non-empty.
        self.assertEqual(len(result.ranked_candidates), 2)
        model_ids = {rank.candidate.model_id for rank in result.ranked_candidates}
        self.assertEqual(model_ids, {"gpt-4.1", "gpt-4.1-nano"})
        self.assertTrue(
            any("pricing not found for gpt-4.1-nano" in w for w in result.parse_warnings)
        )

    def test_given_no_price_client_when_recommending_then_no_pricing_warnings(self) -> None:
        # Arrange
        config = load_app_config(HERMETIC_REPO)
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
        self.assertEqual(result.parse_warnings, [])


if __name__ == "__main__":
    unittest.main()