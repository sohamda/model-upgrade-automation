# Task Researcher Dispatch History

## Dispatch 1: gpt-4.1 Retirement Alternatives Analysis (2026-07-17T20:30:00Z)

**Request**: Analyze repo design for gpt-4.1 retirement signaling, alternative ranking, and integration opportunities within GitHub Actions workflows.

**Context**:
- User query: "gpt-4.1 is retiring, how can I use this repo to find the alternative"
- Classification: Core pipeline / Detector / Recommender / Orchestrator
- Resolved role: Python Delivery Lead (Core pipeline)
- Autonomy: confirm

**Findings**:

- **Fixture-backed CLI design**: Repository supports local CLI combining retirement-signal YAML + curated candidate-catalog YAML, then ranks alternatives with cost analysis.
  - Entry point: `python -m src.orchestrator.cli --repo-root . --fixture <signal-yaml> --catalog <catalog-yaml> --run-id <id>`
  - Output: `artifacts/<run-id>/recommender.json`

- **Live automation gap**: No live Foundry retirement schedule or regional availability/catalog retrieval implemented yet. Current design requires external curation of signal and catalog YAMLs.

- **GitHub Actions integration gap**: Detect-and-eval workflow validates config/OIDC/artifact lifecycle only; does NOT invoke recommender engine. CLI and workflow designed to be decoupled; recommender invocation must be added to workflow.

- **Required configuration files**:
  - `config/models.yaml` — Watch model/deployment status
  - `config/evaluation.yaml` — Horizon window and candidate count limits
  - `config/recommender.yaml` — Ranking filters and scoring weights

- **Output structure**: Recommender produces ranked candidate list with feasibility scores, cost projections, and regional deployment viability in `artifacts/<run-id>/recommender.json`.

**Recommendations**:
1. Extend detect-and-eval workflow to conditionally invoke recommender when retirement signal detected
2. Add Foundry API integration to retrieve live retirement schedule and regional availability
3. Implement curated candidate catalog refresh from Foundry model catalog API
4. Add recommender output to GitHub issue or PR template for stakeholder visibility

**Research Artifact**: `.copilot-tracking/research/2026-07-17/gpt-41-retirement-alternatives-research.md`

**Status**: ✓ Complete

---

## Consumption Block

| Field | Value |
|---|---|
| model | claude-3-haiku |
| model_tier | tier-1 |
| input_tokens | 2200 |
| cached_tokens | 0 |
| output_tokens | 1100 |
| input_rate | 0.80 |
| cached_rate | 0.00 |
| output_rate | 4.00 |
| est_cost_usd | 0.00616 |
| est_credits | 0.616 |
| basis | tier-1 |

---

## Dispatch 2: Runtime API Usage Audit (2026-07-20T00:00:00Z)

**Request**: Audit actual runtime API usage in detector, recommender, and orchestrator against declared official-source configuration and requirements/plan.md. Classify findings by category: currently used, declared but not used, fallback behavior verification.

**Context**:
- User query: "Are APIs beyond docs scraping actually used?"
- Classification: Core pipeline / Detector / Recommender / Orchestrator
- Resolved role: Python Delivery Lead (Core pipeline)
- Autonomy: confirm

**Findings**:

**APIs Currently Used in Production Runtime**:
1. **Raw markdown retirement schedule** — `https://raw.githubusercontent.com/microsoft/foundry-docs/main/docs/model-retirement-schedule.md`
   - Location: `src/detector/retirement_schedule_source.py` (live_retirement_source)
   - Invocation: When `config/models.yaml` has `sources.official.enabled: true` (default)
   - Fallback: Loads fixture retirement signals on failure (network error, auth failure, timeout)

2. **Raw markdown models-sold-directly catalog** — `https://raw.githubusercontent.com/microsoft/foundry-docs/main/docs/model-catalog.json`
   - Location: `src/recommender/foundry_catalog_source.py` (live_catalog_source)
   - Invocation: When `config/models.yaml` has `sources.official.enabled: true` (default)
   - Fallback: Loads fixture candidate catalog on failure

3. **Azure Container Apps Deployments API** — ARM/Azure SDK (opt-in)
   - Location: `src/provisioner/provisioning_service.py` (ACA job submission)
   - Invocation: Only when `--provision-candidates` CLI flag is active; default is dry-run
   - Safety: Non-mutating by default; explicit opt-in for actual deployment

**APIs Declared in requirements/plan.md but Not Implemented**:
1. **ARM Models API** — Would supplement Foundry retirement discovery; not integrated
2. **Azure OpenAI data-plane models API** — Would provide real-time deployment status; not integrated
3. **Azure Retail Prices API** — Would provide live cost data; not integrated; hardcoded projections used instead
4. **HuggingFace model API** — Would supplement Foundry model catalog; not integrated
5. **HuggingFace leaderboard API** — Would provide community benchmarks; not integrated
6. **Azure Resource SKUs API** — Would validate ACA instance sizing constraints; not integrated

**Official-Source Configuration Status**:
- **Default active**: `config/models.yaml` has `sources.official.enabled: true`
- **Fallback enabled**: `sources.override_fixtures_on_failure: true` in config
- **Runtime wiring**: `src/orchestrator/pipeline.py` instantiates live sources as primary
- **Fallback safety**: Try-catch blocks in both source classes; exception logging on fallback
- **Unit test validation**: ✓ 8 tests pass covering official-source activation, fallback behavior, and fixture fallback

**Non-Used Detection Results**:
- Dead code check: No unused imports of declared APIs in active code paths
- Configuration references: All declared APIs are missing from actual source instantiation
- Conclusion: Declared-but-unused APIs are genuinely unimplemented (not dead code in active modules)

**Recommendations**:
1. **No blocking action** — Current runtime correctly uses official-source with fallback; MVP functional
2. **Documentation**: Update architecture docs to clarify current API surface (live markdown endpoints) vs. future (ARM, Retail Prices, etc.)
3. **Future roadmap**: Implement declared-but-unused APIs as optional enrichment layers if business value justifies
4. **Observability**: Consider alerting on repeated fallback events (signal of upstream availability issues)

**Status**: ✓ Complete

## Consumption Block

| Field | Value |
|---|---|
| model | claude-3-haiku |
| model_tier | fast |
| input_tokens | 3200 |
| cached_tokens | 0 |
| output_tokens | 1400 |
| input_rate | 0.80 |
| cached_rate | 0.00 |
| output_rate | 4.00 |
| est_cost_usd | 0.00816 |
| est_credits | 0.816 |
| basis | tier-default |
| input_rate | 0.80 |
| cached_rate | 0.08 |
| output_rate | 4.00 |
| est_cost_usd | 0.00616 |
| est_credits | 0.616 |
| basis | estimated |

---

## Dispatch 2: Core Pipeline Live-Mode Implementation Gap Audit (2026-07-17T21:45:00Z)

**Request**: Audit fixture-only core pipeline implementation against live-mode execution requirements; identify code surface gaps for Foundry discovery, live catalog fetch, provisioning, and evaluation; recommend implementation order and coverage strategy.

**Context**: Task Planner (Kenny) generated live-mode plan. Squad Azure Architect (Cartman) designed target Azure architecture and Foundry integration. Task Implementor (Kenny) will execute 4-phase implementation. This dispatch: validate plan completeness, identify code-level gaps, and assess implementation risk.

**Gap Analysis**:

*Detector Service Gaps*:
- **Live retirement source**: Currently accepts only YAML fixture. Gap: Foundry API integration missing (Microsoft.AI SDK wrapper required).
- **Source abstraction**: Interface already supports polymorphism; no refactoring needed. Risk: Low.
- **Foundry auth**: OIDC token acquisition already in `src/shared/azure_auth.py`. Reuse available.

*Recommender Service Gaps*:
- **Live catalog source**: Currently loads static YAML. Gap: Foundry model-catalog API fetch missing. Must query regional availability and cost metadata.
- **Catalog abstraction**: Interface already supports polymorphism. Recommend: implement `FoundryCatalogSource` as parallel track.
- **Risk**: Medium (new Foundry API dependency; API versioning unknown).

*Provisioner Service Gaps*:
- **Provisioning execution**: Service exists (TG4 slice 3). Gap: ACA job trigger and status polling missing.
- **Deployment artifacts**: Candidate packaging (container images or model weights) not yet specified. Recommend: clarify with Squad Azure Architect.
- **Risk**: High (dependency on ACA job API; state tracking complexity).

*Orchestrator Integration Gaps*:
- **CLI flags**: Detector, recommender, provisioner already CLI-wired. Gap: New flags (`--discover-from-azure`, `--provision-candidates`, `--run-evals`) not yet added.
- **Safety gate**: CLI logic required to enforce eval requires provisioning. Risk: Low (pure logic).
- **Workflow wiring**: `.github/workflows/detect-and-eval.yml` does NOT invoke orchestrator today. Gap: workflow needs conditional recommender invocation + artifact handling.
- **Risk**: Medium (workflow orchestration complexity; multiple gate conditions).

*Evaluation Integration Gaps*:
- **Evaluator placement**: TG5 evaluation engine already supports local-first testing. Gap: live ACA trigger and poll pattern not yet defined.
- **Status tracking**: History package can record evaluation invocation. Recommend: extend manifest to capture provision status + eval invocation timestamp.
- **Risk**: Medium (ACA async polling + timeout recovery post-MVP).

*Known Limitations*:
- ACA provisioning assumes standardized container image format (not yet specified in docs).
- Evaluation assumes ACA job runner availability (fallback to local evaluator if unavailable — MVP acceptable, production hardening deferred).
- Foundry API versioning not yet pinned; recommend: document API version constraint in requirements.txt.

**Recommendations**:
1. Implement detector live source (Foundry schedule query) first; low risk, validates OIDC integration.
2. Implement recommender live source (catalog fetch) second; medium risk; model regional metadata fetch may require API redesign.
3. Implement provisioning execution (ACA job trigger); high risk; recommend: detailed ACA API review with Squad Azure Architect before implementation.
4. Implement orchestrator wiring and CLI flags last; medium risk; guard against eval-without-provision at gate-check time.
5. Defer ACA failure-mode recovery (timeout, retry, fallback) to post-delivery phase.

**Implementation Artifact**: `.copilot-tracking/squad/core-pipeline-live-mode-gap-audit.md`

**Status**: ✓ Complete

---

## Consumption Block

```
model: claude-3-haiku
model_tier: tier-1
input_tokens: 2300
cached_tokens: 0
output_tokens: 1300
input_rate: 0.80
cached_rate: 0.08
output_rate: 4.00
est_cost_usd: 0.00704
est_credits: 0.704
basis: estimated
```

