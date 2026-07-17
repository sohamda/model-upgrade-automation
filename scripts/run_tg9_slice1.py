#!/usr/bin/env python3
"""Deterministic TG9 Slice 1 intake validator and provisional decision generator.

Consumes the TG8 handoff bundle from artifacts/tg8-quality-gates/<tg8_run_id>/,
normalizes a release-intake payload, and emits TG9 slice 1 artifacts under
artifacts/tg9-release-readiness/<run_id>/.
"""

from __future__ import annotations

import argparse
import json
import re
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


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the TG9 slice 1 argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Run TG9 Slice 1 intake validation against TG8 handoff artifacts "
            "and emit intake-payload.json, provisional-decision.md, and "
            "evidence-index.json."
        )
    )
    parser.add_argument(
        "--tg8-run-id",
        type=str,
        default="tg8-full-20260717",
        help="TG8 run identifier under artifacts/tg8-quality-gates/.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="TG9 slice 1 run identifier. Defaults to tg9-s1-<tg8_run_id>.",
    )
    parser.add_argument(
        "--tg8-root",
        type=Path,
        default=Path("artifacts/tg8-quality-gates"),
        help="Root directory containing TG8 quality gate run folders.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/tg9-release-readiness"),
        help="Root directory for TG9 release readiness artifacts.",
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


def _extract_summary_statuses(summary_text: str) -> dict[str, str]:
    statuses: dict[str, str] = {}
    pattern = re.compile(r"^\|\s*(QG-[A-Z]+-\d+)\s*\|\s*[^|]+\|\s*([A-Z_]+)\s*\|", re.MULTILINE)
    for match in pattern.finditer(summary_text):
        statuses[match.group(1)] = match.group(2)
    return statuses


def _extract_handoff_recommendation(handoff_text: str) -> str | None:
    match = re.search(r"Recommendation:\s*\*\*([A-Z_]+)\*\*", handoff_text)
    return match.group(1) if match else None


def _extract_handoff_overall_status(handoff_text: str) -> str | None:
    match = re.search(r"Overall Status:\s*\*\*([A-Z_]+)\*\*", handoff_text)
    return match.group(1) if match else None


def _extract_handoff_blockers(handoff_text: str) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    in_blockers = False

    for line in handoff_text.splitlines():
        stripped = line.strip()
        if stripped == "## Blockers":
            in_blockers = True
            continue
        if in_blockers and stripped.startswith("## "):
            break
        if not in_blockers:
            continue
        if not stripped.startswith("|"):
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 5:
            continue
        if cells[0] in {"Gate ID", "---", "None"}:
            continue

        blockers.append(
            {
                "gate_id": cells[0],
                "severity": cells[1].upper(),
                "owner": cells[2],
                "status": cells[3],
                "blocker": cells[4],
            }
        )

    return blockers


def _is_open_blocker(blocker: dict[str, str]) -> bool:
    return blocker["status"].strip().lower() not in {"closed", "resolved", "none", "n/a"}


def _is_high_or_critical(severity: str) -> bool:
    return severity.upper() in {"HIGH", "CRITICAL"}


def _build_evidence_index(
    run_id: str,
    tg8_run_id: str,
    tg8_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at_utc": _utc_now_iso(),
        "source_run_id": tg8_run_id,
        "entries": [
            {
                "type": "input",
                "path": str(tg8_dir / "gate-results.json"),
                "description": "TG8 canonical machine-readable gate results",
            },
            {
                "type": "input",
                "path": str(tg8_dir / "gate-summary.md"),
                "description": "TG8 human-readable gate summary",
            },
            {
                "type": "input",
                "path": str(tg8_dir / "evidence-index.json"),
                "description": "TG8 evidence completeness index",
            },
            {
                "type": "input",
                "path": str(tg8_dir / "tg9-handoff.md"),
                "description": "TG8 recommendation and blocker handoff",
            },
            {
                "type": "output",
                "path": str(output_dir / "intake-payload.json"),
                "description": "Normalized TG9 intake payload",
            },
            {
                "type": "output",
                "path": str(output_dir / "provisional-decision.md"),
                "description": "TG9 slice 1 provisional release decision",
            },
            {
                "type": "output",
                "path": str(output_dir / "evidence-index.json"),
                "description": "TG9 slice 1 evidence index",
            },
        ],
    }


def _render_decision_markdown(payload: dict[str, Any]) -> str:
    decision = payload["provisional_decision"]
    reasons = payload["decision_reasons"]
    blockers = payload["blockers"]
    coherence_checks = payload["coherence_checks"]

    lines = [
        "# TG9 Slice 1 Provisional Decision",
        "",
        f"- Run ID: `{payload['run_id']}`",
        f"- Source TG8 Run ID: `{payload['source_run_id']}`",
        f"- Generated (UTC): `{payload['generated_at_utc']}`",
        f"- Provisional Decision: **{decision}**",
        "",
        "## Intake Summary",
        "",
        f"- TG8 Overall Status: **{payload.get('overall_status', 'UNKNOWN')}**",
        f"- TG8 Recommendation: **{payload.get('recommendation', 'UNKNOWN')}**",
        f"- All Mandatory Gates PASS: **{payload.get('all_mandatory_pass', False)}**",
        f"- Open Blockers: **{payload.get('open_blocker_count', 0)}**",
        "",
        "## Decision Reasons",
        "",
    ]

    if reasons:
        for reason in reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- None")

    lines.extend([
        "",
        "## Mandatory Gate Statuses",
        "",
        "| Gate ID | Status |",
        "|---|---|",
    ])

    for gate_id in MANDATORY_GATE_IDS:
        status = payload["mandatory_gate_statuses"].get(gate_id, "MISSING")
        lines.append(f"| {gate_id} | {status} |")

    lines.extend([
        "",
        "## Open Blockers",
        "",
        "| Gate ID | Severity | Owner | Status | Blocker |",
        "|---|---|---|---|---|",
    ])

    open_blockers = [b for b in blockers if b.get("is_open", False)]
    if open_blockers:
        for blocker in open_blockers:
            lines.append(
                "| "
                f"{blocker['gate_id']} | {blocker['severity']} | {blocker['owner']} | "
                f"{blocker['status']} | {blocker['blocker']} |"
            )
    else:
        lines.append("| None | None | TG9 | Closed | No open blockers detected |")

    lines.extend([
        "",
        "## Coherence Checks",
        "",
        "| Check | Pass | Detail |",
        "|---|---|---|",
    ])
    for check in coherence_checks:
        lines.append(
            f"| {check['name']} | {str(check['pass']).upper()} | {check['detail']} |"
        )

    lines.append("")
    return "\n".join(lines)


def run() -> int:
    args = create_parser().parse_args()
    tg8_root = args.tg8_root if args.tg8_root.is_absolute() else REPO_ROOT / args.tg8_root
    output_root = args.output_root if args.output_root.is_absolute() else REPO_ROOT / args.output_root

    tg8_run_id = args.tg8_run_id
    run_id = args.run_id or f"tg9-s1-{tg8_run_id}"

    tg8_dir = tg8_root / tg8_run_id
    output_dir = output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    for required in TG8_REQUIRED_FILES:
        if not (tg8_dir / required).exists():
            errors.append(f"Missing required TG8 artifact: {tg8_dir / required}")

    gate_results_json: dict[str, Any] | None = None
    evidence_index_json: dict[str, Any] | None = None
    gate_summary_text: str | None = None
    tg9_handoff_text: str | None = None

    if not errors:
        gate_results_json, err = _read_json(tg8_dir / "gate-results.json")
        if err:
            errors.append(err)
        evidence_index_json, err = _read_json(tg8_dir / "evidence-index.json")
        if err:
            errors.append(err)
        gate_summary_text, err = _read_text(tg8_dir / "gate-summary.md")
        if err:
            errors.append(err)
        tg9_handoff_text, err = _read_text(tg8_dir / "tg9-handoff.md")
        if err:
            errors.append(err)

    mandatory_statuses: dict[str, str] = {}
    summary_statuses: dict[str, str] = {}
    recommendation = "UNKNOWN"
    handoff_overall_status = "UNKNOWN"
    blockers_raw: list[dict[str, str]] = []

    if gate_results_json is not None:
        gate_map = {
            gate.get("gate_id"): gate.get("status", "MISSING")
            for gate in gate_results_json.get("gates", [])
            if isinstance(gate, dict)
        }
        mandatory_statuses = {
            gate_id: str(gate_map.get(gate_id, "MISSING"))
            for gate_id in MANDATORY_GATE_IDS
        }

    if gate_summary_text is not None:
        summary_statuses = _extract_summary_statuses(gate_summary_text)

    if tg9_handoff_text is not None:
        extracted_recommendation = _extract_handoff_recommendation(tg9_handoff_text)
        recommendation = extracted_recommendation if extracted_recommendation else "UNKNOWN"
        extracted_overall = _extract_handoff_overall_status(tg9_handoff_text)
        handoff_overall_status = extracted_overall if extracted_overall else "UNKNOWN"
        blockers_raw = _extract_handoff_blockers(tg9_handoff_text)

    blockers: list[dict[str, Any]] = []
    for blocker in blockers_raw:
        is_open = _is_open_blocker(blocker)
        blockers.append(
            {
                **blocker,
                "is_open": is_open,
                "is_high_or_critical": is_open and _is_high_or_critical(blocker["severity"]),
            }
        )

    all_mandatory_pass = bool(mandatory_statuses) and all(
        mandatory_statuses.get(gate_id) == "PASS" for gate_id in MANDATORY_GATE_IDS
    )
    open_blockers = [blocker for blocker in blockers if blocker["is_open"]]
    high_or_critical_open = [
        blocker for blocker in open_blockers if blocker["is_high_or_critical"]
    ]

    gate_results_overall = (
        str(gate_results_json.get("overall_status", "UNKNOWN"))
        if gate_results_json is not None
        else "UNKNOWN"
    )

    coherence_checks: list[dict[str, Any]] = []

    coherence_checks.append(
        {
            "name": "tg8_run_id_consistency",
            "pass": bool(gate_results_json and gate_results_json.get("run_id") == tg8_run_id)
            and bool(evidence_index_json and evidence_index_json.get("run_id") == tg8_run_id),
            "detail": (
                "gate-results.json and evidence-index.json run_id match the TG8 run id"
                if gate_results_json is not None and evidence_index_json is not None
                else "Unable to verify due to parse or missing-file errors"
            ),
        }
    )

    summary_match = True
    summary_mismatch_reasons: list[str] = []
    if mandatory_statuses and summary_statuses:
        for gate_id, status in mandatory_statuses.items():
            summary_status = summary_statuses.get(gate_id)
            if summary_status is None:
                summary_match = False
                summary_mismatch_reasons.append(f"{gate_id} missing in gate-summary.md")
            elif summary_status != status:
                summary_match = False
                summary_mismatch_reasons.append(
                    f"{gate_id} mismatch (gate-results={status}, gate-summary={summary_status})"
                )
    else:
        summary_match = False
        summary_mismatch_reasons.append("Unable to compare mandatory gate statuses")

    coherence_checks.append(
        {
            "name": "summary_scoreboard_matches_machine_results",
            "pass": summary_match,
            "detail": "; ".join(summary_mismatch_reasons)
            if summary_mismatch_reasons
            else "All mandatory gate statuses match",
        }
    )

    evidence_gate_ids = set()
    if evidence_index_json is not None:
        for entry in evidence_index_json.get("entries", []):
            if isinstance(entry, dict):
                gate_id = entry.get("gate_id")
                if isinstance(gate_id, str):
                    evidence_gate_ids.add(gate_id)

    missing_evidence_for = [
        gate_id for gate_id in MANDATORY_GATE_IDS if gate_id not in evidence_gate_ids
    ]
    coherence_checks.append(
        {
            "name": "mandatory_gates_have_evidence",
            "pass": len(missing_evidence_for) == 0,
            "detail": "All mandatory gates have at least one evidence pointer"
            if not missing_evidence_for
            else f"Missing evidence pointers for: {', '.join(missing_evidence_for)}",
        }
    )

    coherence_checks.append(
        {
            "name": "handoff_overall_status_matches_machine_results",
            "pass": handoff_overall_status == gate_results_overall,
            "detail": (
                "Handoff overall status matches gate-results overall status"
                if handoff_overall_status == gate_results_overall
                else f"handoff={handoff_overall_status}, gate-results={gate_results_overall}"
            ),
        }
    )

    coherence_checks_pass = all(check["pass"] for check in coherence_checks)

    hard_reasons: list[str] = []
    soft_reasons: list[str] = []

    if errors:
        hard_reasons.extend(errors)

    for gate_id, status in mandatory_statuses.items():
        if status != "PASS":
            hard_reasons.append(f"Mandatory gate {gate_id} is {status}")

    if high_or_critical_open:
        for blocker in high_or_critical_open:
            hard_reasons.append(
                f"Open {blocker['severity']} blocker on {blocker['gate_id']}: {blocker['blocker']}"
            )

    if not coherence_checks_pass:
        failed_checks = [check["name"] for check in coherence_checks if not check["pass"]]
        hard_reasons.append(
            "Coherence checks failed: " + ", ".join(sorted(failed_checks))
        )

    if recommendation == "RECOMMEND_HOLD":
        soft_reasons.append("TG8 handoff recommendation is RECOMMEND_HOLD")
    elif recommendation == "REQUIRES_DECISION":
        soft_reasons.append("TG8 handoff recommendation is REQUIRES_DECISION")

    noncritical_open = [b for b in open_blockers if not b["is_high_or_critical"]]
    for blocker in noncritical_open:
        soft_reasons.append(
            f"Open blocker on {blocker['gate_id']} ({blocker['severity']}): {blocker['blocker']}"
        )

    if all_mandatory_pass and not open_blockers:
        provisional_decision = "GO"
        decision_reasons = [
            "All mandatory gates are PASS and no open blockers were detected"
        ]
    elif hard_reasons:
        provisional_decision = "NO_GO"
        decision_reasons = sorted(set(hard_reasons + soft_reasons))
    else:
        provisional_decision = "REQUIRES_DECISION"
        decision_reasons = sorted(set(soft_reasons)) or [
            "Intake requires manual decision despite no hard stop conditions"
        ]

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "source_run_id": tg8_run_id,
        "generated_at_utc": _utc_now_iso(),
        "intake_validation": {
            "required_files": {
                required: (tg8_dir / required).exists() for required in TG8_REQUIRED_FILES
            },
            "parseable": {
                "gate-results.json": gate_results_json is not None,
                "evidence-index.json": evidence_index_json is not None,
                "gate-summary.md": gate_summary_text is not None,
                "tg9-handoff.md": tg9_handoff_text is not None,
            },
            "errors": errors,
        },
        "overall_status": gate_results_overall,
        "recommendation": recommendation,
        "mandatory_gate_statuses": mandatory_statuses,
        "all_mandatory_pass": all_mandatory_pass,
        "blockers": blockers,
        "open_blocker_count": len(open_blockers),
        "coherence_checks": coherence_checks,
        "coherence_pass": coherence_checks_pass,
        "provisional_decision": provisional_decision,
        "decision_reasons": decision_reasons,
    }

    intake_payload_path = output_dir / "intake-payload.json"
    provisional_decision_path = output_dir / "provisional-decision.md"
    evidence_index_path = output_dir / "evidence-index.json"

    intake_payload_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    provisional_decision_path.write_text(
        _render_decision_markdown(payload),
        encoding="utf-8",
    )
    evidence_index_path.write_text(
        json.dumps(_build_evidence_index(run_id, tg8_run_id, tg8_dir, output_dir), indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"TG9 slice 1 output: {output_dir}")
    print(f"provisional_decision: {provisional_decision}")
    print(f"intake_payload: {intake_payload_path}")
    print(f"provisional_decision_doc: {provisional_decision_path}")
    print(f"evidence_index: {evidence_index_path}")

    return EXIT_SUCCESS if provisional_decision == "GO" else EXIT_FAILURE


def main() -> int:
    """Main entrypoint with deterministic exit handling."""
    try:
        return run()
    except KeyboardInterrupt:
        print("Interrupted by user", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
