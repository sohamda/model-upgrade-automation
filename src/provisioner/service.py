"""Provisioner service for local dry-run request shaping."""

from __future__ import annotations

from pathlib import Path
import json

from src.provisioner.deployment_plan import build_provision_request, build_teardown_plan
from src.provisioner.models import ProvisionPlanResult
from src.shared.az_cli import resolve_az, run_az
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

    # Resolve az once up front so a genuinely missing CLI aborts the whole
    # operation (preserving the fallback-to-fixtures contract) instead of being
    # recorded as a per-deployment failure.
    resolve_az()

    operations: list[dict[str, object]] = []
    for request in plan.provision_requests:
        try:
            stdout = run_az(
                [
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
            )
            operations.append(
                {
                    "deployment_name": request.deployment_name,
                    "status": "created",
                    "stdout": stdout.strip(),
                }
            )
        except DependencyUnavailableError as error:
            operations.append(
                {
                    "deployment_name": request.deployment_name,
                    "status": "failed",
                    "stderr": str(error),
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
