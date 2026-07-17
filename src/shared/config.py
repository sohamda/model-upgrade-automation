"""Configuration loading for the core pipeline slice."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any

import yaml

from .contracts import WatchedModel
from .errors import ConfigurationError


@dataclass(slots=True)
class EvaluationConfig:
    retirement_horizon_days: int
    candidates_per_retiring_model: int
    deployment_type_preferences: list[str]
    allowed_regions: list[str]
    quality_gates: dict[str, float]
    timeouts: dict[str, int]


@dataclass(slots=True)
class RecommenderConfig:
    weights: dict[str, float]
    hard_filters: dict[str, bool]


@dataclass(slots=True)
class AzureEnvironmentConfig:
    azure_client_id: str
    azure_tenant_id: str
    azure_subscription_id: str
    resource_group: str
    foundry_account_name: str
    foundry_project_name: str
    aca_environment_name: str
    aca_job_name: str
    storage_account_name: str
    key_vault_name: str
    deployment_type: str
    allowed_regions: list[str]
    retirement_horizon_days: int
    candidates_per_retiring_model: int
    enable_auto_pr: bool
    automation_ownership_tag: str
    automation_scope_tag: str
    managed_by_tag: str
    automation_cleanup_tag: str


@dataclass(slots=True)
class AppConfig:
    repo_root: Path
    watch_list: list[WatchedModel]
    evaluation: EvaluationConfig
    recommender: RecommenderConfig
    azure: AzureEnvironmentConfig


@dataclass(slots=True)
class RuntimeOptions:
    """Runtime controls that can override default fixture-only behavior."""

    retiring_model: str | None = None
    retiring_version: str | None = None
    discover_from_azure: bool = False
    live_catalog: bool = False
    provision_candidates: bool = False
    run_evals: bool = False
    top_k: int = 3


def _read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _require_mapping(value: Any, path: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigurationError(f"{path} must parse to a mapping.")
    return value


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _parse_regions(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_env_defaults(env_path: Path) -> dict[str, str]:
    defaults: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        defaults[key.strip()] = value.strip()
    return defaults


def _resolve_env_value(key: str, defaults: dict[str, str], *, fallback: str | None = None) -> str:
    value = os.environ.get(key, defaults.get(key, "")).strip()
    if value:
        return value
    if fallback is not None:
        return fallback
    raise ConfigurationError(f"Missing required environment value: {key}")


def load_app_config(repo_root: Path) -> AppConfig:
    """Load all config surfaces required for the minimal TG4 slice."""

    config_root = repo_root / "config"
    models_path = config_root / "models.yaml"
    evaluation_path = config_root / "evaluation.yaml"
    recommender_path = config_root / "recommender.yaml"
    env_path = config_root / "azure.env.example"

    models_data = _require_mapping(_read_yaml(models_path), models_path)
    evaluation_data = _require_mapping(_read_yaml(evaluation_path), evaluation_path)
    recommender_data = _require_mapping(_read_yaml(recommender_path), recommender_path)
    env_defaults = _load_env_defaults(env_path)

    raw_watch_list = models_data.get("watch_list")
    if not isinstance(raw_watch_list, list) or not raw_watch_list:
        raise ConfigurationError("config/models.yaml must define a non-empty watch_list.")

    watch_list: list[WatchedModel] = []
    for entry in raw_watch_list:
        if not isinstance(entry, dict):
            raise ConfigurationError("Every watch_list entry must be a mapping.")
        watch_list.append(
            WatchedModel(
                model_id=str(entry["model_id"]),
                current_version=str(entry["current_version"]),
                region=str(entry["region"]),
                workload=str(entry["workload"]),
                retirement_horizon_days=(
                    int(entry["retirement_horizon_days"])
                    if "retirement_horizon_days" in entry
                    else None
                ),
            )
        )

    evaluation = EvaluationConfig(
        retirement_horizon_days=int(evaluation_data["retirement_horizon_days"]),
        candidates_per_retiring_model=int(evaluation_data["candidates_per_retiring_model"]),
        deployment_type_preferences=[
            str(item) for item in evaluation_data["deployment_type_preferences"]
        ],
        allowed_regions=[str(item) for item in evaluation_data["allowed_regions"]],
        quality_gates={
            str(key): float(value)
            for key, value in dict(evaluation_data["quality_gates"]).items()
        },
        timeouts={
            str(key): int(value) for key, value in dict(evaluation_data["timeouts"]).items()
        },
    )

    recommender = RecommenderConfig(
        weights={str(key): float(value) for key, value in dict(recommender_data["weights"]).items()},
        hard_filters={
            str(key): bool(value) for key, value in dict(recommender_data["hard_filters"]).items()
        },
    )

    azure = AzureEnvironmentConfig(
        azure_client_id=_resolve_env_value(
            "AZURE_CLIENT_ID", env_defaults, fallback="local-client-id"
        ),
        azure_tenant_id=_resolve_env_value(
            "AZURE_TENANT_ID", env_defaults, fallback="local-tenant-id"
        ),
        azure_subscription_id=_resolve_env_value(
            "AZURE_SUBSCRIPTION_ID", env_defaults, fallback="local-subscription-id"
        ),
        resource_group=_resolve_env_value("RESOURCE_GROUP", env_defaults, fallback="local-rg"),
        foundry_account_name=_resolve_env_value(
            "FOUNDRY_ACCOUNT_NAME", env_defaults, fallback="local-foundry-account"
        ),
        foundry_project_name=_resolve_env_value(
            "FOUNDRY_PROJECT_NAME", env_defaults, fallback="local-foundry-project"
        ),
        aca_environment_name=_resolve_env_value(
            "ACA_ENVIRONMENT_NAME", env_defaults, fallback="local-aca-env"
        ),
        aca_job_name=_resolve_env_value("ACA_JOB_NAME", env_defaults, fallback="local-aca-job"),
        storage_account_name=_resolve_env_value(
            "STORAGE_ACCOUNT_NAME", env_defaults, fallback="localstorageacct"
        ),
        key_vault_name=_resolve_env_value("KEY_VAULT_NAME", env_defaults, fallback="local-kv"),
        deployment_type=_resolve_env_value("DEPLOYMENT_TYPE", env_defaults),
        allowed_regions=_parse_regions(_resolve_env_value("ALLOWED_REGIONS", env_defaults)),
        retirement_horizon_days=int(
            _resolve_env_value("RETIREMENT_HORIZON_DAYS", env_defaults)
        ),
        candidates_per_retiring_model=int(
            _resolve_env_value("CANDIDATES_PER_RETIRING_MODEL", env_defaults)
        ),
        enable_auto_pr=_parse_bool(_resolve_env_value("ENABLE_AUTO_PR", env_defaults)),
        automation_ownership_tag=_resolve_env_value("AUTOMATION_OWNERSHIP_TAG", env_defaults),
        automation_scope_tag=_resolve_env_value("AUTOMATION_SCOPE_TAG", env_defaults),
        managed_by_tag=_resolve_env_value("MANAGED_BY_TAG", env_defaults),
        automation_cleanup_tag=_resolve_env_value("AUTOMATION_CLEANUP_TAG", env_defaults),
    )

    return AppConfig(
        repo_root=repo_root,
        watch_list=watch_list,
        evaluation=evaluation,
        recommender=recommender,
        azure=azure,
    )
