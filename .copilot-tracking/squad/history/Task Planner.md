# Task Planner Dispatch History

## Dispatch 2026-07-23: Council-Mandated Plan for Live-Backed + Promotion-Grade Eval Runners

**Date**: 2026-07-23  
**Role**: Task Planner  
**Dispatch ID**: TG-plan-live-eval-runners-d52  

**Task**: Produce the council-mandated plan of record for live-backed + promotion-grade eval runners (Council Verdict Decision #51).

**Plan Output**: `.copilot-tracking/plans/2026-07-23/real-quality-safety-gates-plan.instructions.md`  
**Details Artifact**: `.copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md`  
**Log Artifact**: `.copilot-tracking/plans/logs/2026-07-23/real-quality-safety-gates-log.md`

**Plan Structure** (3 Phases + Conditions Tracing):

### Phase 1: Live-Backed Runners (10 Steps)
1. Import-guarded `aoai_client.py` with keyless `DefaultAzureCredential` provider
2. `LiveCustomRunner` delegation to validated `quality_safety_eval_client.py` seam
3. `LiveRedTeamRunner` delegation to validated `quality_safety_eval_client.py` seam
4. `--live` / `MUA_EVAL_MODE` opt-in with fakes as default
5. Independent judge deployment wiring (blocked by PD-01)
6. Capability-driven o3/gpt-5.1 model shape selection
7. Resilience and retry logic for live inference
8. Redaction of sensitive values in live outputs
9. Advisory flag threaded through reporter for live runs
10. Trace all steps to conditions C1-C10

### Phase 2: Promotion-Grade Gate (7 Steps)
1. Versioned SHA-256 adversarial probe set (5 categories)
2. Classifier-primary fail-closed block with nano rule removal (blocked by PD-01)
3. Relative-to-retiring gate comparison logic
4. Poison/discrimination/uniformity canaries
5. Per-run auditability bundle creation
6. Human-in-the-loop gate integration
7. Trace all steps to conditions C11-C13

### Phase 3: Test Strategy + Validation (3 Steps)
1. Fakes-injected unit tests (no CI credentials required)
2. Opt-in live check behind STOP-AND-GATE
3. Validation evidence bundle

**Conditions Tracing**: All 13 conditions (C1-C13) from Council Verdict Decision #51 are traced to specific implementation steps above.

**Plan Validation**: Plan Validator returned **Pass** (no Critical/High findings).

**Open Decision PD-01** (blocking Phase 2 Step 1.2 and Phase 1 Step 1.5):  
Independent judge deployment + safety classifier — two options pending user answer:
- **Option A** (recommended): Dedicated pinned non-candidate judge deployment + Azure AI Content Safety
- **Option B**: Reuse existing non-candidate deployment as judge + azure-ai-evaluation RedTeam classifier

**Binding STOP-AND-GATE** (from Decision #51 + plan record):
- **Authorized**: Implementation of code/commit/workflow scaffolding
- **HARD STOP**: Any LIVE Foundry execution (live inference/judging) requires:
  - Explicit user cost acknowledgment (no cost-manager seat currently wired into CI)
  - Confirmation that 13 conditions (C1-C13) and human gate hold

**Follow-On Work Items Surfaced**:
- WI-01: Extend attack strategies beyond current 5 categories
- WI-02: Add gold answers for groundedness evaluation
- WI-03: Auto-promotion after track record (Phase 2 post-launch)
- WI-04: CI wiring for opt-in live path (Phase 1 integration)

**Status**: Plan complete; awaiting PD-01 answer before Kenny dispatch for Phase 1/2 implementation. Code/scaffolding implementation authorized; live Foundry judging remains hard-STOP pending cost acknowledgment + condition confirmation.

**Consumption Block**:
| Field | Value |
|-------|-------|
| model | claude-3-5-sonnet |
| model_tier | default |
| input_tokens | 5000 |
| cached_tokens | 0 |
| output_tokens | 2200 |
| input_rate | 3.00 |
| cached_rate | 0.30 |
| output_rate | 15.00 |
| est_cost_usd | 0.048 |
| est_credits | 4.8 |
| basis | tier-default |
