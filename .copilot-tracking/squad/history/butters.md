<!-- markdownlint-disable-file -->
# Butters TG3 Execution Notes

## 2026-07-15T02:00:00Z Dispatch: TG3 CI/CD Foundation Implementation (Task Implementor)

**Agent**: Task Implementor  
**Request**: Execute Task Group 3 (CI/CD and Delivery Automation) foundation slice—workflow scaffolding, run-context bootstrap, OIDC-ready permissions, and safe cleanup placeholders.

**Outcome**: ✓ Complete

**Artifacts Delivered**:
- `.github/workflows/ci.yml` — Build, test, lint, publish matrix for Python, TypeScript, infrastructure
- `.github/workflows/detect-and-eval.yml` — Continuous evaluation loop: detect changes, spin up eval environment, run validation, promote on pass
- `.github/workflows/sweep-orphans.yml` — Resource cleanup: orphaned Azure resources, stale branches, cost control triggers
- `config/models.yaml` — Model registry, model tier definitions, provider endpoints, fallback chains
- `config/evaluation.yaml` — Evaluation suite definitions, dataset references, scorer configurations, pass/fail thresholds
- `config/recommender.yaml` — Recommendation engine parameters, ranking weights, promotion gates, notification rules
- `config/azure.env.example` — Resource naming, principal IDs, endpoint overrides (shared with TG2)
- `docs/oidc-setup.md` — OIDC federation, Workload Identity Federation configuration (shared with TG2)
- `docs/setup-guide.md` — Deployment walkthrough, prerequisites, variable binding (shared with TG2)
- `docs/troubleshooting.md` — Common errors, remediation steps (shared with TG2)

**Validation Status**:
- ✓ YAML syntax: clean, schema validated
- ✓ OIDC permissions: surfaces ready for federation
- ✓ Docs: diagnostics clean, markdown lint pass
- ⚠ End-to-end Azure execution: deferred pending TG2 infrastructure readiness

**Consumption Block**:
- Model: claude-3-5-sonnet
- Model Tier: default
- Input Tokens: 7,200
- Cached Tokens: 0
- Output Tokens: 2,100
- Input Rate: $3.00 per 1M
- Cached Rate: $0.30 per 1M
- Output Rate: $15.00 per 1M
- Est. Cost USD: $0.0531
- Est. Credits: 5.31
- Basis: estimated

---

## 2026-07-15T03:00:00Z Dispatch: TG3 Workflow Finalization (Task Implementor)

**Agent**: Task Implementor  
**Request**: Execute Task Group 3 CI/CD workflow finalization—enforce run-context contract, finalize cleanup metadata, tighten orphan cleanup tagging, update docs for governance alignment.

**Outcome**: ✓ Complete

---

## 2026-07-23T00:00:00Z Dispatch: Workflow GH-Variable Verification After Tenant/Subscription Change (Task Researcher)

**Agent**: Task Researcher  
**Member Name**: Butters  
**Role**: DevOps + IaC Engineer  
**Model Tier**: fast (tier-default estimate)  

**Request**: Read-only verification of workflow GH-variable surface after tenant/subscription change (2026-07-22). Live gh (authed as sohamda) and az (authed to new subscription) available; no mutations. Produce variable classification table (repo vars vs. needed vars), live diff (repo vars on OLD env vs. new env), and OIDC re-establishment finding as critical-path blocker.

**Outcome**: ✓ Complete

**Findings Delivered**:
- Variable classification table: 14+ vars across 2 workflows, split into Group A (direct updates to new values), Group B (requires provisioning in new sub), and unset vars (FOUNDRY_PROJECT_ENDPOINT, JUDGE_MODEL)
- Live diff: repo Variables still entirely on OLD environment (tenant `16b3c013…`, sub `3b250d66…`); local az CLI is on NEW env
- OIDC re-establishment finding: federated credential bound to OLD-tenant app registration cannot be moved; NEW-tenant app registration required with explicit federated credential subject + issuer + audience + least-privilege RBAC on new sub/RG
- Commands-only remediation block: no config/IaC changes proposed; user-gated escalation recommended
- Security domain escalation: Kyle (Security/Identity Lead) needed for app reg + federated credential + RBAC creation

**Verification Status**: Read-only, no mutations, auto-tier autonomy

**Consumption Block**:
- Model: claude-3-haiku (tier-default, fast)
- Model Tier: fast
- Input Tokens: 5,200
- Cached Tokens: 0
- Output Tokens: 2,600
- Input Rate: $0.80 per 1M
- Cached Rate: $0.08 per 1M
- Output Rate: $4.00 per 1M
- Est. Cost USD: 0.01560
- Est. Credits: 1.560
- Basis: tier-default

**Artifacts Delivered**:
- `.github/workflows/ci.yml` — Stronger run-context bootstrap validation, compile matrix hardening
- `.github/workflows/detect-and-eval.yml` — Finalized finalize/cleanup metadata behavior, tighter orchestration gates, promotion decision enforcement
- `.github/workflows/sweep-orphans.yml` — Hardened orphan cleanup with resource tagging rules (AUTOMATION_CLEANUP_TAG, MANAGED_BY_TAG), stale-detection window enforcement
- `config/azure.env.example` — Resource naming finalized, tag binding consistency validated
- `docs/setup-guide.md` — Deployment procedure with governance/TG2 contract callouts
- `docs/oidc-setup.md` — OIDC federation contract, Workload Identity Federation governance alignment
- `docs/troubleshooting.md` — Governance-aware error remediation, compliance-layer troubleshooting

**Validation Status**:
- ✓ YAML syntax: all workflows and config files parse clean
- ✓ Contract assertions: run-context, cleanup metadata, orphan tagging rules all pass validation suite
- ✓ Docs: markdown lint pass, governance contract references validated
- ✓ Corrupted files: cleaned and re-validated
- ⚠ End-to-end Azure orchestration: deferred pending TG2 infrastructure readiness (governance modules wired)

**Consumption Block**:
- Model: claude-3-5-sonnet
- Model Tier: default
- Input Tokens: 6,500
- Cached Tokens: 0
- Output Tokens: 1,900
- Input Rate: $3.00 per 1M
- Cached Rate: $0.30 per 1M
- Output Rate: $15.00 per 1M
- Est. Cost USD: $0.0480
- Est. Credits: 4.80
- Basis: estimated

---

## 2026-07-15T14:30:00Z Dispatch: TG3 Local Foundation Completion Push (Task Implementor)

**Agent**: Task Implementor  
**Request**: Complete TG3 (CI/CD and Delivery Automation) locally-fixable surfaces; validate all workflows, configs, and scripts; tighten run-context contract; finalize shared config envelope; checkpoint before TG4 core pipeline entry. Defer Azure-live execution evidence and TG4/TG5 runtime integration.

**Outcome**: ✓ Complete

**Artifacts Delivered**:
- `.github/workflows/ci.yml` — Tightened compile matrix, hardened run-context bootstrap validation, finalized build/test/lint stages
- `.github/workflows/detect-and-eval.yml` — Finalized continuous evaluation loop, promotion gates, orchestration metadata enforcement
- `.github/workflows/sweep-orphans.yml` — Hardened orphan cleanup with resource tagging rules (AUTOMATION_CLEANUP_TAG, MANAGED_BY_TAG), stale-detection window enforcement
- `scripts/validate_tg3_contracts.py` — Completed contract validator script with full TG2 handoff contract schema support
- `config/models.yaml` — Finalized model registry, tier definitions, provider endpoints, fallback chains
- `config/evaluation.yaml` — Finalized evaluation suite definitions, dataset references, scorer configurations, thresholds
- `config/recommender.yaml` — Finalized recommendation engine parameters, ranking weights, promotion gates, notification rules
- `config/azure.env.example` — Finalized shared resource naming envelope (coordinated with TG2), principal ID placeholders
- `docs/oidc-setup.md` — Finalized OIDC federation contract, Workload Identity Federation governance alignment (shared with TG2)
- `docs/setup-guide.md` — Finalized deployment procedure with governance/TG2 contract callouts (shared with TG2)
- Input Rate: $3.00 per 1M
- Cached Rate: $0.30 per 1M
- Output Rate: $15.00 per 1M
- Est. Cost USD: $0.0531
- Est. Credits: 5.31
- Basis: estimated

---

## 2026-07-23T22:00:00Z Dispatch: Provisioning Plan-Only Analysis (PLAN-ONLY, No Azure Mutations)

**Agent**: Task Implementor (role: DevOps + IaC Engineer)  
**Member Name**: Butters  
**Request**: "PLAN-ONLY provisioning of ACA/Storage/KV for live-eval; verify existing Bicep, add bicepparam, local build, gated apply command."

**Outcome**: ✓ PLAN-ONLY (no mutations)

**Key Deliverables**:
- Verified all 4 missing resources covered by existing Bicep modules (container-apps, storage, keyvault, rbac)
- Created `infra/main.bicepparam` (working-tree only) for instance 003, targeting swedencentral / ai-resources / 84b82c4c-… sub
- Local `az bicep build` → **PASS** (exit 0); full template syntax validated
- Flagged two architectural blockers (private-network runner reachability + monolith vs. wire to ff-hub-01)
- Provided gated what-if / apply commands (user approval required)
- Rough cost estimate: ~$30–45/mo (dominated by 4 private endpoints + DNS zones)

**Critical Findings**:
- **BLOCKER #1 (HIGH)**: ACA/Storage/KV all private (internal:true, publicNetworkAccess=Disabled) → GitHub-hosted runner cannot reach. Requires self-hosted runner in VNet or ACA job execution pattern.
- **BLOCKER #2 (MEDIUM)**: Monolith creates NEW Foundry fnd-mua-dev-003, not wiring to existing ff-hub-01. GitHub vars point to ff-hub-01; RBAC points to new Foundry. Mismatch requires refactoring main.bicep.

**Artifacts** (working-tree only):
- `infra/main.bicepparam` — instance 003 parameters
- `.copilot-tracking/changes/2026-07-23/butters-provisioning-plan-only-analysis.md` — analysis memo

**Next**: Architecture council decision (Cartman + Kyle) on runner path + Foundry scope before provisioning apply.

**Consumption Block**:
- Model: claude-3-5-sonnet
- Model Tier: default
- Input Tokens: 7,000
- Cached Tokens: 0
- Output Tokens: 3,600
- Input Rate: $3.00 per 1M
- Cached Rate: $0.30 per 1M
- Output Rate: $15.00 per 1M
- Est. Cost USD: 0.075
- Est. Credits: 7.5
- Basis: tier-default
