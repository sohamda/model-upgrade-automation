"""Local-first and live-backed custom evaluator adapters."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.evaluator.aoai_client import (
    AoaiClient,
    load_default_judge,
    load_deployment_map,
    load_model_api_shapes,
)
from src.evaluator.models import CustomEvaluationResult, EvaluationDataset, EvaluatorWorkItem
from src.evaluator.quality_safety_eval_client import (
    FoundryQualitySafetyEvalClient,
    derive_quality_score,
)
from src.shared.errors import ConfigurationError


class LocalCustomRunner:
    """Fake-backed custom evaluator that preserves the target output shape."""

    evaluator_names = (
        "groundedness",
        "coherence",
        "relevance",
        "fluency",
        "conciseness",
        "violence",
        "sexual",
        "self_harm",
        "hate_unfairness",
    )

    def run(
        self,
        work_item: EvaluatorWorkItem,
        dataset: EvaluationDataset,
    ) -> CustomEvaluationResult:
        """Generate deterministic custom evaluator rows and aggregates."""

        rows: list[dict[str, object]] = []
        for index, record in enumerate(dataset.records, start=1):
            quality_base = max(0.5, min(0.99, work_item.candidate_score + (0.01 * (index % 3))))
            safety_base = max(0.75, min(0.99, 0.9 + (0.01 * (index % 2))))
            rows.append(
                {
                    "row_id": record.row_id,
                    "prompt": record.prompt,
                    "expected_response": record.expected_response,
                    "scores": {
                        "groundedness": round(quality_base, 3),
                        "coherence": round(quality_base - 0.01, 3),
                        "relevance": round(quality_base - 0.02, 3),
                        "fluency": round(quality_base + 0.01, 3),
                        "conciseness": round(quality_base - 0.015, 3),
                        "violence": round(safety_base, 3),
                        "sexual": round(safety_base - 0.01, 3),
                        "self_harm": round(safety_base, 3),
                        "hate_unfairness": round(safety_base - 0.005, 3),
                    },
                }
            )

        aggregates = {
            name: round(
                sum(float(row["scores"][name]) for row in rows) / len(rows),
                3,
            )
            for name in self.evaluator_names
        }
        aggregates["overall"] = round(
            sum(aggregates[name] for name in self.evaluator_names[:5]) / 5,
            3,
        )

        return CustomEvaluationResult(
            candidate_slug=work_item.candidate_slug,
            dataset_sha256=dataset.dataset_sha256,
            rows=rows,
            aggregates=aggregates,
        )


def _model_family(model_id: str) -> str:
    """Return the family root (token before the first ``-``) of ``model_id``.

    Legacy conservative fallback used only when a model generation cannot be
    resolved for either the judge or the candidate (see :func:`_model_generation`).
    """

    return model_id.split("-", 1)[0]


# Data-driven model GENERATION map (LIVE-BUG-01). Judge independence (Council
# C10) is defined at the GENERATION granularity, not the vendor-family token:
# a judge and a candidate are independent only when they belong to DIFFERENT
# model generations. Same-generation models (or the exact same model /
# deployment) share training lineage and failure modes, so a same-generation
# judge reintroduces the circular-reasoning risk this control exists to
# prevent (RAI). A cross-generation judge -- e.g. gpt-4.1 (gen ``gpt-4``)
# grading a gpt-5.1 (gen ``gpt-5``) or an o3 (gen ``o3``) candidate -- is
# genuinely independent and is therefore permitted.
#
# Each entry is (compiled regex, canonical generation). The pattern is
# searched (not anchored) so a generation token embedded in an owned
# DEPLOYMENT name also resolves (e.g. ``tg4-...-gpt-5-1-2025-11-13`` -> ``gpt-5``,
# ``eph-judge-o4-mini-2025-04-16`` -> ``o4``). Patterns are tried in order and
# the first match wins; GPT variants precede the o-series so a ``gpt-4``/``gpt-5``
# token is never mis-read as an o-series generation. Separators are tolerated
# so ``gpt-4.1``, ``gpt_4_1`` and ``gpt-4o`` all fold to ``gpt-4``. The
# o-series patterns require a non-alphanumeric boundary before the ``o`` so
# ``tg4`` / ``sol`` / a bare ``04`` date fragment cannot be mistaken for
# ``o4``/``o3``.
_GENERATION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"gpt[-_]?5"), "gpt-5"),
    (re.compile(r"gpt[-_]?4"), "gpt-4"),
    (re.compile(r"gpt[-_]?3"), "gpt-3"),
    (re.compile(r"(?<![a-z0-9])o4"), "o4"),
    (re.compile(r"(?<![a-z0-9])o3"), "o3"),
    (re.compile(r"(?<![a-z0-9])o1"), "o1"),
)


def _model_generation(model_id: str) -> str | None:
    """Return the canonical GENERATION of ``model_id`` (or a deployment name).

    Maps e.g. ``gpt-4.1``/``gpt-4o`` -> ``gpt-4``, ``gpt-5.1``/``gpt-5.6-sol``
    -> ``gpt-5``, ``o3``/``o3-mini`` -> ``o3``, ``o4-mini`` -> ``o4``. Returns
    ``None`` when no known generation token is present so the caller can fall
    back to a conservative family comparison rather than assuming independence.
    """

    lowered = model_id.lower()
    for pattern, generation in _GENERATION_PATTERNS:
        if pattern.search(lowered):
            return generation
    return None


def assert_independent_judge(judge_model: str, candidate_model_id: str) -> None:
    """Refuse self-grading: the judge and candidate must differ in generation.

    Compares the configured judge deployment/model identifier (``JUDGE_MODEL``,
    or the pinned ``default_judge``) against the candidate's ``model_id`` at the
    model-GENERATION granularity (:func:`_model_generation`). Raises
    :class:`ConfigurationError` when the judge is unset, equals the candidate
    exactly, or shares the candidate's generation -- a candidate must never be
    graded by itself or by a same-generation sibling (Council C10, RAI).

    Rationale: cross-generation independence (e.g. gpt-4.1 judging gpt-5.1 or
    o3) is accepted because different generations do not share the training
    lineage or failure modes that would make a judgement circular; same
    generation (gpt-5.x judging gpt-5.1, or o3/o3-mini judging o3) and the
    exact same model are rejected. When a generation cannot be resolved for
    either side the check conservatively falls back to comparing the legacy
    first-hyphen family token rather than assuming independence.
    """

    if not judge_model:
        raise ConfigurationError(
            "A judge deployment (JUDGE_MODEL) is required for live evaluation; "
            "refusing to run without an independent judge."
        )
    if judge_model == candidate_model_id:
        raise ConfigurationError(
            "The configured judge must not equal the candidate model; refusing self-grading."
        )
    judge_generation = _model_generation(judge_model)
    candidate_generation = _model_generation(candidate_model_id)
    if judge_generation is not None and candidate_generation is not None:
        if judge_generation == candidate_generation:
            raise ConfigurationError(
                "The configured judge is in the same model generation "
                f"('{candidate_generation}') as the candidate; refusing self-grading."
            )
        return
    # Unknown generation on at least one side -- conservative fallback so an
    # unmapped model can never silently pass as independent.
    if _model_family(judge_model) == _model_family(candidate_model_id):
        raise ConfigurationError(
            "The configured judge shares the candidate's model family; refusing self-grading."
        )


@dataclass(slots=True)
class LiveCustomRunner:
    """Live custom evaluator runner delegating to ``FoundryQualitySafetyEvalClient``.

    Never produces a promotion decision -- callers (``src/evaluator/service.py``)
    label every live-backed summary advisory/non-promotion-grade regardless of
    whether this runner's signals are fully scored (RAI HIGH-risk caveat).
    UNSCORED dimensions (``derive_quality_score`` returning ``None``) are
    carried through as ``aggregates["overall"] = None`` rather than coerced to
    a passing or failing value.
    """

    repo_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])

    def run(
        self,
        work_item: EvaluatorWorkItem,
        dataset: EvaluationDataset,
    ) -> CustomEvaluationResult:
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

        aoai_client = AoaiClient(
            azure_ai_project=azure_ai_project,
            model_id_deployment_map=load_deployment_map(self.repo_root),
            model_api_shapes=load_model_api_shapes(self.repo_root),
        )
        deployment_name = work_item.deployment_ref.deployment_name

        def response_provider(model_id: str, prompt: str) -> str | None:
            return aoai_client.chat_completion(model_id, prompt, deployment_ref=deployment_name)

        client = FoundryQualitySafetyEvalClient(
            azure_ai_project=azure_ai_project,
            judge_model=judge_model,
            probe_prompts=tuple(record.prompt for record in dataset.records),
            response_provider=response_provider,
            candidate_deployment_name=deployment_name,
        )
        signals = client.evaluate_model(work_item.candidate_model_id)
        quality_overall = derive_quality_score(signals)

        rows: list[dict[str, object]] = [
            {
                "row_id": record.row_id,
                "prompt": record.prompt,
                "expected_response": record.expected_response,
                "scores": {
                    "groundedness": signals.groundedness,
                    "coherence": signals.coherence,
                    "relevance": signals.relevance,
                    "fluency": signals.fluency,
                },
            }
            for record in dataset.records
        ]

        return CustomEvaluationResult(
            candidate_slug=work_item.candidate_slug,
            dataset_sha256=dataset.dataset_sha256,
            rows=rows,
            aggregates={"overall": quality_overall},
        )