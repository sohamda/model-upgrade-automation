"""Typed contracts for TG6 local-first reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass(slots=True)
class ReporterThresholds:
    """Thresholds derived from candidate summaries."""

    minimum_custom_score: float
    minimum_redteam_block_rate: float


@dataclass(slots=True)
class DatasetHashStatus:
    """Cross-artifact dataset hash validation result."""

    run_context_dataset_sha256: str
    aca_job_dataset_sha256: str
    summary_dataset_sha256: str
    matches_run_context: bool
    matches_aca_job_request: bool
    mismatch_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CandidateArtifacts:
    """Reporter input for one evaluated candidate."""

    candidate_slug: str
    model_id: str
    version: str
    deployment_name: str
    deployment_type: str
    custom_overall: float | None
    redteam_block_rate: float | None
    thresholds: ReporterThresholds
    dataset_hash_status: DatasetHashStatus
    summary_path: Path
    custom_path: Path
    redteam_path: Path
    summary_payload: dict[str, object]
    custom_payload: dict[str, object]
    redteam_payload: dict[str, object]
    recommender_score: float | None = None
    recommender_rank: int | None = None
    recommender_rationale: list[str] = field(default_factory=list)
    # promotion_grade defaults True/advisory defaults False so summaries
    # written before this field existed (or by the default fake path) are
    # read as ordinary promotion-eligible measurements.
    promotion_grade: bool = True
    advisory: bool = False


@dataclass(slots=True)
class RetiringTargetReportInput:
    """Reporter input grouped by retiring model target."""

    model_id: str
    version: str
    region: str
    workload: str
    retirement_date: str
    days_until_retirement: int
    replacement_family: str | None
    artifact_root: Path
    result_root: Path
    history_preview_path: Path
    dry_run_output_path: Path
    candidates: list[CandidateArtifacts] = field(default_factory=list)


@dataclass(slots=True)
class ReporterRunInput:
    """Top-level reporter input for one local run."""

    run_id: str
    dry_run_output_path: Path
    history_preview_path: Path
    targets: list[RetiringTargetReportInput]


@dataclass(slots=True)
class CandidateComparison:
    """Aggregated comparison data for one candidate."""

    candidate_slug: str
    model_id: str
    version: str
    deployment_name: str
    deployment_type: str
    custom_overall: float | None
    redteam_block_rate: float | None
    minimum_safety_score: float
    evaluator_scores: dict[str, float]
    redteam_by_category: dict[str, float]
    thresholds: ReporterThresholds
    dataset_hash_status: DatasetHashStatus
    recommender_score: float | None
    recommender_rank: int | None
    recommender_rationale: list[str] = field(default_factory=list)
    cost_delta_input: float | None = None
    cost_delta_output: float | None = None
    longevity_days: int | None = None
    fallback_notes: list[str] = field(default_factory=list)
    artifact_paths: dict[str, str] = field(default_factory=dict)
    # Carried from CandidateArtifacts (Step 1.9): every live-backed candidate
    # is advisory/non-promotion-grade regardless of whether its measurements
    # are fully scored (RAI HIGH-risk caveat).
    promotion_grade: bool = True
    advisory: bool = False


@dataclass(slots=True)
class RetiringTargetAggregate:
    """Aggregated comparison set for one retiring target."""

    model_id: str
    version: str
    region: str
    workload: str
    retirement_date: str
    days_until_retirement: int
    replacement_family: str | None
    dry_run_output_path: str
    history_preview_path: str
    candidates: list[CandidateComparison]
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CandidateDecision:
    """Decision outcome for one candidate."""

    candidate_slug: str
    model_id: str
    version: str
    verdict: str
    weighted_score: float | None
    rejection_reasons: list[str] = field(default_factory=list)
    advisory_warnings: list[str] = field(default_factory=list)
    tie_break_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RecommendationDecision:
    """Deterministic decision result for a retiring target."""

    model_id: str
    version: str
    hard_safety_threshold: float
    minimum_block_rate: float
    winner: CandidateDecision | None
    ranked_candidates: list[CandidateDecision]
    global_warnings: list[str] = field(default_factory=list)
    scoring_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RenderedReport:
    """Rendered local report plus stable metadata."""

    target_slug: str
    title: str
    content: str
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IssuePayload:
    """Structured local payload for future GitHub issue publication."""

    week_key: str
    title: str
    labels: list[str]
    retiring_model_id: str
    retiring_model_version: str
    winner_candidate_slug: str | None
    summary: str
    warnings: list[str] = field(default_factory=list)
    publication_status: str = "deferred-local-only"


@dataclass(slots=True)
class RemediationPayload:
    """Structured local payload for future remediation PR publication."""

    draft: bool
    enabled_by_config: bool
    labels: list[str]
    target_slug: str
    winner_candidate_slug: str | None
    suggested_parameter_updates: dict[str, str]
    warnings: list[str] = field(default_factory=list)
    publication_status: str = "deferred-local-only"


@dataclass(slots=True)
class ReporterExecutionResult:
    """Run-level local reporter outputs."""

    run_id: str
    output_root: Path
    generated_at: date
    report_paths: list[Path]
    decision_paths: list[Path]
    issue_payload_paths: list[Path]
    remediation_payload_paths: list[Path]
    winners: dict[str, str | None]
    warnings: list[str] = field(default_factory=list)