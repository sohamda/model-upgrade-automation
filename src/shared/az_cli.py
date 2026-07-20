"""Shared Azure CLI (``az``) invocation helpers.

On Windows the Azure CLI ships as ``az.cmd``. Invoking ``subprocess`` with
``["az", ...]`` and the default ``shell=False`` raises ``FileNotFoundError``
because ``PATHEXT`` extension resolution is a shell behavior and is not applied
by the raw process-launch path. Resolving the executable via
:func:`shutil.which` returns the concrete ``az`` / ``az.cmd`` path so
``subprocess`` can launch it directly on every platform without ``shell=True``
(which would open a command-injection surface).

Callers pass CLI arguments WITHOUT the leading ``az`` token, e.g.
``run_az(["rest", "--method", "get", "--url", url, "--output", "json"])``.
"""

from __future__ import annotations

import shutil
import subprocess

from src.shared.errors import DependencyUnavailableError


def resolve_az() -> str:
    """Return the absolute path to the Azure CLI executable.

    Returns:
        The resolved ``az`` (or ``az.cmd`` on Windows) executable path.

    Raises:
        DependencyUnavailableError: when ``az`` cannot be found on ``PATH``.
    """

    az_path = shutil.which("az")
    if az_path is None:
        raise DependencyUnavailableError(
            "Azure CLI (az) not found on PATH. Install az CLI or run `az login`."
        )
    return az_path


def run_az(args: list[str], *, timeout: int | None = None) -> str:
    """Run an Azure CLI command and return its stdout.

    Args:
        args: CLI arguments WITHOUT the leading ``az`` token, e.g.
            ``["rest", "--method", "get", "--url", url, "--output", "json"]``.
        timeout: Optional per-call timeout, in seconds.

    Returns:
        The command's stdout as text.

    Raises:
        DependencyUnavailableError: when ``az`` is missing from ``PATH``, exits
            non-zero, or exceeds ``timeout``.
    """

    az_path = resolve_az()
    try:
        result = subprocess.run(
            [az_path, *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
    except FileNotFoundError as error:
        raise DependencyUnavailableError(
            "Azure CLI is not installed. Install az CLI to run Azure operations."
        ) from error
    except subprocess.CalledProcessError as error:
        raise DependencyUnavailableError(
            f"Azure CLI command failed (az {' '.join(args)}). "
            f"stderr: {(error.stderr or '').strip()}"
        ) from error
    except subprocess.TimeoutExpired as error:
        raise DependencyUnavailableError(
            f"Azure CLI command timed out after {timeout}s (az {' '.join(args)})."
        ) from error
    return result.stdout
