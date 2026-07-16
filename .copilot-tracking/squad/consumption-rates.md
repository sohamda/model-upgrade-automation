# Squad Consumption Rates

Estimated token rates per AI model and tier, used to compute per-dispatch cost estimates. All figures are estimated based on tier placement, not billed amounts.

## Token Rates (estimated, not billed)

| Model Tier | Model | Input Rate (per 1M tokens) | Cached Rate (per 1M tokens) | Output Rate (per 1M tokens) |
|---|---|---|---|---|
| default | claude-3-5-sonnet | $3.00 | $0.30 | $15.00 |
| tier-2 | claude-3-opus | $15.00 | $1.50 | $75.00 |
| tier-1 | claude-3-haiku | $0.80 | $0.08 | $4.00 |

## Notes

- **Cached tokens** (prompt caching enabled): Applies only when SDK returns non-zero `cache_read_input_tokens`.
- **All figures are estimates**: Cost estimates in squad consumption ledgers are for planning purposes only. Azure usage billing and Anthropic invoice amounts are the source of truth.
- **Rate verification**: Rates in this table should be periodically verified against current pricing. Cells marked `<verify>` indicate rates that need confirmation.
- **Baseline single-model iteration**: Assumed 1-hour interactive session with 1 human + 1 agent tier-1 model (claude-3-haiku) at 30 min ramp-up + 30 min work, estimated 150k input tokens + 50k output tokens = ~($0.12 + $0.20) = $0.32.

