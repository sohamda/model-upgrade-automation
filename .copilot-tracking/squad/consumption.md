# Squad Consumption Ledger

Estimated cost per dispatched role. All figures are **estimated, not billed**.

## Per-Role Consumption

| Role | Model | Tier | Input Tokens | Cached Tokens | Output Tokens | Est. Cost USD | Est. Credits |
|---|---|---|---|---|---|---|---|
| MVP Product/Tech Integrator | claude-3-5-sonnet | default | 8,500 | 0 | 2,200 | $0.0585 | 5.85 |
| Security/Identity + Governance Lead | claude-3-5-sonnet | default | 36,400 | 0 | 10,700 | $0.2697 | 26.97 |
| DevOps + IaC Engineer | claude-3-5-sonnet | default | 26,500 | 0 | 7,600 | $0.1935 | 19.35 |
| Python Delivery Lead (Core pipeline) | claude-3-5-sonnet | default | 44,200 | 0 | 13,800 | $0.3396 | 33.96 |
| Evaluation + Quality Engineer | claude-3-5-sonnet | default | 15,700 | 0 | 5,400 | $0.1281 | 12.81 |
| Squad Scribe | claude-3-haiku | tier-1 | 18,600 | 0 | 5,650 | $0.03748 | 3.748 |
| **Run Total** | | | **150,000** | **0** | **45,350** | **$1.0245** | **102.449** |

## Cost Comparison

**Squad dispatch total**: $0.9357 (93.569 credits)

**Baseline single-model iteration** (1-hour interactive, 1 human + 1 tier-1 agent): ~$0.32 (32 credits)

**Squad efficiency vs. baseline**: 263% of baseline cost (estimated, not billed) — 25 dispatches, 6 roles executing TG1/TG2/TG3/TG4 parallel foundation + infrastructure + CI/CD + governance + core pipeline (slices 1–4) + quality validation

---

**Note**: All token counts and cost estimates are for planning purposes only. Actual costs depend on live API billing. Cached token rates apply only when the SDK returns non-zero `cache_read_input_tokens`.

