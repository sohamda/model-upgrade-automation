"""Retirement signal source abstraction for local and future live inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import yaml

from src.shared.contracts import RetiringModel


class RetirementSource(Protocol):
    """Source abstraction for retirement signal loading."""

    def load(self) -> list[RetiringModel]:
        """Load retirement entries from the backing source."""


@dataclass(slots=True)
class FixtureRetirementSource:
    """Load retirement signals from a YAML fixture file."""

    fixture_path: Path

    def load(self) -> list[RetiringModel]:
        with self.fixture_path.open("r", encoding="utf-8") as handle:
            raw_data = yaml.safe_load(handle) or {}
        items = raw_data.get("retiring_models", [])
        models: list[RetiringModel] = []
        for item in items:
            models.append(
                RetiringModel(
                    model_id=str(item["model_id"]),
                    current_version=str(item["current_version"]),
                    retirement_date=str(item["retirement_date"]),
                    replacement_family=(
                        str(item["replacement_family"])
                        if item.get("replacement_family")
                        else None
                    ),
                    source=str(item.get("source", "fixture")),
                )
            )
        return models


def build_default_fixture(repo_root: Path) -> FixtureRetirementSource:
    """Return the default fixture source for local dry runs."""

    return FixtureRetirementSource(repo_root / "tests" / "fixtures" / "retirement_signals.yaml")


def days_until(date_text: str, *, reference: datetime | None = None) -> int:
    """Compute whole-day retirement horizon from an ISO date string."""

    reference_time = reference or datetime.now(timezone.utc)
    retirement_date = datetime.fromisoformat(date_text).replace(tzinfo=timezone.utc)
    delta = retirement_date - reference_time
    return delta.days
