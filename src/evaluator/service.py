"""End-to-end local-first evaluator orchestration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from src.evaluator.aca_job import AcaJobAdapter
from src.evaluator.config_loader import load_evaluator_config
from src.evaluator.custom_runner import LocalCustomRunner
from src.evaluator.dataset_loader import load_jsonl_dataset
from src.evaluator.input_builder import build_work_items_from_artifacts
from src.evaluator.models import CandidateEvaluationArtifacts
from src.evaluator.redteam_runner import LocalRedTeamRunner
from src.evaluator.result_writer import write_candidate_results
from src.shared.errors import PipelineError

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2


def execute_local_evaluation(
    repo_root: Path,
    artifact_root: Path,
    dataset_path: Path,
    *,
    custom_runner: LocalCustomRunner | None = None,
    redteam_runner: LocalRedTeamRunner | None = None,
    aca_job_adapter: AcaJobAdapter | None = None,
) -> dict[str, object]:
    """Run local custom and red-team evaluation for all staged candidates."""

    evaluator_config = load_evaluator_config(repo_root)
    work_items = build_work_items_from_artifacts(
        repo_root,
        artifact_root,
        evaluator_config,
        dataset_path,
    )
    runner_custom = custom_runner or LocalCustomRunner()
    runner_redteam = redteam_runner or LocalRedTeamRunner()
    aca_adapter = aca_job_adapter or AcaJobAdapter()
    dataset = load_jsonl_dataset(dataset_path)

    results: list[dict[str, object]] = []
    for work_item in work_items:
        custom_result = runner_custom.run(work_item, dataset)
        redteam_result = runner_redteam.run(work_item, dataset)
        aca_request = aca_adapter.build_request(work_item)
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
        }
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

    return {
        "run_id": work_items[0].run_context.run_id,
        "dataset_sha256": dataset.dataset_sha256,
        "result_count": len(results),
        "results": results,
        "aca_dispatch_status": "deferred-local-only",
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