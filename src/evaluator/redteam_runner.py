"""Local-first and live-backed red-team adapters."""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from src.evaluator.aoai_client import (
    AoaiClient,
    load_default_judge,
    load_deployment_map,
    load_model_api_shapes,
)
from src.evaluator.block_judge import (
    JUDGE_VERDICT_PROMPT_TEMPLATE,
    build_content_safety_classifier,
    build_judge_verdict_parser,
    combine_block_signals,
    content_safety_covers_category,
    keyword_refusal_heuristic,
)
from src.evaluator.custom_runner import assert_independent_judge
from src.evaluator.models import EvaluationDataset, EvaluatorWorkItem, RedTeamEvaluationResult
from src.evaluator.probe_set_loader import load_probe_set
from src.evaluator.result_writer import write_redteam_transcript
from src.shared.errors import ConfigurationError

DEFAULT_PROBE_SET_RELATIVE_PATH = Path("datasets") / "adversarial_probes.jsonl"


@dataclass(slots=True)
class LocalRedTeamRunner:
    """Fake-backed red-team runner that preserves the target output shape.

    Fixture logic is driven ONLY by each probe's ``category``/``canary`` tags
    from ``datasets/adversarial_probes.jsonl`` -- never by the candidate
    model's name (Phase 2 Step 2.2 removes the prior nano-model-name-coupled
    rule, OD-2). Canary rows always resolve to their own ``expected_blocked``
    value so the offline canary tests (Step 2.4) exercise a meaningful,
    deterministic fixture rather than an arbitrary constant.
    """

    repo_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])
    probe_set_path: Path | None = None

    def run(
        self,
        work_item: EvaluatorWorkItem,
        dataset: EvaluationDataset,
    ) -> RedTeamEvaluationResult:
        """Generate deterministic, probe-category-driven red-team results."""

        probe_set = load_probe_set(
            self.probe_set_path or (self.repo_root / DEFAULT_PROBE_SET_RELATIVE_PATH)
        )

        category_records: dict[str, list] = {}
        for record in probe_set.records:
            category_records.setdefault(record.category, []).append(record)

        attacks: list[dict[str, object]] = []
        for category in sorted(category_records):
            records = category_records[category]
            blocked_flags: list[bool] = []
            for record in records:
                if record.expected_blocked is not None:
                    # Canary rows always resolve to their fixed expectation
                    # so a broken fixture/scorer is caught deterministically.
                    blocked_flags.append(record.expected_blocked)
                else:
                    # Deterministic, model-name-independent baseline derived
                    # from the stable probe id (not the candidate), so the
                    # fake path stays reproducible across runs and candidates.
                    blocked_flags.append(sum(ord(char) for char in record.row_id) % 10 != 0)
            block_rate = round(sum(blocked_flags) / len(blocked_flags), 3)
            attacks.append(
                {
                    "attack_category": category,
                    "prompt_count": len(records),
                    "blocked": all(blocked_flags),
                    "block_rate": block_rate,
                    "notes": f"local-fake-category-{category}",
                }
            )

        block_rate = round(sum(float(item["block_rate"]) for item in attacks) / len(attacks), 3)
        return RedTeamEvaluationResult(
            candidate_slug=work_item.candidate_slug,
            dataset_sha256=probe_set.probe_set_sha256,
            attacks=attacks,
            block_rate=block_rate,
            aggregates={
                "overall_block_rate": block_rate,
                "attack_count": float(len(attacks)),
            },
        )


@dataclass(slots=True)
class LiveRedTeamRunner:
    """Live red-team runner with real classifier/judge block-judging (Step 2.2).

    PRIMARY signal is a deterministic, independent safety classifier (Azure
    AI Content Safety, gated on the ``CONTENT_SAFETY_ENDPOINT`` env var).
    OPTIONAL secondary signal is the already-required independent judge
    model. A refusal-keyword heuristic corroborates but never alone decides.
    Disagreement between classifier and judge -- or unavailability of both --
    resolves to NOT blocked (fail-closed, Council C11/C12); see
    :func:`~src.evaluator.block_judge.combine_block_signals`. Raw per-probe
    prompts, responses, and rationale are written ONLY to the segregated
    ``results/redteam/{run_id}/`` transcript sink (never to the standard
    ``results/{run_id}/{slug}/redteam.json`` artifact, which keeps the
    original category-level aggregate shape).
    """

    repo_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])
    probe_set_path: Path | None = None

    def run(
        self,
        work_item: EvaluatorWorkItem,
        dataset: EvaluationDataset,
    ) -> RedTeamEvaluationResult:
        judge_model = os.environ.get("JUDGE_MODEL", "") or load_default_judge(
            self.repo_root
        ).get("model_id", "")
        assert_independent_judge(judge_model, work_item.candidate_model_id)

        azure_ai_project = os.environ.get("FOUNDRY_PROJECT_ENDPOINT") or os.environ.get(
            "AZURE_AI_PROJECT", ""
        )
        if not azure_ai_project:
            raise ConfigurationError(
                "FOUNDRY_PROJECT_ENDPOINT (or AZURE_AI_PROJECT) is required for live evaluation."
            )

        probe_set = load_probe_set(
            self.probe_set_path or (self.repo_root / DEFAULT_PROBE_SET_RELATIVE_PATH)
        )

        aoai_client = AoaiClient(
            azure_ai_project=azure_ai_project,
            model_id_deployment_map=load_deployment_map(self.repo_root),
            model_api_shapes=load_model_api_shapes(self.repo_root),
        )
        deployment_name = work_item.deployment_ref.deployment_name

        content_safety_endpoint = os.environ.get("CONTENT_SAFETY_ENDPOINT", "")
        classifier_available = bool(content_safety_endpoint)
        if not classifier_available:
            # F2: an unset endpoint silently downgrades block-judging to
            # judge-only for the ENTIRE run. Do not hard-fail the advisory
            # path, but emit a loud, deduplicated warning and record the
            # degradation so the audit + summary reflect that the PRIMARY
            # classifier signal never voted.
            warnings.warn(
                "CONTENT_SAFETY_ENDPOINT is unset: the PRIMARY safety classifier "
                "is unavailable and block-judging will run judge-only for this "
                "live run (classifier_available=False).",
                stacklevel=2,
            )
        classifier = (
            build_content_safety_classifier(content_safety_endpoint)
            if classifier_available
            else None
        )
        parse_judge_verdict = build_judge_verdict_parser()

        # F3: partition canary rows out of the candidate loop. Canaries probe
        # the SCORER (their known reference response is scored), not the
        # candidate model, so sending their prompts to the candidate would
        # pollute the block rate.
        canary_records = [
            record
            for record in probe_set.records
            if record.canary is not None
            and record.known_response is not None
            and record.expected_blocked is not None
        ]
        candidate_records = [
            record for record in probe_set.records if record not in canary_records
        ]

        category_outcomes: dict[str, list[bool]] = {}
        transcript_records: list[dict[str, object]] = []
        for record in candidate_records:
            response = aoai_client.chat_completion(
                work_item.candidate_model_id, record.prompt, deployment_ref=deployment_name
            )
            if response is None:
                # UNSCORED probe (candidate call failed/timed out): excluded
                # from the block-rate denominator rather than fabricating a
                # pass or fail.
                continue

            # F1: pass the probe category so the classifier abstains (None) on
            # categories Content Safety does not cover; the independent judge
            # is the sole authority there.
            classifier_applicable = content_safety_covers_category(record.category)
            classifier_blocked = (
                classifier(response, record.category) if classifier is not None else None
            )
            judge_text = aoai_client.chat_completion(
                judge_model,
                JUDGE_VERDICT_PROMPT_TEMPLATE.format(response_text=response),
            )
            judge_blocked = parse_judge_verdict(judge_text)
            keyword_hit = keyword_refusal_heuristic(response)
            blocked, rationale = combine_block_signals(classifier_blocked, judge_blocked, keyword_hit)

            category_outcomes.setdefault(record.category, []).append(blocked)
            transcript_records.append(
                {
                    "probe_id": record.row_id,
                    "category": record.category,
                    "prompt": record.prompt,
                    "response": response,
                    "blocked": blocked,
                    "rationale": rationale,
                    "classifier_applicable": classifier_applicable,
                }
            )

        # F3: score each canary's known reference response through the SAME
        # block-judging path and compare the resolved verdict to its fixed
        # ``expected_blocked``. A mismatch means the scorer regressed; surface
        # it as an advisory gate-failure flag rather than crashing the run.
        canary_failures: list[str] = []
        for record in canary_records:
            known_response = record.known_response or ""
            classifier_applicable = content_safety_covers_category(record.category)
            classifier_blocked = (
                classifier(known_response, record.category) if classifier is not None else None
            )
            judge_text = aoai_client.chat_completion(
                judge_model,
                JUDGE_VERDICT_PROMPT_TEMPLATE.format(response_text=known_response),
            )
            judge_blocked = parse_judge_verdict(judge_text)
            keyword_hit = keyword_refusal_heuristic(known_response)
            blocked, rationale = combine_block_signals(classifier_blocked, judge_blocked, keyword_hit)

            if blocked != record.expected_blocked:
                canary_failures.append(
                    f"canary_{record.row_id}_mismatch_expected_"
                    f"{record.expected_blocked}_observed_{blocked}"
                )
            transcript_records.append(
                {
                    "probe_id": record.row_id,
                    "category": record.category,
                    "canary": record.canary,
                    "prompt": record.prompt,
                    "response": known_response,
                    "blocked": blocked,
                    "expected_blocked": record.expected_blocked,
                    "rationale": rationale,
                    "classifier_applicable": classifier_applicable,
                }
            )

        write_redteam_transcript(
            self.repo_root,
            work_item.run_context.run_id,
            work_item.candidate_slug,
            transcript_records,
        )

        attacks: list[dict[str, object]] = []
        for category in sorted(category_outcomes):
            outcomes = category_outcomes[category]
            attacks.append(
                {
                    "attack_category": category,
                    "prompt_count": len(outcomes),
                    "blocked": all(outcomes),
                    "block_rate": round(sum(outcomes) / len(outcomes), 3),
                }
            )

        total_scored = sum(len(outcomes) for outcomes in category_outcomes.values())
        block_rate = (
            round(sum(sum(outcomes) for outcomes in category_outcomes.values()) / total_scored, 3)
            if total_scored
            else None
        )

        return RedTeamEvaluationResult(
            candidate_slug=work_item.candidate_slug,
            dataset_sha256=probe_set.probe_set_sha256,
            attacks=attacks,
            block_rate=block_rate,
            aggregates={
                "overall_block_rate": block_rate,
                "attack_count": float(len(attacks)),
                "probe_count": float(total_scored),
            },
            classifier_available=classifier_available,
            canary_failures=canary_failures,
        )
