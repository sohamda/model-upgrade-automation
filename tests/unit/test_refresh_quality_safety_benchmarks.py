"""Hermetic unit tests for the offline benchmark refresh script."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import yaml

from scripts.refresh_quality_safety_benchmarks import (
    EXIT_FAILURE,
    EXIT_SUCCESS,
    build_entries,
    create_parser,
    main,
    _build_live_response_provider,
    _select_client,
)
from src.evaluator.quality_safety_eval_client import (
    RawEvalSignals,
    StubQualitySafetyEvalClient,
)

_CORE_KEYS = {"model_id", "quality_score", "safety_score", "provenance", "as_of_date"}
_ADDITIVE_KEYS = {"source", "run_id", "evaluator_version", "sdk_version"}


class _FakeLiveClient:
    """Deterministic stand-in for the live client used in hermetic tests."""

    def __init__(self, signals: RawEvalSignals) -> None:
        self._signals = signals

    def evaluate_model(self, model_id: str) -> RawEvalSignals:
        return self._signals


class RefreshDryRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_given_dry_run_when_running_then_does_not_write_output(self) -> None:
        # Arrange
        output = self.tmp_path / "out.yaml"

        # Act
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["--dry-run", "--output", str(output), "--run-id", "t1"])

        # Assert
        self.assertEqual(exit_code, 0)
        self.assertFalse(output.exists())
        self.assertIn("dry-run", buffer.getvalue())

    def test_given_dry_run_when_rendering_then_entries_are_valid(self) -> None:
        # Arrange / Act: parse the printed document.
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            main(["--dry-run", "--run-id", "t2"])
        document = buffer.getvalue().split("\n", 1)[1]
        parsed = yaml.safe_load(document)

        # Assert
        entries = parsed["benchmarks"]
        self.assertEqual(len(entries), 8)
        for entry in entries:
            self.assertTrue(_CORE_KEYS.issubset(entry))
            self.assertTrue(_ADDITIVE_KEYS.issubset(entry))
            self.assertTrue(0.0 <= entry["quality_score"] <= 1.0)
            self.assertTrue(0.0 <= entry["safety_score"] <= 1.0)
            self.assertEqual(entry["run_id"], "t2")

    def test_given_write_mode_when_running_then_output_is_parseable(self) -> None:
        # Arrange
        output = self.tmp_path / "written.yaml"

        # Act
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["--output", str(output), "--models", "gpt-4o", "o3"])

        # Assert
        self.assertEqual(exit_code, 0)
        self.assertTrue(output.exists())
        parsed = yaml.safe_load(output.read_text(encoding="utf-8"))
        ids = [entry["model_id"] for entry in parsed["benchmarks"]]
        self.assertEqual(ids, ["gpt-4o", "o3"])


class RefreshModeGuardTests(unittest.TestCase):
    def test_given_dry_run_and_live_when_parsing_then_argparse_errors(self) -> None:
        # Mutually exclusive group -> argparse exits with code 2.
        with self.assertRaises(SystemExit) as caught:
            with redirect_stdout(io.StringIO()):
                create_parser().parse_args(["--dry-run", "--live"])
        self.assertEqual(caught.exception.code, 2)

    def test_given_default_when_selecting_client_then_stub(self) -> None:
        args = create_parser().parse_args([])
        client, seeds, exit_code = _select_client(args)
        self.assertEqual(exit_code, 0)
        self.assertIsInstance(client, StubQualitySafetyEvalClient)
        self.assertIsNone(seeds)


class RefreshCandidateCapTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_given_models_over_cap_when_running_then_fails_without_write(self) -> None:
        output = self.tmp_path / "capped.yaml"
        with redirect_stdout(io.StringIO()):
            exit_code = main(
                [
                    "--max-candidates",
                    "1",
                    "--models",
                    "a",
                    "b",
                    "--output",
                    str(output),
                ]
            )
        self.assertEqual(exit_code, 1)
        self.assertFalse(output.exists())


class RefreshLiveBuildTests(unittest.TestCase):
    def _live_signals(self) -> RawEvalSignals:
        return RawEvalSignals(
            groundedness=4.0,
            coherence=4.0,
            relevance=4.0,
            fluency=4.0,
            content_safety_defect_rate=0.1,
            overall_asr=20.0,
            content_safety_threshold=3,
            content_safety_sample_size=10,
            per_risk_asr={"violence": 25.0},
            asr_convention="overall_asr is a percent",
            sdk_version="1.18.1",
            evaluators_run=("violence", "red_team"),
            scored_deployment="judge-1",
            scan_date="2026-02-02",
            num_objectives=5,
            attack_strategies=("Baseline", "Jailbreak"),
        )

    def test_given_live_signals_when_building_then_provenance_stamped(self) -> None:
        client = _FakeLiveClient(self._live_signals())
        entries = build_entries(
            client,
            ["m1"],
            run_id="r1",
            as_of_date="2026-01-01",
            sdk_version="fallback",
            seed_entries={},
            live=True,
        )
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertTrue(_CORE_KEYS.issubset(entry))
        # C12/C13 provenance stamped additively; tuples rendered as lists.
        self.assertEqual(entry["content_safety_threshold"], 3)
        self.assertEqual(entry["num_objectives"], 5)
        self.assertEqual(entry["attack_strategies"], ["Baseline", "Jailbreak"])
        self.assertEqual(entry["evaluators_run"], ["violence", "red_team"])
        self.assertEqual(entry["per_risk_asr"], {"violence": 25.0})
        self.assertEqual(entry["scored_deployment"], "judge-1")
        self.assertEqual(entry["scan_date"], "2026-02-02")
        self.assertEqual(entry["as_of_date"], "2026-02-02")
        self.assertEqual(entry["sdk_version"], "1.18.1")
        # No raw tuples survive (PyYAML would reject them on dump).
        rendered = yaml.safe_dump({"benchmarks": entries})
        self.assertIn("attack_strategies", rendered)

    def test_given_all_unscored_live_when_building_then_seed_preserved(self) -> None:
        unscored = RawEvalSignals(
            groundedness=None, coherence=None, relevance=None, fluency=None
        )
        client = _FakeLiveClient(unscored)
        seed = {
            "model_id": "m1",
            "quality_score": 0.9,
            "safety_score": 0.95,
            "provenance": "curated-seed",
            "as_of_date": "2026-07-22",
        }
        entries = build_entries(
            client,
            ["m1"],
            run_id="r1",
            as_of_date="2026-01-01",
            sdk_version="fallback",
            seed_entries={"m1": seed},
            live=True,
        )
        self.assertEqual(entries, [seed])


class RefreshLiveProbeDatasetTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _write_dataset(self, prompts: list[str]) -> Path:
        path = self.tmp_path / "probes.jsonl"
        lines = [
            json.dumps({"id": f"p-{index:03d}", "prompt": prompt})
            for index, prompt in enumerate(prompts, start=1)
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_given_live_dataset_when_selecting_then_prompts_and_provider_threaded(
        self,
    ) -> None:
        dataset_path = self._write_dataset(["prompt one", "prompt two"])
        output = self.tmp_path / "absent.yaml"
        args = create_parser().parse_args(
            [
                "--live",
                "--foundry-project",
                "https://owned.example/api/projects/p",
                "--judge-model",
                "judge",
                "--probe-dataset",
                str(dataset_path),
                "--output",
                str(output),
            ]
        )
        sentinel = object()
        captured: dict[str, object] = {}

        class _Capturing:
            def __init__(self, **kwargs: object) -> None:
                captured.update(kwargs)

        with mock.patch(
            "scripts.refresh_quality_safety_benchmarks.FoundryQualitySafetyEvalClient",
            _Capturing,
        ), mock.patch(
            "scripts.refresh_quality_safety_benchmarks._build_live_response_provider",
            return_value=sentinel,
        ):
            client, seeds, exit_code = _select_client(args)

        self.assertEqual(exit_code, EXIT_SUCCESS)
        self.assertIsInstance(client, _Capturing)
        self.assertEqual(captured["probe_prompts"], ("prompt one", "prompt two"))
        self.assertIs(captured["response_provider"], sentinel)
        self.assertEqual(seeds, {})

    def test_given_missing_probe_dataset_when_selecting_then_refuses(self) -> None:
        missing = self.tmp_path / "does-not-exist.jsonl"
        args = create_parser().parse_args(
            [
                "--live",
                "--foundry-project",
                "https://owned.example/api/projects/p",
                "--judge-model",
                "judge",
                "--probe-dataset",
                str(missing),
            ]
        )

        with redirect_stdout(io.StringIO()):
            client, seeds, exit_code = _select_client(args)

        self.assertEqual(exit_code, EXIT_FAILURE)
        self.assertIsNone(client)

    def test_given_project_when_building_provider_then_callable_without_network(
        self,
    ) -> None:
        provider = _build_live_response_provider("https://owned.example/api/projects/p")
        self.assertTrue(callable(provider))


if __name__ == "__main__":
    unittest.main()
