#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check TG7 reliability gate status for TG8 handoff using baseline and latest evidence."
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("artifacts/gatea-policy-remediation-20260717/tg7-reliability-baseline.json"),
        help="Path to TG7 reliability baseline JSON.",
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("artifacts/gatea-policy-remediation-20260717/tg7-reliability-latest-evidence.sample.json"),
        help="Path to latest reliability evidence JSON.",
    )
    return parser


def _load_json(path: Path, label: str) -> dict[str, Any] | None:
    if not path.exists():
        print(f"ERROR: {label} file not found: {path}", file=sys.stderr)
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON in {label} file {path}: {exc}", file=sys.stderr)
        return None
    except OSError as exc:
        print(f"ERROR: Could not read {label} file {path}: {exc}", file=sys.stderr)
        return None

    if not isinstance(payload, dict):
        print(f"ERROR: {label} root must be an object", file=sys.stderr)
        return None

    return payload


def _ratio_success(total: int, failed: int) -> float:
    if total <= 0:
        return 0.0
    return (total - failed) / total


def _get_metric_target(baseline: dict[str, Any], metric_name: str) -> float | None:
    metrics = baseline.get("sli_metrics")
    if not isinstance(metrics, list):
        return None

    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        if metric.get("metric") != metric_name:
            continue
        slo = metric.get("slo")
        if not isinstance(slo, dict):
            return None
        target = slo.get("target")
        if isinstance(target, (int, float)):
            return float(target)
        return None

    return None


def _as_int(mapping: dict[str, Any], key: str) -> int | None:
    value = mapping.get(key)
    if isinstance(value, int):
        return value
    return None


def evaluate_gate(baseline: dict[str, Any], evidence: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    workflow_target = _get_metric_target(baseline, "workflow_success_ratio")
    oidc_target = _get_metric_target(baseline, "oidc_login_success")
    sweep_target = _get_metric_target(baseline, "cleanup_sweep_execution_success")
    latency_target = _get_metric_target(baseline, "end_to_end_gate_completion_latency")

    if None in (workflow_target, oidc_target, sweep_target, latency_target):
        reasons.append("Missing one or more required SLO targets in baseline sli_metrics")
        return False, reasons

    signals = evidence.get("signals")
    if not isinstance(signals, dict):
        reasons.append("Evidence missing required object: signals")
        return False, reasons

    workflow = signals.get("workflow_failure")
    oidc = signals.get("oidc_failure")
    sweep = signals.get("sweep_failure")
    latency = signals.get("latency_breach")

    if not all(isinstance(item, dict) for item in (workflow, oidc, sweep, latency)):
        reasons.append("Evidence missing one or more required signal objects")
        return False, reasons

    workflow_total = _as_int(workflow, "total_runs")
    workflow_failed = _as_int(workflow, "failed_runs")
    if workflow_total is None or workflow_failed is None:
        reasons.append("workflow_failure requires integer total_runs and failed_runs")
    else:
        workflow_ratio = _ratio_success(workflow_total, workflow_failed)
        if workflow_ratio < workflow_target:
            reasons.append(
                "workflow_failure ratio below target "
                f"({workflow_ratio:.3f} < {workflow_target:.3f})"
            )

    oidc_total = _as_int(oidc, "total_logins")
    oidc_failed = _as_int(oidc, "failed_logins")
    if oidc_total is None or oidc_failed is None:
        reasons.append("oidc_failure requires integer total_logins and failed_logins")
    else:
        oidc_ratio = _ratio_success(oidc_total, oidc_failed)
        if oidc_ratio < oidc_target:
            reasons.append(
                "oidc_failure ratio below target "
                f"({oidc_ratio:.3f} < {oidc_target:.3f})"
            )

    sweep_total = _as_int(sweep, "total_sweeps")
    sweep_failed = _as_int(sweep, "failed_sweeps")
    if sweep_total is None or sweep_failed is None:
        reasons.append("sweep_failure requires integer total_sweeps and failed_sweeps")
    else:
        sweep_ratio = _ratio_success(sweep_total, sweep_failed)
        if sweep_ratio < sweep_target:
            reasons.append(
                "sweep_failure ratio below target "
                f"({sweep_ratio:.3f} < {sweep_target:.3f})"
            )

    latency_breaches = _as_int(latency, "breached_runs")
    max_observed_seconds = _as_int(latency, "max_observed_seconds")
    if latency_breaches is None or max_observed_seconds is None:
        reasons.append("latency_breach requires integer breached_runs and max_observed_seconds")
    else:
        if latency_breaches > 0:
            reasons.append(f"latency_breach has breached_runs={latency_breaches}")
        if float(max_observed_seconds) > latency_target:
            reasons.append(
                "latency_breach max_observed_seconds exceeds target "
                f"({max_observed_seconds} > {int(latency_target)})"
            )

    tracking = evidence.get("gate_b_failure_signatures_tracking")
    if not isinstance(tracking, dict):
        reasons.append("Evidence missing gate_b_failure_signatures_tracking object")
    else:
        required_signatures = {
            "hidden artifact upload mismatch",
            "AADSTS700213 OIDC federated subject mismatch",
        }
        missing_signatures = sorted(required_signatures - set(tracking.keys()))
        if missing_signatures:
            reasons.append(
                "Missing Gate B signature tracking entries: "
                + ", ".join(missing_signatures)
            )

    return len(reasons) == 0, reasons


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    baseline = _load_json(args.baseline, "baseline")
    if baseline is None:
        return EXIT_ERROR

    evidence = _load_json(args.evidence, "evidence")
    if evidence is None:
        return EXIT_ERROR

    passed, reasons = evaluate_gate(baseline, evidence)

    print("TG7 reliability gate check")
    print(f"baseline: {args.baseline}")
    print(f"evidence: {args.evidence}")

    if passed:
        print("result: PASS")
        print("reason: all reliability signals satisfy TG7 thresholds for TG8 handoff")
        return EXIT_SUCCESS

    print("result: FAIL")
    for index, reason in enumerate(reasons, start=1):
        print(f"reason_{index}: {reason}")
    return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
