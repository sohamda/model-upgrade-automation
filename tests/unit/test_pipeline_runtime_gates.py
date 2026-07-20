"""Unit tests for runtime gates in orchestrator pipeline."""

from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from src.orchestrator.pipeline import _resolve_catalog, _resolve_source, execute_dry_run
from src.shared.config import RuntimeOptions, load_app_config
from src.shared.contracts import RetiringModel
from src.shared.errors import ContractError, DependencyUnavailableError


REPO_ROOT = Path(__file__).resolve().parents[2]
HERMETIC_REPO = REPO_ROOT / "tests" / "fixtures" / "hermetic_repo"


class PipelineRuntimeGateTests(unittest.TestCase):
    def test_given_top_k_when_running_then_candidates_are_capped(self) -> None:
        # Act
        result = execute_dry_run(
            REPO_ROOT,
            run_id="test-top-k",
            config_root=HERMETIC_REPO,
            runtime=RuntimeOptions(top_k=1),
        )

        # Assert
        recs = result.recommender["recommendations"]
        self.assertEqual(len(recs), 1)
        self.assertEqual(len(recs[0]["ranked_candidates"]), 1)

    def test_given_run_evals_without_provision_when_running_then_contract_error(self) -> None:
        # Act / Assert
        with self.assertRaises(ContractError):
            execute_dry_run(
                REPO_ROOT,
                run_id="test-invalid-gate",
                config_root=HERMETIC_REPO,
                runtime=RuntimeOptions(run_evals=True, provision_candidates=False),
            )

    def test_given_hermetic_config_when_resolving_source_then_fixture_source_is_used(self) -> None:
        # Arrange
        config = load_app_config(HERMETIC_REPO)

        # Act
        source = _resolve_source(REPO_ROOT, config, RuntimeOptions(), fixture_path=None)

        # Assert
        self.assertEqual(source.__class__.__name__, "FixtureRetirementSource")

    def test_given_runtime_override_when_resolving_source_then_official_source_is_enabled(self) -> None:
        # Arrange
        config = load_app_config(HERMETIC_REPO)

        # Act
        source = _resolve_source(
            REPO_ROOT,
            config,
            RuntimeOptions(use_official_sources=True),
            fixture_path=None,
        )

        # Assert
        self.assertEqual(source.__class__.__name__, "_FallbackRetirementSource")

    def test_given_live_retirement_failure_when_loading_then_fixture_fallback_is_used(self) -> None:
        # Arrange
        config = load_app_config(HERMETIC_REPO)
        source = _resolve_source(
            REPO_ROOT,
            config,
            RuntimeOptions(use_official_sources=True),
            fixture_path=None,
        )

        def _raise_unavailable(self):
            raise DependencyUnavailableError("network unavailable")

        # Act
        with patch(
            "src.detector.arm_models_source.ArmModelsRetirementSource.load",
            _raise_unavailable,
        ), patch(
            "src.detector.retirement_schedule_source.LearnRetirementScheduleSource.load",
            _raise_unavailable,
        ):
            items = source.load()

        # Assert
        self.assertGreater(len(items), 0)
        self.assertEqual(items[0].source, "fixture")

    def test_given_live_catalog_failure_when_loading_then_fixture_fallback_is_used(self) -> None:
        # Arrange
        config = load_app_config(HERMETIC_REPO)
        catalog = _resolve_catalog(
            REPO_ROOT,
            config,
            RuntimeOptions(use_official_sources=True),
            catalog_path=None,
        )

        def _raise_unavailable(self):
            raise DependencyUnavailableError("network unavailable")

        # Act
        with patch(
            "src.recommender.arm_catalog_source.ArmModelsCatalogSource.load",
            _raise_unavailable,
        ), patch(
            "src.recommender.foundry_catalog_source.LearnFoundryCatalogSource.load",
            _raise_unavailable,
        ):
            items = catalog.load()

        # Assert
        self.assertGreater(len(items), 0)
        self.assertEqual(items[0].model_id, "gpt-4.1")

    def test_given_official_sources_when_resolving_source_then_arm_is_primary(self) -> None:
        # Arrange
        config = load_app_config(HERMETIC_REPO)

        # Act
        source = _resolve_source(
            REPO_ROOT,
            config,
            RuntimeOptions(use_official_sources=True),
            fixture_path=None,
        )

        # Assert
        self.assertEqual(source.__class__.__name__, "_FallbackRetirementSource")
        self.assertEqual(
            source.primary.__class__.__name__, "ArmModelsRetirementSource"
        )
        # Second tier degrades ARM -> Learn -> fixture.
        self.assertEqual(
            source.fallback.primary.__class__.__name__,
            "LearnRetirementScheduleSource",
        )

    def test_given_live_retirement_failure_at_arm_when_loading_then_learn_is_used(self) -> None:
        # Arrange
        config = load_app_config(HERMETIC_REPO)
        source = _resolve_source(
            REPO_ROOT,
            config,
            RuntimeOptions(use_official_sources=True),
            fixture_path=None,
        )

        def _raise_unavailable(self):
            raise DependencyUnavailableError("arm unavailable")

        learn_rows = [
            RetiringModel(
                model_id="gpt-4o",
                current_version="2024-05-13",
                retirement_date="2026-01-01",
                source="learn",
            )
        ]

        # Act
        with patch(
            "src.detector.arm_models_source.ArmModelsRetirementSource.load",
            _raise_unavailable,
        ), patch(
            "src.detector.retirement_schedule_source.LearnRetirementScheduleSource.load",
            lambda self: learn_rows,
        ):
            items = source.load()

        # Assert
        self.assertEqual(items[0].source, "learn")


if __name__ == "__main__":
    unittest.main()
