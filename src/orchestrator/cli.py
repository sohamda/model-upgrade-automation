"""Command-line entrypoint for the minimal TG4 dry-run slice."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from src.orchestrator.pipeline import execute_dry_run
from src.shared.errors import PipelineError
from src.shared.logging import configure_logging

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
    return parser


def main() -> int:
    """CLI entrypoint."""

    parser = create_parser()
    args = parser.parse_args()
    configure_logging(verbose=args.verbose)

    try:
        output = execute_dry_run(
            args.repo_root.resolve(),
            fixture_path=args.fixture,
            catalog_path=args.catalog,
            run_id=args.run_id,
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
