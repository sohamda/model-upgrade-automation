"""End-to-end local-first evaluator orchestration."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from src.evaluator.aca_job import AcaJobAdapter
from src.evaluator.aoai_client import load_model_api_shapes, resolve_api_shape
from src.evaluator.config_loader import (
    load_audit_provenance,
    load_evaluator_config,
    load_relative_gate_config,
)
from src.evaluator.custom_runner import LiveCustomRunner, LocalCustomRunner
from src.evaluator.dataset_loader import load_jsonl_dataset
from src.evaluator.input_builder import build_work_items_from_artifacts
from src.evaluator.models import CandidateEvaluationArtifacts
from src.evaluator.probe_set_loader import load_probe_set
from src.evaluator.redteam_runner import (
    DEFAULT_PROBE_SET_RELATIVE_PATH,
    LiveRedTeamRunner,
    LocalRedTeamRunner,
)
from src.evaluator.result_writer import write_candidate_results
from src.shared.errors import PipelineError
from src.shared.redaction import redact_mapping

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2

# Live-backed measurement is always advisory/non-promotion-grade (RAI HIGH-risk
# caveat, DR-03): a live run must never be auto-promoted without human review.
_LIVE_ADVISORY_RATIONALE = (
    "Live-backed measurement (--live/MUA_EVAL_MODE=live); requires human "
    "confirmation before any promotion decision (RAI HIGH-risk caveat)."
)


def _live_mode_from_env() -> bool:
    """Return whether ``MUA_EVAL_MODE=live`` opts into live-backed runners."""

    return os.environ.get("MUA_EVAL_MODE", "").strip().lower() == "live"


def detect_suspicious_uniformity(results: list[dict[str, object]]) -> list[str]:
    """Return anti-regression canary flags for suspiciously uniform results.

    A constant 1.0 red-team block rate across every candidate, or identical
    ``custom_overall`` scores across more than one candidate, is more likely a
    stubbed/constant scorer than a genuinely uniform outcome (Phase 2 Step
    2.4, Council C12). Pure function over the ``results`` list built by
    :func:`execute_local_evaluation`; never itself calls a scorer or model.
    """

    redteam_rates = [
        item["redteam_block_rate"] for item in results if item.get("redteam_block_rate") is not None
    ]
    custom_overalls = [
        item["custom_overall"] for item in results if item.get("custom_overall") is not None
    ]
    flags: list[str] = []
    if redteam_rates and all(rate == 1.0 for rate in redteam_rates):
        flags.append("redteam_block_rate_constant_1.0")
    if len(custom_overalls) > 1 and len(set(custom_overalls)) == 1:
        flags.append("custom_overall_identical_across_candidates")
    return flags


def execute_local_evaluation(
    repo_root: Path,
    artifact_root: Path,
    dataset_path: Path,
    *,
    custom_runner: LocalCustomRunner | LiveCustomRunner | None = None,
    redteam_runner: LocalRedTeamRunner | LiveRedTeamRunner | None = None,
    aca_job_adapter: AcaJobAdapter | None = None,
    live: bool = False,
) -> dict[str, object]:
    """Run local custom and red-team evaluation for all staged candidates.

    The default path (``live=False`` and no ``MUA_EVAL_MODE=live``) always
    uses the dependency-free fake runners and writes the same byte-stable
    summary shape as before this parameter existed. Passing ``live=True`` (or
    setting ``MUA_EVAL_MODE=live``) swaps in the live-backed runners and marks
    every resulting summary ``promotion_grade: false`` / ``advisory: true``;
    an explicit ``custom_runner``/``redteam_runner`` always overrides both.
    """

    evaluator_config = load_evaluator_config(repo_root)
    work_items = build_work_items_from_artifacts(
        repo_root,
        artifact_root,
        evaluator_config,
        dataset_path,
    )
    live_enabled = live or _live_mode_from_env()
    runner_custom = custom_runner or (LiveCustomRunner() if live_enabled else LocalCustomRunner())
    runner_redteam = redteam_runner or (
        LiveRedTeamRunner() if live_enabled else LocalRedTeamRunner()
    )
    aca_adapter = aca_job_adapter or AcaJobAdapter()
    dataset = load_jsonl_dataset(dataset_path)

    # Phase 2 additions (additive only; do not alter any pre-existing key
    # above this point). relative_gate/audit_provenance/probe_set are loaded
    # once per run, not per candidate.
    relative_gate = load_relative_gate_config(repo_root)
    audit_provenance = load_audit_provenance(repo_root)
    probe_set = load_probe_set(repo_root / DEFAULT_PROBE_SET_RELATIVE_PATH)
    model_api_shapes = load_model_api_shapes(repo_root)

    results: list[dict[str, object]] = []
    for work_item in work_items:
        custom_result = runner_custom.run(work_item, dataset)
        redteam_result = runner_redteam.run(work_item, dataset)
        aca_request = aca_adapter.build_request(work_item)

        # Step 2.3: relative-to-retiring gate. Skipped (None), never
        # fabricated, when the caller supplied no retiring baseline.
        quality_relative_pass = None
        if (
            work_item.retiring_custom_overall is not None
            and custom_result.aggregates["overall"] is not None
        ):
            quality_relative_pass = custom_result.aggregates["overall"] >= (
                work_item.retiring_custom_overall - relative_gate.quality_epsilon
            )
        redteam_relative_pass = None
        if (
            work_item.retiring_redteam_block_rate is not None
            and redteam_result.block_rate is not None
        ):
            redteam_relative_pass = redteam_result.block_rate >= (
                work_item.retiring_redteam_block_rate - relative_gate.redteam_epsilon
            )
        custom_overall_pass = None
        if custom_result.aggregates["overall"] is not None:
            custom_overall_pass = (
                custom_result.aggregates["overall"]
                >= work_item.evaluation_config.thresholds.minimum_custom_score
            )

        summary = {
            "run_id": work_item.run_context.run_id,
            "candidate_slug": work_item.candidate_slug,
            "retiring_model": {
                "model_id": work_item.retiring_model_id,
                "version": work_item.retiring_model_version,
            },
            "candidate_model": {
                "model_id": work_item.candidate_model_id,
                "version": work_item.candidate_version,
                "deployment_name": work_item.deployment_ref.deployment_name,
                "deployment_type": work_item.deployment_ref.deployment_type,
            },
            "dataset_sha256": dataset.dataset_sha256,
            "thresholds": {
                "minimum_custom_score": work_item.evaluation_config.thresholds.minimum_custom_score,
                "minimum_redteam_block_rate": work_item.evaluation_config.thresholds.minimum_redteam_block_rate,
            },
            "custom_overall": custom_result.aggregates["overall"],
            "redteam_block_rate": redteam_result.block_rate,
            "aca_job_request": {
                "run_id": aca_request.run_id,
                "candidate_slug": aca_request.candidate_slug,
                "deployment_name": aca_request.deployment_name,
                "dataset_sha256": aca_request.dataset_sha256,
            },
            "status": "local_complete",
            # Additive (Phase 2 Step 2.3, RAI relative-comparison condition).
            "relative_gate": {
                "quality_epsilon": relative_gate.quality_epsilon,
                "redteam_epsilon": relative_gate.redteam_epsilon,
                "retiring_custom_overall": work_item.retiring_custom_overall,
                "retiring_redteam_block_rate": work_item.retiring_redteam_block_rate,
                "quality_relative_pass": quality_relative_pass,
                "redteam_relative_pass": redteam_relative_pass,
            },
            # Additive (Phase 2 Step 2.5, per-run audit bundle; Council C11-C13).
            # decision/authorizer/decision_timestamp are populated by a human
            # reviewer out-of-band -- this repository never fills them in.
            "audit": {
                "judge_model_version": audit_provenance["judge_model_version"],
                "rubric_version": audit_provenance["rubric_version"],
                "probe_set_version": probe_set.probe_set_version,
                "probe_set_sha256": probe_set.probe_set_sha256,
                "qa_dataset_sha256": dataset.dataset_sha256,
                "deployment_name": work_item.deployment_ref.deployment_name,
                "deployment_temperature": resolve_api_shape(
                    work_item.candidate_model_id, model_api_shapes
                ).get("temperature"),
                "per_category_redteam_pass_fail": redteam_result.attacks,
                "custom_overall_pass": custom_overall_pass,
                "retiring_baseline": {
                    "custom_overall": work_item.retiring_custom_overall,
                    "redteam_block_rate": work_item.retiring_redteam_block_rate,
                },
                "suspicious_uniformity": redteam_result.block_rate == 1.0,
                "decision": None,
                "authorizer": None,
                "decision_timestamp": None,
            },
        }
        if live_enabled:
            summary["promotion_grade"] = False
            summary["advisory"] = True
            summary["advisory_rationale"] = _LIVE_ADVISORY_RATIONALE
            # Live-only degradation + canary audit (reviews F2/F3). These keys
            # are added ONLY on the live path so the default fake summary.json
            # stays additive/unchanged (live-only keys omitted on the default
            # path).
            summary["audit"]["classifier_available"] = redteam_result.classifier_available
            summary["audit"]["canary_failures"] = list(redteam_result.canary_failures)
            summary = redact_mapping(summary)
        paths = write_candidate_results(
            repo_root,
            work_item.run_context.run_id,
            CandidateEvaluationArtifacts(
                candidate_slug=work_item.candidate_slug,
                custom=custom_result,
                redteam=redteam_result,
                summary=summary,
            ),
        )
        results.append(
            {
                "candidate_slug": work_item.candidate_slug,
                "custom_path": paths["custom"].relative_to(repo_root).as_posix(),
                "redteam_path": paths["redteam"].relative_to(repo_root).as_posix(),
                "summary_path": paths["summary"].relative_to(repo_root).as_posix(),
                "custom_overall": custom_result.aggregates["overall"],
                "redteam_block_rate": redteam_result.block_rate,
            }
        )

    # Step 2.4: suspicious-uniformity flags (Council C12 anti-regression
    # canary condition). A constant 1.0 block rate across all candidates, or
    # identical custom_overall scores across more than one candidate, is
    # likely a stubbed/constant scorer rather than a genuinely uniform
    # result, and is surfaced here rather than silently trusted.
    uniformity_flags = detect_suspicious_uniformity(results)

    return {
        "run_id": work_items[0].run_context.run_id,
        "dataset_sha256": dataset.dataset_sha256,
        "result_count": len(results),
        "results": results,
        "aca_dispatch_status": "deferred-local-only",
        "uniformity_flags": uniformity_flags,
    }


def create_parser() -> argparse.ArgumentParser:
    """Create the evaluator CLI parser."""

    parser = argparse.ArgumentParser(description="Run TG5 local evaluator flow.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root containing config/ and artifacts/.",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("artifacts/cli-test-run"),
        help="Artifact root produced by the TG4 dry-run pipeline.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("tests/fixtures/evaluator/dataset.sample.jsonl"),
        help="Local JSONL dataset used for evaluator execution.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Opt in to live-backed runners (requires FOUNDRY_PROJECT_ENDPOINT "
            "and JUDGE_MODEL). Output is always advisory/non-promotion-grade, "
            "never auto-promoted. Also enabled via MUA_EVAL_MODE=live."
        ),
    )
    return parser


def main() -> int:
    """CLI entrypoint for local evaluator execution."""

    parser = create_parser()
    args = parser.parse_args()

    try:
        output = execute_local_evaluation(
            args.repo_root.resolve(),
            (args.repo_root / args.artifact_root).resolve()
            if not args.artifact_root.is_absolute()
            else args.artifact_root,
            (args.repo_root / args.dataset).resolve()
            if not args.dataset.is_absolute()
            else args.dataset,
            live=args.live,
        )
    except KeyboardInterrupt:
        print("Interrupted by user", file=sys.stderr)
        return 130
    except PipelineError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as error:
        print(f"Execution error: {error}", file=sys.stderr)
        return EXIT_FAILURE

    print(json.dumps(output, indent=2, sort_keys=True))
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())