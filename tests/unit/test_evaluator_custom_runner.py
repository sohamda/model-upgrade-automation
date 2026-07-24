"""Unit tests for the live-backed custom evaluator adapter's guard logic."""

from __future__ import annotations

import importlib
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from src.evaluator.custom_runner import (
    LiveCustomRunner,
    _model_generation,
    assert_independent_judge,
)
from src.evaluator.models import EvaluationDataset, EvaluatorConfig, EvaluatorThresholds, EvaluatorTimeouts, EvaluatorWorkItem
from src.evaluator.quality_safety_eval_client import RawEvalSignals, derive_quality_score
from src.shared.contracts import DeploymentRef, SkipIndexKey, TeardownPlan
from src.shared.errors import ConfigurationError
from src.shared.run_context import RunContext


def _run_context() -> RunContext:
    return RunContext(
        run_id="test-run",
        trigger_type="workflow_dispatch",
        started_at_utc=datetime.now(timezone.utc),
        github_repo="repo",
        github_run_id="1",
        azure_tenant_id="tenant",
        azure_subscription_id="sub",
        resource_group="rg",
        foundry_account_name="acct",
        foundry_project_name="project",
        aca_environment_name="aca-env",
        aca_job_name="aca-job",
        storage_account_name="stg",
        key_vault_name="kv",
        deployment_type="DataZoneStandard",
        allowed_regions=["swedencentral"],
        retirement_horizon_days=90,
        dataset_sha256="abc",
        correlation_version="v1",
    )


def _work_item(candidate_model_id: str = "gpt-4.1-mini") -> EvaluatorWorkItem:
    return EvaluatorWorkItem(
        run_context=_run_context(),
        retiring_model_id="gpt-4.1",
        retiring_model_version="2025-04-14",
        candidate_model_id=candidate_model_id,
        candidate_version="2025-04-14",
        candidate_slug=f"{candidate_model_id.replace('.', '-')}-2025-04-14",
        deployment_ref=DeploymentRef(
            resource_id="/subscriptions/sub/deployments/candidate",
            deployment_name="candidate-deployment",
            region="swedencentral",
            deployment_type="DataZoneStandard",
        ),
        skip_index_key=SkipIndexKey(
            model_id="gpt-4.1",
            version="2025-04-14",
            dataset_sha256="abc",
            candidate_model_id=candidate_model_id,
            candidate_version="2025-04-14",
        ),
        teardown_plan=TeardownPlan(
            idempotency_key="key",
            deployment_name="candidate-deployment",
            resource_group="rg",
            region="swedencentral",
            reason="evaluation-complete",
        ),
        manifest_paths={},
        recommendation_rationale=[],
        candidate_score=0.8,
        evaluation_config=EvaluatorConfig(
            allowed_regions=["swedencentral"],
            deployment_type_preferences=["DataZoneStandard"],
            thresholds=EvaluatorThresholds(minimum_custom_score=0.75, minimum_redteam_block_rate=0.95),
            timeouts=EvaluatorTimeouts(orchestration_minutes=20, cleanup_minutes=20),
        ),
        dataset_path=Path("tests/fixtures/evaluator/dataset.sample.jsonl"),
        dataset_sha256="abc",
    )


def _dataset() -> EvaluationDataset:
    return EvaluationDataset(
        path=Path("tests/fixtures/evaluator/dataset.sample.jsonl"),
        dataset_sha256="abc",
        records=[],
    )


class AssertIndependentJudgeTests(unittest.TestCase):
    def test_given_unset_judge_when_asserting_then_raises(self) -> None:
        with self.assertRaises(ConfigurationError):
            assert_independent_judge("", "gpt-4.1-mini")

    def test_given_judge_equals_candidate_when_asserting_then_raises(self) -> None:
        with self.assertRaises(ConfigurationError):
            assert_independent_judge("gpt-4.1-mini", "gpt-4.1-mini")

    def test_given_same_family_when_asserting_then_raises(self) -> None:
        with self.assertRaises(ConfigurationError):
            assert_independent_judge("gpt-4.1", "gpt-4.1-mini")

    def test_given_independent_family_when_asserting_then_no_error(self) -> None:
        assert_independent_judge("o3-mini", "gpt-4.1-mini")


class ModelGenerationMappingTests(unittest.TestCase):
    """LIVE-BUG-01(a): generation is defined by MODEL GENERATION, not the
    first-hyphen token, so gpt-4.1 and gpt-5.1 are DIFFERENT generations."""

    def test_generation_mapping_table(self) -> None:
        cases = {
            "gpt-4.1": "gpt-4",
            "gpt-4.1-mini": "gpt-4",
            "gpt-4o": "gpt-4",
            "gpt_4_1": "gpt-4",
            "gpt-5.1": "gpt-5",
            "gpt-5.6-sol": "gpt-5",
            "o3": "o3",
            "o3-mini": "o3",
            "o4-mini": "o4",
            "o1": "o1",
        }
        for model_id, expected in cases.items():
            with self.subTest(model_id=model_id):
                self.assertEqual(_model_generation(model_id), expected)

    def test_given_owned_deployment_name_embeds_retiring_prefix_then_first_match_wins(
        self,
    ) -> None:
        # Real owned deployment names embed the RETIRING model's generation as a
        # prefix (e.g. ``tg4-gpt-5-6-sol-...``). First-match-wins therefore
        # resolves BOTH the gpt-5.1 and the o3 candidate deployment names to
        # "gpt-5". This ambiguity is precisely why the independence gate is fed
        # the candidate MODEL ID (o3 / gpt-5.1), never the deployment name.
        self.assertEqual(_model_generation("tg4-gpt-5-6-sol-gpt-5-1-2025-11-13"), "gpt-5")
        self.assertEqual(_model_generation("tg4-gpt-5-6-sol-o3-2025-04-16"), "gpt-5")

    def test_given_o_series_deployment_name_when_resolving_then_lookbehind_holds(
        self,
    ) -> None:
        # A clean o-series judge deployment resolves to its o-series generation,
        # and date fragments (``2025-04-16``) do not spoof the o4/o3 lookbehind
        # because a digit, not a letter, precedes the ``4``/``3``.
        self.assertEqual(_model_generation("eph-judge-o4-mini-2025-04-16"), "o4")
        self.assertIsNone(_model_generation("run-2025-04-16"))

    def test_given_unknown_token_when_resolving_then_none(self) -> None:
        self.assertIsNone(_model_generation("claude-3"))


class GenerationIndependenceTests(unittest.TestCase):
    """LIVE-BUG-01(a): gpt-4.1 is an independent judge for both candidates."""

    def test_given_gpt41_judge_and_gpt51_candidate_when_asserting_then_accepts(self) -> None:
        assert_independent_judge("gpt-4.1", "gpt-5.1")

    def test_given_gpt41_judge_and_o3_candidate_when_asserting_then_accepts(self) -> None:
        assert_independent_judge("gpt-4.1", "o3")

    def test_given_same_generation_gpt5_when_asserting_then_rejects(self) -> None:
        with self.assertRaises(ConfigurationError):
            assert_independent_judge("gpt-5.6-sol", "gpt-5.1")

    def test_given_same_generation_o3_when_asserting_then_rejects(self) -> None:
        with self.assertRaises(ConfigurationError):
            assert_independent_judge("o3-mini", "o3")

    def test_given_exact_same_model_when_asserting_then_rejects(self) -> None:
        with self.assertRaises(ConfigurationError):
            assert_independent_judge("gpt-5.1", "gpt-5.1")


class LiveCustomRunnerGuardTests(unittest.TestCase):
    def test_given_missing_judge_model_when_running_then_raises_before_client_construction(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            runner = LiveCustomRunner()
            with self.assertRaises(ConfigurationError):
                runner.run(_work_item(), _dataset())

    def test_given_self_grading_judge_when_running_then_raises(self) -> None:
        with mock.patch.dict(
            os.environ, {"JUDGE_MODEL": "gpt-4.1-mini"}, clear=True
        ):
            runner = LiveCustomRunner()
            with self.assertRaises(ConfigurationError):
                runner.run(_work_item("gpt-4.1-mini"), _dataset())

    def test_given_independent_judge_but_missing_endpoint_when_running_then_raises(self) -> None:
        with mock.patch.dict(os.environ, {"JUDGE_MODEL": "o3-mini"}, clear=True):
            runner = LiveCustomRunner()
            with self.assertRaises(ConfigurationError):
                runner.run(_work_item(), _dataset())


class ImportModuleTests(unittest.TestCase):
    def test_given_no_extra_when_importing_module_then_succeeds(self) -> None:
        module = importlib.import_module("src.evaluator.custom_runner")
        self.assertTrue(hasattr(module, "LiveCustomRunner"))


class LiveCustomRunnerStubClientTests(unittest.TestCase):
    """Assert LiveCustomRunner delegates to the seam (no forked scoring).

    A Stub client (shaped like ``quality_safety_eval_client.StubQualitySafetyEvalClient``)
    is injected in place of ``FoundryQualitySafetyEvalClient`` so the mapping
    from :class:`RawEvalSignals` to :class:`CustomEvaluationResult` is
    exercised without constructing a real Foundry client (which itself
    import-guards the ``[evaluation]`` extra at construction time).
    """

    def _run_with_stub(self, stub_signals: RawEvalSignals):
        fake_client = mock.Mock()
        fake_client.evaluate_model.return_value = stub_signals
        with mock.patch.dict(
            os.environ,
            {
                "JUDGE_MODEL": "o3-mini",
                "FOUNDRY_PROJECT_ENDPOINT": "https://acct.services.ai.azure.com/api/projects/p",
            },
            clear=True,
        ), mock.patch(
            "src.evaluator.custom_runner.FoundryQualitySafetyEvalClient",
            return_value=fake_client,
        ) as client_ctor:
            runner = LiveCustomRunner()
            result = runner.run(_work_item(), _dataset())
        return result, fake_client, client_ctor

    def test_given_scored_signals_when_running_then_maps_to_derived_quality_score(self) -> None:
        # Arrange
        stub_signals = RawEvalSignals(groundedness=4.0, coherence=4.0, relevance=4.0, fluency=4.0)

        # Act
        result, fake_client, client_ctor = self._run_with_stub(stub_signals)

        # Assert: delegates to the injected client (no forked scoring logic).
        client_ctor.assert_called_once()
        fake_client.evaluate_model.assert_called_once_with("gpt-4.1-mini")
        self.assertEqual(result.aggregates["overall"], derive_quality_score(stub_signals))
        self.assertEqual(result.dataset_sha256, "abc")
        self.assertEqual(result.candidate_slug, _work_item().candidate_slug)

    def test_given_all_unscored_signals_when_running_then_overall_is_none_not_fabricated(
        self,
    ) -> None:
        # Arrange
        stub_signals = RawEvalSignals(groundedness=None, coherence=None, relevance=None, fluency=None)

        # Act
        result, _, _ = self._run_with_stub(stub_signals)

        # Assert
        self.assertIsNone(result.aggregates["overall"])


if __name__ == "__main__":
    unittest.main()
