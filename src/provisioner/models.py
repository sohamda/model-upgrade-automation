"""Provisioner-local planning models."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.shared.contracts import ProvisionRequest, TeardownPlan


@dataclass(slots=True)
class ProvisionPlanResult:
    """Dry-run provisioner output for a retiring target."""

    provision_requests: list[ProvisionRequest] = field(default_factory=list)
    teardown_plans: list[TeardownPlan] = field(default_factory=list)
