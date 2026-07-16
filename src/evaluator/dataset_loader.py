"""Dataset loading and SHA-256 derivation for evaluator runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.evaluator.models import DatasetRecord, EvaluationDataset
from src.shared.errors import ContractError


def load_jsonl_dataset(path: Path) -> EvaluationDataset:
    """Load JSONL records and derive a stable content hash."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise ContractError(f"Dataset file is missing: {path}") from error

    canonical_lines: list[str] = []
    records: list[DatasetRecord] = []
    for index, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise ContractError(f"Dataset row {index} in {path} is not valid JSON.") from error
        if not isinstance(payload, dict):
            raise ContractError(f"Dataset row {index} in {path} must be a JSON object.")

        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            raise ContractError(f"Dataset row {index} in {path} is missing a prompt.")

        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        canonical_lines.append(canonical)
        records.append(
            DatasetRecord(
                row_id=str(payload.get("id", f"row-{index}")),
                prompt=prompt,
                expected_response=(
                    None
                    if payload.get("expected_response") is None
                    else str(payload.get("expected_response"))
                ),
                metadata={
                    key: value
                    for key, value in payload.items()
                    if key not in {"id", "prompt", "expected_response"}
                },
            )
        )

    if not records:
        raise ContractError(f"Dataset file {path} does not contain any executable rows.")

    digest = hashlib.sha256("\n".join(canonical_lines).encode("utf-8")).hexdigest()
    return EvaluationDataset(path=path, dataset_sha256=digest, records=records)