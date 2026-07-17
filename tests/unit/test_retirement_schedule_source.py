"""Unit tests for Learn retirement schedule parsing."""

from __future__ import annotations

import unittest

from src.detector.retirement_schedule_source import LearnRetirementScheduleSource


class RetirementScheduleSourceTests(unittest.TestCase):
    def test_given_markdown_table_when_parsing_then_rows_are_normalized(self) -> None:
        # Arrange
        source = LearnRetirementScheduleSource()
        body = """
| Model | Version | Retirement date |
|---|---|---|
| gpt-4.1-mini | 2025-04-14 | 2026-08-15 |
"""

        # Act
        result = source._parse_rows(body)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model_id, "gpt-4.1-mini")
        self.assertEqual(result[0].current_version, "2025-04-14")
        self.assertEqual(result[0].retirement_date, "2026-08-15")


if __name__ == "__main__":
    unittest.main()
