"""Unit tests for detector normalization."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import unittest

from src.detector.retirement_source import FixtureRetirementSource
from src.detector.service import detect_retiring_targets
from src.shared.config import load_app_config
from src.shared.run_context import build_run_context


REPO_ROOT = Path(__file__).resolve().parents[2]


class DetectorServiceTests(unittest.TestCase):
    def test_given_fixture_input_when_detecting_then_returns_configured_retiring_target(self) -> None:
        # Arrange
        config = load_app_config(REPO_ROOT)
        run_context = build_run_context(config, run_id="test-run")
        source = FixtureRetirementSource(
            REPO_ROOT / "tests" / "fixtures" / "retirement_signals.yaml"
        )

        # Act
        result = detect_retiring_targets(
            config,
            run_context,
            source,
            reference_time=datetime(2026, 7, 15, tzinfo=timezone.utc),
        )

        # Assert
        self.assertEqual(len(result.retiring_targets), 1)
        self.assertEqual(result.retiring_targets[0].model_id, "gpt-4.1-mini")
        self.assertEqual(result.retiring_targets[0].region, "swedencentral")
        self.assertEqual(result.retiring_targets[0].days_until_retirement, 31)

    def test_given_unmatched_retirement_signal_when_detecting_then_emits_warning(self) -> None:
        # Arrange
        config = load_app_config(REPO_ROOT)
        run_context = build_run_context(config, run_id="test-run")
        source = FixtureRetirementSource(
            REPO_ROOT / "tests" / "fixtures" / "retirement_signals.yaml"
        )

        # Act
        result = detect_retiring_targets(
            config,
            run_context,
            source,
            reference_time=datetime(2026, 7, 15, tzinfo=timezone.utc),
        )

        # Assert
        self.assertEqual(len(result.parse_warnings), 1)
        self.assertEqual(result.parse_warnings[0].code, "unwatched_retirement_signal")


if __name__ == "__main__":
    unittest.main()
