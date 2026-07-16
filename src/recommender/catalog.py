"""Local catalog source abstraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml

from src.recommender.models import CatalogCandidate


class CandidateCatalog(Protocol):
    """Source abstraction for local candidate retrieval."""

    def load(self) -> list[CatalogCandidate]:
        """Return the candidate set to evaluate."""


@dataclass(slots=True)
class FixtureCandidateCatalog:
    """Load candidates from a YAML fixture file."""

    fixture_path: Path

    def load(self) -> list[CatalogCandidate]:
        with self.fixture_path.open("r", encoding="utf-8") as handle:
            raw_data = yaml.safe_load(handle) or {}

        candidates: list[CatalogCandidate] = []
        for item in raw_data.get("candidates", []):
            candidates.append(
                CatalogCandidate(
                    model_id=str(item["model_id"]),
                    version=str(item["version"]),
                    region=str(item["region"]),
                    deployment_types=[str(value) for value in item.get("deployment_types", [])],
                    workloads=[str(value) for value in item.get("workloads", [])],
                    replacement_families=[
                        str(value) for value in item.get("replacement_families", [])
                    ],
                    quality_score=float(item.get("quality_score", 0.0)),
                    safety_score=float(item.get("safety_score", 0.0)),
                    cost_score=float(item.get("cost_score", 0.0)),
                )
            )
        return candidates


def build_default_catalog(repo_root: Path) -> FixtureCandidateCatalog:
    """Return the default local catalog for dry-run execution."""

    return FixtureCandidateCatalog(repo_root / "tests" / "fixtures" / "candidate_catalog.yaml")
