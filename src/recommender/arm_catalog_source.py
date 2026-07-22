"""Live candidate catalog source backed by the Azure ARM Models API.

Authenticated ARM reads are performed through the Azure CLI (``az rest``) so
credentials come from the operator's existing ``az login`` / OIDC context,
mirroring :mod:`src.detector.deployed_introspector`. Only generally available,
chat-capable models are surfaced as replacement candidates; deprecating,
deprecated, preview, and non-chat (embeddings/audio/image/rerank/moderation)
models are skipped.

The chat-capability gate is layered because the ARM ``chatCompletion`` flag is
unreliable for non-OpenAI models. The ARM API also returns multiple rows per
model (differing by ``kind``) with divergent capability sets, so the gate runs
against the union of capabilities across all generally-available rows for a
given (model_id, version, region):

* Layer 1 requires ``chatCompletion == "true"``.
* Layer 2 rejects any model whose capability keys include a known non-chat
  capability (embeddings/audio/image/rerank/moderation).
* Layer 3 rejects models whose name matches a non-chat task family
  (rerank/embedding/media-generation/moderation).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re

from src.recommender.models import CatalogCandidate
from src.shared.az_cli import run_az
from src.shared.errors import DependencyUnavailableError

ARM_MODELS_URL_TEMPLATE = (
    "https://management.azure.com/subscriptions/{subscription_id}"
    "/providers/Microsoft.CognitiveServices/locations/{location}/models"
    "?api-version={api_version}"
)

_AVAILABLE_LIFECYCLE_STATUSES = {"GenerallyAvailable", "Stable"}

# Layer 2: capability keys whose presence (regardless of value) signals a
# non-chat model. Matched case-insensitively against capability KEYS.
_NON_CHAT_CAPABILITIES = frozenset(
    {"embeddings", "audio", "imageGenerations", "rerank", "moderations"}
)
_NON_CHAT_CAPABILITIES_LOWER = frozenset(
    capability.lower() for capability in _NON_CHAT_CAPABILITIES
)

# Layer 3: model-name families that are never general-purpose chat models.
# Intentionally excludes bare ``image``/``audio`` tokens (too broad for
# multimodal chat names); those families are gated via Layer 2 capability keys.
_NON_CHAT_NAME_PATTERN = re.compile(
    r"(rerank|embed|embedding|whisper|tts|text-to-speech|dall-?e|sora|"
    r"vision-embed|moderation|guardrail)",
    re.IGNORECASE,
)


def _capability_truthy(value: object) -> bool:
    """Return True when a capability value reads as an ARM ``"true"`` flag."""

    return isinstance(value, str) and value.lower() == "true"


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

    def _to_candidate(
        self,
        model_id: str,
        version: str,
        location: str,
        capabilities: dict,
        deployment_types: list[str],
    ) -> CatalogCandidate | None:
        """Gate a merged model group and build a candidate, or return None.

        ``capabilities`` is the union of capability dicts across every
        generally-available row for this (model_id, version, location), and
        ``deployment_types`` is the union of ``skus[].name`` across those rows.
        """

        # Case-insensitive view of the merged capability keys.
        lower_capabilities = {
            key.lower(): value
            for key, value in capabilities.items()
            if isinstance(key, str)
        }

        # Layer 1: chat-capability required.
        chat_flag = lower_capabilities.get("chatcompletion")
        if not _capability_truthy(chat_flag):
            return None

        # Layer 2: non-chat capability keys exclude (presence is the signal).
        if _NON_CHAT_CAPABILITIES_LOWER & lower_capabilities.keys():
            return None

        # Layer 3: non-chat model-name families exclude.
        if _NON_CHAT_NAME_PATTERN.search(model_id):
            return None

        return CatalogCandidate(
            model_id=model_id,
            version=version,
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
        """Load generally available candidates across all configured locations.

        Rows failing the lifecycle gate are dropped before merging, so a model
        is eligible only when at least one of its rows is GA/Stable. Surviving
        rows sharing a (model_id, version, region) key are merged (capability
        keys unioned, ``"true"`` flags winning value conflicts; sku names
        unioned) and gated once so a mislabeled row can neither drop a legit
        chat model nor admit a mislabeled non-chat one.
        """

        # merged[key] -> {"capabilities": dict, "deployment_types": list[str]}
        merged: dict[tuple[str, str, str], dict] = {}
        for location in self.locations:
            for entry in self._fetch_location(location):
                if not isinstance(entry, dict):
                    continue
                model = entry.get("model") or {}
                name = model.get("name")
                if not isinstance(name, str) or not name:
                    continue

                # Per-row lifecycle gate: only GA/Stable rows are mergeable.
                if model.get("lifecycleStatus") not in _AVAILABLE_LIFECYCLE_STATUSES:
                    continue

                version = model.get("version")
                version_str = str(version) if version is not None else "unspecified"
                key = (name, version_str, location)
                group = merged.get(key)
                if group is None:
                    group = {"capabilities": {}, "deployment_types": []}
                    merged[key] = group

                # Union capability keys; a truthy flag wins on value conflict.
                capabilities = model.get("capabilities")
                if isinstance(capabilities, dict):
                    group_capabilities = group["capabilities"]
                    for cap_key, cap_value in capabilities.items():
                        existing = group_capabilities.get(cap_key)
                        if existing is None or not _capability_truthy(existing):
                            group_capabilities[cap_key] = cap_value

                # Union sku names, preserving first-seen order.
                deployment_types = group["deployment_types"]
                for sku in model.get("skus") or []:
                    if isinstance(sku, dict) and sku.get("name"):
                        sku_name = str(sku["name"])
                        if sku_name not in deployment_types:
                            deployment_types.append(sku_name)

        deduped: dict[tuple[str, str, str], CatalogCandidate] = {}
        for (model_id, version, region), group in merged.items():
            candidate = self._to_candidate(
                model_id,
                version,
                region,
                group["capabilities"],
                group["deployment_types"],
            )
            if candidate is None:
                continue
            deduped[(model_id, version, region)] = candidate

        if not deduped:
            raise DependencyUnavailableError(
                "ARM Models API returned no generally available candidates across "
                f"locations {self.locations!r}. Verify subscription access and "
                f"api-version '{self.api_version}'."
            )
        return list(deduped.values())
