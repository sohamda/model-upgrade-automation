"""Real per-token pricing lookups via the public Azure Retail Prices API.

The Retail Prices API is public and requires no authentication, so it is queried
with the stdlib :mod:`urllib` GET pattern used by the Learn-backed sources.
Results are paginated via ``NextPageLink``; all ``Items`` pages are combined.

Pricing gaps are non-fatal: :meth:`RetailPricesClient.unit_price_for` returns
``None`` when a meter or SKU cannot be matched so that scoring can continue.
Network failures and an empty top-level response raise
:class:`DependencyUnavailableError`.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Final
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.shared.errors import DependencyUnavailableError

RETAIL_PRICES_URL: Final[str] = "https://prices.azure.com/api/retail/prices"


@dataclass(slots=True)
class RetailPricesClient:
    """Fetch and match Azure OpenAI consumption pricing from the Retail Prices API."""

    timeout_seconds: int = 20

    def _fetch_json(self, url: str) -> dict:
        request = Request(url, headers={"User-Agent": "model-upgrade-automation/0.1"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except URLError as error:
            raise DependencyUnavailableError(
                "Failed to fetch Azure Retail Prices. Check network access and URL "
                f"reachability: {url}"
            ) from error
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise DependencyUnavailableError(
                "Azure Retail Prices API returned invalid JSON."
            ) from error
        if not isinstance(payload, dict):
            raise DependencyUnavailableError(
                "Azure Retail Prices API returned an unexpected top-level shape."
            )
        return payload

    def fetch_prices(
        self, region: str, api_version: str = "2023-01-01-preview"
    ) -> list[dict]:
        """Return combined ``Items`` for Azure OpenAI consumption meters in a region."""

        filter_expression = (
            "productName eq 'Azure OpenAI' and priceType eq 'Consumption' "
            f"and armRegionName eq '{region}'"
        )
        url: str | None = (
            f"{RETAIL_PRICES_URL}?api-version={api_version}"
            f"&$filter={quote(filter_expression)}"
        )

        items: list[dict] = []
        first_payload = True
        while url:
            payload = self._fetch_json(url)
            if first_payload and not payload:
                raise DependencyUnavailableError(
                    "Azure Retail Prices API returned an empty response for region "
                    f"'{region}'."
                )
            first_payload = False
            page_items = payload.get("Items")
            if isinstance(page_items, list):
                items.extend(item for item in page_items if isinstance(item, dict))
            next_link = payload.get("NextPageLink")
            url = next_link if isinstance(next_link, str) and next_link else None

        return items

    def unit_price_for(
        self,
        meter_id: str | None,
        sku_name: str | None,
        prices: list[dict],
    ) -> float | None:
        """Return the unit price for a meter/SKU, or ``None`` when unmatched.

        Exact ``meterId`` match is preferred when ``meter_id`` is provided;
        otherwise a case-insensitive substring match on ``skuName`` is used.
        """

        if meter_id:
            for item in prices:
                if item.get("meterId") == meter_id:
                    price = item.get("unitPrice") if item.get("unitPrice") is not None else item.get("retailPrice")
                    if price is not None:
                        return float(price)

        if sku_name:
            needle = sku_name.lower()
            for item in prices:
                candidate_sku = item.get("skuName")
                if isinstance(candidate_sku, str) and needle in candidate_sku.lower():
                    price = item.get("unitPrice") if item.get("unitPrice") is not None else item.get("retailPrice")
                    if price is not None:
                        return float(price)

        return None
