"""Evaluator-local contracts layered on top of TG4 staged artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.shared.contracts import DeploymentRef, SkipIndexKey, TeardownPlan
from src.shared.run_context import RunContext


@dataclass(slots=True)
class DatasetRecord:
    """Single JSONL dataset row used for local-first evaluation."""

    row_id: str
    prompt: str
    expected_response: str | None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationDataset:
    """Loaded dataset plus stable content hash."""

    path: Path
    dataset_sha256: str
    records: list[DatasetRecord]


@dataclass(slots=True)
class EvaluatorThresholds:
    """Thresholds derived from config/evaluation.yaml."""

    minimum_custom_score: float
    minimum_redteam_block_rate: float


@dataclass(slots=True)
class EvaluatorTimeouts:
    """Timeout values derived from config/evaluation.yaml."""

    orchestration_minutes: int
    cleanup_minutes: int


@dataclass(slots=True)
class EvaluatorConfig:
    """Local evaluator configuration subset."""

    allowed_regions: list[str]
    deployment_type_preferences: list[str]
    thresholds: EvaluatorThresholds
    timeouts: EvaluatorTimeouts


@dataclass(slots=True)
class EvaluatorWorkItem:
    """Executable evaluator unit for one candidate deployment."""

    run_context: RunContext
    retiring_model_id: str
    retiring_model_version: str
    candidate_model_id: str
    candidate_version: str
    candidate_slug: str
    deployment_ref: DeploymentRef
    skip_index_key: SkipIndexKey
    teardown_plan: TeardownPlan
    manifest_paths: dict[str, Path]
    recommendation_rationale: list[str]
    candidate_score: float
    evaluation_config: EvaluatorConfig
    dataset_path: Path
    dataset_sha256: str


@dataclass(slots=True)
class CustomEvaluationResult:
    """Custom evaluator output contract."""

    candidate_slug: str
    dataset_sha256: str
    rows: list[dict[str, object]]
    aggregates: dict[str, float]


@dataclass(slots=True)
class RedTeamEvaluationResult:
    """Red-team output contract."""

    candidate_slug: str
    dataset_sha256: str
    attacks: list[dict[str, object]]
    block_rate: float
    aggregates: dict[str, float]


@dataclass(slots=True)
class CandidateEvaluationArtifacts:
    """All evaluator outputs for a single candidate."""

    candidate_slug: str
    custom: CustomEvaluationResult
    redteam: RedTeamEvaluationResult
    summary: dict[str, object]
