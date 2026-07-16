"""Manifest preview builder for orchestrator dry runs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

from src.history.models import HistoryPreview
from src.history.skip_index import build_skip_index_key
from src.shared.contracts import ArtifactManifest, ProvisionRequest, to_serializable_dict
from src.shared.run_context import RunContext


def _build_manifest(
    run_context: RunContext,
    artifact_type: str,
    relative_path: str,
    payload: object,
) -> ArtifactManifest:
    encoded_payload = json.dumps(payload, sort_keys=True).encode("utf-8")
    return ArtifactManifest(
        run_id=run_context.run_id,
        artifact_type=artifact_type,
        relative_path=relative_path,
        created_at_utc=datetime.now(timezone.utc),
        dataset_sha256=run_context.dataset_sha256,
        content_sha256=hashlib.sha256(encoded_payload).hexdigest(),
    )


def build_history_preview(
    run_context: RunContext,
    retiring_targets: list[object],
    recommendation_results: list[dict[str, object]],
    provision_results: list[dict[str, object]],
) -> dict[str, object]:
    """Build manifest and skip-index previews for the dry-run pipeline."""

    preview = HistoryPreview()

    detector_payload = [to_serializable_dict(item) for item in retiring_targets]
    preview.manifests.append(
        _build_manifest(
            run_context,
            "detector-preview",
            f"artifacts/{run_context.run_id}/detector.json",
            detector_payload,
        )
    )
    preview.manifests.append(
        _build_manifest(
            run_context,
            "recommender-preview",
            f"artifacts/{run_context.run_id}/recommender.json",
            recommendation_results,
        )
    )
    preview.manifests.append(
        _build_manifest(
            run_context,
            "provisioner-preview",
            f"artifacts/{run_context.run_id}/provisioner.json",
            provision_results,
        )
    )

    for result in provision_results:
        for item in result["provision_requests"]:
            provision_request = ProvisionRequest(**item)
            preview.skip_index_keys.append(build_skip_index_key(run_context, provision_request))

    return {
        "manifests": [to_serializable_dict(item) for item in preview.manifests],
        "skip_index_keys": [to_serializable_dict(item) for item in preview.skip_index_keys],
    }
