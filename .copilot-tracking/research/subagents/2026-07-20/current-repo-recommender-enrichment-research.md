---
title: Current Repository Recommender Enrichment Research
ms.date: 2026-07-20
ms.topic: research
---

<!-- markdownlint-disable-file -->

## Research Scope

Investigate the current workspace recommender subsystem to define a quality and safety
signal enrichment step that mirrors the existing pricing enrichment implementation.

Questions:

* Where are `quality_score=0.9` and `safety_score=0.9` assigned?
* What is the complete `CatalogCandidate` and ranked/recommendation result contract?
* How are the scoring weights and ranking calculated?
* How does `recommend_candidates` sequence pricing enrichment and propagate warnings?
* What are the concrete source, error, configuration, dependency, and test seams that a
  quality and safety enrichment should mirror?

## Evidence Log

### Placeholder Location

`src/recommender/arm_catalog_source.py:83-97` creates each ARM-derived candidate in
`ArmModelsCatalogSource._to_candidate(self, entry: dict, location: str) ->
CatalogCandidate | None`. The placeholder-bearing portion is:

```python
return CatalogCandidate(
  model_id=name,
  version=str(version) if version is not None else "unspecified",
  region=location,
  deployment_types=deployment_types,
  workloads=["general_qa"],
  replacement_families=[],
  # quality_score/safety_score are heuristic placeholders pending a
  # real benchmark/eval source; they are intentionally uniform so as
  # not to imply fabricated per-model quality differences.
  quality_score=0.9,
  safety_score=0.9,
  cost_score=0.8,
)
```

`load(self) -> list[CatalogCandidate]` at `src/recommender/arm_catalog_source.py:99-121`
loops locations, fetches entries, calls `_to_candidate`, deduplicates by `(model_id,
version, region)`, and raises `DependencyUnavailableError` if no candidates remain.

### Contracts

`src/recommender/models.py:11-33` defines the full local candidate contract:

```python
@dataclass(slots=True)
class CatalogCandidate:
  model_id: str
  version: str
  region: str
  deployment_types: list[str]
  workloads: list[str]
  replacement_families: list[str] = field(default_factory=list)
  quality_score: float = 0.0
  safety_score: float = 0.0
  cost_score: float = 0.0
```

The score fields have no dataclass validation or clamp. Cost is documented as `0..1`,
higher-is-better at `src/recommender/pricing_enrichment.py:3-16`; quality and safety
are consumed identically as weighted numeric inputs at `src/recommender/scorer.py:20-31`.
`to_candidate(self) -> Candidate` at `src/recommender/models.py:25-33` copies only
the model identity, version, region, and deployment types into the downstream shape.

`src/shared/contracts.py:54-61` defines:

```python
@dataclass(slots=True)
class CandidateRank:
  candidate: Candidate
  score: float
  rationale: list[str] = field(default_factory=list)
  rejection_reasons: list[str] = field(default_factory=list)
```

`src/recommender/models.py:36-40` returns `RecommenderResult` with
`ranked_candidates: list[CandidateRank] = field(default_factory=list)` and
`parse_warnings: list[str] = field(default_factory=list)`.

### Scoring and Ranking

`validate_weights(config: AppConfig) -> None` at `src/recommender/scorer.py:10-15`
requires `sum(config.recommender.weights.values())` to be within `1e-9` of `1.0`.
`score_candidate(target: RetiringTarget, candidate: CatalogCandidate, config:
AppConfig) -> CandidateRank` at `src/recommender/scorer.py:18-35` discards `target`,
gets `quality`, `safety`, and `cost` weights with a `0.0` default, and calculates:

```python
score = (
  candidate.quality_score * quality_weight
  + candidate.safety_score * safety_weight
  + candidate.cost_score * cost_weight
)
```

It rounds the score to six decimals and includes three formatted rationale strings.
`config/recommender.yaml:1-7` sets `quality: 0.5`, `safety: 0.3`, and `cost: 0.2`.
`recommend_candidates` sorts at `src/recommender/service.py:45-52` by descending
score, then ascending `model_id`, `version`, and `region`, before applying the
candidate limit at line 54.

### Canonical Enrichment Pattern

The public pricing function is `enrich_cost_scores(target: RetiringTarget,
candidates: list[CatalogCandidate], price_client: RetailPricesClient) ->
tuple[list[CatalogCandidate], list[str]]` at
`src/recommender/pricing_enrichment.py:54-58`.

It creates `warnings`, `price_cache`, and `fetch_failed` at lines 74-76. Its nested
`_prices_for(region: str) -> list[dict] | None` caches successful calls and is
non-fatal only for `DependencyUnavailableError` at lines 78-89:

```python
try:
  prices = price_client.fetch_prices(region)
except DependencyUnavailableError as error:
  fetch_failed.add(region)
  warnings.append(f"pricing unavailable for region '{region}': {error}")
  return None
price_cache[region] = prices
return prices
```

It fetches the retiring model price once (lines 91-95), then iterates candidates in
input order (lines 97-123). When both prices are available and the retiring price is
positive, lines 107-112 calculate `delta = (retiring_price - candidate_price) /
retiring_price`, clamp `0.5 + 0.5 * delta` to `0.0..1.0`, round it to six decimals,
and append `dataclasses.replace(candidate, cost_score=...)`. Missing data appends
`pricing not found for {candidate.model_id}; using catalog cost_score` and a plain
`dataclasses.replace(candidate)` at lines 114-118. It returns `(enriched, warnings)`
at line 123: inputs are never mutated.

`_input_price(model_id: str, prices: list[dict], client: RetailPricesClient) ->
float | None` at `src/recommender/pricing_enrichment.py:29-51` searches a derived
`"{token} Inp"` SKU name, then a bare token. Quality/safety lookup semantics may
differ, but the injected-client, copy-on-return, warning-return contract is canonical.

### Service Wiring and Gating

The exact entry point at `src/recommender/service.py:17-23` is:

```python
def recommend_candidates(
  config: AppConfig,
  run_context: RunContext,
  target: RetiringTarget,
  catalog: CandidateCatalog,
  price_client: RetailPricesClient | None = None,
) -> RecommenderResult:
```

It validates weights and translates `ValueError` to `ConfigurationError` (lines 32-35),
loads and filters candidates (line 37), then invokes pricing after filtering and
before scoring (lines 39-43):

```python
pricing_warnings: list[str] = []
if price_client is not None:
  candidates, pricing_warnings = enrich_cost_scores(
    target, candidates, price_client
  )
```

Lines 54-57 assign `list(pricing_warnings)` to `RecommenderResult.parse_warnings`.
Lines 58-61 append the no-candidates warning afterward.

The enrichment module does not read `use_official_sources`. The upstream gate is
`_should_use_official_sources(config: AppConfig, runtime: RuntimeOptions) -> bool` at
`src/orchestrator/pipeline.py:115-120`: `runtime.live_catalog` wins, then a non-None
runtime override, then `config.use_official_sources`. The orchestrator injects the
pricing client under this gate at `src/orchestrator/pipeline.py:267-273`:

```python
price_client = (
  RetailPricesClient()
  if _should_use_official_sources(config, runtime_options)
  else None
)
```

It calls `recommend_candidates(..., price_client=price_client)` at lines 274-276 and
serializes `list(recommended.parse_warnings)` at lines 292-296. A quality/safety
client should be constructed at this injection boundary under the same gate.

### Pricing Source and Error Contract

`src/recommender/pricing_source.py:24-110` defines
`@dataclass(slots=True) class RetailPricesClient` with `timeout_seconds: int = 20`.
It uses standard-library `urllib`, not az CLI or an SDK:

* `_fetch_json(self, url: str) -> dict` at lines 29-50 creates `Request` and uses
  `urlopen(request, timeout=self.timeout_seconds)`; `URLError`, invalid JSON, and a
  non-dictionary top-level response become `DependencyUnavailableError`
* `fetch_prices(self, region: str, api_version: str = "2023-01-01-preview") ->
  list[dict]` at lines 52-82 filters public Azure Retail Prices data for Azure OpenAI
  consumption in the ARM region, follows `NextPageLink`, combines dictionary `Items`,
  and raises on an empty first top-level payload
* `unit_price_for(self, meter_id: str | None, sku_name: str | None, prices:
  list[dict]) -> float | None` at lines 84-110 chooses exact `meterId`, then
  case-insensitive `skuName` substring matches, and returns `None` when unmatched

There is no formal protocol or injected fetcher constructor parameter. Tests use
either structural fake clients passed to enrichment/service or patch `_fetch_json`.

The ARM catalog instead calls `run_az` at `src/recommender/arm_catalog_source.py:33-43`.
`src/shared/az_cli.py:39-73` defines `run_az(args: list[str], *, timeout: int | None
= None) -> str`. It resolves `az` with `shutil.which` through `resolve_az()` at
lines 20-36, runs `subprocess.run([az_path, *args], capture_output=True, text=True,
check=True, timeout=timeout)` at lines 55-61, never uses a shell or SDK, maps missing
CLI/non-zero exit/timeout to `DependencyUnavailableError`, and returns stdout.

`src/shared/errors.py:6-18` declares `PipelineError`, `ConfigurationError`,
`ContractError`, and:

```python
class DependencyUnavailableError(PipelineError):
  """Raised when an optional upstream dependency cannot be reached."""
```

### Configuration and Dependency Constraint

`AppConfig.use_official_sources: bool` is at `src/shared/config.py:55-63`; the
runtime override `RuntimeOptions.use_official_sources: bool | None = None` is at
lines 67-75. `load_app_config(repo_root: Path) -> AppConfig` at lines 109-225 uses
`yaml.safe_load`, reads `config/azure.env.example`, overlays process environment
values, and sets `use_official_sources=bool(models_data.get("use_official_sources",
True))` at line 224. `config/models.yaml:1` currently sets it to `true`.

`AzureEnvironmentConfig` at `src/shared/config.py:35-53` includes client ID, tenant
ID, subscription ID, resource names, deployment type, `allowed_regions`, run limits,
and tags. `AZURE_SUBSCRIPTION_ID` maps at lines 178-180; `ALLOWED_REGIONS` maps to
`azure.allowed_regions` at lines 194-195. `config/azure.env.example:5-7` provides
the Azure identity keys and lines 19-22 define `ALLOWED_REGIONS=swedencentral` and
the operational defaults. `EvaluationConfig.allowed_regions` is separately loaded
at `src/shared/config.py:143-144`.

The full dependency declaration is `pyproject.toml:1-20`:

```toml
[project]
requires-python = ">=3.12"
dependencies = [
  "pyyaml>=6.0",
]

[project.optional-dependencies]
test = [
  "pytest>=7.4",
]
```

Runtime dependencies are PyYAML-only. The project already has an optional-dependency
mechanism, with a `test` extra; it has no source/enrichment optional extra.

### Hermetic Test Pattern

`tests/unit/test_pricing_enrichment.py:18-32` defines `_FakePriceClient` with
region-keyed fixture data, optional failing regions, and a real `RetailPricesClient`
delegate for `unit_price_for`. Its `fetch_prices` signature matches production and
raises `DependencyUnavailableError` for configured failures. The fake is passed
directly to `enrich_cost_scores` at lines 66, 80, 94, 107, 121, and 135. Tests prove:

* Cheaper, pricier, and equal-price candidates receive expected `cost_score` values
  at lines 59-98
* Missing prices preserve the static score and emit a warning at lines 101-112
* Dependency failures do not escape and preserve the static score at lines 115-124
* The returned candidate differs by identity from the unmutated input at lines 127-138

`tests/unit/test_recommender_service.py:74-88` repeats this structural fake pattern
and passes it as `price_client=price_client` at lines 115-117. Lines 124-129 assert
the pricing warning appears in `result.parse_warnings`; lines 132-158 confirm an
omitted client yields no pricing warnings. Source-unit tests patch the concrete client:
`tests/unit/test_pricing_source.py:38-49` uses
`patch.object(RetailPricesClient, "_fetch_json", side_effect=[_PAGE_ONE, _PAGE_TWO])`,
and lines 86-91 patch an empty payload then assert `DependencyUnavailableError`.

### Design Consequence

Create an injected quality/safety source client and a separate enrichment function
that accepts `RetiringTarget`, `list[CatalogCandidate]`, and that client. Cache source
calls as appropriate, catch only `DependencyUnavailableError`, return copied candidates
using `dataclasses.replace` with `quality_score` and `safety_score`, retain the static
`0.9` values when a signal is missing, and return warnings. Add an optional client to
`recommend_candidates`, invoke it after filtering and before scoring, combine its
warnings with pricing warnings in `parse_warnings`, and construct the real client in
`execute_dry_run` only when `_should_use_official_sources` resolves true. This preserves
hermetic fixture runs and the existing non-fatal degradation behavior.

## Follow-On Questions

* Select the authoritative quality and safety data source and confirm model-ID and
  regional coverage against the ARM catalog
* Decide whether the source provides independent quality/safety dimensions or a
  deterministic mapping into both scores
* Set the warning granularity for missing data: source/region, candidate, or both
