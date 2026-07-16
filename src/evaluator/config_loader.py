"""Evaluator config helpers derived from shared application config."""

from __future__ import annotations

from pathlib import Path

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