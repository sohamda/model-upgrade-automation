"""Unit tests for Learn Foundry catalog parsing."""

from __future__ import annotations

import unittest

from src.recommender.foundry_catalog_source import LearnFoundryCatalogSource


class FoundryCatalogSourceTests(unittest.TestCase):
    def test_given_catalog_rows_when_parsing_then_candidates_are_created(self) -> None:
        # Arrange
        source = LearnFoundryCatalogSource()
        body = """
| Model | Version |
|---|---|
| gpt-4.1 | 2026-01-12 |
| gpt-4.1-mini | 2025-04-14 |
"""

        # Act
        candidates = source._parse(body)

        # Assert
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].model_id, "gpt-4.1")
        self.assertEqual(candidates[1].model_id, "gpt-4.1-mini")


if __name__ == "__main__":
    unittest.main()
