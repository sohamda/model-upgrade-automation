"""Foundry deployment discovery via Azure CLI for MVP live mode."""

from __future__ import annotations

import json

from src.shared.az_cli import run_az
from src.shared.errors import DependencyUnavailableError
from src.shared.run_context import RunContext


def discover_foundry_deployments(run_context: RunContext) -> list[dict[str, str]]:
    """Discover model deployments from Azure Cognitive Services account."""

    stdout = run_az(
        [
            "cognitiveservices",
            "account",
            "deployment",
            "list",
            "--name",
            run_context.foundry_account_name,
            "--resource-group",
            run_context.resource_group,
            "--output",
            "json",
        ]
    )

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise DependencyUnavailableError(
            "Azure CLI returned invalid JSON while discovering deployments."
        ) from error

    discovered: list[dict[str, str]] = []
    for item in payload:
        properties = item.get("properties", {})
        model = properties.get("model", {})
        model_id = model.get("name") or properties.get("modelName")
        version = model.get("version") or properties.get("modelVersion") or "unspecified"
        if isinstance(model_id, str) and model_id:
            discovered.append(
                {
                    "model_id": model_id,
                    "version": str(version),
                    "deployment_name": str(item.get("name", "")),
                }
            )
    return discovered
