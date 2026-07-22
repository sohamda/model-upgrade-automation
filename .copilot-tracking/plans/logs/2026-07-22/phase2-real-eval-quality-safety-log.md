<!-- markdownlint-disable-file -->
# Planning Log: Phase 2 — Real Eval Producer for Quality/Safety Benchmarks

## Discrepancy Log

### Unaddressed Research Items

* DR-01: Full ambient-env-var set is not cleared in conftest; only `DEPLOYMENT_TYPE` + `ALLOWED_REGIONS` are.
  * Source: src/shared/config.py (Lines 200-226) enumerates ~19 config vars; src/shared/run_context.py adds `GITHUB_*`/`RUN_ID`.
  * Reason: Only `DEPLOYMENT_TYPE` and `ALLOWED_REGIONS` are read WITHOUT a fallback (they raise `ConfigurationError` when absent and flip outputs); all others fall back to `azure.env.example` defaults. Research Q6 and terminal evidence confirm these two are the polluters. Keeping the fixture minimal matches the locked research fixture.
  * Impact: low. If future pollution appears from the fallback-backed vars, extend the fixture.

* DR-02: Live Foundry evaluator invocation (real content-safety + RedTeam scan) is not executed this phase.
  * Source: research "Recommended Architecture" (out-of-band refresh) + user locked decision 1.
  * Reason: Deferred by design; seam + `--dry-run` land now, live wiring later.
  * Impact: medium — quality/safety values remain seed-equivalent until a live run replaces them; recommender behavior unchanged.

### Plan Deviations from Research

* DD-01: Research describes a fully wired offline evaluator; the plan lands the injectable seam + stub-backed `--dry-run` and leaves the concrete SDK call body as a thin, documented mapping.
  * Research recommends: run real evaluators against a reference deployment.
  * Plan implements: interface + real-impl skeleton (import-guarded, raises `DependencyUnavailableError`) + stub impl driving the refresh script.
  * Rationale: user locked decision 1 ("build seam now, DEFER live wiring; no live Azure run required to land Phase 2").

* DD-02: `safety_score` uses worst-of-signals `min(1 - defect_rate, 1 - asr/100)` rather than the seed file's `1 - defect_rate`.
  * Research recommends: `safety_score = min(1 - content_safety_defect_rate, 1 - overall_asr/100)`.
  * Plan implements: the research worst-of formula (folding whichever signals are present).
  * Rationale: research is the authoritative Phase 2 mapping; the seed's simpler formula predates red-team signal.

### Implementation Deviations

* DD-03: `scripts/refresh_quality_safety_benchmarks.py` inserts the repo root into `sys.path` before importing the `src` package.
  * Plan specifies: import `src.evaluator.quality_safety_eval_client` directly.
  * Implementation differs: adds a guarded `sys.path.insert(0, str(_REPO_ROOT))` before the `from src...` import (`# noqa: E402`).
  * Rationale: pytest supplies the repo root via `pythonpath=["."]`, but standalone execution (the DoD `--dry-run` command) does not, causing `ModuleNotFoundError: No module named 'src'`. The bootstrap keeps the DoD dry-run runnable without altering runtime behavior; no runtime module imports the script.

## Implementation Paths Considered

### Selected: Seam in src/evaluator/ + local refresh script + additive YAML provenance

* Approach: new `src/evaluator/quality_safety_eval_client.py` (injectable, import-guarded) + `scripts/refresh_quality_safety_benchmarks.py` writing additive provenance keys the runtime parser ignores.
* Rationale: matches existing evaluator adapter layout; keeps runtime pyyaml-only and consumer contract untouched; back-compat proven by parser reading only 5 keys via `.get()`.
* Evidence: src/recommender/quality_safety_source.py (Lines 95-140); src/evaluator/redteam_runner.py (existing local-fake pattern).

### IP-01: Put the seam under src/recommender/

* Approach: co-locate producer with the consumer source/enrichment modules.
* Trade-offs: proximity to consumer, but risks the recommender package importing optional eval deps and violating the pyyaml-only hot-path guarantee.
* Rejection rationale: `src/evaluator/` is the established home for evaluation adapters and keeps the import boundary clean.

### IP-02: Rewrite the YAML schema with a nested `provenance:` object

* Approach: replace the flat provenance string with a structured block (versions, run id, source).
* Trade-offs: richer provenance, but changes the schema shape and would require parser changes — breaking the "producer-only change" constraint.
* Rejection rationale: user hard constraint requires additive-only fields with an unchanged parser; flat additive keys satisfy this without touching `QualitySafetyBenchmarkSource`.

## Suggested Follow-On Work

* WI-01: Wire `FoundryQualitySafetyEvalClient` to real content-safety + RedTeam SDK calls and run one live refresh (medium).
  * Source: DD-01 / DR-02.
  * Dependency: `[evaluation]` extra installed + a reference deployment + Azure credentials.
* WI-02: Optional CI workflow to run the refresh on a schedule and open a PR with updated benchmarks (low).
  * Source: user locked decision 3 (explicitly out of scope this phase).
  * Dependency: WI-01.
* WI-03: Extend conftest env clearing if fallback-backed vars ever cause test pollution (low).
  * Source: DR-01.
  * Dependency: none.
