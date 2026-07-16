"""Deterministic candidate scoring."""

from __future__ import annotations

from src.recommender.models import CatalogCandidate
from src.shared.config import AppConfig
from src.shared.contracts import CandidateRank, RetiringTarget


def validate_weights(config: AppConfig) -> None:
    """Ensure scoring weights sum to 1.0 for predictable ranking."""

    weight_sum = sum(config.recommender.weights.values())
    if abs(weight_sum - 1.0) > 1e-9:
        raise ValueError("Recommender weights must sum to 1.0.")


def score_candidate(
    target: RetiringTarget,
    candidate: CatalogCandidate,
    config: AppConfig,
) -> CandidateRank:
    """Score a candidate and capture rationale details."""

    del target
    quality_weight = config.recommender.weights.get("quality", 0.0)
    safety_weight = config.recommender.weights.get("safety", 0.0)
    cost_weight = config.recommender.weights.get("cost", 0.0)
    score = (
        candidate.quality_score * quality_weight
        + candidate.safety_score * safety_weight
        + candidate.cost_score * cost_weight
    )
    rationale = [
        f"quality={candidate.quality_score:.2f}*{quality_weight:.2f}",
        f"safety={candidate.safety_score:.2f}*{safety_weight:.2f}",
        f"cost={candidate.cost_score:.2f}*{cost_weight:.2f}",
    ]
    return CandidateRank(candidate=candidate.to_candidate(), score=round(score, 6), rationale=rationale)
