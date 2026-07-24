"""Unit tests for the adversarial probe-set loader (Phase 2 Step 2.1)."""

from __future__ import annotations

import importlib
from pathlib import Path
import re
import unittest

from src.evaluator.probe_set_loader import PROBE_SET_VERSION, load_probe_set
from src.shared.errors import ContractError

REPO_ROOT = Path(__file__).resolve().parents[2]
PROBE_SET_PATH = REPO_ROOT / "datasets" / "adversarial_probes.jsonl"

_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ProbeSetLoaderTests(unittest.TestCase):
    def test_given_repo_probe_set_when_loaded_then_all_five_categories_present(self) -> None:
        # Arrange / Act
        probe_set = load_probe_set(PROBE_SET_PATH)

        # Assert
        categories = {record.category for record in probe_set.records}
        self.assertEqual(
            categories,
            {
                "jailbreak_instruction_override",
                "harmful_content_elicitation",
                "pii_extraction",
                "prompt_injection",
                "tos_coc_violation",
            },
        )

    def test_given_repo_probe_set_when_loaded_then_each_category_has_five_to_ten_probes(
        self,
    ) -> None:
        # Arrange / Act
        probe_set = load_probe_set(PROBE_SET_PATH)

        # Assert
        counts: dict[str, int] = {}
        for record in probe_set.records:
            counts[record.category] = counts.get(record.category, 0) + 1
        for category, count in counts.items():
            self.assertTrue(5 <= count <= 10, f"{category} has {count} probes")

    def test_given_repo_probe_set_when_loaded_then_sha256_is_stable_hex_digest(self) -> None:
        # Arrange / Act
        first = load_probe_set(PROBE_SET_PATH)
        second = load_probe_set(PROBE_SET_PATH)

        # Assert
        self.assertRegex(first.probe_set_sha256, _SHA256_HEX_PATTERN)
        self.assertEqual(first.probe_set_sha256, second.probe_set_sha256)

    def test_given_repo_probe_set_when_loaded_then_version_matches_module_constant(self) -> None:
        # Arrange / Act
        probe_set = load_probe_set(PROBE_SET_PATH)

        # Assert
        self.assertEqual(probe_set.probe_set_version, PROBE_SET_VERSION)

    def test_given_repo_probe_set_when_loaded_then_exactly_one_poison_canary_present(self) -> None:
        # Arrange / Act
        probe_set = load_probe_set(PROBE_SET_PATH)

        # Assert
        poison_rows = [record for record in probe_set.records if record.canary == "poison"]
        self.assertEqual(len(poison_rows), 1)
        self.assertTrue(poison_rows[0].expected_blocked)
        self.assertIsNotNone(poison_rows[0].known_response)

    def test_given_repo_probe_set_when_loaded_then_exactly_one_discrimination_canary_present(
        self,
    ) -> None:
        # Arrange / Act
        probe_set = load_probe_set(PROBE_SET_PATH)

        # Assert
        discrimination_rows = [
            record for record in probe_set.records if record.canary == "discrimination"
        ]
        self.assertEqual(len(discrimination_rows), 1)
        self.assertFalse(discrimination_rows[0].expected_blocked)
        self.assertIsNotNone(discrimination_rows[0].known_response)

    def test_given_missing_file_when_loaded_then_raises_contract_error(self) -> None:
        # Arrange
        missing_path = REPO_ROOT / "datasets" / "does_not_exist.jsonl"

        # Act / Assert
        with self.assertRaises(ContractError):
            load_probe_set(missing_path)


class ImportModuleTests(unittest.TestCase):
    def test_given_no_extra_when_importing_module_then_succeeds(self) -> None:
        module = importlib.import_module("src.evaluator.probe_set_loader")
        self.assertTrue(hasattr(module, "load_probe_set"))


if __name__ == "__main__":
    unittest.main()
