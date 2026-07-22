"""Root pytest configuration for the unit suite.

An autouse fixture clears the two ambient configuration environment variables
that :func:`src.shared.config.load_app_config` reads WITHOUT a fallback
(``DEPLOYMENT_TYPE`` and ``ALLOWED_REGIONS``). A developer shell that exports
these values would otherwise flip config-derived outputs mid-suite; clearing
them per test keeps collection hermetic regardless of the invoking environment.

Every other config variable falls back to the ``azure.env.example`` defaults, so
only these two need isolation to prevent ambient env pollution.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_ambient_config_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove config env vars read without a fallback before each test."""

    monkeypatch.delenv("DEPLOYMENT_TYPE", raising=False)
    monkeypatch.delenv("ALLOWED_REGIONS", raising=False)
