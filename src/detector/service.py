"""Detector service composing watch-list and retirement sources."""

from __future__ import annotations

from datetime import datetime, timezone

from src.detector.models import DetectorResult
from src.detector.retirement_source import RetirementSource, days_until
from src.detector.watchlist import load_watch_list
from src.shared.config import AppConfig
from src.shared.contracts import RetiringTarget, WarningRecord
from src.shared.run_context import RunContext


def detect_retiring_targets(
    config: AppConfig,
    run_context: RunContext,
    source: RetirementSource,
    *,
    reference_time: datetime | None = None,
) -> DetectorResult:
    """Normalize retirement signals into TG1 retiring target contracts."""

    watch_list = load_watch_list(config)
    retirement_entries = source.load()
    watch_index = {(entry.model_id, entry.current_version): entry for entry in watch_list}
    reference = reference_time or datetime.now(timezone.utc)

    result = DetectorResult()
    for retiring_model in retirement_entries:
        watched = watch_index.get((retiring_model.model_id, retiring_model.current_version))
        if retiring_model.source == "explicit-cli":
            result.retiring_targets.append(
                RetiringTarget(
                    model_id=retiring_model.model_id,
                    current_version=retiring_model.current_version,
                    region=run_context.allowed_regions[0] if run_context.allowed_regions else "swedencentral",
                    workload="general_qa",
                    retirement_date=retiring_model.retirement_date,
                    days_until_retirement=99999,
                    source=retiring_model.source,
                    replacement_family=retiring_model.replacement_family,
                )
            )
            continue
        if not watched:
            result.parse_warnings.append(
                WarningRecord(
                    code="unwatched_retirement_signal",
                    message=(
                        f"Retirement signal for {retiring_model.model_id}@{retiring_model.current_version} "
                        "did not match any configured watch-list entry."
                    ),
                    source=retiring_model.source,
                )
            )
            continue

        horizon_days = watched.retirement_horizon_days or run_context.retirement_horizon_days
        remaining_days = days_until(retiring_model.retirement_date, reference=reference)
        if remaining_days > horizon_days:
            continue

        result.retiring_targets.append(
            RetiringTarget(
                model_id=retiring_model.model_id,
                current_version=retiring_model.current_version,
                region=watched.region,
                workload=watched.workload,
                retirement_date=retiring_model.retirement_date,
                days_until_retirement=remaining_days,
                source=retiring_model.source,
                replacement_family=retiring_model.replacement_family,
            )
        )

    result.retiring_targets.sort(key=lambda item: (item.days_until_retirement, item.model_id, item.current_version))
    return result
