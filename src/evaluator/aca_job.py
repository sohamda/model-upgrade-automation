"""ACA job execution seam for future Azure-backed evaluator runs."""

from __future__ import annotations

from dataclasses import dataclass

from src.evaluator.models import EvaluatorWorkItem
from src.shared.errors import DependencyUnavailableError


@dataclass(slots=True)
class AcaJobRequest:
    """Contract-level ACA job request payload."""

    run_id: str
    candidate_slug: str
    deployment_name: str
    dataset_sha256: str


class AcaJobAdapter:
    """Deferred Azure-live evaluator execution boundary."""

    def build_request(self, work_item: EvaluatorWorkItem) -> AcaJobRequest:
        """Translate a work item into the future ACA job request contract."""

        return AcaJobRequest(
            run_id=work_item.run_context.run_id,
            candidate_slug=work_item.candidate_slug,
            deployment_name=work_item.deployment_ref.deployment_name,
            dataset_sha256=work_item.dataset_sha256,
        )

    def dispatch(self, request: AcaJobRequest) -> None:
        """Defer live ACA execution until Azure-backed validation is available."""

        raise DependencyUnavailableError(
            "ACA evaluator dispatch is intentionally deferred for local-first TG5 execution. "
            f"Prepared request for {request.candidate_slug} in run {request.run_id}."
        )