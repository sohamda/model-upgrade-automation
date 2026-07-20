"""Unit tests for real-pricing cost-score enrichment."""

from __future__ import annotations

import unittest

from src.recommender.models import CatalogCandidate
from src.recommender.pricing_enrichment import enrich_cost_scores
from src.recommender.pricing_source import RetailPricesClient
from src.shared.contracts import RetiringTarget
from src.shared.errors import DependencyUnavailableError


def _sku(name: str, price: float) -> dict:
    return {"meterId": name, "skuName": name, "unitPrice": price, "retailPrice": price}


class _FakePriceClient:
    """Region-keyed stub delegating matching to the real substring logic."""

    def __init__(self, prices_by_region: dict[str, list[dict]], failing: set[str] | None = None) -> None:
        self._prices_by_region = prices_by_region
        self._failing = failing or set()
        self._delegate = RetailPricesClient()

    def fetch_prices(self, region: str, api_version: str = "2023-01-01-preview") -> list[dict]:
        if region in self._failing:
            raise DependencyUnavailableError(f"boom for {region}")
        return self._prices_by_region.get(region, [])

    def unit_price_for(self, meter_id, sku_name, prices) -> float | None:
        return self._delegate.unit_price_for(meter_id, sku_name, prices)


def _target(region: str = "eastus") -> RetiringTarget:
    return RetiringTarget(
        model_id="gpt-4.1-mini",
        current_version="2025-04-14",
        region=region,
        workload="general_qa",
        retirement_date="2026-08-15",
        days_until_retirement=31,
        source="fixture",
    )


def _candidate(model_id: str, region: str = "eastus", cost_score: float = 0.4) -> CatalogCandidate:
    return CatalogCandidate(
        model_id=model_id,
        version="2025-05-01",
        region=region,
        deployment_types=["Standard"],
        workloads=["general_qa"],
        cost_score=cost_score,
    )


class EnrichCostScoresTests(unittest.TestCase):
    def test_given_cheaper_candidate_when_enriching_then_cost_score_above_midpoint(self) -> None:
        # Arrange: retiring 0.010, candidate 0.005 (cheaper).
        prices = [_sku("gpt 4.1 mini Inp", 0.010), _sku("gpt 4.1 nano Inp", 0.005)]
        client = _FakePriceClient({"eastus": prices})
        candidates = [_candidate("gpt-4.1-nano")]

        # Act
        enriched, warnings = enrich_cost_scores(_target(), candidates, client)

        # Assert
        self.assertEqual(warnings, [])
        self.assertGreater(enriched[0].cost_score, 0.5)
        self.assertAlmostEqual(enriched[0].cost_score, 0.75, places=6)

    def test_given_pricier_candidate_when_enriching_then_cost_score_below_midpoint(self) -> None:
        # Arrange: retiring 0.010, candidate 0.020 (pricier).
        prices = [_sku("gpt 4.1 mini Inp", 0.010), _sku("gpt 4.1 turbo Inp", 0.020)]
        client = _FakePriceClient({"eastus": prices})
        candidates = [_candidate("gpt-4.1-turbo")]

        # Act
        enriched, warnings = enrich_cost_scores(_target(), candidates, client)

        # Assert
        self.assertEqual(warnings, [])
        self.assertLess(enriched[0].cost_score, 0.5)
        self.assertAlmostEqual(enriched[0].cost_score, 0.0, places=6)

    def test_given_equal_price_when_enriching_then_cost_score_at_midpoint(self) -> None:
        # Arrange: retiring and candidate both 0.010.
        prices = [_sku("gpt 4.1 mini Inp", 0.010), _sku("gpt 4.1 peer Inp", 0.010)]
        client = _FakePriceClient({"eastus": prices})
        candidates = [_candidate("gpt-4.1-peer")]

        # Act
        enriched, warnings = enrich_cost_scores(_target(), candidates, client)

        # Assert
        self.assertEqual(warnings, [])
        self.assertAlmostEqual(enriched[0].cost_score, 0.5, places=6)

    def test_given_missing_candidate_price_when_enriching_then_keeps_static_and_warns(self) -> None:
        # Arrange: retiring priced, candidate has no matching sku.
        prices = [_sku("gpt 4.1 mini Inp", 0.010)]
        client = _FakePriceClient({"eastus": prices})
        candidates = [_candidate("gpt-4.1-unlisted", cost_score=0.37)]

        # Act
        enriched, warnings = enrich_cost_scores(_target(), candidates, client)

        # Assert
        self.assertEqual(enriched[0].cost_score, 0.37)
        self.assertEqual(len(warnings), 1)
        self.assertIn("pricing not found for gpt-4.1-unlisted", warnings[0])

    def test_given_region_fetch_failure_when_enriching_then_warns_and_leaves_candidate(self) -> None:
        # Arrange: candidate region fetch raises; retiring region succeeds.
        prices = {"eastus": [_sku("gpt 4.1 mini Inp", 0.010)]}
        client = _FakePriceClient(prices, failing={"westus"})
        candidates = [_candidate("gpt-4.1-nano", region="westus", cost_score=0.42)]

        # Act
        enriched, warnings = enrich_cost_scores(_target(), candidates, client)

        # Assert: no exception escaped; candidate cost_score preserved.
        self.assertEqual(enriched[0].cost_score, 0.42)
        self.assertTrue(any("pricing unavailable for region 'westus'" in w for w in warnings))

    def test_given_candidates_when_enriching_then_inputs_are_not_mutated(self) -> None:
        # Arrange
        prices = [_sku("gpt 4.1 mini Inp", 0.010), _sku("gpt 4.1 nano Inp", 0.005)]
        client = _FakePriceClient({"eastus": prices})
        original = _candidate("gpt-4.1-nano", cost_score=0.4)
        candidates = [original]

        # Act
        enriched, _ = enrich_cost_scores(_target(), candidates, client)

        # Assert: original object untouched; a new object returned.
        self.assertEqual(original.cost_score, 0.4)
        self.assertIsNot(enriched[0], original)


if __name__ == "__main__":
    unittest.main()
