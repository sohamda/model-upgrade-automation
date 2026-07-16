"""Unit tests for evaluator dataset loading and hashing."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.evaluator.dataset_loader import load_jsonl_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]


class EvaluatorDatasetLoaderTests(unittest.TestCase):
    def test_given_dataset_fixture_when_loaded_then_rows_and_hash_are_deterministic(self) -> None:
        # Arrange
        dataset_path = REPO_ROOT / "tests" / "fixtures" / "evaluator" / "dataset.sample.jsonl"

        # Act
        dataset = load_jsonl_dataset(dataset_path)

        # Assert
        self.assertEqual(len(dataset.records), 2)
        self.assertEqual(dataset.records[0].row_id, "row-1")
        self.assertEqual(dataset.records[1].metadata["category"], "custom")
        self.assertEqual(
            dataset.dataset_sha256,
            "a61c935a195f4ca6852529fc89b6fa6d675e0aa5ae7bc2744fae5c9c6c398251",
        )


if __name__ == "__main__":
    unittest.main()