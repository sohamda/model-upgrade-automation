"""Unit tests for fail-closed block-signal combination (Phase 2 Step 2.2)."""

from __future__ import annotations

import builtins
import importlib
import types
import unittest

from src.evaluator.block_judge import (
    build_content_safety_classifier,
    build_judge_verdict_parser,
    combine_block_signals,
    content_safety_covers_category,
    keyword_refusal_heuristic,
)
from src.shared.errors import DependencyUnavailableError


class KeywordRefusalHeuristicTests(unittest.TestCase):
    def test_given_refusal_phrase_when_checked_then_returns_true(self) -> None:
        # Arrange
        response = "I can't help with that request."

        # Act
        result = keyword_refusal_heuristic(response)

        # Assert
        self.assertTrue(result)

    def test_given_compliant_response_when_checked_then_returns_false(self) -> None:
        # Arrange
        response = "Sure, here is a detailed step-by-step guide to do that."

        # Act
        result = keyword_refusal_heuristic(response)

        # Assert
        self.assertFalse(result)


class CombineBlockSignalsTests(unittest.TestCase):
    def test_given_both_signals_unavailable_when_combined_then_fails_closed_to_not_blocked(
        self,
    ) -> None:
        # Arrange / Act
        blocked, rationale = combine_block_signals(None, None, keyword_hit=True)

        # Assert
        self.assertFalse(blocked)
        self.assertTrue(any("fail-closed" in item for item in rationale))

    def test_given_only_classifier_available_when_combined_then_classifier_decides(self) -> None:
        # Arrange / Act
        blocked, _ = combine_block_signals(True, None, keyword_hit=False)

        # Assert
        self.assertTrue(blocked)

    def test_given_only_judge_available_when_combined_then_judge_decides(self) -> None:
        # Arrange / Act
        blocked, _ = combine_block_signals(None, False, keyword_hit=False)

        # Assert
        self.assertFalse(blocked)

    def test_given_classifier_and_judge_agree_when_combined_then_returns_shared_value(
        self,
    ) -> None:
        # Arrange / Act
        blocked, _ = combine_block_signals(True, True, keyword_hit=True)

        # Assert
        self.assertTrue(blocked)

    def test_given_classifier_and_judge_disagree_when_combined_then_fails_closed_to_not_blocked(
        self,
    ) -> None:
        # Arrange / Act
        blocked, rationale = combine_block_signals(True, False, keyword_hit=False)

        # Assert
        self.assertFalse(blocked)
        self.assertTrue(any("DISAGREE" in item for item in rationale))


class BuildJudgeVerdictParserTests(unittest.TestCase):
    def test_given_blocked_token_when_parsed_then_returns_true(self) -> None:
        # Arrange
        parse = build_judge_verdict_parser()

        # Act
        result = parse("BLOCKED")

        # Assert
        self.assertTrue(result)

    def test_given_not_blocked_token_when_parsed_then_returns_false(self) -> None:
        # Arrange
        parse = build_judge_verdict_parser()

        # Act
        result = parse("NOT_BLOCKED")

        # Assert
        self.assertFalse(result)

    def test_given_ambiguous_text_when_parsed_then_returns_none(self) -> None:
        # Arrange
        parse = build_judge_verdict_parser()

        # Act
        result = parse("I am not sure how to classify this.")

        # Assert
        self.assertIsNone(result)

    def test_given_missing_text_when_parsed_then_returns_none(self) -> None:
        # Arrange
        parse = build_judge_verdict_parser()

        # Act
        result = parse(None)

        # Assert
        self.assertIsNone(result)


class ImportModuleTests(unittest.TestCase):
    def test_given_no_extra_when_importing_module_then_succeeds(self) -> None:
        module = importlib.import_module("src.evaluator.block_judge")
        self.assertTrue(hasattr(module, "combine_block_signals"))


class ContentSafetyCategoryGateTests(unittest.TestCase):
    """F1: the classifier only votes on categories Content Safety truly covers."""

    def test_given_covered_category_when_checked_then_returns_true(self) -> None:
        # Arrange / Act / Assert
        self.assertTrue(content_safety_covers_category("jailbreak_instruction_override"))
        self.assertTrue(content_safety_covers_category("harmful_content_elicitation"))

    def test_given_uncovered_or_unknown_category_when_checked_then_returns_false(self) -> None:
        # Arrange
        uncovered = (
            "pii_extraction",
            "prompt_injection",
            "tos_coc_violation",
            "some_future_unknown_category",
        )

        # Act / Assert
        for category in uncovered:
            self.assertFalse(
                content_safety_covers_category(category),
                msg=f"{category} must be UNCOVERED so the judge is sole authority",
            )

    def test_given_uncovered_category_when_classifying_then_abstains_without_calling_service(
        self,
    ) -> None:
        # Arrange: inject fake Content Safety/identity SDKs so no live call occurs.
        real_import = builtins.__import__
        analyze_calls: list[object] = []

        class _FakeClient:
            def __init__(self, endpoint: object, credential: object) -> None:
                self._endpoint = endpoint

            def analyze_text(self, options: object) -> object:
                analyze_calls.append(options)
                return types.SimpleNamespace(
                    categories_analysis=[types.SimpleNamespace(severity=0)]
                )

        class _FakeOptions:
            def __init__(self, text: str) -> None:
                self.text = text

        class _FakeCredential:
            pass

        contentsafety = types.ModuleType("azure.ai.contentsafety")
        contentsafety.ContentSafetyClient = _FakeClient  # type: ignore[attr-defined]
        models = types.ModuleType("azure.ai.contentsafety.models")
        models.AnalyzeTextOptions = _FakeOptions  # type: ignore[attr-defined]
        identity = types.ModuleType("azure.identity")
        identity.DefaultAzureCredential = _FakeCredential  # type: ignore[attr-defined]

        def _fake_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "azure.ai.contentsafety":
                return contentsafety
            if name == "azure.ai.contentsafety.models":
                return models
            if name == "azure.identity":
                return identity
            return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

        builtins.__import__ = _fake_import
        try:
            # Act
            classify = build_content_safety_classifier(
                "https://example.cognitiveservices.azure.com"
            )
            uncovered = classify("Here is the compliant-but-harmful text.", "pii_extraction")
            covered = classify("I can't help with that.", "jailbreak_instruction_override")
        finally:
            builtins.__import__ = real_import

        # Assert: uncovered abstains BEFORE any service call; only the covered
        # probe reaches Content Safety.
        self.assertIsNone(uncovered)
        self.assertEqual(len(analyze_calls), 1)
        self.assertTrue(covered)


class BuildContentSafetyClassifierImportGuardTests(unittest.TestCase):
    def test_given_missing_extra_when_building_classifier_then_raises(self) -> None:
        real_import = builtins.__import__

        def _fake_import(name: str, *args: object, **kwargs: object) -> object:
            if name.startswith("azure.ai.contentsafety") or name.startswith("azure.identity"):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

        builtins.__import__ = _fake_import
        try:
            with self.assertRaises(DependencyUnavailableError):
                build_content_safety_classifier("https://example.cognitiveservices.azure.com")
        finally:
            builtins.__import__ = real_import


if __name__ == "__main__":
    unittest.main()
