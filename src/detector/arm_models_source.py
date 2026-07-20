"""Live retirement signal source backed by the Azure ARM Models API.

Authenticated ARM reads are performed through the Azure CLI (``az rest``) so
that credentials come from the operator's existing ``az login`` / OIDC context,
mirroring :mod:`src.detector.deployed_introspector`. This keeps the runtime free
of heavy Azure SDK dependencies.

The endpoint is the Cognitive Services per-location model catalog:
``GET https://management.azure.com/subscriptions/{sub}/providers/Microsoft.CognitiveServices/locations/{loc}/models``
which reports ``lifecycleStatus`` and ``deprecation`` metadata used to derive
retirement signals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json

from src.shared.az_cli import run_az
from src.shared.contracts import RetiringModel
from src.shared.errors import DependencyUnavailableError

ARM_MODELS_URL_TEMPLATE = (
    "https://management.azure.com/subscriptions/{subscription_id}"
    "/providers/Microsoft.CognitiveServices/locations/{location}/models"
    "?api-version={api_version}"
)

_RETIRING_LIFECYCLE_STATUSES = {"Deprecating", "Deprecated"}


def _date_portion(value: str) -> str:
    """Return the ISO date portion (YYYY-MM-DD) of a date or datetime string."""

    text = value.strip()
    if "T" in text:
        text = text.split("T", 1)[0]
    return text[:10]


@dataclass(slots=True)
class ArmModelsRetirementSource:
    """Load retirement signals from the Azure ARM Models API via ``az rest``."""

    subscription_id: str
    locations: list[str] = field(default_factory=list)
    api_version: str = "2025-06-01"
    timeout_seconds: int = 30

    def _fetch_location(self, location: str) -> list[dict]:
        url = ARM_MODELS_URL_TEMPLATE.format(
            subscription_id=self.subscription_id,
            location=location,
            api_version=self.api_version,
        )
        stdout = run_az(
            [
                "rest",
                "--method",
                "get",
                "--url",
                url,
                "--output",
                "json",
            ],
            timeout=self.timeout_seconds,
        )

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as error:
            raise DependencyUnavailableError(
                "ARM Models API returned invalid JSON for location "
                f"'{location}'."
            ) from error

        value = payload.get("value")
        return value if isinstance(value, list) else []

    def _to_retiring_model(self, entry: dict, source_url: str) -> RetiringModel | None:
        model = entry.get("model") or {}
        name = model.get("name")
        version = model.get("version")
        if not isinstance(name, str) or not name:
            return None

        lifecycle = model.get("lifecycleStatus")
        deprecation = model.get("deprecation") or {}
        inference = deprecation.get("inference")

        is_retiring = lifecycle in _RETIRING_LIFECYCLE_STATUSES or bool(inference)
        if not is_retiring:
            return None

        retirement_date: str | None = None
        if isinstance(inference, str) and inference.strip():
            retirement_date = _date_portion(inference)
        else:
            sku_dates = [
                _date_portion(str(sku["deprecationDate"]))
                for sku in (model.get("skus") or [])
                if isinstance(sku, dict) and sku.get("deprecationDate")
            ]
            if sku_dates:
                retirement_date = min(sku_dates)

        if not retirement_date:
            return None

        return RetiringModel(
            model_id=name,
            current_version=str(version) if version is not None else "unspecified",
            retirement_date=retirement_date,
            replacement_family=None,
            source=source_url,
        )

    def load(self) -> list[RetiringModel]:
        """Load retirement entries across all configured locations."""

        deduped: dict[tuple[str, str], RetiringModel] = {}
        for location in self.locations:
            source_url = ARM_MODELS_URL_TEMPLATE.format(
                subscription_id=self.subscription_id,
                location=location,
                api_version=self.api_version,
            )
            for entry in self._fetch_location(location):
                if not isinstance(entry, dict):
                    continue
                retiring = self._to_retiring_model(entry, source_url)
                if retiring is None:
                    continue
                deduped.setdefault((retiring.model_id, retiring.current_version), retiring)

        if not deduped:
            raise DependencyUnavailableError(
                "ARM Models API returned no retiring models across locations "
                f"{self.locations!r}. Verify subscription access, api-version "
                f"'{self.api_version}', and that Cognitive Services model metadata "
                "is available in these regions."
            )
        return list(deduped.values())
