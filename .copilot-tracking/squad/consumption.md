# Squad Consumption Ledger

Estimated cost per dispatched role. All figures are **estimated, not billed**.

## Per-Role Consumption

| Role | Model | Tier | Input Tokens | Cached Tokens | Output Tokens | Est. Cost USD | Est. Credits |
|---|---|---|---|---|---|---|---|
| MVP Product/Tech Integrator | claude-3-5-sonnet | default | 8,500 | 0 | 2,200 | $0.0585 | 5.85 |
| Security/Identity + Governance Lead | claude-3-5-sonnet | default | 36,400 | 0 | 10,700 | $0.2697 | 26.97 |
| DevOps + IaC Engineer | claude-3-5-sonnet | default | 26,500 | 0 | 7,600 | $0.1935 | 19.35 |
| Python Delivery Lead (Core pipeline) | claude-3-haiku | tier-1 | 46,200 | 0 | 14,300 | $0.3432 | 34.32 |
| Evaluation + Quality Engineer | mixed (default + tier-1) | default / tier-1 | 18,700 | 0 | 6,200 | $0.1337 | 13.37 |
| Platform Reliability + SRE Lead | claude-3-haiku | tier-1 | 8,700 | 0 | 3,900 | $0.0226 | 2.26 |
| Squad Scribe | claude-3-haiku | tier-1 | 18,600 | 0 | 5,650 | $0.03748 | 3.748 |
| Squad Azure Readiness Validator | claude-3-haiku | tier-1 | 3,200 | 0 | 1,100 | $0.00520 | 0.520 |
| Squad Deployer (Cleanup Ops) | tier-1 | fast | 400 | 0 | 150 | $0.00104 | 0.104 |
| Task Implementor (TG8/TG9 Final) | claude-3-haiku | fast | 4,500 | 0 | 1,200 | $0.0084 | 0.84 |
| Task Researcher (gpt-4.1 Analysis) | claude-3-haiku | tier-1 | 2,200 | 0 | 1,100 | $0.00616 | 0.616 |
| Task Planner: Live-Mode Planning | claude-3-5-sonnet | default | 2,600 | 0 | 1,500 | $0.0303 | 3.03 |
| Squad Azure Architect: Live-Mode Architecture | claude-3-5-sonnet | default | 2,100 | 0 | 1,200 | $0.0243 | 2.43 |
| Task Researcher: Live-Mode Gap Audit | claude-3-haiku | tier-1 | 2,300 | 0 | 1,300 | $0.00704 | 0.704 |
| Task Implementor: Live-Mode Execution | claude-3-5-sonnet | default | 5,200 | 0 | 3,200 | $0.0636 | 6.36 |
| **Run Total** | | | **188,400** | **0** | **62,300** | **$1.25194** | **125.194** |

## Cost Comparison

**Squad dispatch total**: $1.12670 → $1.25194 (+$0.12524 this turn)

**Baseline single-model iteration** (1-hour interactive, 1 human + 1 tier-1 agent): ~$0.32 (32 credits)

**Squad efficiency vs. baseline**: 391% of baseline cost (estimated, not billed) — 41 dispatches, 6 roster roles + 8 specialized subagents executing TG1–TG9 phases (foundation → infrastructure → CI/CD → core-pipeline → evaluation → reporting → reliability → quality-gates → release-readiness, plus live-mode core-pipeline transition)

---

**Note**: All token counts and cost estimates are for planning purposes only. Actual costs depend on live API billing. Cached token rates apply only when the SDK returns non-zero `cache_read_input_tokens`.

