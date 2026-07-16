"""Load TG4 and TG5 local artifacts for TG6 reporting."""

from __future__ import annotations

import json
from pathlib import Path

from src.reporter.models import (
    CandidateArtifacts,
    DatasetHashStatus,
    ReporterRunInput,
    ReporterThresholds,
    RetiringTargetReportInput,
)
from src.shared.errors import ContractError


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ContractError(f"Required reporter artifact is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ContractError(f"Reporter artifact is not valid JSON: {path}") from error


def _build_dataset_hash_status(
    run_context_dataset_sha256: str,
    aca_job_dataset_sha256: str,
    summary_dataset_sha256: str,
) -> DatasetHashStatus:
    mismatch_notes: list[str] = []
    matches_run_context = summary_dataset_sha256 == run_context_dataset_sha256
    matches_aca_job_request = summary_dataset_sha256 == aca_job_dataset_sha256
    if not matches_run_context:
        mismatch_notes.append(
            "summary.dataset_sha256 differs from dry_run_output.run_context.dataset_sha256"
        )
    if not matches_aca_job_request:
        mismatch_notes.append(
            "summary.dataset_sha256 differs from summary.aca_job_request.dataset_sha256"
        )
    return DatasetHashStatus(
        run_context_dataset_sha256=run_context_dataset_sha256,
        aca_job_dataset_sha256=aca_job_dataset_sha256,
        summary_dataset_sha256=summary_dataset_sha256,
        matches_run_context=matches_run_context,
        matches_aca_job_request=matches_aca_job_request,
        mismatch_notes=mismatch_notes,
    )


def load_reporter_run_input(repo_root: Path, artifact_root: Path) -> ReporterRunInput:
    """Load TG4 dry-run and TG5 result artifacts for one local reporter run."""

    dry_run_output_path = artifact_root / "dry_run_output.json"
    history_preview_path = artifact_root / "history_preview.json"
    dry_run_output = _read_json(dry_run_output_path)
    _read_json(history_preview_path)

    run_context = dry_run_output.get("run_context")
    if not isinstance(run_context, dict):
        raise ContractError("dry_run_output.json is missing the run_context object.")
    run_id = run_context.get("run_id")
    dataset_sha256 = run_context.get("dataset_sha256")
    if not isinstance(run_id, str) or not run_id:
        raise ContractError("dry_run_output.json is missing run_context.run_id.")
    if not isinstance(dataset_sha256, str) or not dataset_sha256:
        raise ContractError("dry_run_output.json is missing run_context.dataset_sha256.")

    plans = dry_run_output.get("provisioner", {}).get("plans", [])
    recommendation_lookup: dict[tuple[str, str], tuple[int, float, list[str]]] = {}
    recommendations = dry_run_output.get("recommender", {}).get("recommendations", [])
    if isinstance(recommendations, list):
        for recommendation in recommendations:
            if not isinstance(recommendation, dict):
                continue
            ranked_candidates = recommendation.get("ranked_candidates", [])
            if not isinstance(ranked_candidates, list):
                continue
            for index, ranked_candidate in enumerate(ranked_candidates, start=1):
                if not isinstance(ranked_candidate, dict):
                    continue
                candidate = ranked_candidate.get("candidate")
                if not isinstance(candidate, dict):
                    continue
                model_id = candidate.get("model_id")
                version = candidate.get("version")
                if not isinstance(model_id, str) or not isinstance(version, str):
                    continue
                rationale = ranked_candidate.get("rationale")
                recommendation_lookup[(model_id, version)] = (
                    index,
                    float(ranked_candidate.get("score", 0.0)),
                    [str(item) for item in rationale] if isinstance(rationale, list) else [],
                )
    if not isinstance(plans, list) or not plans:
        raise ContractError("dry_run_output.json does not contain any provisioner plans.")

    result_root = repo_root / "results" / run_id
    targets: list[RetiringTargetReportInput] = []
    for plan in plans:
        if not isinstance(plan, dict):
            raise ContractError("Provisioner plans must be JSON objects.")
        retiring_target = plan.get("retiring_target")
        provision_requests = plan.get("provision_requests")
        if not isinstance(retiring_target, dict):
            raise ContractError("Provisioner plan is missing a retiring_target object.")
        if not isinstance(provision_requests, list) or not provision_requests:
            raise ContractError("Provisioner plan is missing provision_requests entries.")

        target = RetiringTargetReportInput(
            model_id=str(retiring_target["model_id"]),
            version=str(retiring_target["current_version"]),
            region=str(retiring_target["region"]),
            workload=str(retiring_target["workload"]),
            retirement_date=str(retiring_target["retirement_date"]),
            days_until_retirement=int(retiring_target["days_until_retirement"]),
            replacement_family=(
                str(retiring_target["replacement_family"])
                if retiring_target.get("replacement_family") is not None
                else None
            ),
            artifact_root=artifact_root,
            result_root=result_root,
            history_preview_path=history_preview_path,
            dry_run_output_path=dry_run_output_path,
        )

        for request in provision_requests:
            if not isinstance(request, dict):
                raise ContractError("Provision request entries must be JSON objects.")
            candidate_slug = (
                f"{str(request['candidate_model_id']).replace('.', '-')}-"
                f"{str(request['candidate_version'])}"
            )
            candidate_root = result_root / candidate_slug
            summary_path = candidate_root / "summary.json"
            custom_path = candidate_root / "custom.json"
            redteam_path = candidate_root / "redteam.json"
            summary_payload = _read_json(summary_path)
            custom_payload = _read_json(custom_path)
            redteam_payload = _read_json(redteam_path)

            aca_job_request = summary_payload.get("aca_job_request")
            thresholds = summary_payload.get("thresholds")
            candidate_model = summary_payload.get("candidate_model")
            if not isinstance(aca_job_request, dict):
                raise ContractError(f"Summary is missing aca_job_request: {summary_path}")
            if not isinstance(thresholds, dict):
                raise ContractError(f"Summary is missing thresholds: {summary_path}")
            if not isinstance(candidate_model, dict):
                raise ContractError(f"Summary is missing candidate_model: {summary_path}")
            recommendation = recommendation_lookup.get(
                (str(candidate_model["model_id"]), str(candidate_model["version"]))
            )

            target.candidates.append(
                CandidateArtifacts(
                    candidate_slug=str(summary_payload["candidate_slug"]),
                    model_id=str(candidate_model["model_id"]),
                    version=str(candidate_model["version"]),
                    deployment_name=str(candidate_model["deployment_name"]),
                    deployment_type=str(candidate_model["deployment_type"]),
                    custom_overall=float(summary_payload["custom_overall"]),
                    redteam_block_rate=float(summary_payload["redteam_block_rate"]),
                    recommender_score=recommendation[1] if recommendation is not None else None,
                    recommender_rank=recommendation[0] if recommendation is not None else None,
                    recommender_rationale=recommendation[2] if recommendation is not None else [],
                    thresholds=ReporterThresholds(
                        minimum_custom_score=float(thresholds["minimum_custom_score"]),
                        minimum_redteam_block_rate=float(thresholds["minimum_redteam_block_rate"]),
                    ),
                    dataset_hash_status=_build_dataset_hash_status(
                        run_context_dataset_sha256=dataset_sha256,
                        aca_job_dataset_sha256=str(aca_job_request["dataset_sha256"]),
                        summary_dataset_sha256=str(summary_payload["dataset_sha256"]),
                    ),
                    summary_path=summary_path,
                    custom_path=custom_path,
                    redteam_path=redteam_path,
                    summary_payload=summary_payload,
                    custom_payload=custom_payload,
                    redteam_payload=redteam_payload,
                )
            )

        targets.append(target)

    return ReporterRunInput(
        run_id=run_id,
        dry_run_output_path=dry_run_output_path,
        history_preview_path=history_preview_path,
        targets=targets,
    )