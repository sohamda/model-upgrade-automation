# Security Planner History

## Council Dispatch: WI-01/WI-02 Foundry Eval Wiring + Phase 2 + CI Refresh (2026-07-22)

**Council Verdict Topic**: wi-01-wi-02-foundry-eval

**Request**: 
Assess security posture for WI-01 live Foundry quality/safety eval client wiring (azure.ai.evaluation + azure.identity) inside Phase 2 quality/safety service implementation + WI-02 scheduled CI refresh workflow. Evaluate:
- Azure credential handling (DefaultAzureCredential, no API keys)
- Endpoint and secret logging (sanitization, no stderr echoing)
- RedTeam artifact containment (git-ignored storage)
- CI/CD auth patterns (OIDC/federated, not secrets)
- Git commit safety (file allowlist, exclusions for .env/token cache)

**Findings**:

**Verdict**: Go-With-Conditions / Medium risk

**Credential Assessment**: DefaultAzureCredential + no API key/connection string acceptance is the correct pattern. No embedded secrets required. Risk is operational (scope isolation, endpoint validation, logging hygiene).

**Binding Conditions**:
1. Endpoint as config not hardcoded; placeholder in `config/azure.env.example`
2. No API key/connection string accepted as CLI arg or env var
3. No endpoint/token/credential logging; sanitize `DependencyUnavailableError` (do NOT echo stderr like run_az style)
4. RedTeam artifacts (prompts, traces) only under git-ignored `results/`, `artifacts/`, or temp directories
5. WI-02 CI: OIDC/federated auth only, `AZURE_*` as vars (not secrets)
6. PR commits ONLY `config/quality_safety_benchmarks.yaml` (gated behind opt-in var)
7. Commit step uses explicit file allowlist (never `git add -A`); verify `.env`/token cache/`results/` excluded

**Residual Risk**: Logging hygiene (must audit all imports for credential leakage), CI scope creep (schedule-triggered vs. manual dispatch gating). Defer to Cost Manager for AZURE_* var scope validation. All conditions are enforceable via code review + test coverage.

**Decision Ref**: `.copilot-tracking/squad/decisions.md#council-verdict-2026-07-22-wi-01-wi-02-foundry-eval`

---

**Consumption** (this dispatch):
- model: claude-3-5-sonnet
- model_tier: default
- input_tokens: 14000
- cached_tokens: 0
- output_tokens: 6000
- input_rate: 3.00
- cached_rate: 0.30
- output_rate: 15.00
- est_cost_usd: 0.132
- est_credits: 13.2
- basis: tier-default

---

## Council Dispatch: WI-03 Live Quality/Safety Evaluation Harness + Golden Dataset (2026-07-22)

**Council Verdict Topic**: wi-03-quality-safety-harness-dataset

**Request**: 
Assess security posture for WI-03 live quality/content-safety evaluation harness (response-provider seam, golden dataset threading, provider construction gating). Evaluate:
- Response-provider credential/config handling (DefaultAzureCredential, no hardcoded keys/endpoints)
- Provider seam endpoint injection (config-sourced, no hardcoding)
- Dataset hygiene (benign-only contract, load from git-tracked JSONL)
- Error message sanitization (no endpoint/credential leakage)
- Scope isolation (assert_owned_target before provider invocation)
- Test coverage (hermetic, no live provider calls except when --live explicitly gated)

**Findings**:

**Verdict**: Go-With-Conditions / Medium risk

**Credential Assessment**: No API key or connection string required for response-provider pattern. Endpoint and model_id pass through caller (config-sourced, not hardcoded). Risk is containment (error messages, transient response handling).

**Binding Conditions**:
1. Response-provider seam: no hardcoded endpoint; provider constructed and invoked only inside --live gate
2. DefaultAzureCredential used for live Foundry calls (if needed within provider body); no static keys
3. No endpoint/credential/error-message logging; sanitize exceptions (do NOT echo stderr)
4. Golden dataset: benign-only JSONL; load via load_jsonl_dataset from git-tracked file; validate rows are benign QA only
5. Responses transient locals; never persisted/logged/committed to repo
6. assert_owned_target enforcement before any provider call; scope lock prevents third-party endpoint usage
7. Hermetic tests confirm --live gate gates provider invocation (no live calls in clean env)
8. New inference SDK (live provider) isolated to [evaluation] optional extra; lazy-imported, not on hot path

**Residual Risk**: Operational/containment (error message hygiene, transient response handling, dataset poisoning). All conditions are enforceable via code review + test coverage.

**Decision Ref**: `.copilot-tracking/squad/decisions.md#council-verdict-2026-07-22-wi-03-quality-safety-harness-dataset`

---

**Consumption** (this dispatch):
- model: claude-3-5-sonnet
- model_tier: default
- input_tokens: 8000
- cached_tokens: 0
- output_tokens: 3000
- input_rate: 3.00
- cached_rate: 0.30
- output_rate: 15.00
- est_cost_usd: 0.069
- est_credits: 6.9
- basis: tier-default
