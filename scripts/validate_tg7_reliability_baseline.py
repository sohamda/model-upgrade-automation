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

EXPECTED_RUNS = {
    "29577754373": "detect-and-eval",
    "29577762865": "sweep-orphans",
}

EXPECTED_METRICS = {
    "workflow_success_ratio",
    "run_context_artifact_availability",
    "oidc_login_success",
    "cleanup_sweep_execution_success",
    "end_to_end_gate_completion_latency",
}


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate TG7 reliability baseline schema and values."
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("artifacts/gatea-policy-remediation-20260717/tg7-reliability-baseline.json"),
        help="Path to TG7 reliability baseline JSON.",
    )
    return parser


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return EXIT_FAILURE


def _require_dict(value: Any, path: str) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        print(f"{path} must be an object", file=sys.stderr)
        return None
    return value


def _require_list(value: Any, path: str) -> list[Any] | None:
    if not isinstance(value, list):
        print(f"{path} must be an array", file=sys.stderr)
        return None
    return value


def validate_top_level(payload: dict[str, Any]) -> int:
    required_keys = {
        "schema_version",
        "baseline_id",
        "generated_on",
        "gate",
        "environment_context",
        "evidence_runs",
        "sli_metrics",
    }
    missing = sorted(required_keys - set(payload.keys()))
    if missing:
        return fail(f"Missing required top-level keys: {', '.join(missing)}")

    if payload["schema_version"] != "1.0.0":
        return fail("schema_version must be '1.0.0'")

    gate = _require_dict(payload["gate"], "gate")
    if gate is None:
        return EXIT_FAILURE
    if gate.get("name") != "Gate B":
        return fail("gate.name must be 'Gate B'")
    if gate.get("status") != "PASS":
        return fail("gate.status must be 'PASS'")

    env = _require_dict(payload["environment_context"], "environment_context")
    if env is None:
        return EXIT_FAILURE
    if env.get("instance") != "002":
        return fail("environment_context.instance must be '002'")

    return EXIT_SUCCESS


def validate_evidence_runs(payload: dict[str, Any]) -> int:
    runs = _require_list(payload["evidence_runs"], "evidence_runs")
    if runs is None:
        return EXIT_FAILURE

    if len(runs) != 2:
        return fail("evidence_runs must contain exactly 2 runs")

    found: dict[str, str] = {}
    for idx, run in enumerate(runs):
        run_obj = _require_dict(run, f"evidence_runs[{idx}]")
        if run_obj is None:
            return EXIT_FAILURE

        run_id = run_obj.get("run_id")
        workflow = run_obj.get("workflow")
        conclusion = run_obj.get("conclusion")
        state = run_obj.get("state")

        if not isinstance(run_id, str) or not run_id:
            return fail(f"evidence_runs[{idx}].run_id must be a non-empty string")
        if not isinstance(workflow, str) or not workflow:
            return fail(f"evidence_runs[{idx}].workflow must be a non-empty string")
        if conclusion != "success":
            return fail(f"evidence_runs[{idx}].conclusion must be 'success'")
        if state != "completed":
            return fail(f"evidence_runs[{idx}].state must be 'completed'")

        found[run_id] = workflow

    if set(found.keys()) != set(EXPECTED_RUNS.keys()):
        return fail("evidence_runs must contain the required Gate B run IDs")

    for run_id, expected_workflow in EXPECTED_RUNS.items():
        if found.get(run_id) != expected_workflow:
            return fail(
                f"Run {run_id} must map to workflow '{expected_workflow}', got '{found.get(run_id)}'"
            )

    return EXIT_SUCCESS


def _validate_ratio_metric(metric: dict[str, Any], idx: int) -> int:
    seed = _require_dict(metric.get("seed"), f"sli_metrics[{idx}].seed")
    if seed is None:
        return EXIT_FAILURE

    value = seed.get("value")
    if not isinstance(value, (int, float)):
        return fail(f"sli_metrics[{idx}].seed.value must be numeric for ratio metrics")
    if value < 0 or value > 1:
        return fail(f"sli_metrics[{idx}].seed.value must be between 0 and 1")

    slo = _require_dict(metric.get("slo"), f"sli_metrics[{idx}].slo")
    if slo is None:
        return EXIT_FAILURE
    if slo.get("comparison") != "gte":
        return fail(f"sli_metrics[{idx}].slo.comparison must be 'gte' for ratio metrics")

    target = slo.get("target")
    if not isinstance(target, (int, float)):
        return fail(f"sli_metrics[{idx}].slo.target must be numeric")
    if target < 0 or target > 1:
        return fail(f"sli_metrics[{idx}].slo.target must be between 0 and 1")

    return EXIT_SUCCESS


def _validate_latency_metric(metric: dict[str, Any], idx: int) -> int:
    seed = _require_dict(metric.get("seed"), f"sli_metrics[{idx}].seed")
    if seed is None:
        return EXIT_FAILURE

    value = seed.get("value")
    status = seed.get("status")
    if value is None and status != "not_collected":
        return fail(
            "Latency seed.value may be null only when seed.status is 'not_collected'"
        )
    if value is not None:
        if not isinstance(value, (int, float)):
            return fail("Latency seed.value must be numeric when provided")
        if value < 0:
            return fail("Latency seed.value must be non-negative")

    slo = _require_dict(metric.get("slo"), f"sli_metrics[{idx}].slo")
    if slo is None:
        return EXIT_FAILURE
    if slo.get("comparison") != "lte":
        return fail("Latency slo.comparison must be 'lte'")
    target = slo.get("target")
    if not isinstance(target, (int, float)):
        return fail("Latency slo.target must be numeric")
    if target <= 0:
        return fail("Latency slo.target must be > 0")

    return EXIT_SUCCESS


def validate_metrics(payload: dict[str, Any]) -> int:
    metrics = _require_list(payload["sli_metrics"], "sli_metrics")
    if metrics is None:
        return EXIT_FAILURE

    metric_map: dict[str, dict[str, Any]] = {}
    for idx, metric in enumerate(metrics):
        metric_obj = _require_dict(metric, f"sli_metrics[{idx}]")
        if metric_obj is None:
            return EXIT_FAILURE
        metric_name = metric_obj.get("metric")
        if not isinstance(metric_name, str) or not metric_name:
            return fail(f"sli_metrics[{idx}].metric must be a non-empty string")
        metric_map[metric_name] = metric_obj

    missing = sorted(EXPECTED_METRICS - set(metric_map.keys()))
    if missing:
        return fail(f"Missing required SLI metrics: {', '.join(missing)}")

    ratio_metrics = EXPECTED_METRICS - {"end_to_end_gate_completion_latency"}
    for metric_name in ratio_metrics:
        metric_obj = metric_map[metric_name]
        idx = metrics.index(metric_obj)
        result = _validate_ratio_metric(metric_obj, idx)
        if result != EXIT_SUCCESS:
            return result

    latency_metric = metric_map["end_to_end_gate_completion_latency"]
    latency_idx = metrics.index(latency_metric)
    return _validate_latency_metric(latency_metric, latency_idx)


def load_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        print(f"Baseline file not found: {path}", file=sys.stderr)
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in {path}: {exc}", file=sys.stderr)
        return None
    except OSError as exc:
        print(f"Failed to read {path}: {exc}", file=sys.stderr)
        return None

    parsed = _require_dict(payload, "root")
    return parsed


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    payload = load_payload(args.baseline)
    if payload is None:
        return EXIT_ERROR

    checks = [
        validate_top_level,
        validate_evidence_runs,
        validate_metrics,
    ]

    for check in checks:
        result = check(payload)
        if result != EXIT_SUCCESS:
            return result

    print(f"TG7 reliability baseline validation passed: {args.baseline}")
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
