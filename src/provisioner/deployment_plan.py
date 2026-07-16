"""Deterministic helpers for local deployment and teardown planning."""

from __future__ import annotations

import hashlib

from src.shared.config import AppConfig
from src.shared.contracts import CandidateRank, ProvisionRequest, RetiringTarget, TeardownPlan
from src.shared.run_context import RunContext


def build_idempotency_key(
    run_context: RunContext,
    target: RetiringTarget,
    ranked_candidate: CandidateRank,
) -> str:
    """Build a stable idempotency key from run scope and deployment identity."""

    material = "|".join(
        [
            run_context.run_id,
            run_context.dataset_sha256,
            target.model_id,
            target.current_version,
            ranked_candidate.candidate.model_id,
            ranked_candidate.candidate.version,
            ranked_candidate.candidate.region,
            run_context.deployment_type,
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_required_tags(config: AppConfig, run_context: RunContext) -> dict[str, str]:
    """Build the minimum governance tag set required by TG2/TG3 contracts."""

    return {
        "owner": config.azure.automation_ownership_tag,
        "managedBy": config.azure.managed_by_tag,
        "cleanup": config.azure.automation_cleanup_tag,
        "taskGroup": "tg4",
        "workload": "model-upgrade-automation",
        "environment": run_context.trigger_type,
    }


def build_deployment_name(target: RetiringTarget, ranked_candidate: CandidateRank) -> str:
    """Build a filesystem-safe deployment name preview."""

    raw_name = (
        f"tg4-{target.model_id}-{ranked_candidate.candidate.model_id}-"
        f"{ranked_candidate.candidate.version}"
    )
    normalized = raw_name.replace(".", "-").replace("_", "-")
    return normalized[:63]


def build_provision_request(
    config: AppConfig,
    run_context: RunContext,
    target: RetiringTarget,
    ranked_candidate: CandidateRank,
) -> ProvisionRequest:
    """Create a local dry-run deployment request."""

    deployment_name = build_deployment_name(target, ranked_candidate)
    return ProvisionRequest(
        idempotency_key=build_idempotency_key(run_context, target, ranked_candidate),
        run_id=run_context.run_id,
        retiring_model_id=target.model_id,
        retiring_model_version=target.current_version,
        candidate_model_id=ranked_candidate.candidate.model_id,
        candidate_version=ranked_candidate.candidate.version,
        region=ranked_candidate.candidate.region,
        deployment_type=run_context.deployment_type,
        tags=build_required_tags(config, run_context),
        deployment_name=deployment_name,
    )


def build_teardown_plan(
    run_context: RunContext,
    provision_request: ProvisionRequest,
) -> TeardownPlan:
    """Create a matching teardown preview for an ephemeral deployment."""

    return TeardownPlan(
        idempotency_key=provision_request.idempotency_key,
        deployment_name=provision_request.deployment_name,
        resource_group=run_context.resource_group,
        region=provision_request.region,
        reason="ephemeral-candidate-validation",
    )
