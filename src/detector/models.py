"""Detector-specific response models."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.shared.contracts import RetiringTarget, WarningRecord


@dataclass(slots=True)
class DetectorResult:
    """Normalized detector output for the orchestrator."""

    retiring_targets: list[RetiringTarget] = field(default_factory=list)
    parse_warnings: list[WarningRecord] = field(default_factory=list)
