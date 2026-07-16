"""Typed contracts shared across TG4 pipeline modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if is_dataclass(value):
        return {key: _serialize_value(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


@dataclass(slots=True)
class WarningRecord:
    """Non-fatal warning emitted during parsing or normalization."""

    code: str
    message: str
    source: str


@dataclass(slots=True)
class WatchedModel:
    """User-declared model watch entry from config/models.yaml."""

    model_id: str
    current_version: str
    region: str
    workload: str
    retirement_horizon_days: int | None = None


@dataclass(slots=True)
class RetiringModel:
    """Retirement signal emitted by a retirement source."""

    model_id: str
    current_version: str
    retirement_date: str
    replacement_family: str | None = None
    source: str = "fixture"


@dataclass(slots=True)
class RetiringTarget:
    """Intersection of watched models and retirement inputs."""

    model_id: str
    current_version: str
    region: str
    workload: str
    retirement_date: str
    days_until_retirement: int
    source: str
    replacement_family: str | None = None


@dataclass(slots=True)
class Candidate:
    """Placeholder recommendation candidate contract for downstream slices."""

    model_id: str
    version: str
    region: str
    deployment_types: list[str]


@dataclass(slots=True)
class CandidateRank:
    """Ranked candidate contract for downstream recommender work."""

    candidate: Candidate
    score: float
    rationale: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProvisionRequest:
    """Provisioning request contract for downstream provisioner work."""

    idempotency_key: str
    run_id: str
    retiring_model_id: str
    retiring_model_version: str
    candidate_model_id: str
    candidate_version: str
    region: str
    deployment_type: str
    tags: dict[str, str] = field(default_factory=dict)
    deployment_name: str = ""


@dataclass(slots=True)
class DeploymentRef:
    """Deployment reference contract for downstream evaluator work."""

    resource_id: str
    deployment_name: str
    region: str
    deployment_type: str


@dataclass(slots=True)
class ArtifactManifest:
    """History/report artifact manifest contract."""

    run_id: str
    artifact_type: str
    relative_path: str
    created_at_utc: datetime
    dataset_sha256: str
    content_sha256: str


@dataclass(slots=True)
class SkipIndexKey:
    """Composite key contract for history de-duplication."""

    model_id: str
    version: str
    dataset_sha256: str
    candidate_model_id: str
    candidate_version: str


@dataclass(slots=True)
class TeardownPlan:
    """Local teardown plan for ephemeral candidate deployments."""

    idempotency_key: str
    deployment_name: str
    resource_group: str
    region: str
    reason: str


def to_serializable_dict(value: Any) -> dict[str, Any]:
    """Convert a dataclass contract object into JSON-safe primitives."""

    serialized = _serialize_value(value)
    if not isinstance(serialized, dict):
        raise TypeError("Expected a dataclass-like object that serializes to a mapping.")
    return serialized
