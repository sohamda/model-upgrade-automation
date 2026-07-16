"""Local-first custom evaluator adapter."""

from __future__ import annotations

from src.evaluator.models import CustomEvaluationResult, EvaluationDataset, EvaluatorWorkItem


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