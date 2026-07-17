# Squad Consumption Ledger

Estimated cost per dispatched role. All figures are **estimated, not billed**.

## Per-Role Consumption

| Role | Model | Tier | Input Tokens | Cached Tokens | Output Tokens | Est. Cost USD | Est. Credits |
|---|---|---|---|---|---|---|---|
| MVP Product/Tech Integrator | claude-3-5-sonnet | default | 8,500 | 0 | 2,200 | $0.0585 | 5.85 |
| Security/Identity + Governance Lead | claude-3-5-sonnet | default | 36,400 | 0 | 10,700 | $0.2697 | 26.97 |
| DevOps + IaC Engineer | claude-3-5-sonnet | default | 26,500 | 0 | 7,600 | $0.1935 | 19.35 |
| Python Delivery Lead (Core pipeline) | claude-3-haiku | tier-1 | 46,200 | 0 | 14,300 | $0.3432 | 34.32 |
| Evaluation + Quality Engineer | claude-3-5-sonnet | default | 15,700 | 0 | 5,400 | $0.1281 | 12.81 |
| Squad Scribe | claude-3-haiku | tier-1 | 18,600 | 0 | 5,650 | $0.03748 | 3.748 |
| Squad Azure Readiness Validator | claude-3-haiku | tier-1 | 3,200 | 0 | 1,100 | $0.00520 | 0.520 |
| Squad Deployer (Cleanup Ops) | tier-1 | fast | 400 | 0 | 150 | $0.00104 | 0.104 |
| **Run Total** | | | **155,600** | **0** | **47,100** | **$1.03434** | **103.434** |

## Cost Comparison

**Squad dispatch total**: $0.9357 (93.569 credits)

**Baseline single-model iteration** (1-hour interactive, 1 human + 1 tier-1 agent): ~$0.32 (32 credits)

**Squad efficiency vs. baseline**: 263% of baseline cost (estimated, not billed) — 25 dispatches, 6 roles executing TG1/TG2/TG3/TG4 parallel foundation + infrastructure + CI/CD + governance + core pipeline (slices 1–4) + quality validation

---

**Note**: All token counts and cost estimates are for planning purposes only. Actual costs depend on live API billing. Cached token rates apply only when the SDK returns non-zero `cache_read_input_tokens`.

