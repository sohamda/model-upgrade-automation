#!/usr/bin/env python3
"""Deterministic TG9 full decision packet generator.

Builds the final TG9 release readiness packet from TG8 gate outputs and TG9 slice1
intake artifacts under artifacts/tg9-release-readiness/<run_id>/.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = "1.0.0"

MANDATORY_GATE_IDS: tuple[str, ...] = (
    "QG-UNIT-01",
    "QG-INT-01",
    "QG-CONFIG-01",
    "QG-SEC-01",
    "QG-REL-01",
    "QG-E2E-01",
)

TG8_REQUIRED_FILES: tuple[str, ...] = (
    "gate-results.json",
    "gate-summary.md",
    "evidence-index.json",
    "tg9-handoff.md",
)

TG9_SLICE1_REQUIRED_FILES: tuple[str, ...] = (
    "intake-payload.json",
    "provisional-decision.md",
    "evidence-index.json",
)


def create_parser() -> argparse.ArgumentParser:
    """Create the TG9 full argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate final TG9 release-readiness decision packet using TG8 evidence "
            "and TG9 slice1 intake artifacts."
        )
    )
    parser.add_argument(
        "--tg8-run-id",
        type=str,
        default="tg8-full-20260717",
        help="TG8 run identifier under artifacts/tg8-quality-gates/.",
    )
    parser.add_argument(
        "--tg9-slice1-run-id",
        type=str,
        default="tg9-slice1-20260717",
        help="TG9 slice1 run identifier under artifacts/tg9-release-readiness/.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="TG9 full run identifier. Defaults to tg9-full-<tg8_run_id>.",
    )
    parser.add_argument(
        "--tg8-root",
        type=Path,
        default=Path("artifacts/tg8-quality-gates"),
        help="Root directory containing TG8 run folders.",
    )
    parser.add_argument(
        "--tg9-root",
        type=Path,
        default=Path("artifacts/tg9-release-readiness"),
        help="Root directory containing TG9 run folders.",
    )
    return parser


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"Missing required file: {path}"
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON in {path}: {exc}"


def _read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except FileNotFoundError:
        return None, f"Missing required file: {path}"
    except OSError as exc:
        return None, f"Failed reading file {path}: {exc}"


def _normalize_blockers(slice1_payload: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in slice1_payload.get("blockers", []):
        if not isinstance(raw, dict):
            continue
        status = str(raw.get("status", "UNKNOWN"))
        severity = str(raw.get("severity", "UNKNOWN")).upper()
        is_open = bool(raw.get("is_open", status.strip().lower() not in {"closed", "resolved", "none", "n/a"}))
        normalized.append(
            {
                "gate_id": str(raw.get("gate_id", "UNKNOWN")),
                "severity": severity,
                "owner": str(raw.get("owner", "UNKNOWN")),
                "status": status,
                "blocker": str(raw.get("blocker", "")),
                "is_open": is_open,
                "is_high_or_critical": is_open and severity in {"HIGH", "CRITICAL"},
            }
        )
    return normalized


def _decision_logic(
    tg8_gate_results: dict[str, Any],
    tg8_handoff_text: str,
    slice1_payload: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    gate_map = {
        gate.get("gate_id"): str(gate.get("status", "MISSING"))
        for gate in tg8_gate_results.get("gates", [])
        if isinstance(gate, dict)
    }

    mandatory_gate_statuses = {
        gate_id: gate_map.get(gate_id, "MISSING")
        for gate_id in MANDATORY_GATE_IDS
    }

    all_mandatory_pass = all(
        mandatory_gate_statuses.get(gate_id) == "PASS"
        for gate_id in MANDATORY_GATE_IDS
    )

    recommendation = str(slice1_payload.get("recommendation", "UNKNOWN"))
    overall_status = str(tg8_gate_results.get("overall_status", "UNKNOWN"))

    blockers = _normalize_blockers(slice1_payload)
    open_blockers = [blocker for blocker in blockers if blocker.get("is_open")]
    high_critical_open = [
        blocker for blocker in open_blockers if blocker.get("is_high_or_critical")
    ]

    rationale: list[str] = [
        f"TG8 overall status is {overall_status}",
        f"TG8 recommendation is {recommendation}",
        f"Mandatory gates passing: {all_mandatory_pass}",
        f"Open blocker count: {len(open_blockers)}",
    ]

    blockers_summary: list[str] = []
    if open_blockers:
        for blocker in open_blockers:
            blockers_summary.append(
                f"{blocker['gate_id']} {blocker['severity']} {blocker['status']}: {blocker['blocker']}"
            )
    else:
        blockers_summary.append("No open blockers reported")

    coherence_pass = bool(slice1_payload.get("coherence_pass", False))

    if not all_mandatory_pass:
        decision_status = "NO_GO"
        release_posture = "HOLD"
        rationale.append("One or more mandatory gates are not PASS")
    elif recommendation == "RECOMMEND_HOLD":
        decision_status = "NO_GO"
        release_posture = "HOLD"
        rationale.append("TG8 explicitly recommends hold")
    elif high_critical_open:
        decision_status = "NO_GO"
        release_posture = "HOLD"
        rationale.append("Open HIGH/CRITICAL blockers exist")
    elif recommendation == "RECOMMEND_RELEASE" and overall_status == "PASS":
        decision_status = "GO"
        release_posture = "RELEASE_READY" if coherence_pass else "CONDITIONAL_GO"
        if not coherence_pass:
            rationale.append("Slice1 coherence checks are not fully passing; proceeding with explicit residual risks")
    else:
        decision_status = "REQUIRES_DECISION"
        release_posture = "HOLD"
        rationale.append("Inputs are mixed and require manual release authority decision")

    decision_payload = {
        "schema_version": SCHEMA_VERSION,
        "decision_type": "tg9_release_readiness",
        "generated_at_utc": _utc_now_iso(),
        "source": {
            "tg8_run_id": str(tg8_gate_results.get("run_id", "UNKNOWN")),
            "tg9_slice1_run_id": str(slice1_payload.get("run_id", "UNKNOWN")),
        },
        "decision": {
            "status": decision_status,
            "release_posture": release_posture,
            "recommendation_honored": recommendation,
        },
        "gate_evaluation": {
            "overall_status": overall_status,
            "mandatory_gate_statuses": mandatory_gate_statuses,
            "all_mandatory_pass": all_mandatory_pass,
        },
        "blockers": {
            "open_count": len(open_blockers),
            "high_or_critical_open_count": len(high_critical_open),
            "items": open_blockers,
        },
        "rationale": rationale,
        "handoff_excerpt": tg8_handoff_text,
    }

    return decision_payload, blockers_summary, blockers


def _render_release_checklist(decision_payload: dict[str, Any]) -> str:
    status = decision_payload["decision"]["status"]
    posture = decision_payload["decision"]["release_posture"]
    mandatory = decision_payload["gate_evaluation"]["mandatory_gate_statuses"]
    lines = [
        "# TG9 Release Checklist",
        "",
        f"- Decision Status: **{status}**",
        f"- Release Posture: **{posture}**",
        "",
        "## Mandatory Gate Confirmation",
        "",
        "| Gate ID | Status | Ready |",
        "|---|---|---|",
    ]

    for gate_id in MANDATORY_GATE_IDS:
        gate_status = mandatory.get(gate_id, "MISSING")
        ready = "YES" if gate_status == "PASS" else "NO"
        lines.append(f"| {gate_id} | {gate_status} | {ready} |")

    lines.extend(
        [
            "",
            "## Operator Checklist",
            "",
            "- [x] TG8 recommendation and mandatory gate statuses reconciled",
            "- [x] Blockers reviewed and release posture recorded",
            "- [x] Decision payload and manifest are valid parseable JSON",
            "- [ ] Release approver sign-off captured externally",
        ]
    )

    return "\n".join(lines) + "\n"


def _render_rollback_plan(decision_payload: dict[str, Any]) -> str:
    status = decision_payload["decision"]["status"]
    lines = [
        "# TG9 Rollback Plan",
        "",
        "## Trigger Conditions",
        "",
        "- Any post-release verification check fails",
        "- New Severity High/Critical blocker is opened",
        "- Reliability regression breaches TG7 baseline thresholds",
        "",
        "## Rollback Actions",
        "",
        "1. Halt further rollout activity immediately.",
        "2. Revert to last known good deployment/version in the active environment.",
        "3. Re-run TG8 mandatory validation gates for confidence restoration.",
        "4. Re-open TG9 decision packet with updated evidence and blocker status.",
        "",
        "## Communications",
        "",
        "- Notify release owner and on-call operator.",
        "- Record rollback timestamp, trigger, and action owner in incident records.",
        "",
        "## Current Context",
        "",
        f"- Decision status at packet generation time: **{status}**",
    ]
    return "\n".join(lines) + "\n"


def _render_post_release_verification(decision_payload: dict[str, Any]) -> str:
    posture = decision_payload["decision"]["release_posture"]
    lines = [
        "# TG9 Post-Release Verification",
        "",
        f"- Release posture: **{posture}**",
        "",
        "## Verification Steps",
        "",
        "1. Confirm deployment health checks pass in target environment.",
        "2. Confirm reliability indicators remain within TG7 baseline threshold.",
        "3. Confirm no new mandatory gate regressions are reported.",
        "4. Confirm no new open High/Critical blockers are introduced.",
        "",
        "## Evidence Recording",
        "",
        "- Append run links, logs, and metric snapshots to the release record.",
        "- Update TG9 packet if any verification result changes release posture.",
    ]
    return "\n".join(lines) + "\n"


def _render_open_risks(slice1_payload: dict[str, Any], blockers: list[dict[str, Any]]) -> str:
    lines = [
        "# TG9 Open Risks",
        "",
        "## Active Risks",
        "",
    ]

    has_risk = False
    for check in slice1_payload.get("coherence_checks", []):
        if isinstance(check, dict) and not bool(check.get("pass", False)):
            has_risk = True
            lines.append(
                f"- {check.get('name', 'unknown-check')}: {check.get('detail', 'no detail provided')}"
            )

    for blocker in blockers:
        if blocker.get("is_open", False):
            has_risk = True
            lines.append(
                f"- Open blocker {blocker['gate_id']} ({blocker['severity']}): {blocker['blocker']}"
            )

    if not has_risk:
        lines.append("- None. No open risks detected at packet generation time.")

    return "\n".join(lines) + "\n"


def _build_evidence_index(
    run_id: str,
    output_dir: Path,
    tg8_dir: Path,
    slice1_dir: Path,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at_utc": _utc_now_iso(),
        "entries": [
            {
                "type": "input",
                "path": str(tg8_dir / "gate-results.json"),
                "description": "TG8 machine-readable gate outcomes",
            },
            {
                "type": "input",
                "path": str(tg8_dir / "tg9-handoff.md"),
                "description": "TG8 recommendation and blocker handoff",
            },
            {
                "type": "input",
                "path": str(slice1_dir / "intake-payload.json"),
                "description": "TG9 slice1 normalized intake payload",
            },
            {
                "type": "output",
                "path": str(output_dir / "final-decision.json"),
                "description": "Final TG9 go/no-go decision payload",
            },
            {
                "type": "output",
                "path": str(output_dir / "release-checklist.md"),
                "description": "Operator release readiness checklist",
            },
            {
                "type": "output",
                "path": str(output_dir / "rollback-plan.md"),
                "description": "Rollback procedures and triggers",
            },
            {
                "type": "output",
                "path": str(output_dir / "post-release-verification.md"),
                "description": "Post-release verification plan",
            },
            {
                "type": "output",
                "path": str(output_dir / "open-risks.md"),
                "description": "Residual open risks or explicit none",
            },
            {
                "type": "output",
                "path": str(output_dir / "evidence-index.json"),
                "description": "TG9 full evidence manifest",
            },
        ],
    }


def _validate_json(path: Path) -> tuple[bool, str]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True, "parseable"
    except json.JSONDecodeError as exc:
        return False, str(exc)


def run() -> int:
    args = create_parser().parse_args()

    tg8_root = args.tg8_root if args.tg8_root.is_absolute() else REPO_ROOT / args.tg8_root
    tg9_root = args.tg9_root if args.tg9_root.is_absolute() else REPO_ROOT / args.tg9_root

    tg8_run_id = args.tg8_run_id
    tg9_slice1_run_id = args.tg9_slice1_run_id
    run_id = args.run_id or f"tg9-full-{tg8_run_id}"

    tg8_dir = tg8_root / tg8_run_id
    slice1_dir = tg9_root / tg9_slice1_run_id
    output_dir = tg9_root / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []

    for required in TG8_REQUIRED_FILES:
        if not (tg8_dir / required).exists():
            errors.append(f"Missing required TG8 artifact: {tg8_dir / required}")

    for required in TG9_SLICE1_REQUIRED_FILES:
        if not (slice1_dir / required).exists():
            errors.append(f"Missing required TG9 slice1 artifact: {slice1_dir / required}")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return EXIT_ERROR

    tg8_gate_results, err = _read_json(tg8_dir / "gate-results.json")
    if err:
        errors.append(err)

    tg8_handoff_text, err = _read_text(tg8_dir / "tg9-handoff.md")
    if err:
        errors.append(err)

    slice1_payload, err = _read_json(slice1_dir / "intake-payload.json")
    if err:
        errors.append(err)

    if errors or tg8_gate_results is None or tg8_handoff_text is None or slice1_payload is None:
        for error in errors:
            print(error, file=sys.stderr)
        return EXIT_ERROR

    decision_payload, blockers_summary, blockers = _decision_logic(
        tg8_gate_results=tg8_gate_results,
        tg8_handoff_text=tg8_handoff_text,
        slice1_payload=slice1_payload,
    )

    final_decision_path = output_dir / "final-decision.json"
    release_checklist_path = output_dir / "release-checklist.md"
    rollback_plan_path = output_dir / "rollback-plan.md"
    post_release_verification_path = output_dir / "post-release-verification.md"
    open_risks_path = output_dir / "open-risks.md"
    evidence_index_path = output_dir / "evidence-index.json"

    final_decision_path.write_text(json.dumps(decision_payload, indent=2) + "\n", encoding="utf-8")
    release_checklist_path.write_text(_render_release_checklist(decision_payload), encoding="utf-8")
    rollback_plan_path.write_text(_render_rollback_plan(decision_payload), encoding="utf-8")
    post_release_verification_path.write_text(
        _render_post_release_verification(decision_payload),
        encoding="utf-8",
    )
    open_risks_path.write_text(
        _render_open_risks(slice1_payload=slice1_payload, blockers=blockers),
        encoding="utf-8",
    )

    evidence_index_payload = _build_evidence_index(
        run_id=run_id,
        output_dir=output_dir,
        tg8_dir=tg8_dir,
        slice1_dir=slice1_dir,
    )
    evidence_index_path.write_text(
        json.dumps(evidence_index_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    decision_parse_ok, decision_parse_detail = _validate_json(final_decision_path)
    manifest_parse_ok, manifest_parse_detail = _validate_json(evidence_index_path)

    print(f"TG9 full output: {output_dir}")
    print(f"decision_status: {decision_payload['decision']['status']}")
    print(f"release_posture: {decision_payload['decision']['release_posture']}")
    print("blockers_summary:")
    for entry in blockers_summary:
        print(f"- {entry}")
    print(f"json_parse_final_decision: {decision_parse_ok} ({decision_parse_detail})")
    print(f"json_parse_evidence_index: {manifest_parse_ok} ({manifest_parse_detail})")

    if not decision_parse_ok or not manifest_parse_ok:
        return EXIT_FAILURE

    return EXIT_SUCCESS if decision_payload["decision"]["status"] == "GO" else EXIT_FAILURE


def main() -> int:
    """Main entrypoint with deterministic exit handling."""
    try:
        return run()
    except KeyboardInterrupt:
        print("Interrupted by user", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
