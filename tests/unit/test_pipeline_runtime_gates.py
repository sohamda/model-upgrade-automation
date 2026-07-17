"""Unit tests for runtime gates in orchestrator pipeline."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.orchestrator.pipeline import execute_dry_run
from src.shared.config import RuntimeOptions
from src.shared.errors import ContractError


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


if __name__ == "__main__":
    unittest.main()
