# RAI Planner History

## Council Dispatch: WI-01/WI-02 Foundry Eval Wiring + Phase 2 + CI Refresh (2026-07-22)

**Council Verdict Topic**: wi-01-wi-02-foundry-eval

**Request**: 
Assess RAI/evaluation posture for WI-01 live Foundry quality/safety eval client wiring (azure.ai.evaluation RedTeam) inside Phase 2 quality/safety service implementation + WI-02 scheduled CI refresh workflow. Evaluate:
- Scope lock (own-deployment-only, no third-party endpoints)
- Bounded execution (num_objectives, attack_strategies restrictions)
- Adversarial-content containment (no harmful prompt commits, aggregate signals only)
- Signal fidelity (missing vs. errored vs. observed-bad distinction)
- Thresholds and provenance (versioning, auditable entries, PII hygiene)

**Findings**:

**Verdict**: Go-With-Conditions / Medium risk

**Red-Teaming Legitimacy**: Red-teaming own models is a legitimate quality signal. Risk is **scope creep, signal leakage, and adversarial-content persistence**—not the red-teaming itself.

**Binding Conditions**:
1. Own-deployment-only scope lock on RedTeam target (refuse third-party endpoints)
2. Bounded gated out-of-band execution: pin `num_objectives`, restrict `attack_strategies` to `Baseline+Jailbreak` only
3. Adversarial-content containment: `skip_upload=True`, persist only aggregate numeric signals (ASR%, defect-rate), never commit harmful prompts
4. Distinguish missing/errored signal (→None/curated-seed fallback, NOT near-zero) from observed-bad
5. Add min-sample-size guard on defect-rate denominator (prevent noise amplification)
6. Explicit provenance-stamped thresholds: T=3, ASR convention, SDK version
7. Auditable entries: evaluators run, deployment, scan date, threshold, num_objectives/strategies, SDK version
8. Regulated-data hygiene on golden JSONL/prompt fixtures (no PII, no regulated content)

**Residual Risk**: Signal interpretation (false-positives in adversarial scoring), model-tuning feedback loops (if signals inform retraining without human review). Mitigated by min-sample-size guards + explicit provenance stamps + threshold versioning.

**Decision Ref**: `.copilot-tracking/squad/decisions.md#council-verdict-2026-07-22-wi-01-wi-02-foundry-eval`

---

**Consumption** (this dispatch):
- model: claude-3-5-sonnet
- model_tier: default
- input_tokens: 10000
- cached_tokens: 0
- output_tokens: 4500
- input_rate: 3.00
- cached_rate: 0.30
- output_rate: 15.00
- est_cost_usd: 0.0975
- est_credits: 9.75
- basis: tier-default
