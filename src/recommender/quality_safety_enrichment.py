"""Evaluation-driven enrichment of candidate quality and safety scores.

The recommender's quality and safety dimensions default to static catalog
placeholders. This module overlays curated, precomputed benchmark scores from
an injected :class:`QualitySafetyBenchmarkSource` so candidates rank on real
evaluation signal rather than a uniform placeholder.

This is a structural twin of :func:`enrich_cost_scores`: an injected client, a
per-model cache, only :class:`DependencyUnavailableError` caught and downgraded
to a warning, immutable copy-on-return via :func:`dataclasses.replace`, and a
``(candidates, warnings)`` tuple. Input candidates are never mutated and the
function never raises.
"""

from __future__ import annotations

import dataclasses
from typing import Final

from src.recommender.models import CatalogCandidate
from src.recommender.quality_safety_source import (
    QualitySafetyBenchmarkSource,
    QualitySafetyRecord,
)
from src.shared.contracts import RetiringTarget
from src.shared.errors import DependencyUnavailableError

# Sentinel distinguishing "not yet looked up" from a cached "no record" miss.
_SENTINEL: Final[object] = object()


def enrich_quality_safety(
    target: RetiringTarget,
    candidates: list[CatalogCandidate],
    qs_client: QualitySafetyBenchmarkSource,
) -> tuple[list[CatalogCandidate], list[str]]:
    """Overlay curated quality/safety benchmark scores onto candidates.

    Records are fetched once per ``model_id`` and cached within the call. When a
    benchmark record is available, the candidate's ``quality_score`` and
    ``safety_score`` are replaced with the normalized benchmark values. A missing
    record or a dependency failure leaves the candidate's static placeholder
    scores unchanged and records a warning. Returns a new list preserving input
    order; inputs are never mutated.
    """

    warnings: list[str] = []
    cache: dict[str, QualitySafetyRecord | None] = {}
    enriched: list[CatalogCandidate] = []

    for candidate in candidates:
        cached = cache.get(candidate.model_id, _SENTINEL)
        if cached is _SENTINEL:
            try:
                record: QualitySafetyRecord | None = qs_client.fetch_record(
                    candidate.model_id, candidate.region
                )
            except DependencyUnavailableError as error:
                record = None
                warnings.append(
                    f"quality/safety eval unavailable for '{candidate.model_id}': {error}"
                )
            cache[candidate.model_id] = record
        else:
            record = cached

        if record is None:
            warnings.append(
                f"quality/safety not found for {candidate.model_id}; using catalog scores"
            )
            enriched.append(dataclasses.replace(candidate))
            continue

        enriched.append(
            dataclasses.replace(
                candidate,
                quality_score=record.quality_score,
                safety_score=record.safety_score,
            )
        )

    return enriched, warnings
