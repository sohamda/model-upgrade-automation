"""Redaction helpers for logs and persisted live-evaluation result payloads.

Strips or masks credential-adjacent material (bearer tokens, endpoint URLs,
and common key/secret markers) before a string, log line, or JSON-serializable
payload is written to disk or a log stream. Deployment NAMES are left
untouched (they are not secrets); only host/endpoint URLs, bearer tokens, and
key/secret-shaped values are redacted (Council conditions C6, C7, C9).
"""

from __future__ import annotations

import re

_BEARER_TOKEN_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-_.=]+", re.IGNORECASE)
_URL_PATTERN = re.compile(r"https?://\S+")
_KEY_VALUE_PATTERN = re.compile(
    r"(?i)(api[-_]?key|secret|password|client[-_]?secret)\s*[:=]\s*\S+"
)
_REDACTED_ENDPOINT = "[REDACTED-ENDPOINT]"
_REDACTED_TOKEN = "Bearer [REDACTED]"
_REDACTED_KEY_VALUE = r"\1=[REDACTED]"
_REDACTED_VALUE = "[REDACTED]"

# Dict/JSON keys whose values are always dropped outright, regardless of
# content -- e.g. an "endpoint" key must never surface a raw project/account
# URL in a persisted result even if the value itself looks benign.
_SENSITIVE_KEY_MARKERS = ("endpoint", "token", "credential", "secret", "authorization")


def redact_text(value: str) -> str:
    """Return ``value`` with bearer tokens, URLs, and key-value secrets masked."""

    redacted = _BEARER_TOKEN_PATTERN.sub(_REDACTED_TOKEN, value)
    redacted = _URL_PATTERN.sub(_REDACTED_ENDPOINT, redacted)
    redacted = _KEY_VALUE_PATTERN.sub(_REDACTED_KEY_VALUE, redacted)
    return redacted


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS)


def redact_mapping(value: object) -> object:
    """Recursively redact a JSON-like structure (dict/list/str/other).

    Values under a sensitive-looking key (matching :data:`_SENSITIVE_KEY_MARKERS`,
    e.g. any key containing ``endpoint``, ``token``, ``credential``, ``secret``
    or ``authorization``) are replaced outright; every other string leaf is
    passed through :func:`redact_text`. Non-string, non-container values are
    returned unchanged.
    """

    if isinstance(value, dict):
        return {
            key: _REDACTED_VALUE if isinstance(key, str) and _is_sensitive_key(key) else redact_mapping(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_mapping(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value
