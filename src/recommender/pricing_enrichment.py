"""Real-pricing enrichment of candidate cost scores.

The recommender's cost dimension defaults to a static catalog ``cost_score`` in
``0..1`` (higher is better). This module overlays real per-token price deltas
from the Azure Retail Prices API so cheaper candidates score higher than the
retiring model and more expensive candidates score lower.

Pricing gaps and network failures are non-fatal: any missing price or region
fetch failure degrades to the existing static ``cost_score`` and records a
warning rather than raising. Enrichment is deterministic and side-effect free
beyond the injected :class:`RetailPricesClient`; input candidates are never
mutated in place (a copy is returned via :func:`dataclasses.replace`).
"""

from __future__ import annotations

import dataclasses

from src.recommender.models import CatalogCandidate
from src.recommender.pricing_source import RetailPricesClient
from src.shared.contracts import RetiringTarget
from src.shared.errors import DependencyUnavailableError


def _sku_token(model_id: str) -> str:
    """Derive a skuName search token from a model id.

    Lowercases and replaces hyphens with spaces so that ``gpt-4.1`` becomes the
    substring ``gpt 4.1`` used against Retail Prices ``skuName`` values.
    """

    return model_id.lower().replace("-", " ")


def _input_price(
    model_id: str,
    prices: list[dict],
    client: RetailPricesClient,
) -> float | None:
    """Return the input-token unit price for a model, or ``None`` when unmatched.

    Prefers an input-meter hint by first searching for ``"{token} Inp"`` (the
    Retail Prices input-token skuName convention), then falls back to the bare
    token so a match on any meter for the model still yields a price.
    """

    token = _sku_token(model_id)
    hinted = client.unit_price_for(None, f"{token} Inp", prices)
    if hinted is not None:
        return hinted
    return client.unit_price_for(None, token, prices)


def enrich_cost_scores(
    target: RetiringTarget,
    candidates: list[CatalogCandidate],
    price_client: RetailPricesClient,
) -> tuple[list[CatalogCandidate], list[str]]:
    """Overlay real price deltas onto candidate cost scores.

    Prices are fetched once per region and cached within the call. For each
    candidate with both a retiring price ``p_r > 0`` and a candidate price
    ``p_c`` available::

        delta = (p_r - p_c) / p_r          # positive = candidate cheaper
        cost_score = clamp(0.0, 1.0, 0.5 + 0.5 * delta)

    A missing price on either side leaves the candidate's static ``cost_score``
    unchanged and records a warning. Returns a new list preserving input order.
    """

    warnings: list[str] = []
    price_cache: dict[str, list[dict]] = {}
    fetch_failed: set[str] = set()

    def _prices_for(region: str) -> list[dict] | None:
        if region in price_cache:
            return price_cache[region]
        if region in fetch_failed:
            return None
        try:
            prices = price_client.fetch_prices(region)
        except DependencyUnavailableError as error:
            fetch_failed.add(region)
            warnings.append(f"pricing unavailable for region '{region}': {error}")
            return None
        price_cache[region] = prices
        return prices

    target_prices = _prices_for(target.region)
    retiring_price = (
        _input_price(target.model_id, target_prices, price_client)
        if target_prices is not None
        else None
    )

    enriched: list[CatalogCandidate] = []
    for candidate in candidates:
        prices = _prices_for(candidate.region)
        candidate_price = (
            _input_price(candidate.model_id, prices, price_client)
            if prices is not None
            else None
        )

        if (
            retiring_price is not None
            and retiring_price > 0
            and candidate_price is not None
        ):
            delta = (retiring_price - candidate_price) / retiring_price
            cost_score = min(1.0, max(0.0, 0.5 + 0.5 * delta))
            enriched.append(
                dataclasses.replace(candidate, cost_score=round(cost_score, 6))
            )
        else:
            warnings.append(
                f"pricing not found for {candidate.model_id}; using catalog cost_score"
            )
            enriched.append(dataclasses.replace(candidate))

    return enriched, warnings
