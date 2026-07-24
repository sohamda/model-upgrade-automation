"""Evaluator config helpers derived from shared application config."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from src.evaluator.models import EvaluatorConfig, EvaluatorThresholds, EvaluatorTimeouts
from src.shared.config import AppConfig, load_app_config


def build_evaluator_config(app_config: AppConfig) -> EvaluatorConfig:
    """Project the shared app config into the evaluator-local subset."""

    return EvaluatorConfig(
        allowed_regions=list(app_config.evaluation.allowed_regions),
        deployment_type_preferences=list(app_config.evaluation.deployment_type_preferences),
        thresholds=EvaluatorThresholds(
            minimum_custom_score=float(
                app_config.evaluation.quality_gates["minimum_custom_score"]
            ),
            minimum_redteam_block_rate=float(
                app_config.evaluation.quality_gates["minimum_redteam_block_rate"]
            ),
        ),
        timeouts=EvaluatorTimeouts(
            orchestration_minutes=int(app_config.evaluation.timeouts["orchestration_minutes"]),
            cleanup_minutes=int(app_config.evaluation.timeouts["cleanup_minutes"]),
        ),
    )


def load_evaluator_config(repo_root: Path) -> EvaluatorConfig:
    """Load evaluator config directly from repository config files."""

    return build_evaluator_config(load_app_config(repo_root))


@dataclass(slots=True)
class RelativeGateConfig:
    """Relative-to-retiring epsilon thresholds (Phase 2 Step 2.3, RAI relative-comparison condition)."""

    quality_epsilon: float
    redteam_epsilon: float


def _read_evaluation_yaml(repo_root: Path) -> dict[str, object]:
    """Return the raw config/evaluation.yaml mapping, or ``{}`` when unreadable.

    Reads the file directly rather than through :class:`AppConfig`/
    :class:`EvaluationConfig`, whose fixed dataclass shape does not carry the
    Phase 2 additive ``relative_gate``/``judge_model_version``/``rubric_version``
    keys. Keeps this addition fully additive and never risks the shared
    config contract consumed elsewhere.
    """

    path = repo_root / "config" / "evaluation.yaml"
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def load_relative_gate_config(repo_root: Path) -> RelativeGateConfig:
    """Load the additive ``relative_gate`` section from config/evaluation.yaml.

    Missing keys default to ``0.0`` epsilon (no additional tolerance beyond
    the absolute ``quality_gates`` floor), never a fabricated positive value.
    """

    relative_gate = _read_evaluation_yaml(repo_root).get("relative_gate")
    relative_gate = relative_gate if isinstance(relative_gate, dict) else {}
    return RelativeGateConfig(
        quality_epsilon=float(relative_gate.get("quality_epsilon", 0.0)),
        redteam_epsilon=float(relative_gate.get("redteam_epsilon", 0.0)),
    )


def load_audit_provenance(repo_root: Path) -> dict[str, str]:
    """Load additive judge/rubric provenance strings for the Step 2.5 audit bundle."""

    data = _read_evaluation_yaml(repo_root)
    return {
        "judge_model_version": str(data.get("judge_model_version", "")),
        "rubric_version": str(data.get("rubric_version", "")),
        "probe_set_version": str(data.get("probe_set_version", "")),
    }