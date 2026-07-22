"""Curated quality/safety benchmark source for recommender enrichment.

Candidates produced from the ARM catalog are catalog entries, not deployed
endpoints, so live per-candidate evaluation is infeasible at recommend time.
This source instead reads a curated, precomputed benchmark file
(``config/quality_safety_benchmarks.yaml``) keyed by ``model_id`` and returns
already-normalized ``0..1`` quality and safety scores.

The runtime import surface is stdlib + :mod:`yaml` only. The benchmark file is
an explicitly-provenanced curated seed, refreshed out-of-band by a future
optional ``[evaluation]`` tool; the recommender only reads the cached file.

Retrieval gaps are non-fatal at the enrichment layer: a missing file, YAML
parse error, malformed score, or unknown ``model_id`` raises
:class:`DependencyUnavailableError` so enrichment can degrade to catalog
placeholder scores and record a warning rather than crashing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.shared.errors import DependencyUnavailableError


@dataclass(slots=True, frozen=True)
class QualitySafetyRecord:
    """A single model's normalized quality/safety benchmark entry."""

    model_id: str
    quality_score: float  # normalized 0..1, higher is better
    safety_score: float  # normalized 0..1, higher is better
    provenance: str
    as_of_date: str


def _validate_score(value: object, *, field_name: str, model_id: str) -> float:
    """Return ``value`` as a float in ``0..1`` or raise ``DependencyUnavailableError``."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DependencyUnavailableError(
            f"Quality/safety benchmark for '{model_id}' has a non-numeric "
            f"{field_name}: {value!r}."
        )
    numeric = float(value)
    if not 0.0 <= numeric <= 1.0:
        raise DependencyUnavailableError(
            f"Quality/safety benchmark for '{model_id}' has {field_name}={numeric} "
            "outside the required 0..1 range."
        )
    return numeric


@dataclass(slots=True)
class QualitySafetyBenchmarkSource:
    """Read curated, precomputed quality/safety scores from a YAML file.

    The file is lazily loaded and cached on first :meth:`fetch_record` call.
    ``region`` is accepted for signature parity with future per-region sources
    but is ignored in this phase; records are keyed by ``model_id`` only.
    """

    data_path: Path
    _cache: dict[str, QualitySafetyRecord] | None = field(
        default=None, init=False, repr=False
    )

    def _load(self) -> dict[str, QualitySafetyRecord]:
        if self._cache is not None:
            return self._cache

        if not self.data_path.exists():
            raise DependencyUnavailableError(
                "Quality/safety benchmark file not found: "
                f"{self.data_path}."
            )
        try:
            with self.data_path.open("r", encoding="utf-8") as handle:
                raw_data = yaml.safe_load(handle) or {}
        except yaml.YAMLError as error:
            raise DependencyUnavailableError(
                f"Quality/safety benchmark file is not valid YAML: {self.data_path}."
            ) from error

        entries = raw_data.get("benchmarks") if isinstance(raw_data, dict) else None
        if not isinstance(entries, list):
            raise DependencyUnavailableError(
                "Quality/safety benchmark file must contain a top-level "
                f"'benchmarks' list: {self.data_path}."
            )

        records: dict[str, QualitySafetyRecord] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            model_id = entry.get("model_id")
            if not isinstance(model_id, str) or not model_id:
                continue
            quality = _validate_score(
                entry.get("quality_score"),
                field_name="quality_score",
                model_id=model_id,
            )
            safety = _validate_score(
                entry.get("safety_score"),
                field_name="safety_score",
                model_id=model_id,
            )
            records[model_id] = QualitySafetyRecord(
                model_id=model_id,
                quality_score=quality,
                safety_score=safety,
                provenance=str(entry.get("provenance", "")),
                as_of_date=str(entry.get("as_of_date", "")),
            )

        self._cache = records
        return records

    def fetch_record(self, model_id: str, region: str) -> QualitySafetyRecord:
        """Return the benchmark record for ``model_id``.

        Raises :class:`DependencyUnavailableError` when the file is missing,
        cannot be parsed, contains a malformed score, or has no entry for the
        requested ``model_id``.
        """

        records = self._load()
        record = records.get(model_id)
        if record is None:
            raise DependencyUnavailableError(
                f"No quality/safety benchmark entry for model '{model_id}'."
            )
        return record
