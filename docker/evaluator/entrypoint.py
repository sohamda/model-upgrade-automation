"""Container entrypoint for the evaluator ACA job contract."""

from __future__ import annotations

from pathlib import Path
import os
import sys

from src.evaluator.service import execute_local_evaluation


def main() -> int:
    """Run the evaluator using contract-level environment variables."""

    repo_root = Path(os.environ.get("EVALUATOR_REPO_ROOT", "/app"))
    artifact_root = Path(os.environ.get("EVALUATOR_ARTIFACT_ROOT", "/app/artifacts/cli-test-run"))
    dataset_path = Path(
        os.environ.get(
            "EVALUATOR_DATASET_PATH",
            "/app/tests/fixtures/evaluator/dataset.sample.jsonl",
        )
    )

    execute_local_evaluation(repo_root, artifact_root, dataset_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())