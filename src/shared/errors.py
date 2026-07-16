"""Shared error types for core pipeline modules."""

from __future__ import annotations


class PipelineError(Exception):
    """Base error for all pipeline failures."""


class ConfigurationError(PipelineError):
    """Raised when static configuration or environment inputs are invalid."""


class ContractError(PipelineError):
    """Raised when a required inter-module contract is incomplete or invalid."""


class DependencyUnavailableError(PipelineError):
    """Raised when an optional upstream dependency cannot be reached."""
