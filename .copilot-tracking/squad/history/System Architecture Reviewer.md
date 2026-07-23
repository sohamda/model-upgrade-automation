# System Architecture Reviewer History

## Council Dispatch: WI-01/WI-02 Foundry Eval Wiring + Phase 2 + CI Refresh (2026-07-22)

**Council Verdict Topic**: wi-01-wi-02-foundry-eval

**Request**: 
Assess architecture soundness for WI-01 live Foundry quality/safety eval client wiring (azure.ai.evaluation) inside Phase 2 quality/safety service implementation + WI-02 scheduled CI refresh workflow (detect-and-eval.yml sister workflow). Evaluate:
- Import guard patterns (optional-deps, TYPE_CHECKING)
- Endpoint injection/config sourcing (no hardcoding)
- Stub vs. live mode gating (--live flag, --dry-run Azure-free)
- Provenance contract preservation (additive scoring, YAML read-only)
- WI-02 workflow posture (OIDC, SHA-pinned, cost ceiling gating)

**Findings**:

**Verdict**: Go-With-Conditions / Medium risk

**Seam Assessment**: The architectural seam is sound. azure.ai.evaluation as an optional lightweight client (no managed endpoints required) fits cleanly into Phase 2 quality/safety service. Residual risk is operational/financial (cost, endpoint scope) not structural (API misalignment, dependency conflict).

**Binding Conditions**:
1. All `azure.ai.evaluation`/`azure.identity`/`RedTeam` imports inside method bodies or `TYPE_CHECKING` only; add guard test that import succeeds with `[evaluation]` uninstalled
2. No hardcoded endpoint or judge deployment; keep `azure_ai_project` field injected/config-sourced
3. Keep Stub as refresh default, gate live client behind explicit `--live` flag, `--dry-run` stays Azure-free
4. Preserve additive-provenance contract: emit normalized 0..1 scores, recommender stays read-only on YAML
5. WI-02 must clone detect-and-eval.yml posture (OIDC, SHA-pinned, persist-credentials:false, concurrency, opt-in var gate, scheduled defaults to stub/dry-run, live only on workflow_dispatch)
6. Add candidate/model cap + per-run cost ceiling before CI wiring

**Residual Risk**: Operational scope (Azure cost, judge deployment lifecycle, adversarial artifact containment). Defer to Security + RAI planners for boundary conditions. Architectural seam itself poses no structural risk.

**Decision Ref**: `.copilot-tracking/squad/decisions.md#council-verdict-2026-07-22-wi-01-wi-02-foundry-eval`

---

**Consumption** (this dispatch):
- model: claude-3-5-sonnet
- model_tier: default
- input_tokens: 12000
- cached_tokens: 0
- output_tokens: 5000
- input_rate: 3.00
- cached_rate: 0.30
- output_rate: 15.00
- est_cost_usd: 0.111
- est_credits: 11.1
- basis: tier-default

---

## Council Dispatch: WI-03 Live Quality/Safety Evaluation Harness + Golden Dataset (2026-07-22)

**Council Verdict Topic**: wi-03-quality-safety-harness-dataset

**Request**: 
Assess architecture soundness for WI-03 live quality/content-safety evaluation harness (response-provider seam, golden dataset, quality-evaluator surfacing, _run_quality/_run_content_safety bodies). Evaluate:
- Response-provider injection pattern (args: model_id, prompt), typing, containment
- Provider seam None handling (scan error vs. fabrication distinction)
- Zero-dep invariant preservation (module-level imports forbidden, lazy provider construction)
- Golden dataset coherence/relevance/fluency surfaces (groundedness dropped, no context fabrication)
- Error handling and row-level isolation (scope-lock, endpoint no-leak, UNSCORED-on-error distinction)
- Hermetic test coverage of _run_* bodies

**Findings**:

**Verdict**: Go-With-Conditions / Medium risk

**Seam Assessment**: The architectural seam is sound. Response-provider pattern (callable args: model_id, prompt) fits cleanly as injectable stub-or-live option. Lazy construction inside _select_client preserves zero-dep invariant. None-return-on-missing-provider correctly signals scan error (not fabrication). Residual risk is implementation detail (defensive error handling, row isolation).

**Binding Conditions**:
1. Response-provider typed via typing.Callable[[str, str], str | None] | None, default None
2. No inference SDK imports at module level; real provider constructed script-side inside --live only
3. Groundedness dropped to None under probe seam (string-only surface: coherence/relevance/fluency only)
4. Quality aggregation: per-dim mean over scored rows; errored rows skipped; all-None → None
5. Content-safety: per-row worst-of-4 severity >= threshold → flagged; return (flagged, total); return None only if zero rows scored
6. Defensive score extraction tolerating vendor-prefixed keys; non-numeric → errored for that row/dim
7. Row-level error isolation; UNSCORED-on-error distinction (never 0/near-zero on error)
8. Responses transient locals only; never logged/persisted/returned; no new RawEvalSignals fields
9. Golden dataset: ~20 benign general-QA rows, sha256-stable, load via load_jsonl_dataset
10. Hermetic tests directly on _run_* bodies, covering all scope-lock/error/falsehood paths
11. Any new inference SDK (live provider) isolated to [evaluation] optional extra, lazy-imported, gated under --live

**Residual Risk**: Implementation detail risk (error messaging leakage, row isolation boundaries). Architectural seam itself poses no structural risk.

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

---

## Council Dispatch: Infra Provisioning + Live Run (2026-07-23)

**Council Verdict Topic**: infra-provisioning-live-run

**Request**: 
Assess architecture soundness for provisioning infrastructure from infra/main.bicep (instance 003) and executing full live detect-and-eval pipeline. Evaluate:
- Monolith vs. wire-to-existing fork decision (new Foundry fnd-mua-dev-003 vs. existing ff-hub-01 binding)
- Private-network runner reachability (GitHub-hosted runner cannot reach private endpoints; self-hosted vs. ACA job vs. bastion)
- Resource composition and module scoping (43 resources, subscription-scope policies, capability for multi-region)
- ADR-readiness of design decisions (when should architecture forks be captured as formal ADRs)

**Findings**:

**Verdict**: Go-With-Conditions / Medium risk

**Architecture Assessment**: The monolith Bicep design is well-structured and comprehensive. Both identified architecture forks (Foundry scope + runner reachability) are valid paths with different trade-offs. Neither fork represents a structural API misalignment or scalability problem. Risk is organizational alignment (design intent clarity), not technical.

**Binding Conditions**:
1. **Architecture Decision #1 — Monolith Fork**: Resolve Foundry scope before apply — either Option A (refactor to wire existing ff-hub-01, preferred, reduces resource duplication) or Option B (deploy new fnd-mua-dev-003, accept duplication, update variables). Document decision + rationale.
2. **Architecture Decision #2 — Private-Network Runner**: Resolve runner reachability before Stage 2 provisioning — self-hosted runner in VNet (preferred, aligns with private-network design), ACA job with MI (asynchronous), or bastion/jump-box (operational complexity). Document decision + implementation plan.
3. **Module Composition**: Preserve hierarchical module structure (networking, monitoring, storage, keyvault, foundry, container-apps, rbac); no monolith flattening into single main.bicep resource list (would lose organization).
4. **Subscription-Scope Policies**: Document policy assignment scoping and exemption criteria (current: audit-only, non-blocking). Enforce in production via Policy initiative assignment at subscription scope with proper change control.
5. **ADR Capture**: Both architecture forks (#1, #2) warrant ADRs once decisions made — document context, options considered, decision, consequences, and when/how to revisit.
6. **Multi-Region Capability**: Current scoping (swedencentral only) is acceptable for MVP; future regions require variable parameterization (location list, per-region SKU variants, global load balancer). Defer to post-live-run hardening.

**Residual Risk**: Organizational alignment on design forks (not structural API risk). Both decision paths are sound; clarity required on which fork is chosen.

**Decision Ref**: `.copilot-tracking/squad/decisions.md#council-verdict-2026-07-23-infra-provisioning-live-run`

---

**Consumption** (this dispatch):
- model: claude-3-5-sonnet
- model_tier: default
- input_tokens: 12000
- cached_tokens: 0
- output_tokens: 4500
- input_rate: 3.00
- cached_rate: 0.30
- output_rate: 15.00
- est_cost_usd: 0.102
- est_credits: 10.2
- basis: tier-default
