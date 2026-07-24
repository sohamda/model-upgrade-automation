# Task Reviewer Dispatch History

## 2026-07-23: Independent Review — Live-Backed + Promotion-Grade Eval Gate Implementation vs Plan + 13 Council Conditions (Decision #51/#53)

**Dispatch Date**: 2026-07-23

**Role**: Task Reviewer (independent adversarial validation)

**Task**: Conduct independent re-validation of the live-backed + promotion-grade eval gate implementation against the implementation plan (Decision #52) and all 13 Council binding conditions (Decision #51/#53).

**Context**: Task Implementor (Kenny) completed Phase 1 + Phase 2 implementation offline (232 unit tests passed, no live Azure). Council Verdict (Decision #51) established 13 binding conditions across Architecture/Security/RAI perspectives. Reviewer role: independent adversarial check — zero assumptions, verify conditions satisfied, audit code safety, escalate findings.

**Verdict**: **CHANGES-REQUIRED**

### Findings Summary

**Criticality Breakdown**:
- **0 Critical** (no auto-promotion blockers, decision_engine verified short-circuits advisory→needs_human_review)
- **1 HIGH** (measurement false-safe on block_rate inflation)
- **3 Medium** (operational degradation paths)
- **2 Low** (data hygiene, edge-case coverage)
- **2 Nit** (cosmetic, wording)

### Finding Details

**HIGH (F1): Block-Rate False-Safe on PII/Injection/ToS Violation Detection**

Location: `src/evaluator/red_team_evaluator.py` — Azure AI Content Safety classifier

**The Problem**:
- Azure Content Safety API scores only 4 harm categories (hate, violence, sexual, self-harm)
- 3 of 5 probe categories (pii_extraction, prompt_injection, tos_coc_violation) are NOT scored by Content Safety
- For these 3 categories, the red-team judge (gpt-4.1) is sole authority
- BUT: When a COMPLIANT HARMFUL response is scored, the classifier returns True("blocked") BEFORE the judge runs
- Consequence: For pii/injection/tos probes, a COMPLIANT response can trigger a low-severity flag → True("blocked") → inflates block_rate
- **Measurement Impact**: block_rate metric on pii/injection/tos is INFLATED (false-safe) because the judge-derived component is missing
- **Decision Impact**: No — decision_engine short-circuits advisory→needs_human_review (verified in decision_engine.py); promotion never auto-runs

**Fix Recommendation**:
- Pass probe `category` into the classifier
- Return None/UNSCORED for pii/injection/tos so the judge is sole authority
- Judge-only path for these 3 categories ensures honest block_rate

**Medium (F2): Silent Degradation When CONTENT_SAFETY_ENDPOINT Unset**

Location: `src/evaluator/red_team_evaluator.py`

**The Problem**:
- When `CONTENT_SAFETY_ENDPOINT` is unset or missing, the code silently degrades to judge-only for the entire run
- No warning logged, no flag recorded in audit
- User has no visibility that Content Safety was unavailable
- **Consequence**: Reported block_rate is judge-derived only, no content-safety signal

**Fix Recommendation**:
- Emit warning when endpoint is unset: "CONTENT_SAFETY_ENDPOINT not set; running judge-only (no Content Safety scoring)"
- Record `classifier_available=false` in the audit RawEvalSignals to signal degradation
- Non-blocking (advisory gated), but user must know

**Medium (F3): Poison/Discrimination Canary Injection Missing at Runtime**

Location: `src/evaluator/live_red_team_runner.py`

**The Problem**:
- Poison/discrimination canaries exist as build-time unit tests only (`test_red_team_evaluator.py`)
- At eval time, the probe dataset does NOT include canary rows (uniform signal=expected, canary signal=false → assertion)
- Canary contract: inject 2 canary rows into live eval, assert expected_blocked=true
- **Consequence**: Runtime canaries don't run; only uniformity flag runs at eval time
- **Risk**: Build-time logic may pass; runtime logic may fail (no redundancy)

**Fix Recommendation**:
- Inject the 2 canary rows into `LiveRedTeamRunner` probe_prompts at eval time
- Assert expected_blocked for each canary row (poison_text and discrimination_text)
- Records runtime contract validation in audit

**Medium (F4): "Byte-Stable Default Summary" Claim Overstated**

Location: `src/evaluator/quality_safety_eval_client.py` docstring

**The Problem**:
- Docstring claims "byte-stable default summary"
- Actual behavior: default summary now always includes relative_gate and audit keys (additive, non-breaking, tested)
- Wording overstates stability (implies immutable; reality is additive-only evolution)

**Fix Recommendation**:
- Reword to "additive-stable default summary: new keys added only with backward-compatible defaults"
- Clarify that addition is non-breaking to schema consumers

**Low (F5): Redact Mapping Misses Common Key Patterns**

Location: `src/shared/logging.py` — redact_mapping dict

**The Problem**:
- Markers list: `password`, `secret`, `token`, `key` (current)
- Missing: `api_key`, `apikey`, `key_*` prefix patterns
- Low likelihood given keyless design (no keys in normal operation)
- But defensive hygiene would catch vendor-prefixed patterns (e.g., `openai_api_key`)

**Fix Recommendation**:
- Add `api_key`, `apikey` to markers
- Optionally: add regex pattern `key_.*` for prefix matching

**Low (F6): Edge Case — Derive_Safety_Score Returns 1.0 When Both Signals None**

Location: `src/evaluator/quality_safety_eval_client.py` — derive_safety_score()

**The Problem**:
- When both safety_score and asr_percent are None (unscored), function returns 1.0 (perfect safety)
- Semantics: None = unscored (not necessarily safe); 1.0 = maximum safety
- Pre-existing behavior (v1), non-blocking (advisory-gated)
- **Risk**: Overstates safety on unscored runs (false-safe)

**Fix Recommendation** (Deferred):
- Return None when both signals unscored (propagate uncertainty, not confidence)
- Or: return 0.5 (neutral), making the advisory decision explicit

**Nit (F7): Per-Row Scores Mirror Aggregate**

Location: `src/evaluator/quality_safety_eval_client.py`

**Observation**:
- Per-row coherence/relevance/fluency scores correctly aggregate to per-dim means
- Aggregate matches design (mean across rows, per dimension)
- No actionable issue, all tests pass

**Nit (F8): _Model_Family Split Over-Broad, Errs Safe**

Location: `src/recommender/recommendation_service.py` — model_family categorization

**Observation**:
- Classification splits model families broadly (e.g., "claude-family", "gpt-family")
- Some models assigned to over-broad families
- Over-broad → errs safe (more candidates eligible), acceptable for MVP
- Post-delivery refinement: narrow families per vendor roadmap

### Condition Checklist (13 Council Conditions)

| Condition | Status | Notes |
|-----------|--------|-------|
| C1: In-method imports + TYPE_CHECKING | ✓ PASS | Module-level imports gated; TYPE_CHECKING verified |
| C2: No hardcoded endpoint/judge; config-sourced | ✓ PASS | Endpoint + judge_model injected via constructor |
| C7: DefaultAzureCredential in-method; no logging | ✓ PASS | Credential created inside method; DependencyUnavailableError sanitized |
| C8: Aggregate-only signals (ASR %, defect-rate) | ✓ PASS | No raw prompts/responses committed; only numeric signals |
| C9: Own-deployment-only scope lock | ✓ PASS | assert_owned_target() rejects foreign endpoints |
| C10: Bounded execution (num_obj ≤20, strategies {Baseline,Jailbreak}) | ✓ PASS | Ceiling enforced; strategy set restricted |
| C11: UNSCORED→fallback, min-sample guard | ✓ PASS | None≠0; min-sample-size guard on defect_rate denominator |
| C12: Provenance stamp (T, ASR convention, SDK version) | ✓ PASS | Audit includes threshold, convention, evaluators_run, scan_date |
| C13: No auto-promotion (advisory-gated) | ✓ PASS | decision_engine verified short-circuits advisory→needs_human_review |
| C4: Scope-lock on owned target | ✓ PASS | (duplicate of C9 from Architecture perspective) |
| C5: Bounded gated out-of-band execution | ✓ PASS | (subsumed in C10) |
| C6: Audit entry content (evaluators_run, deployment, date, threshold) | ✓ PASS | RawEvalSignals includes all audit fields |
| C3: Distinct UNSCORED vs. near-zero | ✓ PASS | None used for unscored; fallback on error |

**All 13 Conditions PASS** with caveats on C6 (F5 low: redact markers incomplete) and C10 (F3 runtime-canary hardening).

### Auto-Promotion Path Verification

**Finding**: decision_engine.py verified — all auto-promotion paths are SHORT-CIRCUITED to advisory (needs_human_review).
- `config/promotion_thresholds.yaml` parsed but decision_engine rejects auto-promotion branches
- No path allows (quality ≥ T ∧ safety ≥ T) → auto-promote
- Everything routes through advisory

**Conclusion**: No auto-promotion blocker (C13 satisfied). HIGH finding (F1) is a measurement false-safe, NOT a promotion path vulnerability.

### Reviewer Guidance

**A LIVE ADVISORY RUN MAY PROCEED AS-IS IF**:
- Block_rate on pii/injection/tos is acknowledged as judge-derived only (Content Safety doesn't score these categories)
- Human-review checklist is hardened with this caveat

**F1 + F2 MUST BE FIXED before any PROMOTION decision consumes these numbers** because:
- F1 inflates block_rate (false-safe measurement)
- F2 silently degrades classifier availability (operator blind)
- If promotion logic ever enables auto-decisions (future), F1 would cause systematic over-blocking on these 3 categories

**Offline unit suite independently re-run**: 232 passed, 0 failed (verification timestamp 2026-07-23T14:22:00Z)

**Full review artifact**: `.copilot-tracking/reviews/2026-07-23/real-quality-safety-gates-plan-review.md`

### Consumption Block

**Model**: unknown (tier-default)  
**Model Tier**: tier-1 (claude-3-haiku)  
**Input Tokens**: 9000 (estimated)  
**Cached Tokens**: 0  
**Output Tokens**: 3500 (estimated)  
**Input Rate**: $0.80 (per MTok)  
**Cached Rate**: $0.08 (per MTok)  
**Output Rate**: $4.00 (per MTok)  
**Est. Cost USD**: 0.0360  
**Est. Credits**: 3.60  
**Basis**: tier-default
