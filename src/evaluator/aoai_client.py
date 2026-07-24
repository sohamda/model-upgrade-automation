"""Live Azure OpenAI candidate response provider for the validated eval seam.

This module supplies the ``(model_id, prompt) -> str | None`` response
provider consumed by
:attr:`src.evaluator.quality_safety_eval_client.FoundryQualitySafetyEvalClient.response_provider`
(the injectable seam validated under Council Decision #48). Importing this
module never requires the ``[evaluation]`` optional extra: the ``openai`` and
``azure-identity`` imports are deferred to inside :meth:`AoaiClient.chat_completion`,
mirroring the existing lazy-import pattern established in
``scripts/refresh_quality_safety_benchmarks.py::_build_live_response_provider``.
Credentials are constructed in-method via keyless ``DefaultAzureCredential``
and are never logged, cached across calls, or serialized.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from src.evaluator.quality_safety_eval_client import (
    DEFAULT_INFERENCE_API_VERSION,
    derive_aoai_endpoint,
)
from src.shared.errors import DependencyUnavailableError

# Token scope for Azure OpenAI data-plane calls (matches the seam's judge path).
AOAI_TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."
DEFAULT_MAX_TOKENS = 512

# Bounded-retry defaults (resilience condition: 3-5 attempts, 30-60s timeout).
MIN_RETRY_ATTEMPTS = 3
MAX_RETRY_ATTEMPTS = 5
DEFAULT_RETRY_ATTEMPTS = 4
MIN_TIMEOUT_SECONDS = 30.0
MAX_TIMEOUT_SECONDS = 60.0
DEFAULT_TIMEOUT_SECONDS = 45.0
_BASE_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 20.0
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

# Additive per-model-family request shape used when config/models.yaml has no
# model_api_shapes section (e.g. a fresh checkout or hermetic fixture repo).
DEFAULT_API_SHAPE: dict[str, object] = {
    "use_system_role": True,
    "temperature": 0,
    "seed": 42,
    "max_tokens_param": "max_tokens",
}


def _read_models_yaml(repo_root: Path) -> dict[str, object]:
    """Return the raw config/models.yaml mapping, or ``{}`` when unreadable."""

    models_path = repo_root / "config" / "models.yaml"
    try:
        with models_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def load_model_api_shapes(repo_root: Path) -> dict[str, dict[str, object]]:
    """Load the additive ``model_api_shapes`` section from config/models.yaml."""

    shapes = _read_models_yaml(repo_root).get("model_api_shapes")
    return shapes if isinstance(shapes, dict) else {}


def load_deployment_map(repo_root: Path) -> dict[str, str]:
    """Load the additive ``deployments`` (model_id -> deployment name) map."""

    deployments = _read_models_yaml(repo_root).get("deployments")
    if not isinstance(deployments, dict):
        return {}
    return {str(key): str(value) for key, value in deployments.items() if value}


def load_default_judge(repo_root: Path) -> dict[str, str]:
    """Load the additive ``default_judge`` block from config/models.yaml.

    Returns ``{"model_id": ..., "version": ...}`` (empty strings when unset).
    This is the pinned, cross-generation-independent judge (gpt-4.1) used as a
    fallback when the ``JUDGE_MODEL`` env var (the owned judge deployment name)
    is not provided; it is never a candidate model (Council C10, PD-01).
    """

    block = _read_models_yaml(repo_root).get("default_judge")
    block = block if isinstance(block, dict) else {}
    return {
        "model_id": str(block.get("model_id", "")),
        "version": str(block.get("version", "")),
    }


def resolve_api_shape(
    model_id: str, model_api_shapes: dict[str, dict[str, object]] | None
) -> dict[str, object]:
    """Resolve the request shape for ``model_id``.

    Match order: exact ``model_id`` key, then a family-prefix key (any
    non-``default`` key that ``model_id`` starts with, e.g. ``o3`` matches
    ``o3-mini``), then ``default``. Falls back to :data:`DEFAULT_API_SHAPE`
    when no shapes are configured at all.
    """

    shapes = model_api_shapes or {}
    if model_id in shapes:
        return shapes[model_id]
    for key, shape in shapes.items():
        if key != "default" and model_id.startswith(key):
            return shape
    return shapes.get("default", DEFAULT_API_SHAPE)


def _is_reasoning_shape(shape: dict[str, object]) -> bool:
    """Return whether ``shape`` describes an o-series reasoning model.

    The ``is_reasoning_model`` flag is AUTHORITATIVE (LIVE-BUG-01): when true,
    the request must use ``max_completion_tokens`` and must omit
    ``temperature``/``seed`` and the system role, because those models reject
    ``max_tokens``/``temperature`` with HTTP 400. Absent/false preserves the
    legacy field-by-field behavior (backward compatible).
    """

    return bool(shape.get("is_reasoning_model", False))


def _build_messages(shape: dict[str, object], prompt: str) -> list[dict[str, str]]:
    # Reasoning-family shapes (e.g. o3) omit the system role entirely; the flag
    # is authoritative and overrides an inconsistent use_system_role value.
    if _is_reasoning_shape(shape) or not shape.get("use_system_role", True):
        return [{"role": "user", "content": f"{DEFAULT_SYSTEM_PROMPT}\n\n{prompt}"}]
    return [
        {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


def _build_completion_kwargs(shape: dict[str, object]) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    reasoning = _is_reasoning_shape(shape)
    # Reasoning models reject temperature/seed (HTTP 400); the flag forces them
    # off regardless of any stale explicit values in the shape.
    if not reasoning:
        temperature = shape.get("temperature")
        if temperature is not None:
            kwargs["temperature"] = temperature
        seed = shape.get("seed")
        if seed is not None:
            kwargs["seed"] = seed
    # A reasoning shape always sends max_completion_tokens even if the config's
    # max_tokens_param was left at the default; a standard shape honors its
    # configured param name (defaulting to max_tokens).
    if reasoning:
        max_tokens_param = "max_completion_tokens"
    else:
        max_tokens_param = str(shape.get("max_tokens_param", "max_tokens"))
    kwargs[max_tokens_param] = int(shape.get("max_tokens", DEFAULT_MAX_TOKENS))
    return kwargs


def _clamp_timeout(value: float) -> float:
    return max(MIN_TIMEOUT_SECONDS, min(MAX_TIMEOUT_SECONDS, value))


def _clamp_attempts(value: int) -> int:
    return max(MIN_RETRY_ATTEMPTS, min(MAX_RETRY_ATTEMPTS, value))


def _extract_status_code(error: Exception) -> int | None:
    status = getattr(error, "status_code", None)
    if isinstance(status, int):
        return status
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def _is_timeout_error(error: Exception) -> bool:
    return "timeout" in type(error).__name__.lower()


def _retry_after_seconds(error: Exception) -> float | None:
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return None
    raw = getter("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _full_jitter_delay(attempt: int) -> float:
    ceiling = min(_MAX_BACKOFF_SECONDS, _BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))
    return random.uniform(0, ceiling)


@dataclass(slots=True)
class AoaiClient:
    """Keyless Azure OpenAI chat-completion provider for candidate scoring.

    Constructed with the owned Foundry project endpoint (never a third-party
    endpoint). ``model_id_deployment_map`` and ``model_api_shapes`` are the
    additive config sections loaded from config/models.yaml (:func:`load_deployment_map`,
    :func:`load_model_api_shapes`). All optional-dependency imports (``openai``,
    ``azure-identity``) and credential construction happen lazily inside
    :meth:`chat_completion`; nothing is imported or authenticated at
    construction or module-import time.
    """

    azure_ai_project: str
    model_id_deployment_map: dict[str, str] = field(default_factory=dict)
    model_api_shapes: dict[str, dict[str, object]] = field(default_factory=dict)
    credential: object | None = None
    inference_api_version: str = DEFAULT_INFERENCE_API_VERSION
    max_attempts: int = DEFAULT_RETRY_ATTEMPTS
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def _resolve_deployment(self, model_id: str, deployment_ref: str | None) -> str | None:
        """Resolve the owned deployment name: kwarg -> config map -> model_id.

        Returns ``None`` (never a fabricated name) when nothing resolves.
        """

        if deployment_ref:
            return deployment_ref
        mapped = self.model_id_deployment_map.get(model_id)
        if mapped:
            return mapped
        return model_id or None

    def chat_completion(
        self, model_id: str, prompt: str, *, deployment_ref: str | None = None
    ) -> str | None:
        """Return one candidate assistant response, or ``None`` on failure.

        Matches the ``Callable[[str, str], str | None]`` seam contract of
        ``FoundryQualitySafetyEvalClient.response_provider`` (exactly two
        positional args). ``deployment_ref`` is supplied by the caller's
        closure (the candidate's owned deployment NAME) rather than a third
        positional parameter, preserving that contract.
        """

        deployment_name = self._resolve_deployment(model_id, deployment_ref)
        if not deployment_name:
            return None

        try:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider
            from openai import AzureOpenAI
        except ImportError as error:
            raise DependencyUnavailableError(
                "The 'evaluation' optional dependencies are not installed. "
                "Install them with: pip install -e '.[evaluation]'."
            ) from error

        shape = resolve_api_shape(model_id, self.model_api_shapes)
        messages = _build_messages(shape, prompt)
        completion_kwargs = _build_completion_kwargs(shape)
        endpoint = derive_aoai_endpoint(self.azure_ai_project)
        credential = self.credential or DefaultAzureCredential()
        token_provider = get_bearer_token_provider(credential, AOAI_TOKEN_SCOPE)
        timeout_seconds = _clamp_timeout(self.timeout_seconds)

        def _invoke() -> str | None:
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider,
                api_version=self.inference_api_version,
                timeout=timeout_seconds,
            )
            response = client.chat.completions.create(
                model=deployment_name,
                messages=messages,
                **completion_kwargs,
            )
            choices = getattr(response, "choices", None)
            if not choices:
                return None
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None)
            return content if isinstance(content, str) else None

        return self._with_retry(_invoke)

    def _with_retry(self, call: Callable[[], str | None]) -> str | None:
        """Invoke ``call`` with bounded exponential backoff plus full jitter.

        Retries only on HTTP 429/5xx or timeout errors, honoring a
        ``Retry-After`` header when present. Non-retryable errors fail fast to
        ``None``; exhaustion also returns ``None`` (UNSCORED) rather than a
        fabricated response. Attempts run strictly sequentially -- this
        wrapper never issues concurrent calls.
        """

        attempts = _clamp_attempts(self.max_attempts)
        for attempt in range(1, attempts + 1):
            try:
                return call()
            except Exception as error:  # noqa: BLE001 - classified below.
                retryable = (
                    _extract_status_code(error) in RETRYABLE_STATUS_CODES
                    or _is_timeout_error(error)
                )
                if not retryable or attempt == attempts:
                    return None
                delay = _retry_after_seconds(error)
                if delay is None:
                    delay = _full_jitter_delay(attempt)
                time.sleep(delay)
        return None
