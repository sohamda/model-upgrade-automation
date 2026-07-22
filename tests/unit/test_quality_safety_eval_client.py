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
    resolve_evaluator_score,
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


class _ScriptedEvaluator:
    """Callable evaluator returning per-row scores under one score key."""

    def __init__(
        self, key: str, scores: list[float | None], *, raise_always: bool = False
    ) -> None:
        self._key = key
        self._scores = list(scores)
        self._index = 0
        self._raise_always = raise_always

    def __call__(self, **kwargs: object) -> dict[str, float]:
        if self._raise_always:
            raise RuntimeError("evaluator error")
        score = self._scores[self._index]
        self._index += 1
        if score is None:
            raise RuntimeError("row error")
        return {self._key: score}


class _StatelessEvaluator:
    """Callable evaluator returning a fixed score irrespective of row."""

    def __init__(self, key: str, score: float) -> None:
        self._key = key
        self._score = score

    def __call__(self, **kwargs: object) -> dict[str, float]:
        return {self._key: self._score}


def _factory(evaluator: object) -> object:
    """Wrap an evaluator instance in a content-safety factory closure."""

    def _make(**kwargs: object) -> object:
        return evaluator

    return _make


def _foundry(
    probe_prompts: tuple[str, ...] | None,
    response_provider: object,
    *,
    content_safety_threshold: int = DEFAULT_CONTENT_SAFETY_THRESHOLD,
) -> FoundryQualitySafetyEvalClient:
    """Construct a live client with an injected probe seam, no extra required."""

    with _allow_azure_import():
        return FoundryQualitySafetyEvalClient(
            azure_ai_project="https://owned.example/api/projects/p",
            judge_model="judge-1",
            probe_prompts=probe_prompts,
            response_provider=response_provider,  # type: ignore[arg-type]
            content_safety_threshold=content_safety_threshold,
            credential=object(),
        )


class RunQualityTests(unittest.TestCase):
    def test_given_scored_rows_when_running_then_per_dim_means_and_groundedness_none(
        self,
    ) -> None:
        client = _foundry(("p1", "p2", "p3"), lambda model_id, prompt: f"resp-{prompt}")
        sdk = SimpleNamespace(
            quality_evaluators={
                "fluency": _ScriptedEvaluator("fluency", [3.0, 4.0, 5.0]),
                "coherence": _ScriptedEvaluator("coherence", [2.0, 3.0, 4.0]),
                "relevance": _ScriptedEvaluator("relevance", [5.0, 5.0, 5.0]),
            }
        )

        scores = client._run_quality(sdk, object(), "m1", "target")

        assert scores is not None
        self.assertIsNone(scores["groundedness"])
        self.assertAlmostEqual(scores["fluency"], 4.0, places=6)
        self.assertAlmostEqual(scores["coherence"], 3.0, places=6)
        self.assertAlmostEqual(scores["relevance"], 5.0, places=6)

    def test_given_one_dimension_errors_when_running_then_that_dim_none(self) -> None:
        client = _foundry(("p1", "p2", "p3"), lambda model_id, prompt: "resp")
        sdk = SimpleNamespace(
            quality_evaluators={
                "fluency": _ScriptedEvaluator("fluency", [4.0, 4.0, 4.0]),
                "coherence": _ScriptedEvaluator("coherence", [], raise_always=True),
                "relevance": _ScriptedEvaluator("relevance", [4.0, 4.0, 4.0]),
            }
        )

        scores = client._run_quality(sdk, object(), "m1", "target")

        assert scores is not None
        self.assertIsNone(scores["coherence"])
        self.assertAlmostEqual(scores["fluency"], 4.0, places=6)
        self.assertAlmostEqual(scores["relevance"], 4.0, places=6)

    def test_given_empty_probe_prompts_when_running_then_none(self) -> None:
        client = _foundry((), lambda model_id, prompt: "resp")
        sdk = SimpleNamespace(quality_evaluators={})

        self.assertIsNone(client._run_quality(sdk, object(), "m1", "target"))

    def test_given_absent_provider_when_running_then_none(self) -> None:
        client = _foundry(("p1",), None)
        sdk = SimpleNamespace(
            quality_evaluators={"fluency": _StatelessEvaluator("fluency", 4.0)}
        )

        self.assertIsNone(client._run_quality(sdk, object(), "m1", "target"))

    def test_given_all_rows_error_when_running_then_none(self) -> None:
        client = _foundry(("p1", "p2"), lambda model_id, prompt: "resp")
        sdk = SimpleNamespace(
            quality_evaluators={
                "fluency": _ScriptedEvaluator("fluency", [], raise_always=True),
                "coherence": _ScriptedEvaluator("coherence", [], raise_always=True),
                "relevance": _ScriptedEvaluator("relevance", [], raise_always=True),
            }
        )

        self.assertIsNone(client._run_quality(sdk, object(), "m1", "target"))


class RunContentSafetyTests(unittest.TestCase):
    def test_given_crafted_severities_when_running_then_exact_flag_and_total(
        self,
    ) -> None:
        client = _foundry(
            ("p1", "p2", "p3", "p4", "p5"), lambda model_id, prompt: "resp"
        )
        sdk = SimpleNamespace(
            content_safety_evaluators={
                "violence": _factory(
                    _ScriptedEvaluator("violence", [4.0, 1.0, 0.0, 2.0, 1.0])
                ),
                "sexual": _factory(
                    _ScriptedEvaluator("sexual", [0.0, 0.0, 0.0, 0.0, 0.0])
                ),
                "self_harm": _factory(
                    _ScriptedEvaluator("self_harm", [0.0, 0.0, 0.0, 0.0, 0.0])
                ),
                "hate_unfairness": _factory(
                    _ScriptedEvaluator("hate_unfairness", [0.0, 0.0, 5.0, 0.0, 0.0])
                ),
            }
        )

        result = client._run_content_safety(sdk, object(), "m1", "target")

        self.assertEqual(result, (2, 5))

    def test_given_empty_probe_prompts_when_running_then_none(self) -> None:
        client = _foundry((), lambda model_id, prompt: "resp")
        sdk = SimpleNamespace(content_safety_evaluators={})

        self.assertIsNone(client._run_content_safety(sdk, object(), "m1", "target"))

    def test_given_all_evaluators_error_when_running_then_none(self) -> None:
        client = _foundry(("p1", "p2"), lambda model_id, prompt: "resp")
        sdk = SimpleNamespace(
            content_safety_evaluators={
                "violence": _factory(
                    _ScriptedEvaluator("violence", [], raise_always=True)
                )
            }
        )

        self.assertIsNone(client._run_content_safety(sdk, object(), "m1", "target"))

    def test_given_unresponsive_row_when_running_then_excluded_from_total(self) -> None:
        def _provider(model_id: str, prompt: str) -> str | None:
            return None if prompt == "p2" else "resp"

        client = _foundry(("p1", "p2", "p3"), _provider)
        sdk = SimpleNamespace(
            content_safety_evaluators={
                "violence": _factory(_ScriptedEvaluator("violence", [4.0, 0.0]))
            }
        )

        result = client._run_content_safety(sdk, object(), "m1", "target")

        self.assertEqual(result, (1, 2))

    def test_given_reused_client_when_running_two_models_then_provider_sees_both(
        self,
    ) -> None:
        seen: list[str] = []

        def _provider(model_id: str, prompt: str) -> str:
            seen.append(model_id)
            return "resp"

        client = _foundry(("p1", "p2"), _provider)
        sdk = SimpleNamespace(
            content_safety_evaluators={
                "violence": _factory(_StatelessEvaluator("violence", 1.0))
            }
        )

        client._run_content_safety(sdk, object(), "m1", "target")
        client._run_content_safety(sdk, object(), "m2", "target")

        self.assertIn("m1", seen)
        self.assertIn("m2", seen)


class EvaluateModelUnderSampleTests(unittest.TestCase):
    def test_given_content_safety_below_min_samples_when_evaluating_then_rate_none(
        self,
    ) -> None:
        with _allow_azure_import():
            client = FoundryQualitySafetyEvalClient(
                azure_ai_project="https://owned.example/api/projects/p",
                judge_model="judge-1",
                min_samples=5,
                credential=object(),
            )
        sdk = SimpleNamespace(
            content_safety_evaluators={
                "violence": object,
                "sexual": object,
                "self_harm": object,
                "hate_unfairness": object,
            }
        )
        target = FoundryQualitySafetyEvalClient
        with mock.patch.object(
            target, "_load_sdk", return_value=sdk
        ), mock.patch.object(
            target, "_sdk_version", return_value="1.18.1"
        ), mock.patch.object(
            target, "_run_quality", return_value=None
        ), mock.patch.object(
            target, "_run_content_safety", return_value=(1, 3)
        ), mock.patch.object(
            target, "_run_red_team", return_value=None
        ):
            signals = client.evaluate_model("gpt-4.1")

        self.assertIsNone(signals.content_safety_defect_rate)
        self.assertEqual(signals.content_safety_sample_size, 3)


class ResolveEvaluatorScoreTests(unittest.TestCase):
    def test_given_bare_key_when_resolving_then_numeric(self) -> None:
        self.assertEqual(resolve_evaluator_score({"coherence": 4.0}, "coherence"), 4.0)

    def test_given_vendor_prefixed_key_when_resolving_then_numeric(self) -> None:
        self.assertEqual(
            resolve_evaluator_score({"gpt_coherence": 3.5}, "coherence"), 3.5
        )

    def test_given_suffixed_key_when_resolving_then_numeric(self) -> None:
        self.assertEqual(resolve_evaluator_score({"violence_score": 2}, "violence"), 2.0)

    def test_given_non_numeric_value_when_resolving_then_none(self) -> None:
        self.assertIsNone(resolve_evaluator_score({"coherence": "high"}, "coherence"))

    def test_given_bool_value_when_resolving_then_none(self) -> None:
        self.assertIsNone(resolve_evaluator_score({"coherence": True}, "coherence"))

    def test_given_non_dict_when_resolving_then_none(self) -> None:
        self.assertIsNone(resolve_evaluator_score(4.0, "coherence"))


if __name__ == "__main__":
    unittest.main()
