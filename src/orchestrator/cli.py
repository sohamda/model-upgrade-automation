"""Command-line entrypoint for the minimal TG4 dry-run slice."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from src.orchestrator.pipeline import execute_dry_run
from src.shared.errors import PipelineError
from src.shared.logging import configure_logging
from src.shared.config import RuntimeOptions

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Run the first TG4 dry-run pipeline slice."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root containing config/ and tests/fixtures/.",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Optional retirement fixture path.",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=None,
        help="Optional candidate catalog fixture path.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional run identifier used for deterministic artifact staging.",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--retiring-model",
        type=str,
        default=None,
        help="Explicit retiring model ID to evaluate.",
    )
    parser.add_argument(
        "--retiring-version",
        type=str,
        default=None,
        help="Optional retiring model version.",
    )
    parser.add_argument(
        "--discover-from-azure",
        action="store_true",
        help="Discover retiring targets from Azure Foundry deployments.",
    )
    parser.add_argument(
        "--live-catalog",
        action="store_true",
        help="Fetch retirement and catalog data from live Azure docs sources.",
    )
    parser.add_argument(
        "--provision-candidates",
        action="store_true",
        help="Opt in to candidate provisioning (default is safe non-mutating mode).",
    )
    parser.add_argument(
        "--run-evals",
        action="store_true",
        help="Opt in to evaluator execution (default is disabled).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Maximum number of candidates to return and process.",
    )
    return parser


def main() -> int:
    """CLI entrypoint."""

    parser = create_parser()
    args = parser.parse_args()
    configure_logging(verbose=args.verbose)

    try:
        runtime = RuntimeOptions(
            retiring_model=args.retiring_model,
            retiring_version=args.retiring_version,
            discover_from_azure=args.discover_from_azure,
            live_catalog=args.live_catalog,
            provision_candidates=args.provision_candidates,
            run_evals=args.run_evals,
            top_k=max(1, args.top_k),
        )
        output = execute_dry_run(
            args.repo_root.resolve(),
            fixture_path=args.fixture,
            catalog_path=args.catalog,
            run_id=args.run_id,
            runtime=runtime,
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

    print(json.dumps(output.to_dict(), indent=2, sort_keys=True))
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
