"""Unit tests for the curated quality/safety benchmark source."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.recommender.quality_safety_source import (
    QualitySafetyBenchmarkSource,
    QualitySafetyRecord,
)
from src.shared.errors import DependencyUnavailableError


_VALID_YAML = """\
benchmarks:
  - model_id: gpt-4.1
    quality_score: 0.86
    safety_score: 0.96
    provenance: "curated-seed: test"
    as_of_date: "2026-07-22"
  - model_id: gpt-4.1-mini
    quality_score: 0.80
    safety_score: 0.95
    provenance: "curated-seed: test"
    as_of_date: "2026-07-22"
"""


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "quality_safety_benchmarks.yaml"
    path.write_text(content, encoding="utf-8")
    return path


class QualitySafetyBenchmarkSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        # A per-test temp directory keeps fixtures isolated from the repo file.
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_given_known_model_when_fetching_then_returns_record(self) -> None:
        # Arrange
        path = _write(self.tmp_path, _VALID_YAML)
        source = QualitySafetyBenchmarkSource(path)

        # Act
        record = source.fetch_record("gpt-4.1", region="eastus")

        # Assert
        self.assertIsInstance(record, QualitySafetyRecord)
        self.assertEqual(record.model_id, "gpt-4.1")
        self.assertAlmostEqual(record.quality_score, 0.86, places=6)
        self.assertAlmostEqual(record.safety_score, 0.96, places=6)
        self.assertEqual(record.as_of_date, "2026-07-22")

    def test_given_second_call_when_fetching_then_uses_cache(self) -> None:
        # Arrange
        path = _write(self.tmp_path, _VALID_YAML)
        source = QualitySafetyBenchmarkSource(path)
        first = source.fetch_record("gpt-4.1-mini", region="eastus")

        # Act: remove the file; a cached load must still succeed.
        path.unlink()
        second = source.fetch_record("gpt-4.1", region="eastus")

        # Assert
        self.assertEqual(first.model_id, "gpt-4.1-mini")
        self.assertEqual(second.model_id, "gpt-4.1")

    def test_given_unknown_model_when_fetching_then_raises(self) -> None:
        # Arrange
        path = _write(self.tmp_path, _VALID_YAML)
        source = QualitySafetyBenchmarkSource(path)

        # Act / Assert
        with self.assertRaises(DependencyUnavailableError):
            source.fetch_record("does-not-exist", region="eastus")

    def test_given_missing_file_when_fetching_then_raises(self) -> None:
        # Arrange
        source = QualitySafetyBenchmarkSource(self.tmp_path / "absent.yaml")

        # Act / Assert
        with self.assertRaises(DependencyUnavailableError):
            source.fetch_record("gpt-4.1", region="eastus")

    def test_given_out_of_range_score_when_fetching_then_raises(self) -> None:
        # Arrange: quality_score above 1.0 is malformed.
        content = (
            "benchmarks:\n"
            "  - model_id: gpt-4.1\n"
            "    quality_score: 1.5\n"
            "    safety_score: 0.9\n"
            '    provenance: "curated-seed: test"\n'
            '    as_of_date: "2026-07-22"\n'
        )
        source = QualitySafetyBenchmarkSource(_write(self.tmp_path, content))

        # Act / Assert
        with self.assertRaises(DependencyUnavailableError):
            source.fetch_record("gpt-4.1", region="eastus")

    def test_given_non_numeric_score_when_fetching_then_raises(self) -> None:
        # Arrange: safety_score as text is malformed.
        content = (
            "benchmarks:\n"
            "  - model_id: gpt-4.1\n"
            "    quality_score: 0.86\n"
            "    safety_score: not-a-number\n"
            '    provenance: "curated-seed: test"\n'
            '    as_of_date: "2026-07-22"\n'
        )
        source = QualitySafetyBenchmarkSource(_write(self.tmp_path, content))

        # Act / Assert
        with self.assertRaises(DependencyUnavailableError):
            source.fetch_record("gpt-4.1", region="eastus")

    def test_given_additive_provenance_keys_when_fetching_then_ignored(self) -> None:
        # Arrange: the refresh script writes additive provenance keys alongside
        # the five core keys; the runtime parser must ignore the extras.
        content = (
            "benchmarks:\n"
            "  - model_id: gpt-4.1\n"
            "    quality_score: 0.86\n"
            "    safety_score: 0.96\n"
            '    provenance: "content-safety+redteam"\n'
            '    as_of_date: "2026-07-22"\n'
            '    source: "content-safety+redteam"\n'
            '    run_id: "local"\n'
            '    evaluator_version: "content-safety+redteam/1"\n'
            '    sdk_version: "1.18.1"\n'
        )
        source = QualitySafetyBenchmarkSource(_write(self.tmp_path, content))

        # Act
        record = source.fetch_record("gpt-4.1", region="eastus")

        # Assert
        self.assertIsInstance(record, QualitySafetyRecord)
        self.assertEqual(record.model_id, "gpt-4.1")
        self.assertAlmostEqual(record.quality_score, 0.86, places=6)
        self.assertAlmostEqual(record.safety_score, 0.96, places=6)
        self.assertEqual(record.provenance, "content-safety+redteam")


if __name__ == "__main__":
    unittest.main()
