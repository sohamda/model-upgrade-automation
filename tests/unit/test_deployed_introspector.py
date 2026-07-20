"""Unit tests for Foundry deployment discovery adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
import subprocess
import unittest

from src.detector.deployed_introspector import discover_foundry_deployments
from src.shared.run_context import RunContext


def _run_context() -> RunContext:
    return RunContext(
        run_id="test-run",
        trigger_type="workflow_dispatch",
        started_at_utc=datetime.now(timezone.utc),
        github_repo="repo",
        github_run_id="1",
        azure_tenant_id="tenant",
        azure_subscription_id="sub",
        resource_group="rg",
        foundry_account_name="acct",
        foundry_project_name="project",
        aca_environment_name="aca-env",
        aca_job_name="aca-job",
        storage_account_name="stg",
        key_vault_name="kv",
        deployment_type="DataZoneStandard",
        allowed_regions=["swedencentral"],
        retirement_horizon_days=90,
        dataset_sha256="abc",
        correlation_version="v1",
    )


class DeployedIntrospectorTests(unittest.TestCase):
    @patch("shutil.which", return_value="/usr/bin/az")
    @patch("subprocess.run")
    def test_given_cli_json_when_discovering_then_models_are_normalized(
        self, mock_run, _mock_which
    ) -> None:
        # Arrange
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='[{"name":"dep1","properties":{"model":{"name":"gpt-4.1-mini","version":"2025-04-14"}}}]',
            stderr="",
        )

        # Act
        result = discover_foundry_deployments(_run_context())

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["model_id"], "gpt-4.1-mini")
        self.assertEqual(result[0]["version"], "2025-04-14")


if __name__ == "__main__":
    unittest.main()
