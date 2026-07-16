"""Provisioner service for local dry-run request shaping."""

from __future__ import annotations

from src.provisioner.deployment_plan import build_provision_request, build_teardown_plan
from src.provisioner.models import ProvisionPlanResult
from src.shared.config import AppConfig
from src.shared.contracts import CandidateRank, RetiringTarget
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
