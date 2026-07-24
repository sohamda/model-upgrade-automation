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
class ProbeSetRecord:
    """Single adversarial red-team probe row (Phase 2 Step 2.1, Council C11).

    ``canary`` tags a row as ``"poison"`` or ``"discrimination"`` (or ``None``
    for an ordinary probe). Canary rows carry a fixed ``known_response`` and
    ``expected_blocked`` value used by offline canary tests to catch a broken
    scorer/classifier without any live model or Content Safety call.
    """

    row_id: str
    category: str
    prompt: str
    canary: str | None = None
    known_response: str | None = None
    expected_blocked: bool | None = None


@dataclass(slots=True)
class ProbeSet:
    """Loaded adversarial probe set plus stable content hash and version."""

    path: Path
    probe_set_sha256: str
    probe_set_version: str
    records: list[ProbeSetRecord]


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
    # Additive (Phase 2 Step 2.3, RAI relative-comparison condition): the
    # retiring target's own measured scores, supplied by the caller. `None`
    # (the default) means no retiring baseline is available -- the relative
    # gate is then skipped rather than fabricated, and only the absolute
    # quality_gates floor applies.
    retiring_custom_overall: float | None = None
    retiring_redteam_block_rate: float | None = None


@dataclass(slots=True)
class CustomEvaluationResult:
    """Custom evaluator output contract.

    ``aggregates`` values are ``float | None``: a live-backed runner that
    cannot produce a signal reports ``None`` (UNSCORED) rather than
    fabricating a passing or failing score.
    """

    candidate_slug: str
    dataset_sha256: str
    rows: list[dict[str, object]]
    aggregates: dict[str, float | None]


@dataclass(slots=True)
class RedTeamEvaluationResult:
    """Red-team output contract.

    ``block_rate`` and ``aggregates`` values are ``float | None``: a
    live-backed runner that cannot derive an attack-success-rate signal
    reports ``None`` (UNSCORED) rather than a fabricated passing block rate.
    """

    candidate_slug: str
    dataset_sha256: str
    attacks: list[dict[str, object]]
    block_rate: float | None
    aggregates: dict[str, float | None]
    # Live-only degradation signal (review F2): ``True`` when a Content Safety
    # endpoint was configured and the classifier could vote, ``False`` when it
    # was unset (block-judging ran judge-only), ``None`` on the fake/default
    # path where the concept does not apply.
    classifier_available: bool | None = None
    # Live-only runtime canary outcomes (review F3): human-readable mismatch
    # flags emitted when a canary's known reference response resolves to a
    # blocked state other than its ``expected_blocked`` fixture. Empty when all
    # canaries agreed (or on the fake/default path, which does not run them).
    canary_failures: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CandidateEvaluationArtifacts:
    """All evaluator outputs for a single candidate."""

    candidate_slug: str
    custom: CustomEvaluationResult
    redteam: RedTeamEvaluationResult
    summary: dict[str, object]
