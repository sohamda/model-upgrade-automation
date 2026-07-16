"""Persist local evaluator results using the TG5 contract."""

from __future__ import annotations

import json
from pathlib import Path

from src.evaluator.models import CandidateEvaluationArtifacts


def write_candidate_results(
    repo_root: Path,
    run_id: str,
    artifacts: CandidateEvaluationArtifacts,
) -> dict[str, Path]:
    """Write custom and red-team result files for one candidate."""

    candidate_root = repo_root / "results" / run_id / artifacts.candidate_slug
    candidate_root.mkdir(parents=True, exist_ok=True)

    output_paths = {
        "custom": candidate_root / "custom.json",
        "redteam": candidate_root / "redteam.json",
        "summary": candidate_root / "summary.json",
    }

    output_paths["custom"].write_text(
        json.dumps(
            {
                "candidate_slug": artifacts.custom.candidate_slug,
                "dataset_sha256": artifacts.custom.dataset_sha256,
                "rows": artifacts.custom.rows,
                "aggregates": artifacts.custom.aggregates,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    output_paths["redteam"].write_text(
        json.dumps(
            {
                "candidate_slug": artifacts.redteam.candidate_slug,
                "dataset_sha256": artifacts.redteam.dataset_sha256,
                "attacks": artifacts.redteam.attacks,
                "block_rate": artifacts.redteam.block_rate,
                "aggregates": artifacts.redteam.aggregates,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    output_paths["summary"].write_text(
        json.dumps(artifacts.summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return output_paths