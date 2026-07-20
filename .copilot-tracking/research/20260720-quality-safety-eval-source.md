<!-- markdownlint-disable-file -->
# Task Research: Evaluation-Driven Quality & Safety Scoring Source

Design how to replace the uniform `quality_score=0.9` / `safety_score=0.9` placeholders in this repo's recommender with a real, evaluation-driven quality and safety scoring source, inspired by `sohamda/azure-ai-redteam-eval`, while honoring this repo's zero-heavy-dependency constraint (pyyaml + az CLI + stdlib urllib only) and its established non-fatal enrichment pattern.

## Task Implementation Requests

* Summarize how the reference repo produces quality and safety/redteam metrics (concrete evaluator names, ranges, normalization).
* Map those metrics to this repo's `quality_score` (0..1) and `safety_score` (0..1), including aggregation and inversion/normalization.
* Design an integration that mirrors `pricing_enrichment.py`: a new source module + enrichment step, injected only when official sources are active, non-fatal, hermetic-testable.
* Decide the dependency path: az CLI / REST under the zero-heavy-dep rule vs. an optional `azure-ai-evaluation` extra.
* Provide a phased plan with the not-yet-deployed-candidate caveat.
* List open questions, risks, and deferred items.

## Scope and Success Criteria

* Scope: research + design only. No production code changes. This artifact and the two subagent artifacts under `.copilot-tracking/research/subagents/2026-07-20/` are the only writes.
* Assumptions:
  * ARM-derived candidates are catalog entries, not deployed endpoints, at recommend time.
  * The recommender must remain runnable with runtime dependency `pyyaml` only.
  * The existing non-fatal degradation contract (fall back to placeholder + `parse_warning`) must be preserved.
* Success Criteria:
  * A metrics-to-scores mapping that is deterministic and defensible.
  * An enrichment design that is a structural twin of `enrich_cost_scores`.
  * A dependency decision that keeps the runtime import surface pyyaml-only.
  * A phased plan that explicitly handles not-yet-deployed candidates.

## Supporting Research Artifacts

* `.copilot-tracking/research/subagents/2026-07-20/reference-redteam-eval-repo-research.md` (reference repo: evaluators, ranges, redteam, deps, config).
* `.copilot-tracking/research/subagents/2026-07-20/current-repo-recommender-enrichment-research.md` (this repo: placeholder location, enrichment pattern, gating, tests).

---

## 1. How the Reference Repo Produces Quality and Safety Metrics

### 1.1 Quality (Azure AI Evaluation SDK, LLM-as-judge)

The reference repo builds an evaluator registry in `src/continuous_evaluation/evaluators.py` importing from the `azure-ai-evaluation` package:

| Evaluator | Package class | Output key(s) | Range | Backing |
|-----------|---------------|---------------|-------|---------|
| Groundedness | `GroundednessEvaluator` | `groundedness`, `gpt_groundedness` | 1-5 Likert | Live Azure OpenAI judge deployment |
| Coherence | `CoherenceEvaluator` | `coherence`, `gpt_coherence` | 1-5 Likert | Live Azure OpenAI judge deployment |
| Relevance | `RelevanceEvaluator` | `relevance`, `gpt_relevance` | 1-5 Likert | Live Azure OpenAI judge deployment |
| Fluency | `FluencyEvaluator` | `fluency`, `gpt_fluency` | 1-5 Likert | Live Azure OpenAI judge deployment |
| Conciseness | local `ConcisenessEvaluator` | `conciseness` | 2.0-5.0 discrete | Deterministic word count (no service) |

Execution: `azure.ai.evaluation.evaluate(data=<jsonl>, evaluators=<dict>, azure_ai_project=<project>, evaluation_name=<str>)`. The runner passes a static JSONL fixture (`eval_golden.jsonl`, 10 rows; PR path `eval_golden_small.jsonl`, 5 rows) with columns `query`, `context`, `response`, `ground_truth`. No `target` callable is passed, so it grades pre-produced `response` text rather than calling a live app per query. The four quality evaluators still require a **deployed Azure OpenAI judge model**; the safety evaluators require **Foundry project access + `DefaultAzureCredential`**.

Aggregation in the repo (`metrics.py`) takes the terminal component of each aggregate key and reports an **unweighted arithmetic mean** across all numeric metrics for display/telemetry only. Quality gates default to 4.0 for each quality metric; a per-metric drop > 0.3 vs. `evaluation_baseline.json` is flagged as regression.

Committed baseline values (GPT-4o, 10-row golden set): groundedness 4.70, coherence 4.00, relevance 4.60, fluency 4.10, conciseness 4.95.

### 1.2 Safety (ContentSafety + RedTeam)

* `src/continuous_evaluation/evaluators.py` also builds `ContentSafetyEvaluator` (composite: violence, sexual, self-harm, hate/unfairness) and `ProtectedMaterialEvaluator`, both constructed with `DefaultAzureCredential` + `AzureAIProject`. Content-safety evaluators return per-category **severity 0-7** plus a `*_result` pass/fail against a threshold. Only produced in full runs (excluded from PR path).
* `src/redteam/run_redteam.py` imports `AttackStrategy`, `RedTeam`, `RiskCategory` from `azure.ai.evaluation.red_team`, runs `red_team.scan(target=<callback>, attack_strategies=[Baseline, Jailbreak], ...)` against a **live `POST /chat` endpoint** over `httpx`, using `RiskCategory.Violence / HateUnfairness / Sexual / SelfHarm`.

Critical finding: the reference repo does **not** compute a numeric ASR, defect rate, per-risk numeric breakdown, or a single safety score from the RedTeam SDK. The SDK result is serialized as a string only. The one usable safety signal is a separate **custom 10-probe suite** (`adversarial_prompts.jsonl`) that yields `passed`, `failed`, `pass_rate`, `max_severity`. The inferable (not code-emitted) formula is:

$$\text{ASR} = \frac{\text{failed probes}}{\text{total probes}}, \qquad \text{blocked rate} = 1 - \text{ASR}$$

Committed sample: 10/10 passed → ASR 0%, blocked rate 100%.

### 1.3 Config and Dependency Footprint (reference)

* Credentials: `DefaultAzureCredential` locally / Azure OIDC in CI. Env vars: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`, `AZURE_AI_FOUNDRY_PROJECT`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`.
* Runtime deps are heavy: `azure-ai-evaluation[redteam]>=1.0.0`, `azure-identity`, `agent-framework-*`, `pydantic`, `opentelemetry-*`, `fastapi`, `httpx`. PyRIT is not directly declared/imported but arrives transitively via the `[redteam]` extra. This footprint is fundamentally incompatible with this repo's pyyaml-only rule.

---

## 2. Metrics → This Repo's `quality_score` / `safety_score` (0..1, higher=better)

This repo's `CatalogCandidate.quality_score`, `safety_score`, `cost_score` are floats in 0..1, higher-is-better, consumed as weighted inputs in `scorer.py` (quality 0.5, safety 0.3, cost 0.2). The mapping must therefore normalize the reference metrics into 0..1.

### 2.1 Quality mapping

Reference quality evaluators are 1-5 Likert. Normalize each to 0..1 with a linear rescale, then take the (optionally weighted) mean of the chosen evaluators:

$$q_i = \frac{s_i - 1}{5 - 1} = \frac{s_i - 1}{4}, \qquad \text{quality\_score} = \operatorname{clamp}_{[0,1]}\!\left(\frac{1}{n}\sum_{i=1}^{n} q_i\right)$$

Aggregate over `{groundedness, coherence, relevance, fluency}` (conciseness optional; exclude the duplicate `gpt_*` keys). Worked example with the committed baseline: mean raw = (4.70+4.00+4.60+4.10)/4 = 4.35 → quality_score = (4.35-1)/4 = **0.8375**. This lands near the current 0.9 placeholder, which is a useful sanity check that the mapping is neither inflating nor collapsing the range.

### 2.2 Safety mapping

Two candidate signals, both invert a "badness" measure into a 0..1 goodness score:

* **Content-safety severity path.** For each safety category, treat a per-row score at or above a severity threshold `T` (commonly `T = 4` on the 0-7 scale) as a defect. Then:

$$\text{defect\_rate} = \frac{\#\{\text{rows with any category severity} \ge T\}}{\#\text{rows}}, \qquad \text{safety\_score} = 1 - \text{defect\_rate}$$

* **RedTeam / adversarial-probe path.** Using attack success rate (ASR) directly:

$$\text{safety\_score} = 1 - \text{ASR} = \text{blocked rate}$$

Both produce 0..1, higher=better. When both are available, combine as a weighted mean (e.g. `0.5 * (1 - defect_rate) + 0.5 * (1 - ASR)`) or take the more conservative `min(...)`; conservative `min` is recommended for a safety dimension. Because the reference repo does not emit numeric ASR, the ASR path here depends on **precomputed** adversarial results (see §5).

### 2.3 Aggregation summary

| This repo field | Source metrics | Aggregate | Normalize/Invert |
|-----------------|----------------|-----------|-------------------|
| `quality_score` | groundedness, coherence, relevance, fluency (1-5) | mean | `(s-1)/4`, clamp 0..1 |
| `safety_score` | content-safety severity 0-7 and/or adversarial ASR | conservative `min` (or weighted mean) | `1 - defect_rate`, `1 - ASR` |

---

## 3. Integration Design (mirrors `pricing_enrichment.py`)

### 3.1 Canonical pattern being mirrored

`enrich_cost_scores(target, candidates, price_client) -> tuple[list[CatalogCandidate], list[str]]` at `src/recommender/pricing_enrichment.py:54-58`:

* Injected client (`RetailPricesClient`), never constructed inside the enrichment.
* Per-region cache; only `DependencyUnavailableError` is caught and downgraded to a `warnings` entry.
* Immutable update via `dataclasses.replace(candidate, cost_score=...)`; inputs never mutated.
* Wired into `recommend_candidates` after filtering and before scoring (`service.py:39-43`); warnings flow into `RecommenderResult.parse_warnings` (`service.py:54-57`).
* Client constructed at the orchestrator injection boundary only under `_should_use_official_sources` (`pipeline.py:267-273`).

### 3.2 New module: `src/recommender/quality_safety_source.py`

A hermetic, stdlib+pyyaml source client that returns per-model quality/safety records and raises `DependencyUnavailableError` on any retrieval failure.

```python
# src/recommender/quality_safety_source.py (design sketch — NOT for implementation here)
from dataclasses import dataclass
from src.shared.errors import DependencyUnavailableError

@dataclass(slots=True, frozen=True)
class QualitySafetyRecord:
    model_id: str
    quality_score: float  # already normalized 0..1
    safety_score: float   # already normalized 0..1
    provenance: str       # e.g. "benchmark:2026-07 content-safety+quality"

@dataclass(slots=True)
class QualitySafetyBenchmarkSource:
    """Reads curated, precomputed benchmark scores (pyyaml/JSON), no heavy deps.

    Refreshed OUT-OF-BAND by an optional tool that runs azure-ai-evaluation;
    the runtime only reads the cached data file, keeping imports pyyaml-only.
    """
    data_path: Path
    def fetch_record(self, model_id: str, region: str) -> QualitySafetyRecord:
        # load+cache the benchmark file; on missing file / parse error / no match:
        #   raise DependencyUnavailableError(...)
        ...
```

Notes:

* The benchmark file is keyed by `model_id` (family-level), because candidates are not deployed and per-region live eval is infeasible at recommend time. Scores are already normalized to 0..1 so the client returns final values, keeping the enrichment step arithmetic trivial.
* A future variant can call `az rest`/`urllib` against an official benchmark or Foundry evaluation results endpoint, still returning the same `QualitySafetyRecord` and still raising `DependencyUnavailableError` on failure — the enrichment does not change.

### 3.3 New enrichment: `enrich_quality_safety`

```python
# src/recommender/quality_safety_enrichment.py (design sketch)
def enrich_quality_safety(
    target: RetiringTarget,
    candidates: list[CatalogCandidate],
    qs_client: QualitySafetyBenchmarkSource,
) -> tuple[list[CatalogCandidate], list[str]]:
    warnings: list[str] = []
    cache: dict[str, QualitySafetyRecord | None] = {}
    enriched: list[CatalogCandidate] = []
    for candidate in candidates:  # preserve input order
        record = cache.get(candidate.model_id, _SENTINEL)
        if record is _SENTINEL:
            try:
                record = qs_client.fetch_record(candidate.model_id, candidate.region)
            except DependencyUnavailableError as error:
                record = None
                warnings.append(
                    f"quality/safety eval unavailable for '{candidate.model_id}': {error}"
                )
            cache[candidate.model_id] = record
        if record is None:
            # keep the existing 0.9 placeholder values already on the candidate
            enriched.append(replace(candidate))
            warnings.append(
                f"quality/safety not found for {candidate.model_id}; using catalog scores"
            )
            continue
        enriched.append(
            replace(candidate, quality_score=record.quality_score, safety_score=record.safety_score)
        )
    return enriched, warnings
```

Behavioral parity with pricing: injected client, per-model cache, only `DependencyUnavailableError` caught, copy-on-return, warnings returned, placeholder retained on miss.

### 3.4 Service wiring

Add an optional client param to `recommend_candidates` and run it alongside pricing (after filtering, before scoring):

```python
def recommend_candidates(
    config, run_context, target, catalog,
    price_client: RetailPricesClient | None = None,
    qs_client: QualitySafetyBenchmarkSource | None = None,   # NEW
) -> RecommenderResult:
    ...
    qs_warnings: list[str] = []
    if qs_client is not None:
        candidates, qs_warnings = enrich_quality_safety(target, candidates, qs_client)
    # combine into parse_warnings alongside pricing_warnings
```

Orchestrator injection mirrors the pricing boundary (`pipeline.py:267-273`), constructing the client only under `_should_use_official_sources(config, runtime_options)`; otherwise `qs_client=None` preserves the hermetic default (placeholders). Warnings merge into the serialized `parse_warnings`.

### 3.5 Hermetic testability

Follow `tests/unit/test_pricing_enrichment.py`: a structural `_FakeQualitySafetyClient` with a `fetch_record` matching the production signature, configured to return records for some models and raise `DependencyUnavailableError` for others. Assert: enriched scores replace placeholders; missing model retains 0.9 and emits a warning; a dependency failure does not escape and preserves 0.9; returned candidate differs by identity from input; and the warning appears in `RecommenderResult.parse_warnings` (mirroring `test_recommender_service.py`).

---

## 4. Dependency Decision

**Constraint:** runtime deps are `pyyaml` only; the repo deliberately uses az CLI (subprocess) + stdlib `urllib` and avoids heavy Azure SDKs. `azure-ai-evaluation` (and especially the `[redteam]` extra pulling PyRIT/promptflow/openai) is a large transitive footprint and cannot be a runtime import.

### 4.1 Options

| Option | Runtime import surface | Fits not-yet-deployed candidates? | Risk |
|--------|------------------------|-----------------------------------|------|
| A. Cached benchmark data file (pyyaml/JSON), read via `QualitySafetyBenchmarkSource` | pyyaml + stdlib only | Yes — scores keyed by model_id, no live endpoint needed | Low |
| B. `az rest` / `urllib` to a Foundry evaluation results or benchmark REST endpoint | stdlib only | Partial — requires an existing evaluation run/results; still no live per-candidate eval | Medium (API shape, auth, no clean public endpoint for arbitrary model quality) |
| C. Optional `azure-ai-evaluation` extra behind a feature flag, guarded import, `DependencyUnavailableError` fallback | Heavy when extra installed | No for live scoring (candidates undeployed); usable only to *generate* the cache offline | High online; acceptable offline |
| D. RedTeam/PyRIT online | Very heavy | No | Very high |

### 4.2 Recommendation

**Primary: Option A (cached benchmark file), refreshed out-of-band by Option C behind an optional `[evaluation]` extra.**

* Runtime stays pyyaml-only; the recommender reads `config/quality_safety_benchmarks.yaml` (or similar) via stdlib+pyyaml and raises `DependencyUnavailableError` on missing/parse/no-match, giving the exact non-fatal fallback to the current 0.9 placeholder.
* The heavy `azure-ai-evaluation[redteam]` work lives in an **optional, out-of-band refresh script** installed via a new `[project.optional-dependencies] evaluation = ["azure-ai-evaluation[redteam]>=1.0.0", ...]` extra (the repo already has a `test` extra, so the mechanism exists). That script runs offline against a reference deployment, computes the §2 mappings, and writes the cache file. It never imports into the recommender runtime.
* RedTeam/PyRIT stays **offline/precomputed only** (Option D is rejected for online use). Safety scores come from cached content-safety defect rates and/or precomputed adversarial ASR.

Tradeoffs: cached scores can go stale (mitigated by a `provenance`/date field and a refresh cadence); they are family-level rather than per-deployment (acceptable because candidates are undeployed); Option B remains a future upgrade path that swaps only the client internals, not the enrichment contract.

---

## 5. Phased Plan (with not-yet-deployed caveat)

**Core caveat:** ARM catalog candidates are catalog entries, not deployed endpoints. Live `evaluate()` and RedTeam `scan()` both require a reachable deployed model/`/chat` target. Therefore online per-candidate scoring at recommend time is infeasible. Scoring must be either (a) **cached benchmark scores** keyed by model_id, or (b) computed **post-provisioning** against the actual deployment. Phases below use cached scores at recommend time and treat live eval as an offline producer.

### Phase 0 — Data contract + cache format (no runtime deps)
* Define `config/quality_safety_benchmarks.yaml` schema: `model_id`, `quality_score` (0..1), `safety_score` (0..1), `provenance`, `as_of_date`, optional per-evaluator breakdown.
* Seed with a small curated set derived from the §2 mapping (can start from published model/benchmark data). Validates the mapping end-to-end with zero heavy deps.

### Phase 1 — Quality enrichment (cached, online-safe)
* Implement `QualitySafetyBenchmarkSource` + `enrich_quality_safety`, wire into `recommend_candidates` and the orchestrator injection boundary under `_should_use_official_sources`.
* Populate `quality_score` from cached normalized quality means; leave `safety_score` at placeholder if safety data absent (partial enrichment is allowed — warn per missing dimension).
* Hermetic tests as in §3.5. Runtime remains pyyaml-only.
* "Needs a deployed endpoint" note: none at recommend time; the cache is the input. A separate optional refresh tool (behind `[evaluation]`) regenerates the cache offline against a reference deployment.

### Phase 2 — Safety enrichment (content-safety + redteam, offline/cached)
* Extend the cache with `safety_score` from content-safety defect rates (`1 - defect_rate`) and/or precomputed adversarial ASR (`1 - ASR`), combined via conservative `min`.
* RedTeam/PyRIT runs strictly offline in the `[evaluation]` refresh tool; never online. Cache stores the resulting per-model safety numbers.
* Add `provenance`/`as_of_date` surfacing so stale safety data can be flagged as a `parse_warning`.

### Phase 3 (optional, future) — Post-provisioning / live upgrade
* If a reference or post-provisioned deployment becomes available, add an alternate client (Option B `az rest`/`urllib`, or the optional SDK) that returns the same `QualitySafetyRecord`, swapping client internals only. Enrichment, service wiring, and tests are unchanged.

---

## 6. Open Questions, Risks, Deferred Items

Open questions:

* Which authoritative benchmark backs the cache initially, and what is its model_id/region coverage vs. the ARM catalog? (Follow-on from subagent report.)
* Independent quality/safety dimensions vs. a single blended source record — recommended independent so partial enrichment and per-dimension warnings work.
* Warning granularity for missing data: source-level, per-model, per-dimension. Recommended: per-model + per-dimension.
* Severity threshold `T` for the content-safety defect definition (proposed `T = 4` on 0-7) and whether to weight or `min` when both safety signals exist.

Risks:

* Cache staleness / provenance drift — mitigate with `as_of_date` and a documented refresh cadence + staleness warning.
* Family-level (not per-deployment) scores may misrepresent a specific deployment config — acceptable given undeployed candidates; revisit in Phase 3.
* Reference repo's own safety wiring is partially mismatched (no numeric ASR, `content_safety`→`safety` gate gap); do not copy its aggregation verbatim — use the §2 mapping instead.
* Optional `[evaluation]` extra footprint (azure-ai-evaluation[redteam] + transitive PyRIT) must never leak into runtime imports; enforce with a guarded import boundary in the offline tool only.

Deferred:

* Live/post-provisioning evaluation (Phase 3).
* Telemetry emission of quality/safety scores (reference repo's OpenTelemetry `ce.score.*` pattern) — out of scope for the recommender enrichment.
* Any RedTeam online scanning.

---

## Research Executed

### File Analysis (this repo, via subagent)

* src/recommender/arm_catalog_source.py:83-97 — placeholder `quality_score=0.9`, `safety_score=0.9`, `cost_score=0.8` in `_to_candidate`.
* src/recommender/models.py:11-33 — `CatalogCandidate` float score fields default 0.0, no clamp.
* src/recommender/scorer.py:18-35 — weighted sum with quality/safety/cost weights (0.5/0.3/0.2 from config/recommender.yaml).
* src/recommender/pricing_enrichment.py:54-58,74-123 — `enrich_cost_scores` canonical pattern (injected client, cache, non-fatal `DependencyUnavailableError`, `dataclasses.replace`, warnings return).
* src/recommender/service.py:17-23,39-43,54-57 — `recommend_candidates` injection point and `parse_warnings` propagation.
* src/recommender/pricing_source.py:24-110 — `RetailPricesClient` urllib source raising `DependencyUnavailableError`.
* src/shared/az_cli.py:39-73 — `run_az(args, *, timeout=None) -> str` subprocess helper.
* src/shared/errors.py:6-18 — `DependencyUnavailableError`.
* src/shared/config.py:55-75,109-225 — `use_official_sources`, `RuntimeOptions` override, config load.
* src/orchestrator/pipeline.py:115-120,267-276 — `_should_use_official_sources` gate and client injection boundary.
* pyproject.toml:1-20 — runtime deps `pyyaml>=6.0` only; existing `[project.optional-dependencies] test`.
* tests/unit/test_pricing_enrichment.py, test_recommender_service.py, test_pricing_source.py — hermetic fake-client and patch patterns.

### External Research (reference repo, via subagent)

* raw.githubusercontent.com/sohamda/azure-ai-redteam-eval/main/src/continuous_evaluation/* — evaluator registry, `evaluate()` runner, metrics/thresholds, baseline.
* raw.githubusercontent.com/sohamda/azure-ai-redteam-eval/main/src/redteam/* — RedTeam SDK scan, custom probes, report.
* raw.githubusercontent.com/sohamda/azure-ai-redteam-eval/main/src/config.py and .env.example — credential/config contract.
* raw.githubusercontent.com/sohamda/azure-ai-redteam-eval/main/pyproject.toml + requirements.txt — dependency footprint.
* [Azure AI Evaluation SDK docs](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/evaluate-sdk) — evaluator identities, `evaluate()` shape, Foundry/model requirements.

## Potential Next Research

* Confirm the initial authoritative benchmark data source and its model/region coverage vs. the ARM catalog.
  * Reasoning: determines cache seed feasibility and coverage-gap warning rate.
  * Reference: subagent follow-on questions.
* Prototype the offline `[evaluation]` refresh tool contract (inputs: reference deployment; outputs: cache YAML).
  * Reasoning: validates the §2 mapping produces stable 0..1 scores before Phase 1 wiring.
  * Reference: §4.2, §5 Phase 0-2.
