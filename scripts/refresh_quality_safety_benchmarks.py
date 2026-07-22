#!/usr/bin/env python3
"""Offline producer that refreshes the cached quality/safety benchmark file.

This local, manual tool derives normalized quality and safety scores per model
through an injectable :class:`QualitySafetyEvalClient` seam and rewrites
``config/quality_safety_benchmarks.yaml`` with additive provenance fields. The
recommender runtime is unaffected: it only reads the cached YAML, and the new
provenance keys are ignored by :class:`~src.recommender.quality_safety_source.QualitySafetyBenchmarkSource`.

The default and ``--dry-run`` paths use :class:`StubQualitySafetyEvalClient`,
need no Azure or network access, and (for ``--dry-run``) do not mutate the
on-disk config. The opt-in ``--live`` flag selects the real
:class:`FoundryQualitySafetyEvalClient` (requiring an owned Foundry project and
a judge model); ``--live`` and ``--dry-run`` are mutually exclusive, and any
UNSCORED live signal falls back to the existing curated-seed entry.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
# Allow standalone execution (python scripts/...) to import the src package.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.evaluator.quality_safety_eval_client import (  # noqa: E402
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_NUM_OBJECTIVES,
    FoundryQualitySafetyEvalClient,
    QualitySafetyEvalClient,
    StubQualitySafetyEvalClient,
    derive_quality_score,
    derive_safety_score,
    has_safety_signal,
)
from src.shared.errors import DependencyUnavailableError  # noqa: E402

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
_DEFAULT_OUTPUT = _REPO_ROOT / "config" / "quality_safety_benchmarks.yaml"
# Per-run model ceiling; large enough for the full seed set but bounded.
_DEFAULT_MAX_CANDIDATES = 16

# Current curated seed set; used when the target YAML cannot be read for ids.
_SEED_MODELS = (
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-5.1",
    "o3",
    "o4-mini",
)

_EVALUATOR_VERSION = "content-safety+redteam/1"
_PROVENANCE = (
    "content-safety+redteam: quality=(mean likert-1)/4; "
    "safety=worst(1-defect_rate,1-asr/100)"
)
_SOURCE = "content-safety+redteam"

_HEADER = """\
# Quality & safety benchmark cache for recommender enrichment.
#
# Refreshed OUT-OF-BAND by scripts/refresh_quality_safety_benchmarks.py using an
# injectable evaluator-client seam. Scores are normalized 0..1 (higher=better):
#   quality_score = (mean_likert - 1) / 4        (1..5 Likert -> 0..1)
#   safety_score  = worst(1 - defect_rate, 1 - asr/100)
# Each entry carries additive provenance (source, run_id, evaluator_version,
# sdk_version) that the runtime parser ignores. The recommender only reads the
# cached quality_score/safety_score/provenance/as_of_date keys.
"""


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh the cached quality/safety benchmark YAML offline."
    )
    # --dry-run and --live are mutually exclusive: --dry-run stays 100% Azure-free
    # (stub client, no write), --live opts in to the real Foundry evaluator.
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Use the stub client and print entries without writing the file.",
    )
    mode.add_argument(
        "--live",
        action="store_true",
        help=(
            "Opt in to the real Foundry evaluator client (requires "
            "--foundry-project/FOUNDRY_PROJECT_ENDPOINT and --judge-model/JUDGE_MODEL)."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help="Target YAML path (default: config/quality_safety_benchmarks.yaml).",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Optional subset of model_ids to refresh (default: all seeded).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Provenance run id (default: RUN_ID / GITHUB_RUN_ID env or 'local').",
    )
    parser.add_argument(
        "--foundry-project",
        default=None,
        help=(
            "Owned Foundry project endpoint for --live "
            "(default: FOUNDRY_PROJECT_ENDPOINT / AZURE_AI_PROJECT env)."
        ),
    )
    parser.add_argument(
        "--judge-model",
        default=None,
        help="Judge/grader model deployment name for --live (default: JUDGE_MODEL env).",
    )
    parser.add_argument(
        "--num-objectives",
        type=int,
        default=DEFAULT_NUM_OBJECTIVES,
        help=f"Bounded red-team objective budget (default: {DEFAULT_NUM_OBJECTIVES}).",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=_DEFAULT_MAX_CANDIDATES,
        help=(
            "Per-run model cap; refresh refuses to exceed it "
            f"(default: {_DEFAULT_MAX_CANDIDATES})."
        ),
    )
    parser.add_argument(
        "--content-safety-threshold",
        type=int,
        default=None,
        help="Content-safety severity threshold T for --live (default: client default).",
    )
    return parser


def _resolve_run_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    return os.environ.get("RUN_ID") or os.environ.get("GITHUB_RUN_ID") or "local"


def _resolve_model_ids(output: Path, subset: list[str] | None) -> list[str]:
    if subset:
        return list(subset)
    try:
        with output.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError):
        return list(_SEED_MODELS)
    entries = raw.get("benchmarks") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        return list(_SEED_MODELS)
    ids = [
        entry["model_id"]
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("model_id"), str)
    ]
    return ids or list(_SEED_MODELS)


def _sdk_version() -> str:
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("azure-ai-evaluation")
    except Exception:  # noqa: BLE001 - optional dep absent on the offline path
        return "not-installed"


def _load_seed_entries(output: Path) -> dict[str, dict[str, object]]:
    """Return existing entries keyed by ``model_id`` for curated-seed fallback.

    When a live signal is UNSCORED the refresh tool reuses the cached entry
    rather than fabricating a score. Returns an empty map when the file is
    absent or unreadable.
    """

    try:
        with output.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError):
        return {}
    entries = raw.get("benchmarks") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        return {}
    seed: dict[str, dict[str, object]] = {}
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("model_id"), str):
            seed[entry["model_id"]] = dict(entry)
    return seed


def _stamp_live_provenance(entry: dict[str, object], signals: object) -> None:
    """Additively stamp live audit metadata onto ``entry`` (tuples -> lists).

    Only fields the live client populated are added; the runtime recommender
    parser ignores every key beyond quality_score/safety_score/provenance/
    as_of_date, so this stays schema-additive.
    """

    if getattr(signals, "content_safety_threshold", None) is not None:
        entry["content_safety_threshold"] = signals.content_safety_threshold
    if getattr(signals, "content_safety_sample_size", None) is not None:
        entry["content_safety_sample_size"] = signals.content_safety_sample_size
    if getattr(signals, "per_risk_asr", None):
        entry["per_risk_asr"] = dict(signals.per_risk_asr)
    if getattr(signals, "asr_convention", None):
        entry["asr_convention"] = signals.asr_convention
    if getattr(signals, "evaluators_run", None):
        entry["evaluators_run"] = list(signals.evaluators_run)
    if getattr(signals, "scored_deployment", None):
        entry["scored_deployment"] = signals.scored_deployment
    if getattr(signals, "scan_date", None):
        entry["scan_date"] = signals.scan_date
    if getattr(signals, "num_objectives", None) is not None:
        entry["num_objectives"] = signals.num_objectives
    if getattr(signals, "attack_strategies", None):
        entry["attack_strategies"] = list(signals.attack_strategies)


def build_entries(
    client: QualitySafetyEvalClient,
    model_ids: list[str],
    *,
    run_id: str,
    as_of_date: str,
    sdk_version: str,
    seed_entries: dict[str, dict[str, object]] | None = None,
    live: bool = False,
) -> list[dict[str, object]]:
    """Derive provenance-stamped benchmark entries for ``model_ids``.

    On the stub path both dimensions are always scored, so entries are produced
    directly. On the ``live`` path any UNSCORED dimension (``None`` quality mean
    or absent safety signal) falls back to the curated-seed value; when neither
    dimension is scored the existing seed entry is preserved unchanged, and when
    no seed exists the model is skipped rather than fabricated.
    """

    seeds = seed_entries or {}
    entries: list[dict[str, object]] = []
    for model_id in model_ids:
        signals = client.evaluate_model(model_id)
        quality = derive_quality_score(signals)
        safety = derive_safety_score(signals) if has_safety_signal(signals) else None
        seed = seeds.get(model_id)

        if live and quality is None and safety is None:
            if seed is not None:
                entries.append(dict(seed))
            continue

        if quality is None:
            quality = _seed_score(seed, "quality_score")
        if safety is None:
            safety = _seed_score(seed, "safety_score")
        if quality is None or safety is None:
            if seed is not None:
                entries.append(dict(seed))
            continue

        entry: dict[str, object] = {
            "model_id": model_id,
            "quality_score": round(quality, 4),
            "safety_score": round(safety, 4),
            "provenance": _PROVENANCE,
            "as_of_date": getattr(signals, "scan_date", None) or as_of_date,
            "source": _SOURCE,
            "run_id": run_id,
            "evaluator_version": _EVALUATOR_VERSION,
            "sdk_version": getattr(signals, "sdk_version", None) or sdk_version,
        }
        if live:
            _stamp_live_provenance(entry, signals)
        entries.append(entry)
    return entries


def _seed_score(seed: dict[str, object] | None, key: str) -> float | None:
    if seed is None:
        return None
    value = seed.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def render_yaml(entries: list[dict[str, object]]) -> str:
    """Render the header plus a ``benchmarks:`` document for ``entries``."""

    body = yaml.safe_dump(
        {"benchmarks": entries}, sort_keys=False, default_flow_style=False
    )
    return f"{_HEADER}\n{body}"


def _select_client(
    args: argparse.Namespace,
) -> tuple[QualitySafetyEvalClient | None, dict[str, dict[str, object]] | None, int]:
    """Return ``(client, seed_entries, exit_code)`` for the requested mode.

    On the default/dry-run path returns the dependency-free stub and no seeds.
    On ``--live`` resolves the owned Foundry project and judge model from args or
    env, refusing (EXIT_FAILURE) when either is missing or the optional extra is
    absent. ``client`` is ``None`` only when ``exit_code`` is non-zero.
    """

    if not args.live:
        return StubQualitySafetyEvalClient(), None, EXIT_SUCCESS

    project = (
        args.foundry_project
        or os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
        or os.environ.get("AZURE_AI_PROJECT")
    )
    judge = args.judge_model or os.environ.get("JUDGE_MODEL")
    missing = [
        label
        for label, value in (
            ("--foundry-project/FOUNDRY_PROJECT_ENDPOINT", project),
            ("--judge-model/JUDGE_MODEL", judge),
        )
        if not value
    ]
    if missing:
        print(f"--live requires: {', '.join(missing)}.", file=sys.stderr)
        return None, None, EXIT_FAILURE

    client_kwargs: dict[str, object] = {
        "azure_ai_project": project,
        "judge_model": judge,
        "num_objectives": args.num_objectives,
        "max_candidates": args.max_candidates,
    }
    if args.content_safety_threshold is not None:
        client_kwargs["content_safety_threshold"] = args.content_safety_threshold
    try:
        client = FoundryQualitySafetyEvalClient(**client_kwargs)
    except DependencyUnavailableError as error:
        print(f"--live unavailable: {error}", file=sys.stderr)
        return None, None, EXIT_FAILURE
    except ValueError as error:
        print(f"--live configuration rejected: {error}", file=sys.stderr)
        return None, None, EXIT_FAILURE
    return client, _load_seed_entries(args.output), EXIT_SUCCESS


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    model_ids = _resolve_model_ids(args.output, args.models)
    if len(model_ids) > args.max_candidates:
        print(
            f"Refusing to refresh {len(model_ids)} models; "
            f"--max-candidates={args.max_candidates}.",
            file=sys.stderr,
        )
        return EXIT_FAILURE

    client, seed_entries, exit_code = _select_client(args)
    if exit_code != EXIT_SUCCESS or client is None:
        return exit_code

    run_id = _resolve_run_id(args.run_id)
    entries = build_entries(
        client,
        model_ids,
        run_id=run_id,
        as_of_date=date.today().isoformat(),
        sdk_version=_sdk_version(),
        seed_entries=seed_entries,
        live=args.live,
    )
    document = render_yaml(entries)

    if args.dry_run:
        print(f"[dry-run] derived {len(entries)} entries (no file written):")
        print(document)
        return EXIT_SUCCESS

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document, encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {args.output}")
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
