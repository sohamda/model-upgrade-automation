"""Unit tests for the quality/safety evaluator seam and score helpers."""

from __future__ import annotations

import builtins
import importlib
import unittest
from types import SimpleNamespace
from unittest import mock

from src.evaluator.quality_safety_eval_client import (
    ALLOWED_ATTACK_STRATEGIES,
    ASR_CONVENTION,
    DEFAULT_CONTENT_SAFETY_THRESHOLD,
    DEFAULT_NUM_OBJECTIVES,
    NUM_OBJECTIVES_CEILING,
    FoundryQualitySafetyEvalClient,
    RawEvalSignals,
    StubQualitySafetyEvalClient,
    assert_owned_target,
    clamp01,
    compute_defect_rate,
    derive_quality_score,
    derive_safety_score,
    has_safety_signal,
)
from src.shared.errors import DependencyUnavailableError


def _allow_azure_import() -> mock._patch:
    """Patch ``builtins.__import__`` so azure SDK imports succeed as stubs.

    Lets :class:`FoundryQualitySafetyEvalClient` construct in a hermetic test
    without the ``[evaluation]`` extra installed; the real SDK surface is then
    supplied by patching ``_load_sdk``.
    """

    real_import = builtins.__import__

    def _fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("azure.ai.evaluation") or name.startswith("azure.identity"):
            return SimpleNamespace()
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    return mock.patch("builtins.__import__", _fake_import)


class ClampTests(unittest.TestCase):
    def test_given_in_range_when_clamping_then_unchanged(self) -> None:
        self.assertEqual(clamp01(0.5), 0.5)

    def test_given_below_zero_when_clamping_then_returns_zero(self) -> None:
        self.assertEqual(clamp01(-2.0), 0.0)

    def test_given_above_one_when_clamping_then_returns_one(self) -> None:
        self.assertEqual(clamp01(3.5), 1.0)


class DeriveQualityScoreTests(unittest.TestCase):
    def test_given_all_fives_when_deriving_then_returns_one(self) -> None:
        signals = RawEvalSignals(
            groundedness=5.0, coherence=5.0, relevance=5.0, fluency=5.0
        )
        self.assertAlmostEqual(derive_quality_score(signals), 1.0, places=6)

    def test_given_all_ones_when_deriving_then_returns_zero(self) -> None:
        signals = RawEvalSignals(
            groundedness=1.0, coherence=1.0, relevance=1.0, fluency=1.0
        )
        self.assertAlmostEqual(derive_quality_score(signals), 0.0, places=6)

    def test_given_mixed_likert_when_deriving_then_returns_known_value(self) -> None:
        # mean = (4 + 3 + 5 + 4) / 4 = 4.0 -> (4.0 - 1) / 4 = 0.75
        signals = RawEvalSignals(
            groundedness=4.0, coherence=3.0, relevance=5.0, fluency=4.0
        )
        self.assertAlmostEqual(derive_quality_score(signals), 0.75, places=6)


class DeriveSafetyScoreTests(unittest.TestCase):
    def test_given_defect_and_asr_when_deriving_then_returns_worst(self) -> None:
        # 1 - 0.1 = 0.9 ; 1 - 20/100 = 0.8 ; worst = 0.8
        signals = RawEvalSignals(
            groundedness=4.0,
            coherence=4.0,
            relevance=4.0,
            fluency=4.0,
            content_safety_defect_rate=0.1,
            overall_asr=20.0,
        )
        self.assertAlmostEqual(derive_safety_score(signals), 0.8, places=6)

    def test_given_only_defect_rate_when_deriving_then_uses_defect(self) -> None:
        signals = RawEvalSignals(
            groundedness=4.0,
            coherence=4.0,
            relevance=4.0,
            fluency=4.0,
            content_safety_defect_rate=0.25,
        )
        self.assertAlmostEqual(derive_safety_score(signals), 0.75, places=6)

    def test_given_both_none_when_deriving_then_defaults_to_one(self) -> None:
        signals = RawEvalSignals(
            groundedness=4.0, coherence=4.0, relevance=4.0, fluency=4.0
        )
        self.assertAlmostEqual(derive_safety_score(signals), 1.0, places=6)


class StubClientTests(unittest.TestCase):
    def test_given_same_model_when_evaluating_then_deterministic(self) -> None:
        client = StubQualitySafetyEvalClient()
        first = client.evaluate_model("gpt-4.1")
        second = client.evaluate_model("gpt-4.1")
        self.assertEqual(first, second)

    def test_given_stub_signals_when_deriving_then_scores_in_range(self) -> None:
        client = StubQualitySafetyEvalClient()
        signals = client.evaluate_model("o3")
        quality = derive_quality_score(signals)
        safety = derive_safety_score(signals)
        self.assertTrue(0.0 <= quality <= 1.0)
        self.assertTrue(0.0 <= safety <= 1.0)


class FoundryClientImportGuardTests(unittest.TestCase):
    def test_given_missing_extra_when_constructing_then_raises(self) -> None:
        real_import = builtins.__import__

        def _fake_import(name: str, *args: object, **kwargs: object) -> object:
            if name.startswith("azure.ai.evaluation") or name.startswith(
                "azure.identity"
            ):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

        builtins.__import__ = _fake_import
        try:
            with self.assertRaises(DependencyUnavailableError):
                FoundryQualitySafetyEvalClient(azure_ai_project="proj")
        finally:
            builtins.__import__ = real_import


class ImportWithoutExtraTests(unittest.TestCase):
    def test_given_no_extra_when_importing_module_then_succeeds(self) -> None:
        # Importing the seam must never require the [evaluation] extra.
        module = importlib.import_module("src.evaluator.quality_safety_eval_client")
        self.assertTrue(hasattr(module, "FoundryQualitySafetyEvalClient"))


class OwnedTargetScopeLockTests(unittest.TestCase):
    def test_given_foreign_host_when_asserting_then_refuses_without_url(self) -> None:
        with self.assertRaises(RuntimeError) as caught:
            assert_owned_target(
                "https://owned.example/api/projects/p",
                "https://foreign.example/api/projects/x",
            )
        self.assertNotIn("foreign.example", str(caught.exception))

    def test_given_same_host_when_asserting_then_allows(self) -> None:
        assert_owned_target(
            "https://owned.example/api/projects/p",
            "https://owned.example/other",
        )

    def test_given_unresolvable_host_when_asserting_then_refuses(self) -> None:
        with self.assertRaises(RuntimeError):
            assert_owned_target("", "https://owned.example/x")


class ComputeDefectRateTests(unittest.TestCase):
    def test_given_enough_samples_when_computing_then_returns_rate(self) -> None:
        self.assertAlmostEqual(
            compute_defect_rate(1, 10, min_samples=5), 0.1, places=6
        )

    def test_given_too_few_samples_when_computing_then_returns_none(self) -> None:
        self.assertIsNone(compute_defect_rate(1, 3, min_samples=5))

    def test_given_zero_total_when_computing_then_returns_none(self) -> None:
        self.assertIsNone(compute_defect_rate(0, 0, min_samples=5))


class DeriveQualityScoreNoneTests(unittest.TestCase):
    def test_given_all_none_dims_when_deriving_then_returns_none(self) -> None:
        signals = RawEvalSignals(
            groundedness=None, coherence=None, relevance=None, fluency=None
        )
        self.assertIsNone(derive_quality_score(signals))

    def test_given_partial_dims_when_deriving_then_averages_present(self) -> None:
        # only groundedness=5 and fluency=3 present -> mean 4 -> 0.75
        signals = RawEvalSignals(
            groundedness=5.0, coherence=None, relevance=None, fluency=3.0
        )
        self.assertAlmostEqual(derive_quality_score(signals), 0.75, places=6)


class HasSafetySignalTests(unittest.TestCase):
    def test_given_defect_present_when_checking_then_true(self) -> None:
        signals = RawEvalSignals(
            groundedness=None,
            coherence=None,
            relevance=None,
            fluency=None,
            content_safety_defect_rate=0.0,
        )
        self.assertTrue(has_safety_signal(signals))

    def test_given_both_none_when_checking_then_false(self) -> None:
        signals = RawEvalSignals(
            groundedness=None, coherence=None, relevance=None, fluency=None
        )
        self.assertFalse(has_safety_signal(signals))


class FoundryBoundedParamTests(unittest.TestCase):
    def test_given_num_objectives_over_ceiling_when_constructing_then_raises(
        self,
    ) -> None:
        with _allow_azure_import():
            with self.assertRaises(ValueError):
                FoundryQualitySafetyEvalClient(
                    azure_ai_project="https://owned.example/p",
                    judge_model="judge",
                    num_objectives=NUM_OBJECTIVES_CEILING + 1,
                )

    def test_given_disallowed_strategy_when_constructing_then_raises(self) -> None:
        with _allow_azure_import():
            with self.assertRaises(ValueError):
                FoundryQualitySafetyEvalClient(
                    azure_ai_project="https://owned.example/p",
                    judge_model="judge",
                    attack_strategies=("Baseline", "Nuclear"),
                )

    def test_given_zero_max_candidates_when_constructing_then_raises(self) -> None:
        with _allow_azure_import():
            with self.assertRaises(ValueError):
                FoundryQualitySafetyEvalClient(
                    azure_ai_project="https://owned.example/p",
                    judge_model="judge",
                    max_candidates=0,
                )


class FoundryEvaluateModelTests(unittest.TestCase):
    def _build(self) -> FoundryQualitySafetyEvalClient:
        with _allow_azure_import():
            return FoundryQualitySafetyEvalClient(
                azure_ai_project="https://owned.example/api/projects/p",
                judge_model="judge-1",
                credential=object(),
            )

    def test_given_all_runs_error_when_evaluating_then_signals_none(self) -> None:
        client = self._build()
        sdk = SimpleNamespace(content_safety_evaluators={"violence": object})

        def _raise(*args: object, **kwargs: object) -> None:
            raise RuntimeError("scan failed")

        target = FoundryQualitySafetyEvalClient
        with mock.patch.object(target, "_load_sdk", return_value=sdk), mock.patch.object(
            target, "_run_quality", side_effect=_raise
        ), mock.patch.object(
            target, "_run_content_safety", side_effect=_raise
        ), mock.patch.object(
            target, "_run_red_team", side_effect=_raise
        ):
            signals = client.evaluate_model("gpt-4.1")

        self.assertIsNone(signals.groundedness)
        self.assertIsNone(signals.content_safety_defect_rate)
        self.assertIsNone(signals.overall_asr)
        self.assertFalse(has_safety_signal(signals))

    def test_given_successful_runs_when_evaluating_then_provenance_stamped(
        self,
    ) -> None:
        client = self._build()
        sdk = SimpleNamespace(
            content_safety_evaluators={
                "violence": object,
                "sexual": object,
                "self_harm": object,
                "hate_unfairness": object,
            }
        )
        target = FoundryQualitySafetyEvalClient
        with mock.patch.object(target, "_load_sdk", return_value=sdk), mock.patch.object(
            target, "_sdk_version", return_value="1.18.1"
        ), mock.patch.object(
            target,
            "_run_quality",
            return_value={
                "groundedness": 4.0,
                "coherence": 4.0,
                "relevance": 4.0,
                "fluency": 4.0,
            },
        ), mock.patch.object(
            target, "_run_content_safety", return_value=(1, 10)
        ), mock.patch.object(
            target, "_run_red_team", return_value=(20.0, {"violence": 25.0})
        ):
            signals = client.evaluate_model("gpt-4.1")

        self.assertAlmostEqual(signals.content_safety_defect_rate, 0.1, places=6)
        self.assertEqual(signals.content_safety_sample_size, 10)
        self.assertEqual(signals.overall_asr, 20.0)
        self.assertEqual(signals.per_risk_asr, {"violence": 25.0})
        self.assertEqual(
            signals.content_safety_threshold, DEFAULT_CONTENT_SAFETY_THRESHOLD
        )
        self.assertEqual(signals.asr_convention, ASR_CONVENTION)
        self.assertEqual(signals.sdk_version, "1.18.1")
        self.assertEqual(signals.scored_deployment, "judge-1")
        self.assertEqual(signals.num_objectives, DEFAULT_NUM_OBJECTIVES)
        self.assertEqual(signals.attack_strategies, ALLOWED_ATTACK_STRATEGIES)
        self.assertIsNotNone(signals.scan_date)
        self.assertIn("red_team", signals.evaluators_run or ())

    def test_given_missing_judge_when_evaluating_then_raises(self) -> None:
        with _allow_azure_import():
            client = FoundryQualitySafetyEvalClient(
                azure_ai_project="https://owned.example/p", credential=object()
            )
        sdk = SimpleNamespace(content_safety_evaluators={})
        with mock.patch.object(
            FoundryQualitySafetyEvalClient, "_load_sdk", return_value=sdk
        ):
            with self.assertRaises(RuntimeError):
                client.evaluate_model("gpt-4.1")


if __name__ == "__main__":
    unittest.main()
