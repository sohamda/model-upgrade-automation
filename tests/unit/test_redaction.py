"""Unit tests for logging/result redaction (Phase 1 Step 1.8, Council C6/C7/C9)."""

from __future__ import annotations

import importlib
import unittest

from src.shared.redaction import redact_mapping, redact_text


class RedactTextTests(unittest.TestCase):
    def test_given_bearer_token_when_redacted_then_masked(self) -> None:
        # Arrange
        value = "Authorization: Bearer abc123.def456-ghi"

        # Act
        result = redact_text(value)

        # Assert
        self.assertNotIn("abc123.def456-ghi", result)
        self.assertIn("Bearer [REDACTED]", result)

    def test_given_endpoint_url_when_redacted_then_masked(self) -> None:
        # Arrange
        value = "calling https://my-account.services.ai.azure.com/api/projects/p"

        # Act
        result = redact_text(value)

        # Assert
        self.assertNotIn("my-account.services.ai.azure.com", result)
        self.assertIn("[REDACTED-ENDPOINT]", result)

    def test_given_api_key_value_pair_when_redacted_then_masked(self) -> None:
        # Arrange
        value = "api-key=sk-super-secret-value"

        # Act
        result = redact_text(value)

        # Assert
        self.assertNotIn("sk-super-secret-value", result)
        self.assertIn("[REDACTED]", result)

    def test_given_plain_text_when_redacted_then_unchanged(self) -> None:
        # Arrange
        value = "deployment candidate-deployment completed successfully"

        # Act
        result = redact_text(value)

        # Assert
        self.assertEqual(result, value)


class RedactMappingTests(unittest.TestCase):
    def test_given_sensitive_key_when_redacted_then_value_dropped_outright(self) -> None:
        # Arrange
        payload = {"endpoint": "https://acct.services.ai.azure.com/api/projects/p"}

        # Act
        result = redact_mapping(payload)

        # Assert
        self.assertEqual(result["endpoint"], "[REDACTED]")

    def test_given_deployment_name_key_when_redacted_then_value_preserved(self) -> None:
        # Arrange
        payload = {"deployment_name": "candidate-deployment"}

        # Act
        result = redact_mapping(payload)

        # Assert
        self.assertEqual(result["deployment_name"], "candidate-deployment")

    def test_given_nested_structure_when_redacted_then_recurses(self) -> None:
        # Arrange
        payload = {
            "audit": {
                "credential": "should-be-dropped",
                "notes": ["Bearer abc.def", "plain text"],
            }
        }

        # Act
        result = redact_mapping(payload)

        # Assert
        self.assertEqual(result["audit"]["credential"], "[REDACTED]")
        self.assertEqual(result["audit"]["notes"][0], "Bearer [REDACTED]")
        self.assertEqual(result["audit"]["notes"][1], "plain text")

    def test_given_non_string_leaf_when_redacted_then_returned_unchanged(self) -> None:
        # Arrange
        payload = {"custom_overall": 0.82, "flag": True, "count": None}

        # Act
        result = redact_mapping(payload)

        # Assert
        self.assertEqual(result, payload)


class ImportModuleTests(unittest.TestCase):
    def test_given_no_extra_when_importing_module_then_succeeds(self) -> None:
        module = importlib.import_module("src.shared.redaction")
        self.assertTrue(hasattr(module, "redact_text"))


if __name__ == "__main__":
    unittest.main()
