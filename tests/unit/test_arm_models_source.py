"""Unit tests for the ARM Models retirement source."""

from __future__ import annotations

import json
import subprocess
import unittest
from unittest.mock import patch

from src.detector.arm_models_source import ArmModelsRetirementSource
from src.shared.errors import DependencyUnavailableError


def _completed(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["az"], returncode=0, stdout=stdout, stderr="")


class ArmModelsRetirementSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        # Route az resolution through a fake path so run_az stays hermetic
        # regardless of whether az is installed on the test host.
        patcher = patch("shutil.which", return_value="/usr/bin/az")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_given_deprecating_model_when_loading_then_retiring_model_is_emitted(self) -> None:
        # Arrange
        payload = {
            "value": [
                {
                    "model": {
                        "name": "gpt-4o",
                        "version": "2024-05-13",
                        "format": "OpenAI",
                        "lifecycleStatus": "Deprecating",
                        "deprecation": {"inference": "2026-08-15T00:00:00Z"},
                        "skus": [{"name": "Standard", "deprecationDate": "2026-09-01"}],
                    }
                }
            ]
        }
        source = ArmModelsRetirementSource(subscription_id="sub", locations=["eastus"])

        # Act
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            result = source.load()

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model_id, "gpt-4o")
        self.assertEqual(result[0].current_version, "2024-05-13")
        self.assertEqual(result[0].retirement_date, "2026-08-15")
        self.assertIsNone(result[0].replacement_family)

    def test_given_no_inference_when_loading_then_earliest_sku_date_is_used(self) -> None:
        # Arrange
        payload = {
            "value": [
                {
                    "model": {
                        "name": "gpt-4",
                        "version": "0613",
                        "lifecycleStatus": "Deprecated",
                        "skus": [
                            {"name": "Standard", "deprecationDate": "2026-10-01"},
                            {"name": "GlobalStandard", "deprecationDate": "2026-05-01"},
                        ],
                    }
                }
            ]
        }
        source = ArmModelsRetirementSource(subscription_id="sub", locations=["eastus"])

        # Act
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            result = source.load()

        # Assert
        self.assertEqual(result[0].retirement_date, "2026-05-01")

    def test_given_generally_available_only_when_loading_then_dependency_error(self) -> None:
        # Arrange
        payload = {
            "value": [
                {
                    "model": {
                        "name": "gpt-4.1",
                        "version": "2026-01-12",
                        "lifecycleStatus": "GenerallyAvailable",
                        "skus": [{"name": "Standard"}],
                    }
                }
            ]
        }
        source = ArmModelsRetirementSource(subscription_id="sub", locations=["eastus"])

        # Act / Assert
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            with self.assertRaises(DependencyUnavailableError):
                source.load()

    def test_given_missing_cli_when_loading_then_dependency_error(self) -> None:
        # Arrange
        source = ArmModelsRetirementSource(subscription_id="sub", locations=["eastus"])

        # Act / Assert
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            with self.assertRaises(DependencyUnavailableError):
                source.load()

    def test_given_cli_error_when_loading_then_dependency_error(self) -> None:
        # Arrange
        source = ArmModelsRetirementSource(subscription_id="sub", locations=["eastus"])
        error = subprocess.CalledProcessError(1, ["az"], stderr="forbidden")

        # Act / Assert
        with patch("subprocess.run", side_effect=error):
            with self.assertRaises(DependencyUnavailableError):
                source.load()


if __name__ == "__main__":
    unittest.main()
