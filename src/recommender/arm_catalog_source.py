"""Live candidate catalog source backed by the Azure ARM Models API.

Authenticated ARM reads are performed through the Azure CLI (``az rest``) so
credentials come from the operator's existing ``az login`` / OIDC context,
mirroring :mod:`src.detector.deployed_introspector`. Only generally available,
chat-capable models are surfaced as replacement candidates; deprecating,
deprecated, preview, and non-chat (embeddings/audio/image) models are skipped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json

from src.recommender.models import CatalogCandidate
from src.shared.az_cli import run_az
from src.shared.errors import DependencyUnavailableError

ARM_MODELS_URL_TEMPLATE = (
    "https://management.azure.com/subscriptions/{subscription_id}"
    "/providers/Microsoft.CognitiveServices/locations/{location}/models"
    "?api-version={api_version}"
)

_AVAILABLE_LIFECYCLE_STATUSES = {"GenerallyAvailable", "Stable"}


@dataclass(slots=True)
class ArmModelsCatalogSource:
    """Load replacement candidates from the Azure ARM Models API via ``az rest``."""

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

    def _to_candidate(self, entry: dict, location: str) -> CatalogCandidate | None:
        model = entry.get("model") or {}
        name = model.get("name")
        version = model.get("version")
        if not isinstance(name, str) or not name:
            return None

        lifecycle = model.get("lifecycleStatus")
        if lifecycle not in _AVAILABLE_LIFECYCLE_STATUSES:
            return None

        # Chat-capability gate: only surface general-purpose chat completion
        # models. GA embeddings/audio/image models expose other capability keys
        # (e.g. ``embeddings``, ``audio``) and are not valid successors for the
        # general_qa workload. The ARM API reports capability flags as strings.
        capabilities = model.get("capabilities") or {}
        chat_flag = capabilities.get("chatCompletion")
        if not isinstance(chat_flag, str) or chat_flag.lower() != "true":
            return None

        deployment_types = [
            str(sku["name"])
            for sku in (model.get("skus") or [])
            if isinstance(sku, dict) and sku.get("name")
        ]

        return CatalogCandidate(
            model_id=name,
            version=str(version) if version is not None else "unspecified",
            region=location,
            deployment_types=deployment_types,
            workloads=["general_qa"],
            # Empty families admit every chat-capable GA model as a potential
            # successor for any retiring target; quality/safety/cost ranking
            # decides ordering rather than a hardcoded family allowlist.
            replacement_families=[],
            # quality_score/safety_score are heuristic placeholders pending a
            # real benchmark/eval source; they are intentionally uniform so as
            # not to imply fabricated per-model quality differences.
            quality_score=0.9,
            safety_score=0.9,
            cost_score=0.8,
        )

    def load(self) -> list[CatalogCandidate]:
        """Load generally available candidates across all configured locations."""

        deduped: dict[tuple[str, str, str], CatalogCandidate] = {}
        for location in self.locations:
            for entry in self._fetch_location(location):
                if not isinstance(entry, dict):
                    continue
                candidate = self._to_candidate(entry, location)
                if candidate is None:
                    continue
                key = (candidate.model_id, candidate.version, candidate.region)
                deduped.setdefault(key, candidate)

        if not deduped:
            raise DependencyUnavailableError(
                "ARM Models API returned no generally available candidates across "
                f"locations {self.locations!r}. Verify subscription access and "
                f"api-version '{self.api_version}'."
            )
        return list(deduped.values())
