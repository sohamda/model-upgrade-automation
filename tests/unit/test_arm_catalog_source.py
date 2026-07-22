"""Unit tests for the ARM Models catalog source."""

from __future__ import annotations

import json
import subprocess
import unittest
from unittest.mock import patch

from src.recommender.arm_catalog_source import ArmModelsCatalogSource
from src.shared.errors import DependencyUnavailableError


def _completed(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["az"], returncode=0, stdout=stdout, stderr="")


class ArmModelsCatalogSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        # Route az resolution through a fake path so run_az stays hermetic
        # regardless of whether az is installed on the test host.
        patcher = patch("shutil.which", return_value="/usr/bin/az")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_given_mixed_lifecycle_when_loading_then_only_available_are_candidates(self) -> None:
        # Arrange: a GA chat model plus a Deprecating chat model. The lifecycle
        # gate must exclude the Deprecating model even though it is chat-capable.
        payload = {
            "value": [
                {
                    "model": {
                        "name": "gpt-4.1",
                        "version": "2026-01-12",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {"chatCompletion": "true"},
                        "skus": [
                            {"name": "Standard"},
                            {"name": "GlobalStandard"},
                        ],
                    }
                },
                {
                    "model": {
                        "name": "gpt-4o",
                        "version": "2024-05-13",
                        "lifecycleStatus": "Deprecating",
                        "capabilities": {"chatCompletion": "true"},
                        "skus": [{"name": "Standard"}],
                    }
                },
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            result = source.load()

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model_id, "gpt-4.1")
        self.assertEqual(result[0].region, "eastus")
        self.assertEqual(result[0].deployment_types, ["Standard", "GlobalStandard"])
        self.assertEqual(result[0].replacement_families, [])

    def test_given_ga_chat_model_when_loading_then_candidate_has_empty_families(self) -> None:
        # Arrange
        payload = {
            "value": [
                {
                    "model": {
                        "name": "gpt-4o",
                        "version": "2024-11-20",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {"chatCompletion": "true"},
                        "skus": [{"name": "GlobalStandard"}],
                    }
                }
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            result = source.load()

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model_id, "gpt-4o")
        self.assertEqual(result[0].replacement_families, [])
        self.assertEqual(result[0].workloads, ["general_qa"])

    def test_given_ga_embeddings_model_when_loading_then_skipped(self) -> None:
        # Arrange: embeddings models expose an ``embeddings`` capability and no
        # ``chatCompletion`` flag, so the chat gate must skip them.
        payload = {
            "value": [
                {
                    "model": {
                        "name": "text-embedding-3-large",
                        "version": "1",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {"embeddings": "true"},
                        "skus": [{"name": "Standard"}],
                    }
                }
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act / Assert: no chat candidates remain.
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            with self.assertRaises(DependencyUnavailableError):
                source.load()

    def test_given_ga_audio_model_when_loading_then_skipped(self) -> None:
        # Arrange: whisper/audio models expose an ``audio`` capability only.
        payload = {
            "value": [
                {
                    "model": {
                        "name": "whisper",
                        "version": "001",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {"audio": "true"},
                        "skus": [{"name": "Standard"}],
                    }
                }
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act / Assert
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            with self.assertRaises(DependencyUnavailableError):
                source.load()

    def test_given_deprecating_chat_model_when_loading_then_skipped(self) -> None:
        # Arrange: chat-capable but Deprecating; the lifecycle gate excludes it.
        payload = {
            "value": [
                {
                    "model": {
                        "name": "gpt-4o",
                        "version": "2024-05-13",
                        "lifecycleStatus": "Deprecating",
                        "capabilities": {"chatCompletion": "true"},
                        "skus": [{"name": "Standard"}],
                    }
                }
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act / Assert
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            with self.assertRaises(DependencyUnavailableError):
                source.load()

    def test_given_no_available_models_when_loading_then_dependency_error(self) -> None:
        # Arrange
        payload = {
            "value": [
                {
                    "model": {
                        "name": "gpt-4o",
                        "version": "2024-05-13",
                        "lifecycleStatus": "Deprecated",
                        "capabilities": {"chatCompletion": "true"},
                        "skus": [{"name": "Standard"}],
                    }
                }
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act / Assert
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            with self.assertRaises(DependencyUnavailableError):
                source.load()

    def test_given_missing_cli_when_loading_then_dependency_error(self) -> None:
        # Arrange
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act / Assert
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            with self.assertRaises(DependencyUnavailableError):
                source.load()

    def test_given_non_openai_chat_model_when_loading_then_candidate_kept(self) -> None:
        # Arrange: a non-OpenAI GA chat model with a chat-like name must pass
        # all three gate layers and surface as a candidate.
        payload = {
            "value": [
                {
                    "model": {
                        "name": "Codestral-2501",
                        "version": "2501",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {"chatCompletion": "true"},
                        "skus": [{"name": "GlobalStandard"}],
                    }
                }
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            result = source.load()

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model_id, "Codestral-2501")

    def test_given_reranker_claiming_chat_when_loading_then_skipped_by_name(self) -> None:
        # Arrange: rerankers falsely report ``chatCompletion == "true"``; the
        # Layer 3 name denylist must exclude them despite the chat flag.
        payload = {
            "value": [
                {
                    "model": {
                        "name": "Cohere-rerank-v4.0-fast",
                        "version": "4.0",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {"chatCompletion": "true"},
                        "skus": [{"name": "GlobalStandard"}],
                    }
                }
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act / Assert
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            with self.assertRaises(DependencyUnavailableError):
                source.load()

    def test_given_embeddings_capability_and_chat_flag_when_loading_then_skipped(self) -> None:
        # Arrange: a chat-flagged model that also advertises an ``embeddings``
        # capability key. Layer 2 excludes it on the non-chat capability key.
        payload = {
            "value": [
                {
                    "model": {
                        "name": "text-encoder-x",
                        "version": "1",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {
                            "chatCompletion": "true",
                            "embeddings": "true",
                        },
                        "skus": [{"name": "Standard"}],
                    }
                }
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act / Assert
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            with self.assertRaises(DependencyUnavailableError):
                source.load()

    def test_given_image_generation_capability_and_chat_flag_when_loading_then_skipped(self) -> None:
        # Arrange: chat-flagged model advertising an ``imageGenerations``
        # capability key; Layer 2 must exclude it.
        payload = {
            "value": [
                {
                    "model": {
                        "name": "media-gen-x",
                        "version": "1",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {
                            "chatCompletion": "true",
                            "imageGenerations": "true",
                        },
                        "skus": [{"name": "Standard"}],
                    }
                }
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act / Assert
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            with self.assertRaises(DependencyUnavailableError):
                source.load()

    def test_given_merged_rows_with_non_chat_capability_when_loading_then_skipped(self) -> None:
        # Arrange: two GA rows for the same model. One claims chat, the other
        # advertises embeddings. The union of capabilities carries a non-chat
        # key, so the merged group is excluded by Layer 2.
        payload = {
            "value": [
                {
                    "model": {
                        "name": "hybrid-model",
                        "version": "1",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {"chatCompletion": "true"},
                        "skus": [{"name": "Standard"}],
                    }
                },
                {
                    "model": {
                        "name": "hybrid-model",
                        "version": "1",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {"embeddings": "true"},
                        "skus": [{"name": "GlobalStandard"}],
                    }
                },
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act / Assert
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            with self.assertRaises(DependencyUnavailableError):
                source.load()

    def test_given_merged_rows_where_only_one_flags_chat_when_loading_then_kept(self) -> None:
        # Arrange: duplicate ARM rows per model with divergent capability sets.
        # Only one row carries the ``chatCompletion`` flag, but the merged
        # union must still admit the model and combine its sku names.
        payload = {
            "value": [
                {
                    "model": {
                        "name": "gpt-4.1",
                        "version": "2026-01-12",
                        "lifecycleStatus": "GenerallyAvailable",
                        "kind": "OpenAI",
                        "capabilities": {"chatCompletion": "true"},
                        "skus": [{"name": "Standard"}],
                    }
                },
                {
                    "model": {
                        "name": "gpt-4.1",
                        "version": "2026-01-12",
                        "lifecycleStatus": "GenerallyAvailable",
                        "kind": "AIServices",
                        "capabilities": {"completion": "true"},
                        "skus": [{"name": "GlobalStandard"}],
                    }
                },
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            result = source.load()

        # Assert: single deduped candidate with unioned deployment types.
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model_id, "gpt-4.1")
        self.assertEqual(result[0].deployment_types, ["Standard", "GlobalStandard"])

    def test_given_conflicting_chat_flag_values_when_loading_then_truthy_wins(self) -> None:
        # Arrange: one row reports ``chatCompletion == "false"`` and another
        # reports ``"true"`` for the same model. The truthy flag must win the
        # merge so the model is admitted.
        payload = {
            "value": [
                {
                    "model": {
                        "name": "phi-4",
                        "version": "1",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {"chatCompletion": "false"},
                        "skus": [{"name": "Standard"}],
                    }
                },
                {
                    "model": {
                        "name": "phi-4",
                        "version": "1",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {"chatCompletion": "true"},
                        "skus": [{"name": "GlobalStandard"}],
                    }
                },
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            result = source.load()

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model_id, "phi-4")

    def test_given_non_ga_row_when_merging_then_capabilities_ignored(self) -> None:
        # Arrange: the only chat-flagged row is Deprecating. It must be dropped
        # before merging, leaving the GA embeddings row alone, so nothing
        # survives the gate.
        payload = {
            "value": [
                {
                    "model": {
                        "name": "legacy-model",
                        "version": "1",
                        "lifecycleStatus": "Deprecating",
                        "capabilities": {"chatCompletion": "true"},
                        "skus": [{"name": "Standard"}],
                    }
                },
                {
                    "model": {
                        "name": "legacy-model",
                        "version": "1",
                        "lifecycleStatus": "GenerallyAvailable",
                        "capabilities": {"embeddings": "true"},
                        "skus": [{"name": "GlobalStandard"}],
                    }
                },
            ]
        }
        source = ArmModelsCatalogSource(subscription_id="sub", locations=["eastus"])

        # Act / Assert
        with patch("subprocess.run", return_value=_completed(json.dumps(payload))):
            with self.assertRaises(DependencyUnavailableError):
                source.load()


if __name__ == "__main__":
    unittest.main()
