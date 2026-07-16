"""Internal recommender response models."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.shared.contracts import Candidate, CandidateRank


@dataclass(slots=True)
class CatalogCandidate:
    """Local catalog candidate used for filtering and scoring."""

    model_id: str
    version: str
    region: str
    deployment_types: list[str]
    workloads: list[str]
    replacement_families: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    safety_score: float = 0.0
    cost_score: float = 0.0

    def to_candidate(self) -> Candidate:
        """Convert the catalog shape to the shared candidate contract."""

        return Candidate(
            model_id=self.model_id,
            version=self.version,
            region=self.region,
            deployment_types=list(self.deployment_types),
        )


@dataclass(slots=True)
class RecommenderResult:
    """Ranked candidates and non-fatal filtering warnings."""

    ranked_candidates: list[CandidateRank] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)
