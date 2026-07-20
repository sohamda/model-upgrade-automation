# Squad Consumption Ledger

Estimated cost per dispatched role. All figures are **estimated, not billed**.

## Per-Role Consumption

| Role | Model | Tier | Input Tokens | Cached Tokens | Output Tokens | Est. Cost USD | Est. Credits |
|---|---|---|---|---|---|---|---|
| MVP Product/Tech Integrator | claude-3-5-sonnet | default | 8,500 | 0 | 2,200 | $0.0585 | 5.85 |
| Security/Identity + Governance Lead | claude-3-5-sonnet | default | 36,400 | 0 | 10,700 | $0.2697 | 26.97 |
| DevOps + IaC Engineer | claude-3-5-sonnet | default | 26,500 | 0 | 7,600 | $0.1935 | 19.35 |
| Python Delivery Lead (Core pipeline) | claude-3-5-sonnet | default | 72,900 | 0 | 24,700 | $0.5892 | 58.92 |
| Evaluation + Quality Engineer | mixed (default + tier-1) | default / tier-1 | 18,700 | 0 | 6,200 | $0.1337 | 13.37 |
| Platform Reliability + SRE Lead | claude-3-haiku | tier-1 | 8,700 | 0 | 3,900 | $0.0226 | 2.26 |
| Squad Scribe | claude-3-haiku | tier-1 | 27,500 | 0 | 8,950 | $0.05744 | 5.744 |
| Squad Azure Readiness Validator | claude-3-haiku | tier-1 | 3,200 | 0 | 1,100 | $0.00520 | 0.520 |
| Squad Deployer (Cleanup Ops) | tier-1 | fast | 400 | 0 | 150 | $0.00104 | 0.104 |
| Task Implementor (TG8/TG9 Final) | claude-3-5-sonnet | default | 15,300 | 0 | 7,400 | $0.1569 | 15.69 |
| Task Researcher (API Audit + gpt-4.1) | claude-3-haiku | tier-1 | 11,400 | 0 | 5,900 | $0.03212 | 3.212 |
| Task Planner: Live-Mode Planning | claude-3-5-sonnet | default | 2,600 | 0 | 1,500 | $0.0303 | 3.03 |
| Squad Azure Architect: Live-Mode Architecture | claude-3-5-sonnet | default | 2,100 | 0 | 1,200 | $0.0243 | 2.43 |
| Task Researcher: Live-Mode Gap Audit | claude-3-haiku | tier-1 | 2,300 | 0 | 1,300 | $0.00704 | 0.704 |
| Task Implementor: Live-Mode Execution | claude-3-5-sonnet | default | 5,200 | 0 | 3,200 | $0.0636 | 6.36 |
| Squad Scribe | claude-3-haiku | tier-1/fast | 27,900 | 0 | 9,150 | $0.05892 | 5.892 |
| **Run Total** | | | **244,400** | **0** | **95,100** | **$1.66496** | **166.496** |

## Cost Comparison

**Squad dispatch total**: $1.66496 → 166.496 credits (+$0.01952 this turn: task researcher quality/safety design research + scribe dispatch recording)

**Baseline single-model iteration** (1-hour interactive, 1 human + 1 tier-1 agent): ~$0.32 (32 credits)

**Squad efficiency vs. baseline**: 520% of baseline cost (estimated, not billed) — 54 dispatches, 6 roster roles + 8 specialized subagents executing TG1–TG9 phases plus live-mode core-pipeline transition, official-source activation, API audit, ARM Models + Retail Prices integration, and quality/safety scoring design research

---

**Note**: All token counts and cost estimates are for planning purposes only. Actual costs depend on live API billing. Cached token rates apply only when the SDK returns non-zero `cache_read_input_tokens`.



