"""Adversarial probe-set loading and SHA-256 derivation (Phase 2, Step 2.1).

Mirrors the conventions established by ``dataset_loader.load_jsonl_dataset``:
JSONL rows, a stable content hash computed over canonicalized rows, and a
``ContractError`` on malformed or missing input. The adversarial probe set is
intentionally a SEPARATE file from the quality dataset (``general_qa.jsonl``)
so red-team probing never mixes with quality-scoring prompts (Council C11).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.evaluator.models import ProbeSet, ProbeSetRecord
from src.shared.errors import ContractError

# Bump when datasets/adversarial_probes.jsonl content changes meaningfully.
# Recorded alongside the file's SHA-256 in every audit bundle (Step 2.5).
PROBE_SET_VERSION = "v1"

# The 5 required categories (Council C11); not enforced structurally here to
# keep the loader tolerant of future category additions, but documented for
# maintainers authoring new probe rows.
REQUIRED_CATEGORIES = (
    "jailbreak_instruction_override",
    "harmful_content_elicitation",
    "pii_extraction",
    "prompt_injection",
    "tos_coc_violation",
)


def load_probe_set(path: Path) -> ProbeSet:
    """Load JSONL adversarial probe rows and derive a stable content hash."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise ContractError(f"Probe set file is missing: {path}") from error

    canonical_lines: list[str] = []
    records: list[ProbeSetRecord] = []
    for index, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise ContractError(f"Probe set row {index} in {path} is not valid JSON.") from error
        if not isinstance(payload, dict):
            raise ContractError(f"Probe set row {index} in {path} must be a JSON object.")

        row_id = str(payload.get("id", "")).strip()
        category = str(payload.get("category", "")).strip()
        prompt = str(payload.get("prompt", "")).strip()
        if not row_id or not category or not prompt:
            raise ContractError(
                f"Probe set row {index} in {path} is missing id/category/prompt."
            )

        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        canonical_lines.append(canonical)
        expected_blocked_raw = payload.get("expected_blocked")
        records.append(
            ProbeSetRecord(
                row_id=row_id,
                category=category,
                prompt=prompt,
                canary=(str(payload["canary"]) if payload.get("canary") else None),
                known_response=(
                    str(payload["known_response"]) if payload.get("known_response") else None
                ),
                expected_blocked=(
                    bool(expected_blocked_raw) if isinstance(expected_blocked_raw, bool) else None
                ),
            )
        )

    if not records:
        raise ContractError(f"Probe set file {path} does not contain any executable rows.")

    digest = hashlib.sha256("\n".join(canonical_lines).encode("utf-8")).hexdigest()
    return ProbeSet(
        path=path,
        probe_set_sha256=digest,
        probe_set_version=PROBE_SET_VERSION,
        records=records,
    )
