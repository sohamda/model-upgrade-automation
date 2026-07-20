"""Minimal TG4 pipeline orchestration for local dry runs and live-source MVP toggles."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from src.detector.arm_models_source import ArmModelsRetirementSource
from src.detector.deployed_introspector import discover_foundry_deployments
from src.detector.retirement_schedule_source import LearnRetirementScheduleSource
from src.detector.retirement_source import (
    FixtureRetirementSource,
    RetirementSource,
    build_default_fixture,
)
from src.detector.service import detect_retiring_targets
from src.evaluator.service import execute_local_evaluation
from src.history.manifest_builder import build_history_preview
from src.provisioner.service import execute_provisioning_mvp, plan_provisioning
from src.recommender.arm_catalog_source import ArmModelsCatalogSource
from src.recommender.catalog import CandidateCatalog, FixtureCandidateCatalog, build_default_catalog
from src.recommender.foundry_catalog_source import LearnFoundryCatalogSource
from src.recommender.pricing_source import RetailPricesClient
from src.recommender.service import recommend_candidates
from src.shared.azure_auth import create_credential_descriptor
from src.shared.config import AppConfig, RuntimeOptions, load_app_config
from src.shared.contracts import RetiringModel, to_serializable_dict
from src.shared.errors import ContractError, DependencyUnavailableError
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
    runtime_payload: dict[str, object],
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

    history_relative_path = (
        Path("artifacts") / run_context.run_id / "history_preview.json"
    ).as_posix()
    _write_json(repo_root / history_relative_path, history_preview)
    staged_files.append(history_relative_path)

    summary_relative_path = (
        Path("artifacts") / run_context.run_id / "dry_run_output.json"
    ).as_posix()
    _write_json(
        repo_root / summary_relative_path,
        {
            "run_context": run_context.to_dict(),
            "detector": detector_payload,
            "recommender": recommender_payload,
            "provisioner": provisioner_payload,
            "history": history_preview,
            "credential": credential_payload,
            "runtime": runtime_payload,
        },
    )
    staged_files.append(summary_relative_path)

    return {
        "artifact_root": artifact_root.relative_to(repo_root).as_posix(),
        "files": staged_files,
    }


def _should_use_official_sources(config: AppConfig, runtime: RuntimeOptions) -> bool:
    if runtime.live_catalog:
        return True
    if runtime.use_official_sources is not None:
        return runtime.use_official_sources
    return config.use_official_sources


@dataclass(slots=True)
class _FallbackRetirementSource:
    primary: RetirementSource
    fallback: RetirementSource

    def load(self) -> list[RetiringModel]:
        try:
            return self.primary.load()
        except DependencyUnavailableError:
            return self.fallback.load()


@dataclass(slots=True)
class _FallbackCatalogSource:
    primary: CandidateCatalog
    fallback: CandidateCatalog

    def load(self):
        try:
            return self.primary.load()
        except DependencyUnavailableError:
            return self.fallback.load()


def _resolve_source(
    repo_root: Path,
    config: AppConfig,
    runtime: RuntimeOptions,
    fixture_path: Path | None,
):
    if fixture_path:
        return FixtureRetirementSource(fixture_path)

    if _should_use_official_sources(config, runtime):
        # Fallback chain: authoritative ARM Models API -> Learn retirement schedule
        # -> bundled fixture. Each tier degrades to the next on
        # DependencyUnavailableError so a runtime always resolves signals.
        learn_to_fixture = _FallbackRetirementSource(
            primary=LearnRetirementScheduleSource(),
            fallback=build_default_fixture(repo_root),
        )
        return _FallbackRetirementSource(
            primary=ArmModelsRetirementSource(
                subscription_id=config.azure.azure_subscription_id,
                locations=list(config.azure.allowed_regions),
            ),
            fallback=learn_to_fixture,
        )

    return build_default_fixture(repo_root)


def _resolve_catalog(
    repo_root: Path,
    config: AppConfig,
    runtime: RuntimeOptions,
    catalog_path: Path | None,
):
    if catalog_path:
        return FixtureCandidateCatalog(catalog_path)

    if _should_use_official_sources(config, runtime):
        # Fallback chain: authoritative ARM Models API -> Learn Foundry catalog
        # -> bundled fixture. Each tier degrades to the next on
        # DependencyUnavailableError so a runtime always resolves candidates.
        learn_to_fixture = _FallbackCatalogSource(
            primary=LearnFoundryCatalogSource(),
            fallback=build_default_catalog(repo_root),
        )
        return _FallbackCatalogSource(
            primary=ArmModelsCatalogSource(
                subscription_id=config.azure.azure_subscription_id,
                locations=list(config.azure.allowed_regions),
            ),
            fallback=learn_to_fixture,
        )

    return build_default_catalog(repo_root)


def _build_inline_target_source(runtime: RuntimeOptions):
    injected_source_models = [
        RetiringModel(
            model_id=runtime.retiring_model or "",
            current_version=runtime.retiring_version or "unspecified",
            retirement_date="2099-12-31",
            replacement_family=runtime.retiring_model,
            source="explicit-cli",
        )
    ]

    class _InlineSource:
        def load(self) -> list[RetiringModel]:
            return injected_source_models

    return _InlineSource()


def execute_dry_run(
    repo_root: Path,
    *,
    fixture_path: Path | None = None,
    catalog_path: Path | None = None,
    run_id: str | None = None,
    config_root: Path | None = None,
    runtime: RuntimeOptions | None = None,
) -> DryRunOutput:
    """Execute the pipeline end-to-end with safe defaults."""

    runtime_options = runtime or RuntimeOptions()
    config: AppConfig = load_app_config(config_root or repo_root)
    run_context = build_run_context(config, run_id=run_id)

    if runtime_options.run_evals and not runtime_options.provision_candidates:
        raise ContractError("--run-evals requires --provision-candidates to be enabled.")

    source = _resolve_source(repo_root, config, runtime_options, fixture_path)
    catalog = _resolve_catalog(repo_root, config, runtime_options, catalog_path)

    if runtime_options.discover_from_azure:
        discovered = discover_foundry_deployments(run_context)
        if not discovered:
            raise DependencyUnavailableError(
                "No Foundry deployments discovered. Ensure AZ CLI auth and Foundry account/project are configured."
            )
        if runtime_options.retiring_model is None:
            runtime_options.retiring_model = discovered[0]["model_id"]
        if runtime_options.retiring_version is None:
            runtime_options.retiring_version = discovered[0].get("version")

    if runtime_options.retiring_model is not None:
        source = _build_inline_target_source(runtime_options)

    detector_result = detect_retiring_targets(config, run_context, source)
    recommendation_results: list[dict[str, object]] = []
    provision_results: list[dict[str, object]] = []

    safety = {
        "provision_candidates": runtime_options.provision_candidates,
        "run_evals": runtime_options.run_evals,
        "mode": "dry-run" if not runtime_options.provision_candidates else "live-mvp",
    }

    provision_exec = {"status": "skipped", "reason": "no targets"}
    # Only consult live Retail Prices when official sources are enabled; hermetic
    # and fixture runs fall back to static catalog cost scores.
    price_client = (
        RetailPricesClient()
        if _should_use_official_sources(config, runtime_options)
        else None
    )
    for target in detector_result.retiring_targets:
        recommended = recommend_candidates(
            config, run_context, target, catalog, price_client=price_client
        )
        top_candidates = recommended.ranked_candidates[: runtime_options.top_k]
        provision_plan = plan_provisioning(config, run_context, target, top_candidates)
        provision_exec = execute_provisioning_mvp(
            run_context,
            provision_plan,
            enabled=runtime_options.provision_candidates,
            repo_root=repo_root,
        )

        recommendation_results.append(
            {
                "retiring_target": to_serializable_dict(target),
                "ranked_candidates": [to_serializable_dict(item) for item in top_candidates],
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
                "executed": runtime_options.provision_candidates,
            }
        )

    history_preview = build_history_preview(
        run_context,
        detector_result.retiring_targets,
        recommendation_results,
        provision_results,
    )

    detector_payload = {
        "retiring_targets": [
            to_serializable_dict(item) for item in detector_result.retiring_targets
        ],
        "parse_warnings": [
            to_serializable_dict(item) for item in detector_result.parse_warnings
        ],
    }
    recommender_payload = {"recommendations": recommendation_results}

    eval_payload: dict[str, object] = {
        "status": "skipped",
        "note": "Evaluation disabled by default. Use --run-evals to enable.",
    }
    if runtime_options.run_evals and runtime_options.provision_candidates:
        dataset = repo_root / "tests" / "fixtures" / "evaluator" / "dataset.sample.jsonl"
        eval_payload = execute_local_evaluation(
            repo_root,
            repo_root / "artifacts" / run_context.run_id,
            dataset,
        )
        eval_payload["status"] = "local-mvp-fallback"
        eval_payload[
            "note"
        ] = "ACA job execution unavailable in this environment; local deterministic fallback used."

    provisioner_payload = {
        "plans": provision_results,
        "safety": safety,
        "execution": provision_exec,
        "evaluation": eval_payload,
    }
    credential_payload = to_serializable_dict(
        create_credential_descriptor(
            tenant_id=run_context.azure_tenant_id,
            client_id=config.azure.azure_client_id,
        )
    )
    runtime_payload = {
        "retiring_model": runtime_options.retiring_model,
        "retiring_version": runtime_options.retiring_version,
        "discover_from_azure": runtime_options.discover_from_azure,
        "live_catalog": runtime_options.live_catalog,
        "provision_candidates": runtime_options.provision_candidates,
        "run_evals": runtime_options.run_evals,
        "top_k": runtime_options.top_k,
        "safety": safety,
    }

    staging = _stage_dry_run_output(
        repo_root,
        run_context,
        detector_payload,
        recommender_payload,
        provisioner_payload,
        history_preview,
        credential_payload,
        runtime_payload,
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
