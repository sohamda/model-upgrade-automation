# Squad Cost Manager History

## Council Dispatch: Infra Provisioning + Live Run Cost Assessment (2026-07-23)

**Council Verdict Topic**: infra-provisioning-live-run

**Request**: 
Assess cost posture for provisioning infra/main.bicep resources and executing full live detect-and-eval pipeline. Evaluate:
- Staged escalation cost breakdown (Stage 0 free / Stage 1 free / Stage 2 $50–150 / Stage 3 $100–300)
- Regional cost optimization (swedencentral vs. other EU regions)
- Idle-state cost floor (private-endpoints, storage baseline, Key Vault operations)
- Cost ceiling monitoring during Stages 2–3
- Sweeper cleanup automation to prevent orphan accumulation

**Findings**:

**Verdict**: Go-With-Conditions / Medium risk

**Staged Escalation Cost Analysis**: Cost-aware framework enabling progressive commitment with clear rollback points.

| Stage | Operation | Free? | Est. Cost | Duration | Rollback |
|---|---|---|---|---|---|
| 0 | Dry-run (fixture data, no Azure) | ✓ Yes | $0 | ~5 min | N/A |
| 1 | Live discovery + live_catalog (read-only) | ✓ Yes | $0 | ~10 min | N/A |
| 2 | Provision candidates (Foundry deployments) | ✗ No | $50–150 | ~30 min | Delete candidates + deployments |
| 3 | Run evals (quality + red-team probes) | ✗ No | $100–300 | ~2–4 hours | Clear storage; re-run with dry-run |
| **Total Run Cost** | | | **$150–450** | **~3–5 hours** | Staged rollback available |

**Cost Drivers**:
- **Stage 2 (Provisioning)**: Model deployment SKUs vary widely (gpt-4.1 cheaper than gpt-5.6-sol; exact cost TBD by SKU/hours active). Sweeper cleanup deletes after eval → cost contained.
- **Stage 3 (Evals)**: Quality judges (coherence/relevance/fluency) + red-team evaluation tokens. Cost scales with probe_count + model response tokens. Hermetic test path (dry-run) = $0.
- **Baseline Idle** (~$30–45/mo): Private-endpoints (~$20–25/mo), Storage LRS Hot (100 GB tier ~$1–2/mo), Key Vault operations (~$1–2/mo baseline), ACA scales to zero when not running.

**Regional Cost Optimization**: swedencentral pricing ~5–10% lower than westeurope/northeurope/eastus. Good regional choice for cost control. No change recommended.

**Cost Ceiling Monitoring**: Recommend Azure budget alert at $200 threshold before Stage 2 apply. Monitor daily during Stages 2–3. Hard stop if spending exceeds $200 (re-evaluate Stages 2–3 strategy).

**Binding Conditions**:
1. **Staging Discipline**: Execute in order (Stage 0 → 1 → 2 → 3); do not skip stages. Cost impact compounds if stages combined.
2. **Cost Ceiling**: Set Azure budget alert at $200 before Stage 2 provisioning apply. Monitor daily.
3. **Sweeper Cleanup Automation**: Sweeper workflow (sweep-orphans) enabled and tested before Stage 3. Hard stop if sweeper unhealthy (prevents orphan accumulation and runaway costs). Sweeper deletes tagged resources post-eval.
4. **Resource Tagging**: All new resources tagged with `Cleanup=auto` (sweeper recognizes and auto-deletes). Sweeper workflow verifies tags before deletion.
5. **Stage 3 Cost Cap**: If real-time cost tracking shows spending approaching $300, pause Stage 3 and re-evaluate probe count / model choice before continuing.
6. **Post-Eval Cleanup**: Manual cleanup of any eval artifacts (storage blobs, logs, manifests) if sweeper does not complete or tags missing.
7. **No Resource Resurrection**: Do NOT re-run Stage 2 or Stage 3 without completing sweeper cleanup first (orphans accumulate cost).
8. **Cost Reporting**: Document actual spend per stage in `.copilot-tracking/squad/cost-report-live-run-2026-07-23.md` for post-run analysis and future cost estimation tuning.

**Residual Risk**: Cost overrun if Stage 3 evaluation loops repeat without cleanup (sweeper failure + re-provision + re-eval = cost compounding). Mitigated by sweeper health check (hard stop) and daily cost monitoring.

**Decision Ref**: `.copilot-tracking/squad/decisions.md#council-verdict-2026-07-23-infra-provisioning-live-run`

---

**Consumption** (this dispatch):
- model: claude-3-5-sonnet
- model_tier: default
- input_tokens: 10000
- cached_tokens: 0
- output_tokens: 3500
- input_rate: 3.00
- cached_rate: 0.30
- output_rate: 15.00
- est_cost_usd: 0.083
- est_credits: 8.3
- basis: tier-default
