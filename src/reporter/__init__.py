"""Local-first TG6 reporter package."""

from __future__ import annotations

from pathlib import Path

from src.reporter.models import ReporterExecutionResult

__all__ = ["execute_local_report"]


def execute_local_report(repo_root: Path, artifact_root: Path, output_root: Path | None = None) -> ReporterExecutionResult:
	"""Proxy the package entrypoint to the reporter service lazily."""

	from src.reporter.service import execute_local_report as _execute_local_report

	return _execute_local_report(repo_root, artifact_root, output_root)