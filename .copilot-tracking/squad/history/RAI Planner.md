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

---

## Council Dispatch: Live-Backed Eval Runners RAI Assessment (2026-07-23)

**Council Verdict Topic**: live-backed-eval-runners

**Request**: 
Assess RAI/evaluation posture for live-backed evaluation runners (LiveCustomRunner, LiveRedTeamRunner). Current stubbed evaluators (Decision #50) are fake-backed with simulated scores; live variants will invoke real azure-ai-evaluation with real LLM-as-judge and red-team adversarial scoring. Risk: Scorer that looks authoritative but inherits the stub's false-safe behavior (emitting PASS with zero actual measurement). Evaluate:
- Quality scoring design (independent judge, versioned rubric, relative-to-retiring comparison)
- Red-team data (separate versioned hashed probe set, multiple attack categories, safety classifier + judge)
- Anti-regression (poison canary, discrimination canary, ban constant returns)
- Auditability (raw prompts, raw responses, judge rationale, scorer versions, dataset SHA-256)
- Human-in-the-loop gate (no auto-promotion until conditions proven)

**Findings**:

**Verdict**: Conditional / HIGH risk (Proceed ONLY if conditions met)

**Danger Assessment**: Shipping a scorer that looks real but inherits the stub's false-safe behavior is the specific danger. The stubbed evaluators emit authoritative PASS with zero actual measurement—this is a material maturity gap. Framework: NIST AI RMF 1.0 (Measure/Manage). Intent is correct and necessary; risk is in execution.

**Binding Conditions**:
1. Quality scoring: LLM-as-judge with PUBLISHED VERSIONED RUBRIC via SEPARATE INDEPENDENT judge deployment (never candidate or its family—o3 not grading o3, gpt-5.1 not grading gpt-5.1)
2. Score retiring model on same dataset so gate is RELATIVE (candidate ≥ retiring − ε), not absolute threshold
3. Judge temperature=0, blind/randomize response ordering, persist raw responses + judge rationale per item
4. Red-team: SEPARATE VERSIONED HASHED adversarial probe set (5 categories: jailbreak/instruction-override, harmful-content elicitation, PII extraction, prompt-injection/indirect, TOS/CoC-violating; 5-10 probes per category floor)
5. Safety classifier (deterministic, independent) as best primary signal; independent judge model acceptable but not candidate; keyword heuristics rejected as sole judge
6. COMBINE classifier+judge; disagreement → not blocked (fail-closed on ambiguity)
7. Define "blocked" = explicit refusal OR safe non-compliance; fail-closed on ambiguity
8. REMOVE hard-coded nano/jailbreak rule entirely (condition for safety classifier)
9. Poison canary: probe healthy model MUST refuse—if candidate complies, FAIL gate
10. Discrimination canary: known-bad reference must score below threshold every run; if not, scorer broken → FAIL gate
11. Ban constant returns: block_rate==1.0 or identical custom_overall across candidates → suspicious-uniformity flag
12. Never default-pass on error: timeout/empty/parse-fail → FAIL/ABSTAIN, never PASS
13. Auditability: persist raw prompts (QA+red-team), raw responses, judge/classifier rationale per item, scorer/judge version+deployment ID+temp+rubric version, dataset SHA-256 for both sets, thresholds in effect, computed scores, per-item pass/fail, retiring-model baseline, decision+authorizer+timestamp
14. Human-in-the-loop gate for auto-promotion: NO auto-promotion until conditions 1-13 have track record in production. Runner may RECOMMEND; qualified human confirms swap with full audit bundle
15. Use relative-to-retiring comparison (not absolute threshold) in gate logic

**Residual Risk**: Signal interpretation (false-positives in adversarial scoring), model-tuning feedback loops (if signals inform retraining without human review). Mitigated by conditions 9-12 (anti-regression canaries) + explicit provenance stamps (condition 13) + threshold versioning + human gate (condition 14).

**RAI Advisory**: This is an RAI advisory, not a compliance sign-off. Intent is correct and necessary; danger is material. A qualified human must review any automated model-swap decision.

**Decision Ref**: `.copilot-tracking/squad/decisions.md#decision-51-council-verdict-live-backed-eval-runners--go-with-conditions-rai-high-risk-caveat-reuse-validated-quality_safety_eval_client-seam-no-auto-promotion-until-judgeprobe-setcanaries-proven--2026-07-23`

---

**Consumption** (this dispatch):
- model: unknown
- model_tier: tier-1
- input_tokens: 2500
- cached_tokens: 0
- output_tokens: 1500
- input_rate: 0.80
- cached_rate: 0.08
- output_rate: 4.00
- est_cost_usd: 0.008
- est_credits: 0.8
- basis: tier-default
