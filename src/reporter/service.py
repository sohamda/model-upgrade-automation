"""End-to-end local-first TG6 reporter orchestration."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from src.reporter.aggregator import aggregate_reporter_run
from src.reporter.artifact_loader import load_reporter_run_input
from src.reporter.decision_engine import decide_recommendation
from src.reporter.issue_payload import build_issue_payload
from src.reporter.markdown_report import render_markdown_report
from src.reporter.models import ReporterExecutionResult
from src.reporter.remediation_payload import build_remediation_payload
from src.shared.config import load_app_config
from src.shared.errors import PipelineError

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _target_slug(model_id: str, version: str) -> str:
    return f"{model_id.replace('.', '-')}-{version}"


def execute_local_report(
    repo_root: Path,
    artifact_root: Path,
    output_root: Path | None = None,
) -> ReporterExecutionResult:
    """Run the local TG6 reporting flow and write report artifacts."""

    report_input = load_reporter_run_input(repo_root, artifact_root)
    aggregates = aggregate_reporter_run(report_input)
    app_config = load_app_config(repo_root)
    final_output_root = output_root or (artifact_root / "reporter")
    final_output_root.mkdir(parents=True, exist_ok=True)

    report_paths: list[Path] = []
    decision_paths: list[Path] = []
    issue_payload_paths: list[Path] = []
    remediation_payload_paths: list[Path] = []
    winners: dict[str, str | None] = {}
    warnings: list[str] = []

    for aggregate in aggregates:
        target_slug = _target_slug(aggregate.model_id, aggregate.version)
        decision = decide_recommendation(aggregate)
        report = render_markdown_report(aggregate, decision)
        issue_payload = build_issue_payload(aggregate, decision)
        remediation_payload = build_remediation_payload(
            aggregate,
            decision,
            enable_auto_pr=app_config.azure.enable_auto_pr,
        )

        report_path = final_output_root / f"{target_slug}-report.md"
        decision_path = final_output_root / f"{target_slug}-decision.json"
        issue_payload_path = final_output_root / f"{target_slug}-issue-payload.json"
        remediation_payload_path = final_output_root / f"{target_slug}-remediation-payload.json"

        report_path.write_text(report.content, encoding="utf-8")
        _write_json(decision_path, asdict(decision))
        _write_json(issue_payload_path, asdict(issue_payload))
        _write_json(remediation_payload_path, asdict(remediation_payload))

        report_paths.append(report_path)
        decision_paths.append(decision_path)
        issue_payload_paths.append(issue_payload_path)
        remediation_payload_paths.append(remediation_payload_path)
        winners[target_slug] = decision.winner.candidate_slug if decision.winner is not None else None
        warnings.extend(report.warnings)

    return ReporterExecutionResult(
        run_id=report_input.run_id,
        output_root=final_output_root,
        generated_at=datetime.now(timezone.utc).date(),
        report_paths=report_paths,
        decision_paths=decision_paths,
        issue_payload_paths=issue_payload_paths,
        remediation_payload_paths=remediation_payload_paths,
        winners=winners,
        warnings=sorted(set(warnings)),
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the reporter CLI parser."""

    parser = argparse.ArgumentParser(description="Run the TG6 local reporter flow.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root containing artifacts/, results/, and config/.",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("artifacts/cli-test-run"),
        help="Artifact root produced by the TG4 dry-run pipeline.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Optional output directory for generated TG6 reporter artifacts.",
    )
    return parser


def main() -> int:
    """CLI entrypoint for local reporter execution."""

    parser = create_parser()
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    artifact_root = (repo_root / args.artifact_root).resolve() if not args.artifact_root.is_absolute() else args.artifact_root
    output_root = None
    if args.output_root is not None:
        output_root = (repo_root / args.output_root).resolve() if not args.output_root.is_absolute() else args.output_root

    try:
        result = execute_local_report(repo_root, artifact_root, output_root)
    except KeyboardInterrupt:
        print("Interrupted by user", file=sys.stderr)
        return 130
    except PipelineError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as error:
        print(f"Execution error: {error}", file=sys.stderr)
        return EXIT_FAILURE

    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "output_root": result.output_root.as_posix(),
                "generated_at": result.generated_at.isoformat(),
                "report_paths": [path.as_posix() for path in result.report_paths],
                "decision_paths": [path.as_posix() for path in result.decision_paths],
                "issue_payload_paths": [path.as_posix() for path in result.issue_payload_paths],
                "remediation_payload_paths": [path.as_posix() for path in result.remediation_payload_paths],
                "winners": result.winners,
                "warnings": result.warnings,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())