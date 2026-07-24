"""Unit tests for the live Azure OpenAI candidate response provider."""

from __future__ import annotations

import builtins
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from src.evaluator.aoai_client import (
    DEFAULT_API_SHAPE,
    AoaiClient,
    _build_completion_kwargs,
    _build_messages,
    _is_reasoning_shape,
    load_default_judge,
    load_deployment_map,
    load_model_api_shapes,
    resolve_api_shape,
)
from src.shared.errors import DependencyUnavailableError


def _write_models_yaml(repo_root: Path, payload: dict[str, object]) -> None:
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "models.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")


class LoadModelApiShapesTests(unittest.TestCase):
    def test_given_configured_shapes_when_loading_then_returns_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _write_models_yaml(
                repo_root,
                {"model_api_shapes": {"default": {"use_system_role": True}}},
            )
            shapes = load_model_api_shapes(repo_root)
            self.assertEqual(shapes, {"default": {"use_system_role": True}})

    def test_given_missing_file_when_loading_then_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_model_api_shapes(Path(tmp)), {})

    def test_given_no_shapes_key_when_loading_then_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _write_models_yaml(repo_root, {"watch_list": []})
            self.assertEqual(load_model_api_shapes(repo_root), {})


class LoadDeploymentMapTests(unittest.TestCase):
    def test_given_configured_deployments_when_loading_then_returns_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _write_models_yaml(repo_root, {"deployments": {"gpt-4.1": "prod-gpt41"}})
            self.assertEqual(load_deployment_map(repo_root), {"gpt-4.1": "prod-gpt41"})

    def test_given_empty_values_when_loading_then_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _write_models_yaml(repo_root, {"deployments": {"gpt-4.1": ""}})
            self.assertEqual(load_deployment_map(repo_root), {})

    def test_given_missing_file_when_loading_then_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_deployment_map(Path(tmp)), {})


class ResolveApiShapeTests(unittest.TestCase):
    def test_given_exact_match_when_resolving_then_returns_exact(self) -> None:
        shapes = {"gpt-5.1": {"seed": 1}, "default": {"seed": 0}}
        self.assertEqual(resolve_api_shape("gpt-5.1", shapes), {"seed": 1})

    def test_given_family_prefix_when_resolving_then_returns_family_shape(self) -> None:
        shapes = {"o3": {"use_system_role": False}, "default": {"use_system_role": True}}
        self.assertEqual(resolve_api_shape("o3-mini", shapes), {"use_system_role": False})

    def test_given_no_match_when_resolving_then_returns_default(self) -> None:
        shapes = {"o3": {"use_system_role": False}, "default": {"use_system_role": True}}
        self.assertEqual(resolve_api_shape("gpt-4.1", shapes), {"use_system_role": True})

    def test_given_no_shapes_configured_when_resolving_then_returns_module_default(self) -> None:
        self.assertEqual(resolve_api_shape("gpt-4.1", None), DEFAULT_API_SHAPE)
        self.assertEqual(resolve_api_shape("gpt-4.1", {}), DEFAULT_API_SHAPE)


class ResolveDeploymentTests(unittest.TestCase):
    def test_given_explicit_deployment_ref_when_resolving_then_wins(self) -> None:
        client = AoaiClient(
            azure_ai_project="https://acct.services.ai.azure.com/api/projects/p",
            model_id_deployment_map={"gpt-4.1": "config-mapped"},
        )
        self.assertEqual(client._resolve_deployment("gpt-4.1", "explicit-ref"), "explicit-ref")

    def test_given_config_map_when_no_explicit_ref_then_uses_map(self) -> None:
        client = AoaiClient(
            azure_ai_project="https://acct.services.ai.azure.com/api/projects/p",
            model_id_deployment_map={"gpt-4.1": "config-mapped"},
        )
        self.assertEqual(client._resolve_deployment("gpt-4.1", None), "config-mapped")

    def test_given_no_map_or_ref_when_resolving_then_falls_back_to_model_id(self) -> None:
        client = AoaiClient(azure_ai_project="https://acct.services.ai.azure.com/api/projects/p")
        self.assertEqual(client._resolve_deployment("gpt-4.1", None), "gpt-4.1")

    def test_given_no_model_id_or_ref_when_resolving_then_returns_none(self) -> None:
        client = AoaiClient(azure_ai_project="https://acct.services.ai.azure.com/api/projects/p")
        self.assertIsNone(client._resolve_deployment("", None))


class ChatCompletionImportGuardTests(unittest.TestCase):
    def test_given_missing_extra_when_calling_then_raises(self) -> None:
        real_import = builtins.__import__

        def _fake_import(name: str, *args: object, **kwargs: object) -> object:
            if name.startswith("openai") or name.startswith("azure.identity"):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

        client = AoaiClient(azure_ai_project="https://acct.services.ai.azure.com/api/projects/p")
        builtins.__import__ = _fake_import
        try:
            with self.assertRaises(DependencyUnavailableError):
                client.chat_completion("gpt-4.1", "hello")
        finally:
            builtins.__import__ = real_import

    def test_given_unresolvable_deployment_when_calling_then_returns_none(self) -> None:
        client = AoaiClient(azure_ai_project="https://acct.services.ai.azure.com/api/projects/p")
        self.assertIsNone(client.chat_completion("", "hello"))


class ImportWithoutExtraTests(unittest.TestCase):
    def test_given_no_extra_when_importing_module_then_succeeds(self) -> None:
        module = importlib.import_module("src.evaluator.aoai_client")
        self.assertTrue(hasattr(module, "AoaiClient"))


class LoadDefaultJudgeTests(unittest.TestCase):
    def test_given_configured_default_judge_when_loading_then_returns_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _write_models_yaml(
                repo_root,
                {"default_judge": {"model_id": "gpt-4.1", "version": "2025-04-14"}},
            )
            self.assertEqual(
                load_default_judge(repo_root),
                {"model_id": "gpt-4.1", "version": "2025-04-14"},
            )

    def test_given_missing_block_when_loading_then_returns_empty_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _write_models_yaml(repo_root, {"watch_list": []})
            self.assertEqual(load_default_judge(repo_root), {"model_id": "", "version": ""})

    def test_given_repo_config_when_loading_then_returns_pinned_gpt41(self) -> None:
        # The committed config must pin gpt-4.1 as the cross-generation-
        # independent default judge (LIVE-BUG-01c), with its version recorded
        # as provenance.
        repo_root = Path(__file__).resolve().parents[2]
        judge = load_default_judge(repo_root)
        self.assertEqual(judge["model_id"], "gpt-4.1")
        self.assertEqual(judge["version"], "2025-04-14")


class ReasoningShapeTests(unittest.TestCase):
    """LIVE-BUG-01(b): the ``is_reasoning_model`` flag reshapes the request."""

    def test_given_reasoning_flag_when_checking_then_true(self) -> None:
        self.assertTrue(_is_reasoning_shape({"is_reasoning_model": True}))

    def test_given_flag_absent_when_checking_then_false(self) -> None:
        self.assertFalse(_is_reasoning_shape({"max_tokens_param": "max_tokens"}))

    def test_given_reasoning_shape_when_building_kwargs_then_uses_max_completion_tokens(
        self,
    ) -> None:
        shape = {
            "is_reasoning_model": True,
            "temperature": 0,
            "seed": 42,
            "max_tokens_param": "max_tokens",
            "max_tokens": 256,
        }
        kwargs = _build_completion_kwargs(shape)
        # max_completion_tokens is forced; the stale max_tokens_param is ignored.
        self.assertIn("max_completion_tokens", kwargs)
        self.assertEqual(kwargs["max_completion_tokens"], 256)
        self.assertNotIn("max_tokens", kwargs)
        # temperature/seed are dropped even though present in the shape.
        self.assertNotIn("temperature", kwargs)
        self.assertNotIn("seed", kwargs)

    def test_given_reasoning_shape_when_building_messages_then_omits_system_role(
        self,
    ) -> None:
        messages = _build_messages({"is_reasoning_model": True, "use_system_role": True}, "hi")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertNotIn("system", [message["role"] for message in messages])

    def test_given_standard_shape_when_building_kwargs_then_honors_configured_param(
        self,
    ) -> None:
        shape = {
            "temperature": 0,
            "seed": 42,
            "max_tokens_param": "max_tokens",
            "max_tokens": 128,
        }
        kwargs = _build_completion_kwargs(shape)
        self.assertEqual(kwargs["max_tokens"], 128)
        self.assertNotIn("max_completion_tokens", kwargs)
        self.assertEqual(kwargs["temperature"], 0)
        self.assertEqual(kwargs["seed"], 42)

    def test_given_o3_repo_shape_when_building_kwargs_then_reasoning_shaped(self) -> None:
        # The committed o3 shape must be reasoning-flagged so a live o3 call
        # sends max_completion_tokens (LIVE-BUG-01b) rather than 400ing.
        repo_root = Path(__file__).resolve().parents[2]
        shapes = load_model_api_shapes(repo_root)
        o3_shape = resolve_api_shape("o3", shapes)
        self.assertTrue(_is_reasoning_shape(o3_shape))
        kwargs = _build_completion_kwargs(o3_shape)
        self.assertIn("max_completion_tokens", kwargs)
        self.assertNotIn("max_tokens", kwargs)
        self.assertNotIn("temperature", kwargs)


class WithRetryTests(unittest.TestCase):
    def _client(self) -> AoaiClient:
        return AoaiClient(azure_ai_project="https://acct.services.ai.azure.com/api/projects/p")

    def test_given_immediate_success_when_retrying_then_returns_value(self) -> None:
        client = self._client()
        self.assertEqual(client._with_retry(lambda: "ok"), "ok")

    def test_given_retryable_error_then_success_when_retrying_then_recovers(self) -> None:
        client = self._client()
        error = Exception("boom")
        error.status_code = 503  # type: ignore[attr-defined]
        calls = {"count": 0}

        def _call() -> str | None:
            calls["count"] += 1
            if calls["count"] == 1:
                raise error
            return "recovered"

        with mock.patch("src.evaluator.aoai_client.time.sleep") as sleep_mock:
            result = client._with_retry(_call)
        self.assertEqual(result, "recovered")
        sleep_mock.assert_called_once()

    def test_given_non_retryable_error_when_retrying_then_returns_none_immediately(self) -> None:
        client = self._client()
        calls = {"count": 0}

        def _call() -> str | None:
            calls["count"] += 1
            raise Exception("permanent failure")

        result = client._with_retry(_call)
        self.assertIsNone(result)
        self.assertEqual(calls["count"], 1)

    def test_given_exhausted_retries_when_retrying_then_returns_none(self) -> None:
        client = self._client()
        error = Exception("boom")
        error.status_code = 429  # type: ignore[attr-defined]

        def _call() -> str | None:
            raise error

        with mock.patch("src.evaluator.aoai_client.time.sleep"):
            result = client._with_retry(_call)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
