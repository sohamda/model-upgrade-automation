"""Recommender service orchestration."""

from __future__ import annotations

from src.recommender.catalog import CandidateCatalog
from src.recommender.filters import filter_candidates
from src.recommender.models import RecommenderResult
from src.recommender.pricing_enrichment import enrich_cost_scores
from src.recommender.pricing_source import RetailPricesClient
from src.recommender.scorer import score_candidate, validate_weights
from src.shared.config import AppConfig
from src.shared.contracts import RetiringTarget
from src.shared.errors import ConfigurationError
from src.shared.run_context import RunContext


def recommend_candidates(
    config: AppConfig,
    run_context: RunContext,
    target: RetiringTarget,
    catalog: CandidateCatalog,
    price_client: RetailPricesClient | None = None,
) -> RecommenderResult:
    """Return stable candidate ranking for a retiring target.

    When ``price_client`` is provided, candidate cost scores are enriched with
    real per-token price deltas before scoring; pricing failures degrade to the
    static ``cost_score`` and surface as parse warnings. Omitting the client
    preserves the prior static-catalog behavior.
    """

    try:
        validate_weights(config)
    except ValueError as error:
        raise ConfigurationError(str(error)) from error

    candidates = filter_candidates(target, catalog.load(), config, run_context)

    pricing_warnings: list[str] = []
    if price_client is not None:
        candidates, pricing_warnings = enrich_cost_scores(
            target, candidates, price_client
        )

    ranked = [score_candidate(target, item, config) for item in candidates]
    ranked.sort(
        key=lambda item: (
            -item.score,
            item.candidate.model_id,
            item.candidate.version,
            item.candidate.region,
        )
    )

    limit = config.evaluation.candidates_per_retiring_model
    result = RecommenderResult(
        ranked_candidates=ranked[:limit],
        parse_warnings=list(pricing_warnings),
    )
    if not ranked:
        result.parse_warnings.append(
            f"No candidates matched retiring target {target.model_id}@{target.current_version}."
        )
    return result
