#!/usr/bin/env python3
"""Deterministic entrypoint for TG8 Slice 1 quality gate evidence generation.

Populates the frozen TG8 gate taxonomy (QG-UNIT-01, QG-INT-01, QG-CONFIG-01,
QG-SEC-01, QG-REL-01, QG-E2E-01) into a schema-valid evidence package under
``artifacts/tg8-quality-gates/<run_id>/``. Only QG-REL-01 is evaluated in this
slice, by invoking ``scripts/check_tg7_reliability_gate.py`` against the TG7
baseline and latest evidence artifacts. The remaining gates are represented as
not-run placeholders while preserving the gate status enum
PASS/FAIL/ERROR.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2

REPO_ROOT = Path(__file__).resolve().parent.parent

SCHEMA_VERSION = "1.0.0"

GateStatus = Literal["PASS", "FAIL", "ERROR"]

MANDATORY_GATE_IDS: tuple[str, ...] = (
    "QG-UNIT-01",
    "QG-INT-01",
    "QG-CONFIG-01",
    "QG-SEC-01",
    "QG-REL-01",
    "QG-E2E-01",
)

GATE_CATEGORIES: dict[str, str] = {
    "QG-UNIT-01": "unit",
    "QG-INT-01": "integration",
    "QG-CONFIG-01": "config",
    "QG-SEC-01": "security",
    "QG-REL-01": "reliability",
    "QG-E2E-01": "e2e",
}


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Run TG8 Slice 1: evaluate QG-REL-01 via the TG7 reliability "
            "checker and publish a schema-valid TG8 evidence package with "
            "placeholder gates for the remaining categories."
        )
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("artifacts/gatea-policy-remediation-20260717/tg7-reliability-baseline.json"),
        help="Path to the TG7 reliability baseline JSON.",
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("artifacts/gatea-policy-remediation-20260717/tg7-reliability-latest-evidence.sample.json"),
        help="Path to the TG7 latest reliability evidence JSON.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/tg8-quality-gates"),
        help="Root directory for TG8 quality gate evidence packages.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Explicit run identifier. Defaults to a UTC timestamp-based run id.",
    )
    return parser


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_run_id() -> str:
    return f"tg8-s1-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _placeholder_gate(gate_id: str) -> dict[str, Any]:
    """Build a placeholder gate record for a not-yet-implemented category."""
    return {
        "gate_id": gate_id,
        "category": GATE_CATEGORIES[gate_id],
        "status": "ERROR",
        "execution_state": "NOT_RUN",
        "command": None,
        "inputs": [],
        "outputs": [],
        "reasons": ["Not run in TG8 Slice 1: category runner not yet implemented"],
        "duration_seconds": 0.0,
    }


def _parse_reasons(stdout: str) -> list[str]:
    """Extract fail reasons emitted by check_tg7_reliability_gate.py."""
    reasons: list[str] = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("reason_") and ":" in stripped:
            reasons.append(stripped.split(":", 1)[1].strip())
        elif stripped.startswith("reason:"):
            reasons.append(stripped.split(":", 1)[1].strip())
    return reasons


def run_reliability_gate(baseline: Path, evidence: Path) -> dict[str, Any]:
    """Invoke the TG7 reliability checker and normalize its result into a QG-REL-01 record."""
    checker_script = REPO_ROOT / "scripts" / "check_tg7_reliability_gate.py"
    command = [
        sys.executable,
        str(checker_script),
        "--baseline",
        str(baseline),
        "--evidence",
        str(evidence),
    ]

    start = time.perf_counter()
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        duration = time.perf_counter() - start
        return {
            "gate_id": "QG-REL-01",
            "category": "reliability",
            "status": "ERROR",
            "execution_state": "EXECUTED",
            "command": " ".join(command),
            "inputs": [str(baseline), str(evidence)],
            "outputs": [],
            "reasons": [f"Failed to execute reliability checker: {exc}"],
            "duration_seconds": round(duration, 3),
            "exit_code": None,
            "raw_stdout": "",
            "raw_stderr": "",
        }
    duration = time.perf_counter() - start

    status: GateStatus
    if result.returncode == EXIT_SUCCESS:
        status = "PASS"
    elif result.returncode == EXIT_FAILURE:
        status = "FAIL"
    else:
        status = "ERROR"

    reasons = _parse_reasons(result.stdout)
    if status == "ERROR" and not reasons and result.stderr.strip():
        reasons = [result.stderr.strip()]

    return {
        "gate_id": "QG-REL-01",
        "category": "reliability",
        "status": status,
        "execution_state": "EXECUTED",
        "command": " ".join(command),
        "inputs": [str(baseline), str(evidence)],
        "outputs": [],
        "reasons": reasons,
        "duration_seconds": round(duration, 3),
        "exit_code": result.returncode,
        "raw_stdout": result.stdout,
        "raw_stderr": result.stderr,
    }


def _compute_overall_status(gates: list[dict[str, Any]]) -> str:
    """Roll up individual gate statuses into an informational overall status.

    ERROR/FAIL take precedence for executed gates; placeholder not-run records
    yield PARTIAL; an all-PASS run yields PASS.
    """
    if any(
        gate["status"] == "ERROR" and gate.get("execution_state") != "NOT_RUN"
        for gate in gates
    ):
        return "ERROR"
    if any(gate.get("execution_state") == "NOT_RUN" for gate in gates):
        return "PARTIAL"
    statuses = {gate["status"] for gate in gates}
    if "FAIL" in statuses:
        return "FAIL"
    return "PASS"


def build_gate_results(run_id: str, baseline: Path, evidence: Path) -> dict[str, Any]:
    """Assemble the full gate-results.json payload for this run."""
    gates: list[dict[str, Any]] = []
    for gate_id in MANDATORY_GATE_IDS:
        if gate_id == "QG-REL-01":
            gates.append(run_reliability_gate(baseline, evidence))
        else:
            gates.append(_placeholder_gate(gate_id))

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at_utc": _utc_now_iso(),
        "overall_status": _compute_overall_status(gates),
        "gates": gates,
    }


def build_evidence_index(run_id: str, baseline: Path, evidence: Path, output_dir: Path) -> dict[str, Any]:
    """Assemble the evidence-index.json manifest for this run."""
    entries = [
        {
            "gate_id": "QG-REL-01",
            "type": "input",
            "path": str(baseline),
            "description": "TG7 reliability baseline SLI/SLO targets",
        },
        {
            "gate_id": "QG-REL-01",
            "type": "input",
            "path": str(evidence),
            "description": "TG7 latest reliability evidence signals",
        },
        {
            "gate_id": None,
            "type": "output",
            "path": str(output_dir / "gate-results.json"),
            "description": "Normalized TG8 gate result records for this run",
        },
        {
            "gate_id": None,
            "type": "output",
            "path": str(output_dir / "gate-summary.md"),
            "description": "Human-readable TG8 gate summary for this run",
        },
        {
            "gate_id": None,
            "type": "output",
            "path": str(output_dir / "evidence-index.json"),
            "description": "This evidence manifest",
        },
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at_utc": _utc_now_iso(),
        "entries": entries,
    }


def render_gate_summary(gate_results: dict[str, Any]) -> str:
    """Render the human-readable gate-summary.md content."""
    lines = [
        "# TG8 Quality Gate Summary",
        "",
        f"- Run ID: `{gate_results['run_id']}`",
        f"- Generated (UTC): `{gate_results['generated_at_utc']}`",
        f"- Overall status: **{gate_results['overall_status']}**",
        "",
        "| Gate ID | Category | Status | Reasons |",
        "|---|---|---|---|",
    ]
    for gate in gate_results["gates"]:
        reasons = "; ".join(gate["reasons"]) if gate["reasons"] else "-"
        lines.append(f"| {gate['gate_id']} | {gate['category']} | {gate['status']} | {reasons} |")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Only `QG-REL-01` is evaluated in TG8 Slice 1, by invoking "
            "`scripts/check_tg7_reliability_gate.py` against the TG7 baseline "
            "and latest evidence artifacts.",
            "- Remaining gates (`QG-UNIT-01`, `QG-INT-01`, `QG-CONFIG-01`, "
            "`QG-SEC-01`, `QG-E2E-01`) are placeholders with "
            "`execution_state=NOT_RUN` pending later TG8 slices.",
            "",
        ]
    )
    return "\n".join(lines)


def run() -> int:
    parser = create_parser()
    args = parser.parse_args()

    baseline: Path = args.baseline
    evidence: Path = args.evidence

    if not baseline.exists():
        print(f"ERROR: baseline file not found: {baseline}", file=sys.stderr)
        return EXIT_ERROR
    if not evidence.exists():
        print(f"ERROR: evidence file not found: {evidence}", file=sys.stderr)
        return EXIT_ERROR

    run_id = args.run_id or _default_run_id()
    output_dir = args.output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    gate_results = build_gate_results(run_id, baseline, evidence)
    evidence_index = build_evidence_index(run_id, baseline, evidence, output_dir)
    gate_summary = render_gate_summary(gate_results)

    (output_dir / "gate-results.json").write_text(json.dumps(gate_results, indent=2) + "\n", encoding="utf-8")
    (output_dir / "evidence-index.json").write_text(json.dumps(evidence_index, indent=2) + "\n", encoding="utf-8")
    (output_dir / "gate-summary.md").write_text(gate_summary, encoding="utf-8")

    reliability_gate = next(gate for gate in gate_results["gates"] if gate["gate_id"] == "QG-REL-01")

    print("TG8 Slice 1 quality gate run complete")
    print(f"run_id: {run_id}")
    print(f"evidence_package: {output_dir}")
    print(f"overall_status: {gate_results['overall_status']}")
    print(f"QG-REL-01 status: {reliability_gate['status']}")

    if reliability_gate["status"] == "ERROR":
        return EXIT_ERROR
    if reliability_gate["status"] == "FAIL":
        return EXIT_FAILURE
    return EXIT_SUCCESS


def main() -> int:
    """Main entry point with top-level error handling."""
    try:
        return run()
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except BrokenPipeError:
        sys.stderr.close()
        return EXIT_FAILURE
    except Exception as exc:  # noqa: BLE001 - top-level guard for a CLI entrypoint
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
