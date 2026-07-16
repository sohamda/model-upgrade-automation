"""Local-first red-team adapter."""

from __future__ import annotations

from src.evaluator.models import EvaluationDataset, EvaluatorWorkItem, RedTeamEvaluationResult


class LocalRedTeamRunner:
    """Fake-backed red-team runner that preserves the target output shape."""

    categories = (
        "prompt_injection",
        "jailbreak",
        "pii_extraction",
        "harmful_content",
        "social_engineering",
        "misinformation",
    )

    def run(
        self,
        work_item: EvaluatorWorkItem,
        dataset: EvaluationDataset,
    ) -> RedTeamEvaluationResult:
        """Generate deterministic red-team attack results."""

        attacks: list[dict[str, object]] = []
        for index, category in enumerate(self.categories, start=1):
            blocked = not (work_item.candidate_model_id.endswith("nano") and category == "jailbreak")
            attacks.append(
                {
                    "attack_category": category,
                    "prompt_count": len(dataset.records),
                    "blocked": blocked,
                    "block_rate": round(1.0 if blocked else 0.84, 3),
                    "notes": f"local-fake-run-{index}",
                }
            )

        block_rate = round(
            sum(float(item["block_rate"]) for item in attacks) / len(attacks),
            3,
        )
        return RedTeamEvaluationResult(
            candidate_slug=work_item.candidate_slug,
            dataset_sha256=dataset.dataset_sha256,
            attacks=attacks,
            block_rate=block_rate,
            aggregates={
                "overall_block_rate": block_rate,
                "attack_count": float(len(attacks)),
            },
        )