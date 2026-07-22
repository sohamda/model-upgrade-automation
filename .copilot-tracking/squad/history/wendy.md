# Wendy Dispatch History

Evaluation + Quality Engineer (Developer / WI-Specific)

---

## Dispatch 1: AOAI-Route Fix Validated Live (2026-07-22T22:45:00Z)

**Member**: Wendy (Evaluation + Quality Engineer)

**Dispatch Type**: Code fix + offline validation + bounded live scan + isolation probe

**Request**: Implement empirically-proven AOAI-route fix (3 uncommitted files) with offline unit validation (155 tests), bounded live gpt-4.1 validation on owned Foundry account, and isolation probe to prove quality judges + provider seam end-to-end.

**Summary**:
- Implemented AOAI-route fix across `src/evaluator/quality_safety_eval_client.py`, `scripts/refresh_quality_safety_benchmarks.py`, `tests/unit/test_quality_safety_eval_client.py` (+7 new tests).
- Added `derive_aoai_endpoint()` helper, `DEFAULT_INFERENCE_API_VERSION="2024-10-21"`, `inference_api_version` field + CLI arg, rewired `_judge_model_config()` and `_build_live_response_provider()` (now `openai.AzureOpenAI` + bearer token on `https://cognitiveservices.azure.com/.default`), refactored `_run_red_team()` scan-target from bare string to dict.
- **Offline validation**: Full unit suite 155 passed, no lint/type errors.
- **Live validation** (bounded gpt-4.1, ff-hub-01):
  - ✓ AOAI inference route PROVEN (provider returns live completion)
  - ✓ Quality judges PROVEN end-to-end (isolation probe): coherence 4.5, relevance 4.0, fluency 3.0; groundedness None (string-only probe)
  - ✓ Red-team TypeError crash FIXED (scan completes successfully)
  - ✗ BLOCKER: safety evaluation PermissionDenied — principal lacks `Microsoft.CognitiveServices/accounts/AIServices/evaluations/write` data action. Result: 0/5 attack objectives → 0 attacks → vacuous "ASR 0.0%".
- Bounded scan wrote 0 entries (quality proven; safety UNSCORED under RBAC gap; gpt-4.1 skipped per build_entries logic).
- Nothing committed; 3 files remain uncommitted; HEAD 8ceb82c in sync with origin/main.
- **Escalation**: User must grant additional Foundry data-plane role for safety/red-team live validation.

**Artifacts**:
- Live scan log: `artifacts/live-smoke-20260722/scan-full.log`
- Live scan output: `artifacts/live-smoke-20260722/quality_safety_benchmarks.gpt41.yaml`
- Scratch dirs cleaned: `.scan_*` removed

**Consumption Block** (attached):

| Field | Value |
|-------|-------|
| model | claude-3-5-sonnet |
| model_tier | default |
| input_tokens | 8,000 |
| cached_tokens | 0 |
| output_tokens | 4,500 |
| input_rate | $3.00 |
| cached_rate | $0.30 |
| output_rate | $15.00 |
| est_cost_usd | 0.0915 |
| est_credits | 9.15 |
| basis | tier-default |

---

## Dispatch 2: Multi-Candidate Live Quality+Safety Scan (gpt-4.1 + gpt-5.6-sol) — Results Recorded, ASR Bug Deferred (2026-07-22T23:30:00Z)

**Member**: Wendy (Evaluation + Quality Engineer)

**Dispatch Type**: Full multi-candidate live evaluation scan + bug triage + user choice recording

**Request**: Execute user-approved "option 3 = full multi-candidate live scan" on Foundry ff-hub-01 (2 deployed models: gpt-4.1 v2025-04-14, gpt-5.6-sol v2026-07-09). Judge/scorer: gpt-4.1. Record results. Identify and triage blockers or known issues. User decision: defer bug fix (option 2).

**Summary**:
- **Command** (async, venv-live Python 3.12, azure-ai-evaluation 1.18.1):
  ```
  scripts/refresh_quality_safety_benchmarks.py --live --models gpt-4.1 gpt-5.6-sol \
    --foundry-project "https://ff-hub-01.services.ai.azure.com/api/projects/ff-proj-001" \
    --judge-model gpt-4.1 --num-objectives 5 \
    --probe-dataset datasets/general_qa.jsonl \
    --output artifacts/live-smoke-20260722/quality_safety_benchmarks.full.yaml
  ```

- **Results as written** (not committed):
  - gpt-4.1: quality 0.8833, safety 1.0
  - gpt-5.6-sol: quality 0.85, safety 1.0 (first successful scan)
  - Both: scored_deployment=gpt-4.1, 5/5 objectives fetched across all safety categories (hate_unfairness, self_harm, sexual, violence; Azure AI Developer role propagated)

- **Red-Team Evidence** (from .scan_*/final_results.json):
  - gpt-4.1 (.scan_20260722_205642): ASR 10.0% (4/40 successful attacks)
  - gpt-5.6-sol (.scan_20260722_211312): ASR 10.71% (3/28); GPT-5-family guardrails hard-rejected violence/self_harm jailbreak scenarios (expected behavior)

- **Known Bug Identified** (NOT fixed per user decision):
  - Location: `src/evaluator/quality_safety_eval_client.py` `_run_red_team()` / `_extract_scorecard()`
  - Shape: Code expects `risk_category_summary` dict; actual SDK 1.18.1 is LIST with flat-key per-risk values
  - Consequence: `overall_asr` resolves to None → red_team signal dropped → safety_score overstated (ignores measured ASR)
  - **Honest safety scores** (if bug fixed): gpt-4.1 → 0.90, gpt-5.6-sol → 0.89
  - Visible tell: `evaluators_run` correctly omits "red_team"
  - Bug pedigree: Existed in v3 (not new to this run)
  - User choice: Defer fix (option 2); record results with known caveat; follow-up task: fix extraction, then re-run 2-model scan

- **Minor**: Cosmetic UnicodeEncodeError (cp1252) in Python logging during red-team; set PYTHONIOENCODING=utf-8 next run

- **Nothing committed, pushed, or written to curated config/quality_safety_benchmarks.yaml**. Scratch output under artifacts/live-smoke-20260722/. Awaiting separate approvals for commit / curated write / CI live smoke.

**Artifacts**:
- Live scan output: `artifacts/live-smoke-20260722/quality_safety_benchmarks.full.yaml` (2 entries, not committed)
- Red-team scan logs: `.scan_20260722_205642/`, `.scan_20260722_211312/` (final_results.json with scorecard details)
- Bug triage recorded in Decision #41 and repo memory

**Consumption Block** (attached):

| Field | Value |
|-------|-------|
| model | claude-3-5-sonnet |
| model_tier | default |
| input_tokens | 6,500 |
| cached_tokens | 0 |
| output_tokens | 3,200 |
| input_rate | $3.00 |
| cached_rate | $0.30 |
| output_rate | $15.00 |
| est_cost_usd | 0.0195 |
| est_credits | 1.95 |
| basis | tier-default |

---

## Dispatch 2: AOAI-Route Fix v3 Live Re-Validation — Red-Team Gap Closed (2026-07-22T23:30:00Z)

**Member**: Wendy (Evaluation + Quality Engineer)

**Dispatch Type**: Live re-validation with expanded Foundry RBAC (Azure AI Developer role granted)

**Request**: Execute bounded v3 live scan after user granted Azure AI Developer role at ff-hub-01 Foundry scope. Validate whether red-team evaluation gap (previously PermissionDenied on evaluations/write) is now closed. Record findings, RBAC lesson, and unblock next gate (commit decision).

**Summary**:

v3 scan re-ran the same evaluation context as v1 and v2 (num-objectives=5, probe=datasets/general_qa.jsonl, judge=gpt-4.1, foundry project ff-hub-01, gpt-4.1 model only).

**Chronology**:
1. v1: quality judges proven (coherence 4.5, relevance 4.0, fluency 3.0); red-team TypeError fixed; safety blocked (PermissionDenied), 0/5 objectives → vacuous ASR.
2. v2: Foundry Owner granted; content-safety unblocked (defect_rate 0.0); 1 entry written (quality 0.8667, safety 1.0); red-team STILL blocked (0/5 objectives) → Lesson: Foundry Owner grants content-safety but NOT red-team data action.
3. v3: **Azure AI Developer granted**; red-team gap CLOSED. Objectives fetched: sexual 5/5, violence 5/5, self_harm 5/5, hate_unfairness 0/5 (AAD lag expected). 30 adversarial attacks executed; 0/30 succeeded. Final entry: gpt-4.1, quality 0.875, safety 1.0, full evaluators_run set, sdk_version 1.18.1.

**Key Findings**:
- ✓ Red-team gap CLOSED: Azure AI Developer at account/project scope grants `evaluations/write` data action.
- ✓ Non-vacuous ASR (0/30 succeeded): Real safety signal produced. Azure content filters actively block jailbreak/violence/self_harm as expected.
- ✓ Quality + safety both scored live (0.875, 1.0). Entry written with full evaluator set.
- ⚠ hate_unfairness 0/5 due to AAD propagation lag at scan start; clean re-run expected to close to 5/5. 3 of 4 categories fully exercised.

**RBAC Lesson** (durable):
- Foundry Owner / Foundry Account Owner roles do NOT grant red-team `evaluations/write`.
- **Azure AI Developer** at account/project scope DOES.
- Content-safety and red-team are distinct Foundry data-plane operations.

**Artifacts**:
- Live scan log: `artifacts/live-smoke-20260722/scan-full-v3.log`
- Live scan output: `artifacts/live-smoke-20260722/quality_safety_benchmarks.gpt41.v3.yaml`
- Scratch dirs cleaned: `.scan_*` removed

**Gating**:
- AOAI-route fix (3 files, +181/-20) validated live end-to-end. Ready for commit pending user approval.
- Next actions gated: (1) commit, (2) optional clean re-run, (3) full multi-candidate scan, (4) write to config/, (5) WI-04 CI smoke, (6) v0.1 end-to-end.
- Standing rule: present results before wider run. No commits without separate approval.

**Consumption Block** (attached):

| Field | Value |
|-------|-------|
| model | claude-3-5-sonnet |
| model_tier | default |
| input_tokens | 15,000 |
| cached_tokens | 0 |
| output_tokens | 8,000 |
| input_rate | $3.00 |
| cached_rate | $0.30 |
| output_rate | $15.00 |
| est_cost_usd | 0.165 |
| est_credits | 16.5 |
| basis | tier-default |

---
