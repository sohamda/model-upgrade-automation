"""Hard filters for candidate selection."""

from __future__ import annotations

from src.recommender.models import CatalogCandidate
from src.shared.config import AppConfig
from src.shared.contracts import RetiringTarget
from src.shared.run_context import RunContext


def filter_candidates(
    target: RetiringTarget,
    candidates: list[CatalogCandidate],
    config: AppConfig,
    run_context: RunContext,
) -> list[CatalogCandidate]:
    """Apply config-driven hard filters before scoring."""

    filtered = list(candidates)
    if config.recommender.hard_filters.get("require_same_region", False):
        filtered = [item for item in filtered if item.region == target.region]

    if config.recommender.hard_filters.get("require_supported_deployment_type", False):
        filtered = [
            item for item in filtered if run_context.deployment_type in item.deployment_types
        ]

    filtered = [item for item in filtered if target.workload in item.workloads]
    if target.replacement_family:
        filtered = [
            item
            for item in filtered
            if not item.replacement_families
            or target.replacement_family in item.replacement_families
            or item.model_id == target.replacement_family
        ]

    # Never recommend the retiring model back to itself: the same model_id and
    # version is not a migration. Same-family or newer versions remain eligible.
    filtered = [
        item
        for item in filtered
        if not (item.model_id == target.model_id and item.version == target.current_version)
    ]
    return filtered
