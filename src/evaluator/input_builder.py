"""Build evaluator work items from TG4 staged dry-run artifacts."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from src.evaluator.models import EvaluatorConfig, EvaluatorWorkItem
from src.shared.contracts import DeploymentRef, SkipIndexKey, TeardownPlan
from src.shared.errors import ContractError
from src.shared.run_context import RunContext


REQUIRED_MANIFEST_TYPES = {
    "detector-preview",
    "recommender-preview",
    "provisioner-preview",
}


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ContractError(f"Required evaluator input is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ContractError(f"Malformed JSON payload: {path}") from error


def _build_run_context(payload: dict[str, object]) -> RunContext:
    try:
        started_at = str(payload["started_at_utc"])
        return RunContext(
            run_id=str(payload["run_id"]),
            trigger_type=str(payload["trigger_type"]),
            started_at_utc=datetime.fromisoformat(started_at),
            github_repo=str(payload["github_repo"]),
            github_run_id=str(payload["github_run_id"]),
            azure_tenant_id=str(payload["azure_tenant_id"]),
            azure_subscription_id=str(payload["azure_subscription_id"]),
            resource_group=str(payload["resource_group"]),
            foundry_account_name=str(payload["foundry_account_name"]),
            foundry_project_name=str(payload["foundry_project_name"]),
            aca_environment_name=str(payload["aca_environment_name"]),
            aca_job_name=str(payload["aca_job_name"]),
            storage_account_name=str(payload["storage_account_name"]),
            key_vault_name=str(payload["key_vault_name"]),
            deployment_type=str(payload["deployment_type"]),
            allowed_regions=[str(item) for item in payload["allowed_regions"]],
            retirement_horizon_days=int(payload["retirement_horizon_days"]),
            dataset_sha256=str(payload["dataset_sha256"]),
            correlation_version=str(payload["correlation_version"]),
        )
    except KeyError as error:
        raise ContractError(f"Run context is missing required field: {error.args[0]}") from error
    except (TypeError, ValueError) as error:
        raise ContractError("Run context payload is malformed.") from error


def _candidate_slug(candidate_model_id: str, candidate_version: str) -> str:
    return f"{candidate_model_id}-{candidate_version}".replace(".", "-")


def _index_skip_keys(history_payload: dict[str, object]) -> dict[tuple[str, str], SkipIndexKey]:
    keys = history_payload.get("skip_index_keys")
    if not isinstance(keys, list):
        raise ContractError("history_preview.json must contain a skip_index_keys list.")

    indexed: dict[tuple[str, str], SkipIndexKey] = {}
    for raw_key in keys:
        if not isinstance(raw_key, dict):
            raise ContractError("Skip-index entries must be mappings.")
        key = SkipIndexKey(
            model_id=str(raw_key["model_id"]),
            version=str(raw_key["version"]),
            dataset_sha256=str(raw_key["dataset_sha256"]),
            candidate_model_id=str(raw_key["candidate_model_id"]),
            candidate_version=str(raw_key["candidate_version"]),
        )
        indexed[(key.candidate_model_id, key.candidate_version)] = key
    return indexed


def _manifest_paths(repo_root: Path, history_payload: dict[str, object]) -> dict[str, Path]:
    manifests = history_payload.get("manifests")
    if not isinstance(manifests, list):
        raise ContractError("history_preview.json must contain a manifests list.")

    paths: dict[str, Path] = {}
    for manifest in manifests:
        if not isinstance(manifest, dict):
            raise ContractError("Manifest entries must be mappings.")
        try:
            artifact_type = str(manifest["artifact_type"])
            relative_path = str(manifest["relative_path"])
        except KeyError as error:
            raise ContractError(
                f"Manifest entry is missing required field: {error.args[0]}"
            ) from error
        paths[artifact_type] = repo_root / relative_path

    missing = REQUIRED_MANIFEST_TYPES.difference(paths)
    if missing:
        raise ContractError(
            f"history_preview.json is missing required manifest types: {sorted(missing)}"
        )

    return paths


def build_work_items_from_artifacts(
    repo_root: Path,
    artifact_root: Path,
    evaluator_config: EvaluatorConfig,
    dataset_path: Path,
) -> list[EvaluatorWorkItem]:
    """Load TG4 staged artifacts and create deterministic evaluator work items."""

    summary_payload = _read_json(artifact_root / "dry_run_output.json")
    history_payload = _read_json(artifact_root / "history_preview.json")
    run_context = _build_run_context(summary_payload["run_context"])
    manifest_paths = _manifest_paths(repo_root, history_payload)
    skip_keys = _index_skip_keys(history_payload)

    plans = summary_payload.get("provisioner", {}).get("plans")
    if not isinstance(plans, list) or not plans:
        raise ContractError("dry_run_output.json must contain at least one provisioner plan.")

    work_items: list[EvaluatorWorkItem] = []
    for plan in plans:
        if not isinstance(plan, dict):
            raise ContractError("Provisioner plans must be mappings.")

        target = plan.get("retiring_target")
        requests = plan.get("provision_requests")
        teardowns = plan.get("teardown_plans")
        if not isinstance(target, dict) or not isinstance(requests, list) or not isinstance(teardowns, list):
            raise ContractError("Provisioner plans must include target, provision_requests, and teardown_plans.")
        if len(requests) != len(teardowns):
            raise ContractError("Provisioner plan has mismatched provision and teardown counts.")

        rationale_map: dict[tuple[str, str], tuple[float, list[str]]] = {}
        recommendations = summary_payload.get("recommender", {}).get("recommendations")
        if not isinstance(recommendations, list):
            raise ContractError("dry_run_output.json must contain recommender recommendations.")
        for recommendation in recommendations:
            if not isinstance(recommendation, dict):
                continue
            retiring_target = recommendation.get("retiring_target")
            if retiring_target != target:
                continue
            ranked_candidates = recommendation.get("ranked_candidates")
            if not isinstance(ranked_candidates, list):
                continue
            for ranked_candidate in ranked_candidates:
                candidate = ranked_candidate.get("candidate")
                if not isinstance(candidate, dict):
                    continue
                rationale_map[(str(candidate["model_id"]), str(candidate["version"]))] = (
                    float(ranked_candidate["score"]),
                    [str(item) for item in ranked_candidate.get("rationale", [])],
                )

        for request, teardown in zip(requests, teardowns):
            if not isinstance(request, dict) or not isinstance(teardown, dict):
                raise ContractError("Provisioner request and teardown entries must be mappings.")

            candidate_model_id = str(request["candidate_model_id"])
            candidate_version = str(request["candidate_version"])
            key = skip_keys.get((candidate_model_id, candidate_version))
            if key is None:
                raise ContractError(
                    f"No skip-index key found for candidate {candidate_model_id}@{candidate_version}."
                )

            score, rationale = rationale_map.get((candidate_model_id, candidate_version), (0.0, []))
            work_items.append(
                EvaluatorWorkItem(
                    run_context=run_context,
                    retiring_model_id=str(request["retiring_model_id"]),
                    retiring_model_version=str(request["retiring_model_version"]),
                    candidate_model_id=candidate_model_id,
                    candidate_version=candidate_version,
                    candidate_slug=_candidate_slug(candidate_model_id, candidate_version),
                    deployment_ref=DeploymentRef(
                        resource_id=f"dryrun://{request['deployment_name']}",
                        deployment_name=str(request["deployment_name"]),
                        region=str(request["region"]),
                        deployment_type=str(request["deployment_type"]),
                    ),
                    skip_index_key=key,
                    teardown_plan=TeardownPlan(
                        idempotency_key=str(teardown["idempotency_key"]),
                        deployment_name=str(teardown["deployment_name"]),
                        resource_group=str(teardown["resource_group"]),
                        region=str(teardown["region"]),
                        reason=str(teardown["reason"]),
                    ),
                    manifest_paths=dict(manifest_paths),
                    recommendation_rationale=rationale,
                    candidate_score=score,
                    evaluation_config=evaluator_config,
                    dataset_path=dataset_path,
                    dataset_sha256=run_context.dataset_sha256,
                )
            )

    if not work_items:
        raise ContractError("No evaluator work items could be derived from staged artifacts.")

    return work_items