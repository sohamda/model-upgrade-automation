"""Unit tests for evaluation-driven quality/safety enrichment."""

from __future__ import annotations

import unittest

from src.recommender.models import CatalogCandidate
from src.recommender.quality_safety_enrichment import enrich_quality_safety
from src.recommender.quality_safety_source import QualitySafetyRecord
from src.shared.contracts import RetiringTarget
from src.shared.errors import DependencyUnavailableError


class _FakeQualitySafetyClient:
    """Structural stub matching the ``fetch_record`` signature."""

    def __init__(
        self,
        records: dict[str, QualitySafetyRecord],
        failing: set[str] | None = None,
    ) -> None:
        self._records = records
        self._failing = failing or set()
        self.calls: list[str] = []

    def fetch_record(self, model_id: str, region: str) -> QualitySafetyRecord:
        self.calls.append(model_id)
        if model_id in self._failing:
            raise DependencyUnavailableError(f"boom for {model_id}")
        record = self._records.get(model_id)
        if record is None:
            raise DependencyUnavailableError(f"no entry for {model_id}")
        return record


def _record(model_id: str, quality: float, safety: float) -> QualitySafetyRecord:
    return QualitySafetyRecord(
        model_id=model_id,
        quality_score=quality,
        safety_score=safety,
        provenance="curated-seed: test",
        as_of_date="2026-07-22",
    )


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


def _candidate(
    model_id: str,
    region: str = "eastus",
    quality: float = 0.0,
    safety: float = 0.0,
) -> CatalogCandidate:
    return CatalogCandidate(
        model_id=model_id,
        version="2025-05-01",
        region=region,
        deployment_types=["Standard"],
        workloads=["general_qa"],
        quality_score=quality,
        safety_score=safety,
    )


class EnrichQualitySafetyTests(unittest.TestCase):
    def test_given_benchmarked_candidate_when_enriching_then_scores_replaced(self) -> None:
        # Arrange
        client = _FakeQualitySafetyClient({"gpt-4.1": _record("gpt-4.1", 0.86, 0.96)})
        candidates = [_candidate("gpt-4.1", quality=0.1, safety=0.2)]

        # Act
        enriched, warnings = enrich_quality_safety(_target(), candidates, client)

        # Assert
        self.assertEqual(warnings, [])
        self.assertAlmostEqual(enriched[0].quality_score, 0.86, places=6)
        self.assertAlmostEqual(enriched[0].safety_score, 0.96, places=6)

    def test_given_missing_record_when_enriching_then_keeps_static_and_warns(self) -> None:
        # Arrange: no record and not in the failing set -> fetch raises "no entry".
        client = _FakeQualitySafetyClient({})
        candidates = [_candidate("gpt-4.1-unlisted", quality=0.33, safety=0.44)]

        # Act
        enriched, warnings = enrich_quality_safety(_target(), candidates, client)

        # Assert: placeholder preserved. The source raises for an unknown model, so
        # enrichment surfaces both the caught "unavailable" warning and the
        # subsequent "not found" degradation, mirroring the pricing twin's
        # two-tier (fetch failure + per-candidate miss) degradation.
        self.assertAlmostEqual(enriched[0].quality_score, 0.33, places=6)
        self.assertAlmostEqual(enriched[0].safety_score, 0.44, places=6)
        self.assertEqual(len(warnings), 2)
        self.assertIn("quality/safety eval unavailable for 'gpt-4.1-unlisted'", warnings[0])
        self.assertIn("quality/safety not found for gpt-4.1-unlisted", warnings[1])

    def test_given_dependency_failure_when_enriching_then_does_not_escape(self) -> None:
        # Arrange
        client = _FakeQualitySafetyClient({}, failing={"gpt-4.1"})
        candidates = [_candidate("gpt-4.1", quality=0.5, safety=0.6)]

        # Act
        enriched, warnings = enrich_quality_safety(_target(), candidates, client)

        # Assert: no exception escaped; originals preserved; warning recorded.
        self.assertAlmostEqual(enriched[0].quality_score, 0.5, places=6)
        self.assertAlmostEqual(enriched[0].safety_score, 0.6, places=6)
        self.assertTrue(
            any("quality/safety eval unavailable for 'gpt-4.1'" in w for w in warnings)
        )

    def test_given_repeated_model_when_enriching_then_fetches_once(self) -> None:
        # Arrange: two candidates share a model_id.
        client = _FakeQualitySafetyClient({"gpt-4.1": _record("gpt-4.1", 0.86, 0.96)})
        candidates = [
            _candidate("gpt-4.1", region="eastus"),
            _candidate("gpt-4.1", region="westus"),
        ]

        # Act
        enriched, warnings = enrich_quality_safety(_target(), candidates, client)

        # Assert: cached after first lookup; order preserved.
        self.assertEqual(client.calls, ["gpt-4.1"])
        self.assertEqual(len(enriched), 2)
        self.assertEqual(warnings, [])

    def test_given_candidates_when_enriching_then_inputs_are_not_mutated(self) -> None:
        # Arrange
        client = _FakeQualitySafetyClient({"gpt-4.1": _record("gpt-4.1", 0.86, 0.96)})
        original = _candidate("gpt-4.1", quality=0.0, safety=0.0)
        candidates = [original]

        # Act
        enriched, _ = enrich_quality_safety(_target(), candidates, client)

        # Assert: original untouched; a new object returned.
        self.assertEqual(original.quality_score, 0.0)
        self.assertEqual(original.safety_score, 0.0)
        self.assertIsNot(enriched[0], original)


if __name__ == "__main__":
    unittest.main()
