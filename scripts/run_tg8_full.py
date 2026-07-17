#!/usr/bin/env python3
"""Deterministic TG8 full gate runner.

Executes all mandatory TG8 gates:
QG-UNIT-01, QG-INT-01, QG-CONFIG-01, QG-SEC-01, QG-REL-01, QG-E2E-01.

Outputs a complete evidence package under:
artifacts/tg8-quality-gates/<run_id>/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml

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

REQUIRED_E2E_RUN_IDS = ("29577754373", "29577762865")


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(description="Run all mandatory TG8 quality gates.")
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
        "--gate-b-evidence-doc",
        type=Path,
        default=Path(".copilot-tracking/squad/azure-gate-b-2026-07-17.md"),
        help="Path to Gate B pass evidence markdown.",
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
    parser.add_argument(
        "--skip-gh-check",
        action="store_true",
        help="Skip optional GitHub CLI run verification for Gate B run IDs.",
    )
    return parser


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_run_id() -> str:
    return f"tg8-full-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _run_cmd(command: list[str], cwd: Path | None = None) -> tuple[int, str, str, float]:
    start = time.perf_counter()
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=cwd)
    except OSError as exc:
        duration = time.perf_counter() - start
        return EXIT_ERROR, "", str(exc), duration
    duration = time.perf_counter() - start
    return result.returncode, result.stdout, result.stderr, duration


def _gate_record(
    gate_id: str,
    status: GateStatus,
    command: str | None,
    inputs: list[str],
    outputs: list[str],
    reasons: list[str],
    duration_seconds: float,
    *,
    exit_code: int | None = None,
    raw_stdout: str = "",
    raw_stderr: str = "",
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "gate_id": gate_id,
        "category": GATE_CATEGORIES[gate_id],
        "status": status,
        "command": command,
        "inputs": inputs,
        "outputs": outputs,
        "reasons": reasons,
        "duration_seconds": round(duration_seconds, 3),
    }
    if exit_code is not None:
        record["exit_code"] = exit_code
    if raw_stdout:
        record["raw_stdout"] = raw_stdout
    if raw_stderr:
        record["raw_stderr"] = raw_stderr
    return record


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def _parse_reliability_reasons(stdout: str) -> list[str]:
    reasons: list[str] = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("reason_") and ":" in stripped:
            reasons.append(stripped.split(":", 1)[1].strip())
        elif stripped.startswith("reason:"):
            reasons.append(stripped.split(":", 1)[1].strip())
    return reasons


def run_unit_gate() -> dict[str, Any]:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests/unit"]
    exit_code, stdout, stderr, duration = _run_cmd(command, cwd=REPO_ROOT)
    status: GateStatus = "PASS" if exit_code == EXIT_SUCCESS else "FAIL"
    reasons = [] if status == "PASS" else ["Unit test discovery/execution returned non-zero exit code"]
    return _gate_record(
        "QG-UNIT-01",
        status,
        " ".join(command),
        ["tests/unit"],
        [],
        reasons,
        duration,
        exit_code=exit_code,
        raw_stdout=stdout,
        raw_stderr=stderr,
    )


def run_integration_gate() -> dict[str, Any]:
    start = time.perf_counter()
    reasons: list[str] = []
    outputs: list[str] = []

    fixture_repo = REPO_ROOT / "tests" / "fixtures" / "hermetic_repo"
    artifact_root = fixture_repo / "artifacts" / "cli-test-run"
    results_root = fixture_repo / "results" / "cli-test-run"
    dry_run_output_path = artifact_root / "dry_run_output.json"
    history_preview_path = artifact_root / "history_preview.json"

    required_paths = [fixture_repo, artifact_root, results_root, dry_run_output_path, history_preview_path]
    for required_path in required_paths:
        if not required_path.exists():
            reasons.append(f"Missing required integration artifact path: {required_path}")

    if not reasons:
        try:
            dry_run_output = _load_json(dry_run_output_path)
            history_preview = _load_json(history_preview_path)
            run_context = dry_run_output.get("run_context")
            plans = dry_run_output.get("provisioner", {}).get("plans", [])
            manifests = history_preview.get("manifests")
            if not isinstance(run_context, dict):
                reasons.append("dry_run_output.json missing run_context object")
            else:
                for key in ("run_id", "dataset_sha256", "resource_group", "foundry_account_name"):
                    value = run_context.get(key)
                    if not isinstance(value, str) or not value:
                        reasons.append(f"run_context missing required non-empty field: {key}")
            if not isinstance(plans, list) or not plans:
                reasons.append("dry_run_output.json missing provisioner.plans")
            if not isinstance(manifests, list) or not manifests:
                reasons.append("history_preview.json missing manifests")

            if not reasons:
                from src.reporter.artifact_loader import load_reporter_run_input

                loaded = load_reporter_run_input(fixture_repo, artifact_root)
                if not loaded.targets:
                    reasons.append("Reporter artifact loader returned no retiring targets")
                else:
                    target = loaded.targets[0]
                    if not target.candidates:
                        reasons.append("Reporter artifact loader returned target with no candidates")
                    else:
                        outputs.append(str(target.candidates[0].summary_path))
                        outputs.append(str(target.candidates[0].custom_path))
                        outputs.append(str(target.candidates[0].redteam_path))
        except Exception as exc:  # noqa: BLE001 - deterministic gate-level error capture
            reasons.append(f"Integration contract validation failed with exception: {exc}")

    duration = time.perf_counter() - start
    status: GateStatus = "PASS" if not reasons else "FAIL"
    return _gate_record(
        "QG-INT-01",
        status,
        "python integration-contract-check",
        [
            str(dry_run_output_path),
            str(history_preview_path),
            str(results_root),
        ],
        outputs,
        reasons,
        duration,
    )


def _validate_tg7_contract_triplet() -> list[str]:
    reasons: list[str] = []
    alert_path = REPO_ROOT / "config" / "tg7-reliability-alert-definitions.yaml"
    workbook_path = REPO_ROOT / "config" / "tg7-reliability-workbook-definitions.yaml"
    playbook_path = REPO_ROOT / "docs" / "tg7-incident-playbook-gateb.md"

    alert = _load_yaml(alert_path)
    workbook = _load_yaml(workbook_path)
    playbook_text = playbook_path.read_text(encoding="utf-8")

    for key in ("schema_version", "alert_contract_id", "signals", "alert_rules"):
        if key not in alert:
            reasons.append(f"Alert contract missing key: {key}")
    for key in ("schema_version", "workbook_id", "dashboard"):
        if key not in workbook:
            reasons.append(f"Workbook contract missing key: {key}")

    alert_signals = {
        signal.get("id")
        for signal in alert.get("signals", [])
        if isinstance(signal, dict) and isinstance(signal.get("id"), str)
    }
    required_signals = {"workflow_failure", "oidc_failure", "sweep_failure", "latency_breach"}
    missing_signals = sorted(required_signals - alert_signals)
    if missing_signals:
        reasons.append("Alert contract missing required signal ids: " + ", ".join(missing_signals))

    panel_signals = {
        panel.get("signal")
        for panel in workbook.get("dashboard", {}).get("panels", [])
        if isinstance(panel, dict) and isinstance(panel.get("signal"), str)
    }
    missing_panel_signals = sorted(required_signals - panel_signals)
    if missing_panel_signals:
        reasons.append("Workbook panels missing signal coverage: " + ", ".join(missing_panel_signals))

    rule_signals = {
        rule.get("signal")
        for rule in alert.get("alert_rules", [])
        if isinstance(rule, dict) and isinstance(rule.get("signal"), str)
    }
    missing_rule_signals = sorted(required_signals - rule_signals)
    if missing_rule_signals:
        reasons.append("Alert rules missing signal coverage: " + ", ".join(missing_rule_signals))

    required_playbook_headings = (
        "## Workflow Failure Path",
        "## OIDC Failure Path",
        "## Sweep Failure Path",
        "## Latency Breach Path",
    )
    for heading in required_playbook_headings:
        if heading not in playbook_text:
            reasons.append(f"Playbook missing heading: {heading}")

    for panel in workbook.get("dashboard", {}).get("panels", []):
        if not isinstance(panel, dict):
            continue
        triage_entrypoint = panel.get("triage_entrypoint")
        if not isinstance(triage_entrypoint, str) or not triage_entrypoint.startswith(
            "docs/tg7-incident-playbook-gateb.md#"
        ):
            reasons.append(
                "Workbook panel has invalid triage_entrypoint (must target docs/tg7-incident-playbook-gateb.md#...): "
                f"{triage_entrypoint}"
            )

    return reasons


def run_config_gate() -> dict[str, Any]:
    start = time.perf_counter()
    reasons: list[str] = []
    command = [sys.executable, str(REPO_ROOT / "scripts" / "validate_tg3_contracts.py")]
    exit_code, stdout, stderr, _ = _run_cmd(command, cwd=REPO_ROOT)
    if exit_code != EXIT_SUCCESS:
        reasons.append("scripts/validate_tg3_contracts.py returned non-zero exit code")

    try:
        reasons.extend(_validate_tg7_contract_triplet())
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"TG7 config contract validation failed with exception: {exc}")

    duration = time.perf_counter() - start
    status: GateStatus = "PASS" if not reasons else "FAIL"
    return _gate_record(
        "QG-CONFIG-01",
        status,
        " ".join(command) + " + tg7-contract-key-check",
        [
            "scripts/validate_tg3_contracts.py",
            "config/tg7-reliability-alert-definitions.yaml",
            "config/tg7-reliability-workbook-definitions.yaml",
            "docs/tg7-incident-playbook-gateb.md",
        ],
        [],
        reasons,
        duration,
        exit_code=exit_code,
        raw_stdout=stdout,
        raw_stderr=stderr,
    )


def _scan_for_secret_patterns(paths: list[Path]) -> list[str]:
    reasons: list[str] = []
    secret_assignment = re.compile(
        r"(?i)\b(password|passwd|secret|token|api[_-]?key|client[_-]?secret)\b\s*[:=]\s*['\"]?([^\s'\"]{12,})"
    )
    private_key_pattern = re.compile(r"-----BEGIN (RSA|EC|OPENSSH|DSA)? ?PRIVATE KEY-----")
    github_pat_pattern = re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")
    generic_jwt_pattern = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")

    allowed_value_markers = (
        "<",
        "${",
        "example",
        "changeme",
        "placeholder",
        "pending",
        "local-",
        "xxxxx",
        "your_",
    )

    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            reasons.append(f"Could not read file during secret scan: {path} ({exc})")
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            assignment_match = secret_assignment.search(line)
            if assignment_match:
                value = assignment_match.group(2).strip().lower()
                if value and not any(marker in value for marker in allowed_value_markers):
                    reasons.append(
                        f"Potential hardcoded secret pattern in {path}:{line_number}"
                    )
            if private_key_pattern.search(line):
                reasons.append(f"Private key block marker detected in {path}:{line_number}")
            if github_pat_pattern.search(line):
                reasons.append(f"Potential GitHub PAT detected in {path}:{line_number}")
            if generic_jwt_pattern.search(line):
                reasons.append(f"Potential JWT token detected in {path}:{line_number}")

    return reasons


def _validate_bicep_contract_invariants() -> list[str]:
    reasons: list[str] = []
    main_bicep = (REPO_ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    governance_defs = (REPO_ROOT / "infra" / "modules" / "governance-definitions.bicep").read_text(
        encoding="utf-8"
    )

    required_main_markers = (
        "foundryPublicNetworkAccess: 'Disabled'",
        "storagePublicNetworkAccess: 'Disabled'",
        "keyVaultPublicNetworkAccess: 'Disabled'",
        "storageAllowSharedKeyAccess: false",
        "foundryDisableLocalAuth: true",
        "owner: 'model-upgrade-automation'",
        "cleanup: 'ephemeral'",
    )
    required_governance_markers = (
        "mua-tg2-enforce-foundry-private-only",
        "mua-tg2-enforce-storage-private-only",
        "mua-tg2-enforce-keyvault-private-only",
        "mua-tg2-require-workload-tag",
        "mua-tg2-require-environment-tag",
        "mua-tg2-require-managedby-tag",
        "mua-tg2-require-taskgroup-tag",
        "mua-tg2-require-owner-tag",
        "mua-tg2-require-cleanup-tag",
    )

    for marker in required_main_markers:
        if marker not in main_bicep:
            reasons.append(f"infra/main.bicep missing required invariant marker: {marker}")
    for marker in required_governance_markers:
        if marker not in governance_defs:
            reasons.append(
                "infra/modules/governance-definitions.bicep missing required policy marker: "
                f"{marker}"
            )

    return reasons


def run_security_gate() -> dict[str, Any]:
    start = time.perf_counter()
    reasons: list[str] = []

    scan_roots = [
        REPO_ROOT / "config",
        REPO_ROOT / "docs",
        REPO_ROOT / "scripts",
    ]
    include_suffixes = {".md", ".yaml", ".yml", ".json", ".py", ".txt", ".bicep", ".ps1", ".sh"}
    scan_paths: list[Path] = []
    for root in scan_roots:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in include_suffixes:
                scan_paths.append(path)

    reasons.extend(_scan_for_secret_patterns(scan_paths))

    try:
        reasons.extend(_validate_bicep_contract_invariants())
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"Bicep security invariant validation failed with exception: {exc}")

    duration = time.perf_counter() - start
    status: GateStatus = "PASS" if not reasons else "FAIL"
    return _gate_record(
        "QG-SEC-01",
        status,
        "security-baseline-local-scan",
        ["config/", "docs/", "scripts/", "infra/main.bicep", "infra/modules/governance-definitions.bicep"],
        [],
        reasons,
        duration,
    )


def run_reliability_gate(baseline: Path, evidence: Path) -> dict[str, Any]:
    checker_script = REPO_ROOT / "scripts" / "check_tg7_reliability_gate.py"
    command = [
        sys.executable,
        str(checker_script),
        "--baseline",
        str(baseline),
        "--evidence",
        str(evidence),
    ]
    exit_code, stdout, stderr, duration = _run_cmd(command, cwd=REPO_ROOT)

    if exit_code == EXIT_SUCCESS:
        status: GateStatus = "PASS"
    elif exit_code == EXIT_FAILURE:
        status = "FAIL"
    else:
        status = "ERROR"

    reasons = _parse_reliability_reasons(stdout)
    if status == "PASS" and not reasons:
        reasons = ["All reliability signals satisfy TG7 thresholds"]
    if status == "ERROR" and not reasons:
        reasons = [stderr.strip() or "Reliability checker returned an unexpected error"]

    return _gate_record(
        "QG-REL-01",
        status,
        " ".join(command),
        [str(baseline), str(evidence)],
        [],
        reasons,
        duration,
        exit_code=exit_code,
        raw_stdout=stdout,
        raw_stderr=stderr,
    )


def _validate_gate_b_markdown_evidence(path: Path) -> list[str]:
    reasons: list[str] = []
    if not path.exists():
        return [f"Gate B evidence markdown missing: {path}"]

    content = path.read_text(encoding="utf-8")
    required_markers = [
        "Final Gate B Verdict",
        "**Gate B: PASS**",
        "Run ID: `29577754373`",
        "Run ID: `29577762865`",
        "Azure login with OIDC",
    ]
    for marker in required_markers:
        if marker not in content:
            reasons.append(f"Gate B evidence markdown missing marker: {marker}")
    return reasons


def _gh_available() -> bool:
    return any(
        Path(path_dir, "gh.exe").exists() or Path(path_dir, "gh").exists()
        for path_dir in os.environ.get("PATH", "").split(os.pathsep)
        if path_dir
    )


def _validate_gh_runs(run_ids: tuple[str, ...]) -> list[str]:
    reasons: list[str] = []
    for run_id in run_ids:
        command = ["gh", "run", "view", run_id, "--json", "status,conclusion"]
        exit_code, stdout, stderr, _ = _run_cmd(command, cwd=REPO_ROOT)
        if exit_code != EXIT_SUCCESS:
            reasons.append(f"Unable to verify GH run {run_id} via gh CLI: {stderr.strip() or stdout.strip()}")
            continue
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            reasons.append(f"Invalid JSON from gh run view for {run_id}: {exc}")
            continue

        status = payload.get("status")
        conclusion = payload.get("conclusion")
        if status != "completed" or conclusion != "success":
            reasons.append(
                f"GH run {run_id} not successful (status={status}, conclusion={conclusion})"
            )
    return reasons


def run_e2e_gate(gate_b_evidence_doc: Path, skip_gh_check: bool) -> dict[str, Any]:
    start = time.perf_counter()
    reasons: list[str] = []
    info: list[str] = []

    reasons.extend(_validate_gate_b_markdown_evidence(gate_b_evidence_doc))

    if not skip_gh_check:
        if _gh_available():
            gh_reasons = _validate_gh_runs(REQUIRED_E2E_RUN_IDS)
            if gh_reasons:
                reasons.extend(gh_reasons)
            else:
                info.append("GitHub run verification succeeded for required Gate B run IDs")
        else:
            info.append("gh CLI not available; used markdown Gate B evidence only")

    duration = time.perf_counter() - start
    status: GateStatus = "PASS" if not reasons else "FAIL"
    return _gate_record(
        "QG-E2E-01",
        status,
        "gate-b-evidence-check (+ optional gh run view)",
        [str(gate_b_evidence_doc)],
        [],
        reasons + info,
        duration,
    )


def _compute_overall_status(gates: list[dict[str, Any]]) -> str:
    statuses = {gate["status"] for gate in gates}
    if "ERROR" in statuses:
        return "ERROR"
    if all(gate["status"] == "PASS" for gate in gates):
        return "PASS"
    return "FAIL"


def _build_blockers(gates: list[dict[str, Any]]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for gate in gates:
        if gate["status"] == "PASS":
            continue
        reasons = gate.get("reasons") or ["No reason captured"]
        blockers.append(
            {
                "gate_id": str(gate["gate_id"]),
                "severity": "Critical" if gate["status"] == "ERROR" else "High",
                "owner": "TG8",
                "status": "Open",
                "reason": str(reasons[0]),
            }
        )
    return blockers


def build_gate_results(
    run_id: str,
    baseline: Path,
    evidence: Path,
    gate_b_evidence_doc: Path,
    skip_gh_check: bool,
) -> dict[str, Any]:
    gates = [
        run_unit_gate(),
        run_integration_gate(),
        run_config_gate(),
        run_security_gate(),
        run_reliability_gate(baseline, evidence),
        run_e2e_gate(gate_b_evidence_doc, skip_gh_check),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at_utc": _utc_now_iso(),
        "mandatory_gate_ids": list(MANDATORY_GATE_IDS),
        "overall_status": _compute_overall_status(gates),
        "gates": gates,
    }


def build_evidence_index(
    run_id: str,
    baseline: Path,
    evidence: Path,
    gate_b_evidence_doc: Path,
    output_dir: Path,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at_utc": _utc_now_iso(),
        "entries": [
            {
                "gate_id": "QG-UNIT-01",
                "type": "input",
                "path": "tests/unit",
                "description": "Unit test suite",
            },
            {
                "gate_id": "QG-INT-01",
                "type": "input",
                "path": "tests/fixtures/hermetic_repo",
                "description": "Deterministic integration fixtures for reporter contract validation",
            },
            {
                "gate_id": "QG-CONFIG-01",
                "type": "input",
                "path": "config/tg7-reliability-alert-definitions.yaml",
                "description": "TG7 alert contract",
            },
            {
                "gate_id": "QG-CONFIG-01",
                "type": "input",
                "path": "config/tg7-reliability-workbook-definitions.yaml",
                "description": "TG7 workbook contract",
            },
            {
                "gate_id": "QG-CONFIG-01",
                "type": "input",
                "path": "docs/tg7-incident-playbook-gateb.md",
                "description": "TG7 incident playbook",
            },
            {
                "gate_id": "QG-REL-01",
                "type": "input",
                "path": str(baseline),
                "description": "TG7 reliability baseline",
            },
            {
                "gate_id": "QG-REL-01",
                "type": "input",
                "path": str(evidence),
                "description": "TG7 reliability latest evidence",
            },
            {
                "gate_id": "QG-E2E-01",
                "type": "input",
                "path": str(gate_b_evidence_doc),
                "description": "Gate B success evidence",
            },
            {
                "gate_id": None,
                "type": "output",
                "path": str(output_dir / "gate-results.json"),
                "description": "Normalized TG8 gate execution results",
            },
            {
                "gate_id": None,
                "type": "output",
                "path": str(output_dir / "gate-summary.md"),
                "description": "Human-readable TG8 gate summary",
            },
            {
                "gate_id": None,
                "type": "output",
                "path": str(output_dir / "evidence-index.json"),
                "description": "Evidence package manifest",
            },
            {
                "gate_id": None,
                "type": "output",
                "path": str(output_dir / "tg9-handoff.md"),
                "description": "TG8 to TG9 release readiness handoff",
            },
        ],
    }


def render_gate_summary(gate_results: dict[str, Any]) -> str:
    lines = [
        "# TG8 Full Quality Gate Summary",
        "",
        f"- Run ID: `{gate_results['run_id']}`",
        f"- Generated (UTC): `{gate_results['generated_at_utc']}`",
        f"- Overall status: **{gate_results['overall_status']}**",
        "",
        "| Gate ID | Category | Status | Primary Reason |",
        "|---|---|---|---|",
    ]
    for gate in gate_results["gates"]:
        reason = gate["reasons"][0] if gate["reasons"] else "-"
        lines.append(f"| {gate['gate_id']} | {gate['category']} | {gate['status']} | {reason} |")
    lines.append("")
    return "\n".join(lines)


def render_tg9_handoff(gate_results: dict[str, Any]) -> str:
    blockers = _build_blockers(gate_results["gates"])
    recommendation = "RECOMMEND_RELEASE" if gate_results["overall_status"] == "PASS" else "RECOMMEND_HOLD"

    lines = [
        "---",
        "title: TG8 to TG9 Handoff",
        "description: TG8 quality gate release readiness handoff for TG9 go/no-go intake",
        f"ms.date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "ms.topic: reference",
        "---",
        "",
        "## Release Recommendation",
        "",
        f"- Run ID: `{gate_results['run_id']}`",
        f"- Overall Status: **{gate_results['overall_status']}**",
        f"- Recommendation: **{recommendation}**",
        "",
        "## TG8 Gate Scoreboard",
        "",
        "| Gate ID | Status |",
        "|---|---|",
    ]
    for gate in gate_results["gates"]:
        lines.append(f"| {gate['gate_id']} | {gate['status']} |")

    lines.extend([
        "",
        "## Blockers",
        "",
        "| Gate ID | Severity | Owner | Status | Blocker |",
        "|---|---|---|---|---|",
    ])
    if blockers:
        for blocker in blockers:
            lines.append(
                "| "
                f"{blocker['gate_id']} | {blocker['severity']} | {blocker['owner']} | {blocker['status']} | {blocker['reason']}"
                " |"
            )
    else:
        lines.append("| None | None | TG8 | Closed | No blockers; all mandatory gates passed |")

    lines.extend(
        [
            "",
            "## TG9 Intake Checklist",
            "",
            "1. Confirm gate-results.json is machine-parseable and complete.",
            "2. Confirm QG-REL-01 PASS is traceable to TG7 baseline/evidence inputs.",
            "3. Confirm blocker table has no open Critical or High entries.",
            "4. Proceed with TG9 go/no-go decision record.",
            "",
        ]
    )
    return "\n".join(lines)


def run() -> int:
    parser = create_parser()
    args = parser.parse_args()

    baseline = args.baseline if args.baseline.is_absolute() else REPO_ROOT / args.baseline
    evidence = args.evidence if args.evidence.is_absolute() else REPO_ROOT / args.evidence
    gate_b_evidence_doc = (
        args.gate_b_evidence_doc
        if args.gate_b_evidence_doc.is_absolute()
        else REPO_ROOT / args.gate_b_evidence_doc
    )

    for path, label in ((baseline, "baseline"), (evidence, "evidence"), (gate_b_evidence_doc, "gate_b_evidence_doc")):
        if not path.exists():
            print(f"ERROR: {label} file not found: {path}", file=sys.stderr)
            return EXIT_ERROR

    run_id = args.run_id or _default_run_id()
    output_root = args.output_root if args.output_root.is_absolute() else REPO_ROOT / args.output_root
    output_dir = output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    gate_results = build_gate_results(
        run_id=run_id,
        baseline=baseline,
        evidence=evidence,
        gate_b_evidence_doc=gate_b_evidence_doc,
        skip_gh_check=args.skip_gh_check,
    )
    evidence_index = build_evidence_index(run_id, baseline, evidence, gate_b_evidence_doc, output_dir)
    gate_summary = render_gate_summary(gate_results)
    tg9_handoff = render_tg9_handoff(gate_results)

    gate_results_path = output_dir / "gate-results.json"
    evidence_index_path = output_dir / "evidence-index.json"
    gate_summary_path = output_dir / "gate-summary.md"
    tg9_handoff_path = output_dir / "tg9-handoff.md"

    gate_results_path.write_text(json.dumps(gate_results, indent=2) + "\n", encoding="utf-8")
    evidence_index_path.write_text(json.dumps(evidence_index, indent=2) + "\n", encoding="utf-8")
    gate_summary_path.write_text(gate_summary, encoding="utf-8")
    tg9_handoff_path.write_text(tg9_handoff, encoding="utf-8")

    # Validate output JSON parseability as a deterministic post-condition.
    _ = _load_json(gate_results_path)
    _ = _load_json(evidence_index_path)

    print("TG8 full quality gate run complete")
    print(f"run_id: {run_id}")
    print(f"evidence_package: {output_dir}")
    print(f"overall_status: {gate_results['overall_status']}")
    for gate in gate_results["gates"]:
        print(f"{gate['gate_id']} status: {gate['status']}")
    print(f"tg9_handoff: {tg9_handoff_path}")

    if gate_results["overall_status"] == "PASS":
        return EXIT_SUCCESS
    if gate_results["overall_status"] == "ERROR":
        return EXIT_ERROR
    return EXIT_FAILURE


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