"""Persist local evaluator results using the TG5 contract."""

from __future__ import annotations

import json
from pathlib import Path

from src.evaluator.models import CandidateEvaluationArtifacts
from src.shared.redaction import redact_mapping


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


def write_redteam_transcript(
    repo_root: Path,
    run_id: str,
    candidate_slug: str,
    transcript_records: list[dict[str, object]],
) -> Path:
    """Write a redacted, per-probe live red-team transcript (Phase 2 Step 2.5).

    Written under ``results/redteam/{run_id}/{candidate_slug}.json`` --
    segregated from the standard ``results/{run_id}/{candidate_slug}/`` output
    tree established by :func:`write_candidate_results` and never included in
    CI artifact-upload globs (Council C6-C9 containment; verified against
    ``.github/workflows`` upload-artifact globs during Phase 1). Every value
    is passed through :func:`~src.shared.redaction.redact_mapping` before
    being persisted. Only called by :class:`LiveRedTeamRunner`; never
    exercised by the default fake path.
    """

    transcript_root = repo_root / "results" / "redteam" / run_id
    transcript_root.mkdir(parents=True, exist_ok=True)
    transcript_path = transcript_root / f"{candidate_slug}.json"
    payload = redact_mapping({"candidate_slug": candidate_slug, "probes": transcript_records})
    transcript_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return transcript_path