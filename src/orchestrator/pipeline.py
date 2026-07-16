"""Minimal TG4 pipeline orchestration for local dry runs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from src.detector.retirement_source import FixtureRetirementSource, build_default_fixture
from src.detector.service import detect_retiring_targets
from src.history.manifest_builder import build_history_preview
from src.recommender.catalog import FixtureCandidateCatalog, build_default_catalog
from src.recommender.service import recommend_candidates
from src.provisioner.service import plan_provisioning
from src.shared.azure_auth import create_credential_descriptor
from src.shared.config import AppConfig, load_app_config
from src.shared.contracts import to_serializable_dict
from src.shared.run_context import RunContext, build_run_context


@dataclass(slots=True)
class DryRunOutput:
    """Serializable result of the first TG4 execution slice."""

    run_context: RunContext
    detector: dict[str, object]
    recommender: dict[str, object]
    provisioner: dict[str, object]
    history: dict[str, object]
    credential: dict[str, str]
    staging: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "run_context": self.run_context.to_dict(),
            "detector": self.detector,
            "recommender": self.recommender,
            "provisioner": self.provisioner,
            "history": self.history,
            "credential": self.credential,
            "staging": self.staging,
        }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _stage_dry_run_output(
    repo_root: Path,
    run_context: RunContext,
    detector_payload: dict[str, object],
    recommender_payload: dict[str, object],
    provisioner_payload: dict[str, object],
    history_preview: dict[str, object],
    credential_payload: dict[str, str],
) -> dict[str, object]:
    artifact_root = repo_root / "artifacts" / run_context.run_id
    staged_files: list[str] = []

    manifest_payloads = {
        "detector-preview": detector_payload,
        "recommender-preview": recommender_payload,
        "provisioner-preview": provisioner_payload,
    }
    for manifest in history_preview["manifests"]:
        artifact_type = str(manifest["artifact_type"])
        relative_path = Path(str(manifest["relative_path"]))
        _write_json(repo_root / relative_path, manifest_payloads[artifact_type])
        staged_files.append(relative_path.as_posix())

    history_relative_path = (Path("artifacts") / run_context.run_id / "history_preview.json").as_posix()
    _write_json(repo_root / history_relative_path, history_preview)
    staged_files.append(history_relative_path)

    summary_relative_path = (Path("artifacts") / run_context.run_id / "dry_run_output.json").as_posix()
    _write_json(
        repo_root / summary_relative_path,
        {
            "run_context": run_context.to_dict(),
            "detector": detector_payload,
            "recommender": recommender_payload,
            "provisioner": provisioner_payload,
            "history": history_preview,
            "credential": credential_payload,
        },
    )
    staged_files.append(summary_relative_path)

    return {
        "artifact_root": artifact_root.relative_to(repo_root).as_posix(),
        "files": staged_files,
    }


def execute_dry_run(
    repo_root: Path,
    *,
    fixture_path: Path | None = None,
    catalog_path: Path | None = None,
    run_id: str | None = None,
    config_root: Path | None = None,
) -> DryRunOutput:
    """Execute the minimal non-Azure TG4 slice end-to-end."""

    config: AppConfig = load_app_config(config_root or repo_root)
    run_context = build_run_context(config, run_id=run_id)
    source = FixtureRetirementSource(fixture_path) if fixture_path else build_default_fixture(repo_root)
    catalog = FixtureCandidateCatalog(catalog_path) if catalog_path else build_default_catalog(repo_root)
    detector_result = detect_retiring_targets(config, run_context, source)
    recommendation_results = []
    provision_results = []
    for target in detector_result.retiring_targets:
        recommended = recommend_candidates(config, run_context, target, catalog)
        provision_plan = plan_provisioning(config, run_context, target, recommended.ranked_candidates)
        recommendation_results.append(
            {
                "retiring_target": to_serializable_dict(target),
                "ranked_candidates": [
                    to_serializable_dict(item) for item in recommended.ranked_candidates
                ],
                "parse_warnings": list(recommended.parse_warnings),
            }
        )
        provision_results.append(
            {
                "retiring_target": to_serializable_dict(target),
                "provision_requests": [
                    to_serializable_dict(item) for item in provision_plan.provision_requests
                ],
                "teardown_plans": [
                    to_serializable_dict(item) for item in provision_plan.teardown_plans
                ],
            }
        )
    history_preview = build_history_preview(
        run_context,
        detector_result.retiring_targets,
        recommendation_results,
        provision_results,
    )
    detector_payload = {
        "retiring_targets": [to_serializable_dict(item) for item in detector_result.retiring_targets],
        "parse_warnings": [to_serializable_dict(item) for item in detector_result.parse_warnings],
    }
    recommender_payload = {"recommendations": recommendation_results}
    provisioner_payload = {"plans": provision_results}
    credential_payload = to_serializable_dict(
        create_credential_descriptor(
        tenant_id=run_context.azure_tenant_id,
        client_id=config.azure.azure_client_id,
        )
    )
    staging = _stage_dry_run_output(
        repo_root,
        run_context,
        detector_payload,
        recommender_payload,
        provisioner_payload,
        history_preview,
        credential_payload,
    )
    return DryRunOutput(
        run_context=run_context,
        detector=detector_payload,
        recommender=recommender_payload,
        provisioner=provisioner_payload,
        history=history_preview,
        credential=credential_payload,
        staging=staging,
    )
