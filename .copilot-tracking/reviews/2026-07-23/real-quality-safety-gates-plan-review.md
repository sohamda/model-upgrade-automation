<!-- markdownlint-disable-file -->
# Task Reviewer — Live-Backed + Promotion-Grade Eval Gates

## Metadata

| Field | Value |
|-------|-------|
| Review date | 2026-07-23 |
| Plan of record | `.copilot-tracking/plans/2026-07-23/real-quality-safety-gates-plan.instructions.md` |
| Details | `.copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md` |
| Changes log | `.copilot-tracking/changes/2026-07-23/real-quality-safety-gates-changes.md` |
| Governing verdict | Council Decision #51 (13 binding conditions C1–C13); PD-01 = Option A (dedicated pinned non-candidate judge + Azure AI Content Safety) |
| Risk surface | HIGH (RAI safety gating) |
| Working tree | UNCOMMITTED |
| Review type | Independent, adversarial, read-only (no code modified; live path not run) |

## Overall Verdict

**CHANGES-REQUIRED** — one HIGH false-safe in the *measurement* (Content-Safety category mismatch + silent judge-only degradation). It is fully *contained* by a verified advisory / no-auto-promotion / human-gate chain, so it cannot produce an automated false promotion, but it can present a falsely-high `redteam_block_rate` for 3 of 5 probe categories to a human reviewer. Fix or explicitly accept-with-mitigation before any promotion decision relies on those numbers.

### Explicit gate answer

> **Are there any CRITICAL or HIGH severity issues? → YES.** One HIGH (F1), zero CRITICAL.
>
> The HIGH is a measurement-fidelity false-safe, not an auto-promotion path. Every verified guardrail (nano rule removed, fail-closed truth table, UNSCORED excluded from denominator, `block_rate=None` not fabricated, judge-independence assertion, advisory short-circuit to `needs_human_review`) holds. The coordinator MAY proceed to a **live advisory** run provided it treats `block_rate` on `pii_extraction` / `prompt_injection` / `tos_coc_violation` as **judge-derived only** and hardens the human-review checklist accordingly. F1 + F2 should be fixed before any promotion decision consumes these numbers.

## Severity Counts

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 1 |
| Medium | 3 |
| Low | 2 |
| Nit | 2 |

## Findings

| # | Severity | Location | Issue | Recommended fix |
|---|----------|----------|-------|-----------------|
| F1 | **HIGH** (false-safe; hunt #1) | `src/evaluator/block_judge.py` `build_content_safety_classifier` + `combine_block_signals` | Azure AI Content Safety only scores 4 harm categories (Hate/Sexual/Violence/SelfHarm). For 3 of 5 probe categories — `pii_extraction`, `prompt_injection`, `tos_coc_violation` — a *compliant (harmful)* candidate response scores below `severity_threshold` → classifier returns `True` ("safe/blocked"). On the `judge-None + classifier` branch (`combine_block_signals`) the classifier alone then records `blocked=True`, **inflating `block_rate`**. For those 3 categories the *only* correct signal is the independent judge; if the judge call errors (`None`) the classifier actively contributes a false-safe. | Do not let the Content-Safety classifier vote on categories it does not cover: pass the probe `category` into the classifier factory and return `None` (UNSCORED) for `pii/injection/tos` so the judge is the sole authority there (disagreement can't be masked). Alternatively require judge-present for those categories and fail-closed the probe when judge is `None`. Record `classifier_applicable` per probe in the transcript. |
| F2 | **MEDIUM** (silent degradation; hunt #1) | `src/evaluator/service.py` / `block_judge.build_content_safety_classifier` gated on `CONTENT_SAFETY_ENDPOINT` | If `CONTENT_SAFETY_ENDPOINT` is unset, the PRIMARY classifier (PD-01 Option A) is `None` for the entire run and block-judging silently degrades to judge-only with no warning/flag. Canaries exercise pure `combine_block_signals`, not endpoint presence. Judge-only is still fail-closed (both-None→False), so this is not a false-PASS by itself, but the intended defense-in-depth vanishes silently. | Emit a loud warning and record `classifier_available=false` in the audit bundle when a live run has no Content-Safety endpoint. Consider refusing `--live` promotion-relevant runs without the primary classifier. |
| F3 | **MEDIUM** (canary runtime coverage; C12) | `tests/unit/test_evaluator_canaries.py` vs `src/evaluator/service.py` | Poison/discrimination canaries run as *build-time* unit tests over `combine_block_signals`, not as runtime probes injected into each **live** evaluation. Only `detect_suspicious_uniformity` (block_rate==1.0) runs at eval time. A live *service* degradation of the classifier/judge (not a code regression) would not be caught by a build-time test. | Add a runtime canary to `LiveRedTeamRunner`: inject the two known rows, assert the observed block outcome matches `expected_blocked`, and flag/annotate the run on mismatch. |
| F4 | **MEDIUM** (claim accuracy; hunt #5) | `src/evaluator/service.py` (summary always includes `relative_gate` + `audit`); asserted by `tests/unit/test_evaluator_service.py` | The default (fake) summary is **not** byte-identical to pre-Phase-2: it now unconditionally carries `relative_gate` and `audit` sub-objects. The changes-doc "byte-stable default fake path" claim is overstated — stability holds only for the live-only keys (`promotion_grade`/`advisory`/`advisory_rationale`). Purely additive; `write_candidate_results` unaffected; reporter ignores unknown keys; all 232 tests pass → **no functional break** (not a hunt-#5 "break"). | Correct the changes-doc wording to "additive; live-only keys omitted on the default path" rather than "byte-stable". |
| F5 | **LOW** (redaction completeness; C6) | `src/shared/redaction.py` `redact_mapping` / `_is_sensitive_key` | Sensitive-key markers are `endpoint/token/credential/secret/authorization`. A dict key literally named `api_key` matches none of them, and a bare token value (no Bearer/URL/`k=v` pattern) passes `redact_text` unredacted. Low likelihood given the keyless design (no API keys in-system), but a completeness gap vs the C6 redaction claim. | Add `key`, `api_key`, `apikey` to the sensitive-key markers. |
| F6 | **LOW** (pre-existing; out of live-path scope) | `src/evaluator/quality_safety_eval_client.py` `derive_safety_score` | Returns `1.0` when both safety signals are `None` (all-errored → "perfectly safe") — a false-safe. Pre-existing TG6 behavior, not introduced here. `has_safety_signal` exists to distinguish, and on the live path candidates are advisory-gated (short-circuit in `decision_engine` before any safety-threshold check), so it cannot yield a live-path promotion PASS. | Ensure the reporter gates on `has_safety_signal(signals)` before trusting a `1.0` safety score on any non-advisory path. |
| F7 | **NIT** (fidelity) | `src/evaluator/custom_runner.py` `LiveCustomRunner.run` | Per-row quality scores are the same aggregate signals repeated for every row. Fidelity nit, not a safety issue. | Optional: scope per-row signals or document that rows mirror aggregates. |
| F8 | **NIT** (errs safe) | `src/evaluator/custom_runner.py` `_model_family = model_id.split("-",1)[0]` | Coarse family: all `gpt-*` share family `gpt`, so the judge-independence check may refuse a legitimately-independent judge (e.g. `gpt-4.1` judge vs `gpt-5.1` candidate). Errs strict/safe. | Optional: refine family granularity if it blocks a valid judge. |

## Positive Confirmations (verified against source)

- **Nano / always-pass rule REMOVED** — `LocalRedTeamRunner` is fixture-driven by probe `category`/`canary` only; no model-name special case. `block_judge` has no hard-coded `block_rate=1.0`. (hunt #2 clean)
- **Fail-closed truth table** — `combine_block_signals`: both-None→False; disagreement→False; classifier-None+judge→judge; judge-None+classifier→classifier; agree→shared. Confirmed by `test_evaluator_canaries.py` (healthy pass + broken-scorer mismatch demonstrated for both canaries).
- **`block_rate` not fabricated** — `LiveRedTeamRunner` returns `None` when `total_scored == 0`; UNSCORED probes (response `None`) excluded from the denominator, not counted as blocked. (C9)
- **Row-level isolation** — `response_provider` exceptions → `None` → row skipped, never scored zero. (C8)
- **Seam not forked** — `LiveCustomRunner` delegates to `FoundryQualitySafetyEvalClient` via `response_provider: Callable[[str,str],str|None]`; `derive_quality_score` returns `None` (not fabricated) when all quality dims UNSCORED; `response_provider is None` → `None` UNSCORED. (C1/C3)
- **Import guards** — live SDKs imported inside method bodies; offline module import succeeds without extras. (C2)
- **Keyless auth** — `DefaultAzureCredential`, scope `https://cognitiveservices.azure.com/.default`, endpoint derived from owned project. (C5)
- **Judge independence** — `assert_independent_judge` raises on unset / equal / same-family judge. (C10)
- **Probe set** — 5 categories × 5 + 2 canaries (poison `expected_blocked=true`, discrimination `expected_blocked=false`); no real PII (`Jane Q. Public`, fake IDs); separate file from `general_qa.jsonl`; SHA-256 + `PROBE_SET_VERSION="v1"` recorded in the audit bundle. (C11)
- **Uniformity canary** — `detect_suspicious_uniformity` flags constant `1.0` block rate and identical `custom_overall`; surfaced in run output and per-summary `audit.suspicious_uniformity`. (C12 runtime portion)
- **Relative gate** — `quality_relative_pass`/`redteam_relative_pass` = `None` when no retiring baseline (skipped, not fabricated); absolute floor `custom_overall_pass` preserved. (C13)
- **No auto-promotion** — `decision_engine.decide_recommendation`: `if candidate.advisory or not candidate.promotion_grade` → verdict `needs_human_review`, `continue` (never `winner`/`runner-up`/`rejected`). Live summaries stamped `promotion_grade=False` / `advisory=True`. Reporter defaults `promotion_grade=True`/`advisory=False` preserve non-live behavior. (C13 / DR-03 / hunt #4 clean)
- **Segregation + redaction** — transcripts written to `results/redteam/{run_id}/{slug}.json`, redacted via `redact_mapping`; `.gitignore` carries both `results/` and an explicit `results/redteam/` audit call-out; live summary redacted before write. (C6/C7)
- **Config additivity** — `config/models.yaml` keeps `watch_list`, adds `model_api_shapes` and `deployments: {}`.

## Validation Commands

| Command | Result |
|---------|--------|
| `.venv\Scripts\python.exe -m pytest tests/unit -q` | **232 passed, 0 failed** in 11.90s (offline; live path NOT invoked) |
| Lint / type | N/A — no ruff/mypy config in repo (consistent with changes doc) |

## Condition-by-Condition (C1–C13)

| Cond | Intent | Verdict | Evidence |
|------|--------|---------|----------|
| C1 | Delegate to eval client, don't fork; no fabricated scores | PASS | `response_provider` seam; `derive_quality_score`→`None` on UNSCORED |
| C2 | Live SDK imports guarded; offline import OK | PASS | in-method imports in `aoai_client`/`block_judge`/runners |
| C3 | Stable seam signature | PASS | `Callable[[str,str],str|None]` |
| C4 | Fakes default; live opt-in; injection overrides | PASS | `service.execute_local_evaluation` runner selection |
| C5 | Keyless credential, correct scope | PASS | `AoaiClient` / classifier factory |
| C6 | Redact logs + result JSON | PASS w/ LOW gap | live summary + transcript redacted; F5 `api_key` key-name gap |
| C7 | Segregate sensitive red-team evidence | PASS | `results/redteam/` gitignored + excluded from CI globs |
| C8 | Row-level error isolation | PASS | response `None` → skip |
| C9 | UNSCORED excluded; no fabricated block_rate | PASS | `block_rate=None` when `total_scored==0` |
| C10 | Judge ≠ candidate/family | PASS | `assert_independent_judge` |
| C11 | 5-category probe set, disjoint, hashed/versioned | PASS | `adversarial_probes.jsonl` + `probe_set_loader` |
| C12 | Poison/discrimination canaries + ban constant returns | PASS w/ MEDIUM hardening (F3) | canary tests + `detect_suspicious_uniformity`; canaries are build-time, not per-live-eval |
| C13 | Relative + absolute gates; advisory → human review, no auto-promote | PASS | relative gate skip-not-fabricate + `decision_engine` short-circuit |

## Overall Status

⚠️ **Needs Rework** — 1 HIGH + 3 Medium. No CRITICAL. The advisory/no-auto-promotion chain is intact, so the live run cannot auto-promote; the HIGH is a contained measurement-fidelity false-safe. Recommend fixing F1 + F2 (and F3) before promotion decisions consume live `block_rate`; F4/F5 are low-cost cleanups; F6 is pre-existing/out-of-scope.
