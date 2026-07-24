"""Offline canary tests for red-team block-judging (Phase 2 Step 2.4).

Loads the two canary rows from ``datasets/adversarial_probes.jsonl`` (fixed
``known_response`` text, never a live model call) and exercises them through
the real :mod:`src.evaluator.block_judge` functions. Each test also
demonstrates the specific broken-scorer failure mode the canary exists to
catch (Council C12 anti-regression condition).
"""

from __future__ import annotations

from pathlib import Path
import unittest

from src.evaluator.block_judge import combine_block_signals, keyword_refusal_heuristic
from src.evaluator.probe_set_loader import load_probe_set

REPO_ROOT = Path(__file__).resolve().parents[2]
PROBE_SET_PATH = REPO_ROOT / "datasets" / "adversarial_probes.jsonl"


class PoisonCanaryTests(unittest.TestCase):
    """A known-good refusal must be recognized as blocked=True."""

    def setUp(self) -> None:
        probe_set = load_probe_set(PROBE_SET_PATH)
        self.row = next(record for record in probe_set.records if record.canary == "poison")

    def test_given_healthy_pipeline_when_poison_canary_judged_then_correctly_blocked(
        self,
    ) -> None:
        # Arrange: a healthy classifier and judge both correctly recognize
        # the known refusal text.
        keyword_hit = keyword_refusal_heuristic(self.row.known_response)

        # Act
        blocked, _ = combine_block_signals(
            classifier_blocked=True, judge_blocked=True, keyword_hit=keyword_hit
        )

        # Assert
        self.assertEqual(blocked, self.row.expected_blocked)
        self.assertTrue(blocked)

    def test_given_broken_scorer_that_never_blocks_when_poison_canary_judged_then_canary_catches_it(
        self,
    ) -> None:
        # Arrange: simulate a broken classifier/judge pair that never
        # reports a block (a "passes everything" regression).
        # Act
        blocked, _ = combine_block_signals(
            classifier_blocked=False, judge_blocked=False, keyword_hit=False
        )

        # Assert: mismatch against expected_blocked=True demonstrates the
        # canary would flag this regression rather than silently pass it.
        self.assertNotEqual(blocked, self.row.expected_blocked)


class DiscriminationCanaryTests(unittest.TestCase):
    """A known-bad (harmful-compliant) response must be recognized as blocked=False."""

    def setUp(self) -> None:
        probe_set = load_probe_set(PROBE_SET_PATH)
        self.row = next(
            record for record in probe_set.records if record.canary == "discrimination"
        )

    def test_given_healthy_pipeline_when_discrimination_canary_judged_then_correctly_not_blocked(
        self,
    ) -> None:
        # Arrange: a healthy classifier and judge both correctly recognize
        # the known harmful-compliant text as NOT a refusal.
        keyword_hit = keyword_refusal_heuristic(self.row.known_response)

        # Act
        blocked, _ = combine_block_signals(
            classifier_blocked=False, judge_blocked=False, keyword_hit=keyword_hit
        )

        # Assert
        self.assertEqual(blocked, self.row.expected_blocked)
        self.assertFalse(blocked)

    def test_given_broken_scorer_that_always_blocks_when_discrimination_canary_judged_then_canary_catches_it(
        self,
    ) -> None:
        # Arrange: simulate a broken classifier/judge pair that reports
        # every response as blocked (an over-aggressive/stubbed regression).
        # Act
        blocked, _ = combine_block_signals(
            classifier_blocked=True, judge_blocked=True, keyword_hit=True
        )

        # Assert: mismatch against expected_blocked=False demonstrates the
        # canary would flag this regression rather than silently pass it.
        self.assertNotEqual(blocked, self.row.expected_blocked)


if __name__ == "__main__":
    unittest.main()
