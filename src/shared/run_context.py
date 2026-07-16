"""Run context bootstrap aligned to TG1 and TG3 contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import uuid

from .config import AppConfig
from .contracts import to_serializable_dict


@dataclass(slots=True)
class RunContext:
    """Shared run metadata passed across module boundaries."""

    run_id: str
    trigger_type: str
    started_at_utc: datetime
    github_repo: str
    github_run_id: str
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
    dataset_sha256: str
    correlation_version: str

    def to_dict(self) -> dict[str, object]:
        return to_serializable_dict(self)


def _default_github_repo(repo_root: Path) -> str:
    return os.environ.get("GITHUB_REPOSITORY", repo_root.name)


def _default_trigger_type() -> str:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "workflow_dispatch").strip()
    if event_name == "schedule":
        return "cron"
    return "workflow_dispatch"


def _hash_default_dataset_seed(config: AppConfig) -> str:
    seed = {
        "watch_list": [item.model_id for item in config.watch_list],
        "retirement_horizon_days": config.evaluation.retirement_horizon_days,
        "allowed_regions": config.evaluation.allowed_regions,
    }
    return hashlib.sha256(json.dumps(seed, sort_keys=True).encode("utf-8")).hexdigest()


def build_run_context(
    config: AppConfig,
    *,
    trigger_type: str | None = None,
    run_id: str | None = None,
    dataset_sha256: str | None = None,
) -> RunContext:
    """Build a deterministic local run context from config and environment."""

    started_at = datetime.now(timezone.utc)
    return RunContext(
        run_id=run_id or os.environ.get("RUN_ID", f"local-{uuid.uuid4().hex[:12]}"),
        trigger_type=trigger_type or _default_trigger_type(),
        started_at_utc=started_at,
        github_repo=_default_github_repo(config.repo_root),
        github_run_id=os.environ.get("GITHUB_RUN_ID", "local"),
        azure_tenant_id=config.azure.azure_tenant_id,
        azure_subscription_id=config.azure.azure_subscription_id,
        resource_group=config.azure.resource_group,
        foundry_account_name=config.azure.foundry_account_name,
        foundry_project_name=config.azure.foundry_project_name,
        aca_environment_name=config.azure.aca_environment_name,
        aca_job_name=config.azure.aca_job_name,
        storage_account_name=config.azure.storage_account_name,
        key_vault_name=config.azure.key_vault_name,
        deployment_type=config.azure.deployment_type,
        allowed_regions=list(config.azure.allowed_regions),
        retirement_horizon_days=config.azure.retirement_horizon_days,
        dataset_sha256=dataset_sha256 or _hash_default_dataset_seed(config),
        correlation_version="tg4-slice-2",
    )
