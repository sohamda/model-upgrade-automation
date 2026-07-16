"""Skip-index helpers for local dry-run previews."""

from __future__ import annotations

from src.shared.contracts import ProvisionRequest, SkipIndexKey
from src.shared.run_context import RunContext


def build_skip_index_key(
    run_context: RunContext,
    provision_request: ProvisionRequest,
) -> SkipIndexKey:
    """Build the TG4 skip-index composite key preview."""

    return SkipIndexKey(
        model_id=provision_request.retiring_model_id,
        version=provision_request.retiring_model_version,
        dataset_sha256=run_context.dataset_sha256,
        candidate_model_id=provision_request.candidate_model_id,
        candidate_version=provision_request.candidate_version,
    )
