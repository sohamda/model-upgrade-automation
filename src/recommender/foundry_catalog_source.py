"""Live candidate catalog source backed by Microsoft Learn model pages."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Final
from urllib.error import URLError
from urllib.request import Request, urlopen

from src.recommender.models import CatalogCandidate
from src.shared.errors import DependencyUnavailableError

LEARN_MODELS_URL: Final[str] = (
    "https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure"
)


@dataclass(slots=True)
class LearnFoundryCatalogSource:
    """Fetch and parse model catalog from Microsoft Learn."""

    url: str = LEARN_MODELS_URL
    timeout_seconds: int = 20

    def _fetch(self) -> str:
        request = Request(self.url, headers={"User-Agent": "model-upgrade-automation/0.1"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read().decode("utf-8", errors="replace")
        except URLError as error:
            raise DependencyUnavailableError(
                "Failed to fetch live Foundry catalog from Microsoft Learn. "
                f"Check network access and URL reachability: {self.url}"
            ) from error

    def _parse(self, body: str) -> list[CatalogCandidate]:
        candidates: list[CatalogCandidate] = []
        row_pattern = re.compile(
            r"\|\s*(gpt-[^|]+?)\s*\|\s*([^|]+?)\s*\|",
            re.IGNORECASE,
        )
        for model_id, version in row_pattern.findall(body):
            normalized = model_id.strip()
            if not normalized.startswith("gpt-"):
                continue
            candidates.append(
                CatalogCandidate(
                    model_id=normalized,
                    version=version.strip(),
                    region="swedencentral",
                    deployment_types=["DataZoneStandard"],
                    workloads=["general_qa"],
                    replacement_families=["gpt-4.1"],
                    quality_score=0.9,
                    safety_score=0.9,
                    cost_score=0.8,
                )
            )
        if not candidates:
            raise DependencyUnavailableError(
                "Unable to parse live model candidates from Microsoft Learn catalog page."
            )
        return candidates

    def load(self) -> list[CatalogCandidate]:
        """Load live candidate set."""

        return self._parse(self._fetch())
