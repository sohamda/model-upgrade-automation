<!-- markdownlint-disable-file -->
# Implementation Details: Phase 2 — Real Eval Producer for Quality/Safety Benchmarks

## Context Reference

Sources: .copilot-tracking/research/2026-07-22/phase2-real-eval-quality-safety-research.md; .copilot-tracking/research/subagents/2026-07-22/pytest-env-isolation-conftest.md; verified reads of src/recommender/quality_safety_source.py, src/recommender/quality_safety_enrichment.py, src/shared/config.py, src/shared/run_context.py, config/quality_safety_benchmarks.yaml, src/evaluator/models.py.

## Implementation Phase 1: Test Env Isolation

<!-- parallelizable: true -->

### Step 1.1: Create root tests/conftest.py

Add an autouse, function-scoped fixture that deletes the two ambient config env vars read WITHOUT a fallback, so a developer shell exporting them cannot flip `load_app_config` outputs mid-suite.

Files:
* tests/conftest.py - CREATE. Module docstring; `from __future__ import annotations`; `import pytest`; autouse fixture using `monkeypatch.delenv("DEPLOYMENT_TYPE", raising=False)` and `monkeypatch.delenv("ALLOWED_REGIONS", raising=False)`.

Discrepancy references:
* Addresses user work item 0. See DR-01 for the broader env-var set intentionally NOT cleared.

Success criteria:
* Fixture is autouse and applies to unittest.TestCase collections (pytest applies autouse fixtures to TestCase).
* Running the suite with `DEPLOYMENT_TYPE`/`ALLOWED_REGIONS` exported still passes.

Context references:
* .copilot-tracking/research/subagents/2026-07-22/pytest-env-isolation-conftest.md - autouse fixture pattern.

Dependencies:
* None.

## Implementation Phase 2: Optional Evaluation Extra

<!-- parallelizable: true -->

### Step 2.1: Add [project.optional-dependencies] evaluation

Append an `evaluation` extra next to the existing `test` extra. Do not touch `[project] dependencies` (stays `pyyaml>=6.0`).

Files:
* pyproject.toml - MODIFY. Under `[project.optional-dependencies]` add:
  `evaluation = ["azure-ai-evaluation[redteam]>=1.18.1", "azure-identity>=1.17"]`.

Discrepancy references:
* Addresses user hard constraint (runtime pyyaml-only).

Success criteria:
* `pip install -e .` unaffected; `[test]` install still pulls only pytest; `[evaluation]` is opt-in.

Context references:
* .copilot-tracking/research/2026-07-22/phase2-real-eval-quality-safety-research.md - dependency footprint (PyRIT/transformers heavy; offline only).

Dependencies:
* None.

## Implementation Phase 3: Eval Client Seam + Score Helpers

<!-- parallelizable: true -->

### Step 3.1: Create src/evaluator/quality_safety_eval_client.py

Define the injectable seam. The recommender hot path must never import this module.

Files:
* src/evaluator/quality_safety_eval_client.py - CREATE. Contents:
  * Module docstring; `from __future__ import annotations`.
  * `@dataclass(slots=True) RawEvalSignals`: `groundedness: float`, `coherence: float`, `relevance: float`, `fluency: float` (1..5 Likert), `content_safety_defect_rate: float | None`, `overall_asr: float | None` (red-team ASR PERCENT).
  * `class QualitySafetyEvalClient(Protocol)` (typing.Protocol) with `evaluate_model(self, model_id: str) -> RawEvalSignals`.
  * `@dataclass(slots=True) StubQualitySafetyEvalClient`: returns deterministic in-band signals per model_id (for `--dry-run` and tests); no third-party imports.
  * `class FoundryQualitySafetyEvalClient`: real impl. Import `azure.ai.evaluation` / `azure.identity` INSIDE `__init__` (or `evaluate_model`) wrapped in try/except `ImportError` -> raise `DependencyUnavailableError` from `src.shared.errors`. Constructor takes project/credential config; method runs content-safety evaluators + `RedTeam` scan and maps outputs into `RawEvalSignals`.

Discrepancy references:
* Addresses user work item 2. See DD-01 (defer live wiring: real impl may leave the concrete SDK call body as a thin, documented mapping stub raising clearly if config absent).

Success criteria:
* Importing the module with `[evaluation]` absent does NOT raise at import time (guards are inside methods/ctor).
* `FoundryQualitySafetyEvalClient` raises `DependencyUnavailableError` when the extra is missing.
* No import of this module anywhere under `src/recommender/`.

Context references:
* src/evaluator/redteam_runner.py - existing local-fake runner style (categories, block_rate) to echo.
* src/evaluator/models.py (Lines 1-60) - `@dataclass(slots=True)` conventions.
* .copilot-tracking/research/2026-07-22/phase2-real-eval-quality-safety-research.md - content-safety severity/threshold, RedTeam `overall_asr` percent.

Dependencies:
* src/shared/errors.py `DependencyUnavailableError`.

### Step 3.2: Add pure score-derivation helpers

Same module, module-level pure functions (no client, no I/O).

Files:
* src/evaluator/quality_safety_eval_client.py - ADD helpers:
  * `def clamp01(value: float) -> float` -> `max(0.0, min(1.0, value))`.
  * `def derive_quality_score(signals: RawEvalSignals) -> float` -> `clamp01((mean(groundedness, coherence, relevance, fluency) - 1.0) / 4.0)`.
  * `def derive_safety_score(signals: RawEvalSignals) -> float` -> worst-of-signals: start at 1.0; if `content_safety_defect_rate` is not None, fold in `1 - content_safety_defect_rate`; if `overall_asr` is not None, fold in `1 - overall_asr/100`; take `min(...)`; `clamp01`. When both None, return `1.0` (documented) or raise — choose min-of-available, default 1.0 with a docstring note.

Success criteria:
* Helpers are import-safe and network-free; deterministic for fixed inputs.
* `overall_asr` divided by 100 (percent), matching research.

Context references:
* .copilot-tracking/research/2026-07-22/phase2-real-eval-quality-safety-research.md - exact formulas.

Dependencies:
* Step 3.1 dataclass.

## Implementation Phase 4: Refresh Script

<!-- parallelizable: false -->

### Step 4.1: Create scripts/refresh_quality_safety_benchmarks.py

Offline producer: derive scores per model, rewrite the cached YAML with additive provenance.

Files:
* scripts/refresh_quality_safety_benchmarks.py - CREATE. Contents:
  * Module docstring; `from __future__ import annotations`; `argparse`.
  * `_SEED_MODELS` constant = the 8 model_ids (gpt-4o, gpt-4o-mini, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, gpt-5.1, o3, o4-mini) OR read existing model_ids from the target YAML to stay in sync.
  * CLI flags: `--dry-run` (use `StubQualitySafetyEvalClient`, no Azure; print entries and skip/echo write or write to a temp path), `--output` (default `config/quality_safety_benchmarks.yaml`), `--models` (optional subset), `--run-id` (default from `RUN_ID`/`GITHUB_RUN_ID` env or `"local"`).
  * For each model: `signals = client.evaluate_model(model_id)`; `quality = derive_quality_score(signals)`; `safety = derive_safety_score(signals)`; build entry dict: `model_id`, `quality_score` (round 4), `safety_score` (round 4), `provenance` (string: `"content-safety+redteam: quality=(mean likert-1)/4; safety=worst(1-defect_rate,1-asr/100)"`), `as_of_date` (today ISO), plus ADDITIVE keys `source: "content-safety+redteam"`, `run_id`, `evaluator_version`, `sdk_version`.
  * Writer: emit `{"benchmarks": [...]}` via `yaml.safe_dump(sort_keys=False)`, preserving the top-level `benchmarks:` key and prepending the existing header comment block.
  * `main(argv)` returns process exit code; `if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))`.

Discrepancy references:
* Addresses user work item 3. See DD-01 (real client wiring deferred; `--dry-run` is the landing path this phase).

Success criteria:
* `--dry-run` runs with `[evaluation]` absent (stub client) and produces 8 valid entries.
* Output YAML round-trips through `QualitySafetyBenchmarkSource` (validated in Phase 5).
* No Azure/network calls on the `--dry-run` path.

Context references:
* config/quality_safety_benchmarks.yaml (Lines 1-60) - schema + header comment to preserve.
* src/recommender/quality_safety_source.py (Lines 60-120) - the exact keys the parser reads.

Dependencies:
* Phase 3 (client + helpers).

## Implementation Phase 5: Hermetic Tests

<!-- parallelizable: false -->

### Step 5.1: tests/unit/test_quality_safety_eval_client.py

Files:
* tests/unit/test_quality_safety_eval_client.py - CREATE. unittest.TestCase style.
  * `derive_quality_score`: e.g. all-5s -> 1.0; all-1s -> 0.0; mixed -> known value.
  * `clamp01` bounds.
  * `derive_safety_score`: worst-of-signals (defect 0.1 + asr 20% -> min(0.9, 0.8) = 0.8); asr percent divided by 100; both-None default.
  * `FoundryQualitySafetyEvalClient.evaluate_model` (or ctor) raises `DependencyUnavailableError` when the extra is unavailable (simulate via monkeypatching the import to raise, or assert on a clean env without the extra).

Success criteria:
* All hermetic (no network); deterministic asserts.

Context references:
* tests/unit/test_quality_safety_source.py (Lines 1-60) - TestCase + assertAlmostEqual style.

Dependencies:
* Phase 3.

### Step 5.2: tests/unit/test_refresh_quality_safety_benchmarks.py

Files:
* tests/unit/test_refresh_quality_safety_benchmarks.py - CREATE.
  * Invoke `main(["--dry-run", "--output", <tmp yaml>])` (or call the writer with the stub client) into a tmp path.
  * Assert top-level `benchmarks` list has 8 entries; each has the 5 core keys + additive `source`/`run_id`; scores in [0,1].

Success criteria:
* Runs without `[evaluation]`; no Azure.

Context references:
* config/quality_safety_benchmarks.yaml - expected shape.

Dependencies:
* Phase 4.

### Step 5.3: Backward-compat parse test

Files:
* tests/unit/test_quality_safety_source.py - MODIFY (add one test) OR add to the refresh test module.
  * Write a YAML entry carrying the new additive keys (`source`, `run_id`, `evaluator_version`, `sdk_version`) alongside the 5 core keys; assert `QualitySafetyBenchmarkSource.fetch_record` returns a valid `QualitySafetyRecord` and ignores the extras.

Success criteria:
* Proves additive provenance does not break the runtime parser.

Context references:
* src/recommender/quality_safety_source.py (Lines 95-140) - parser only extracts 5 keys via `.get()`.

Dependencies:
* None beyond existing runtime.

## Implementation Phase 6: Validation

<!-- parallelizable: false -->

### Step 6.1: Run full unit suite

`.venv/Scripts/python.exe -m pytest tests/unit -q` — expect green.

### Step 6.2: Refresh-script dry-run smoke

`.venv/Scripts/python.exe scripts/refresh_quality_safety_benchmarks.py --dry-run` — expect 8 provenance-stamped entries, exit 0, no Azure/network.

### Step 6.3: Report blocking issues

Document anything requiring further research (e.g., live Foundry evaluator mapping); provide next steps; avoid large-scale fixes inline.

## Dependencies

* Python 3.12 `.venv` with `[test]` extra installed.
* `pyyaml` (runtime).

## Success Criteria

* Suite green with ambient env vars set; refresh `--dry-run` writes 8 back-compat entries with no optional deps installed.
