"""Unit tests for the shared Azure CLI invocation helpers."""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from src.shared.az_cli import resolve_az, run_az
from src.shared.errors import DependencyUnavailableError


def _completed(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["az"], returncode=0, stdout=stdout, stderr="")


class ResolveAzTests(unittest.TestCase):
    def test_given_az_on_path_when_resolving_then_returns_path(self) -> None:
        # Act
        with patch("shutil.which", return_value="/usr/bin/az") as mock_which:
            resolved = resolve_az()

        # Assert
        self.assertEqual(resolved, "/usr/bin/az")
        mock_which.assert_called_once_with("az")

    def test_given_az_absent_when_resolving_then_dependency_error(self) -> None:
        # Act / Assert
        with patch("shutil.which", return_value=None):
            with self.assertRaises(DependencyUnavailableError):
                resolve_az()


class RunAzTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch("shutil.which", return_value="/usr/bin/az")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_given_success_when_running_then_returns_stdout(self) -> None:
        # Act
        with patch("subprocess.run", return_value=_completed("ok")) as mock_run:
            result = run_az(["account", "show"], timeout=5)

        # Assert
        self.assertEqual(result, "ok")
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], ["/usr/bin/az", "account", "show"])
        self.assertEqual(kwargs["timeout"], 5)
        self.assertTrue(kwargs["check"])

    def test_given_missing_cli_at_launch_when_running_then_dependency_error(self) -> None:
        # Act / Assert
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            with self.assertRaises(DependencyUnavailableError):
                run_az(["account", "show"])

    def test_given_nonzero_exit_when_running_then_dependency_error(self) -> None:
        # Arrange
        error = subprocess.CalledProcessError(
            returncode=1, cmd=["az", "account", "show"], stderr="boom"
        )

        # Act / Assert
        with patch("subprocess.run", side_effect=error):
            with self.assertRaises(DependencyUnavailableError):
                run_az(["account", "show"])

    def test_given_timeout_when_running_then_dependency_error(self) -> None:
        # Arrange
        error = subprocess.TimeoutExpired(cmd=["az", "account", "show"], timeout=3)

        # Act / Assert
        with patch("subprocess.run", side_effect=error):
            with self.assertRaises(DependencyUnavailableError):
                run_az(["account", "show"], timeout=3)


if __name__ == "__main__":
    unittest.main()
