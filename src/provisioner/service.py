"""Provisioner service for local dry-run request shaping."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess

from src.provisioner.deployment_plan import build_provision_request, build_teardown_plan
from src.provisioner.models import ProvisionPlanResult
from src.shared.config import AppConfig
from src.shared.contracts import CandidateRank, RetiringTarget
from src.shared.errors import DependencyUnavailableError
from src.shared.run_context import RunContext


def plan_provisioning(
    config: AppConfig,
    run_context: RunContext,
    target: RetiringTarget,
    ranked_candidates: list[CandidateRank],
) -> ProvisionPlanResult:
    """Shape provision and teardown plans for ranked candidates."""

    result = ProvisionPlanResult()
    for ranked_candidate in ranked_candidates:
        provision_request = build_provision_request(
            config,
            run_context,
            target,
            ranked_candidate,
        )
        result.provision_requests.append(provision_request)
        result.teardown_plans.append(build_teardown_plan(run_context, provision_request))
    return result


def execute_provisioning_mvp(
    run_context: RunContext,
    plan: ProvisionPlanResult,
    *,
    enabled: bool,
    repo_root: Path,
) -> dict[str, object]:
    """Execute CLI provisioning in MVP mode when explicitly enabled."""

    if not enabled:
        return {"status": "skipped", "reason": "provisioning disabled by safety gate"}

    operations: list[dict[str, object]] = []
    for request in plan.provision_requests:
        command = [
            "az",
            "cognitiveservices",
            "account",
            "deployment",
            "create",
            "--name",
            run_context.foundry_account_name,
            "--resource-group",
            run_context.resource_group,
            "--deployment-name",
            request.deployment_name,
            "--model-name",
            request.candidate_model_id,
            "--model-version",
            request.candidate_version,
            "--model-format",
            "OpenAI",
            "--sku-capacity",
            "1",
            "--sku-name",
            request.deployment_type,
            "--only-show-errors",
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, check=True)
            operations.append(
                {
                    "deployment_name": request.deployment_name,
                    "status": "created",
                    "stdout": completed.stdout.strip(),
                }
            )
        except FileNotFoundError as error:
            raise DependencyUnavailableError("Azure CLI is required for provisioning execution.") from error
        except subprocess.CalledProcessError as error:
            operations.append(
                {
                    "deployment_name": request.deployment_name,
                    "status": "failed",
                    "stderr": error.stderr.strip(),
                }
            )

    teardown_plan = {
        "run_id": run_context.run_id,
        "teardown": [item.deployment_name for item in plan.teardown_plans],
    }
    output_path = repo_root / "artifacts" / run_context.run_id / "teardown-plan.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(teardown_plan, indent=2) + "\n", encoding="utf-8")

    return {
        "status": "completed",
        "operations": operations,
        "teardown_plan": output_path.relative_to(repo_root).as_posix(),
    }
