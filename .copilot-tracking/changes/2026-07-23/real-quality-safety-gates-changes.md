<!-- markdownlint-disable-file -->
# Release Changes: Make the Evaluator's Quality + Safety Gates Real

**Related Plan**: real-quality-safety-gates-plan.instructions.md
**Implementation Date**: 2026-07-23

## Summary

Make the promotion-gate quality + safety signals real (live Azure-backed) instead of stubbed, while keeping fakes as the default and live strictly opt-in, per Council Decision #51's 13 binding conditions (HIGH-risk RAI surface). Live runners delegate to the existing validated `quality_safety_eval_client.py` seam; every live output is advisory / non-promotion-grade and no code path auto-promotes.

## Changes

### Added

* src/evaluator/aoai_client.py - Import-guarded keyless AOAI chat client; `chat_completion(model_id, prompt, *, deployment_ref=None) -> str|None` with deployment resolution (kwarg -> deployments map -> model_id) and `_with_retry` resilience (Phase 1 Steps 1.2/1.3; C2, C5, DD-03).
* src/shared/redaction.py - Redaction helper stripping bearer tokens/keys/endpoint FQDNs from logs and result JSON (Step 1.8; C6-C9).
* tests/unit/test_evaluator_aoai_client.py - Retry/UNSCORED/deployment-resolution/guard-import tests.
* tests/unit/test_evaluator_custom_runner.py - LiveCustomRunner guard + closure tests.
* tests/unit/test_evaluator_redteam_runner.py - LiveRedTeamRunner guard + block-rate tests.

### Modified

* config/models.yaml - Additive `model_api_shapes` (default/o3/gpt-5.1, documented match order) + `deployments` map; `watch_list` untouched (Steps 1.1/1.2; C2).
* config/evaluation.yaml - Additive `judge_model_version`, `rubric_version` keys; existing `quality_gates`/`timeouts` unchanged (Step 1.7; C10).
* .gitignore - Explicit `results/redteam/` entry (Step 1.8).
* src/evaluator/models.py - Support for advisory/UNSCORED live result mapping.
* src/evaluator/custom_runner.py - Added `LiveCustomRunner` delegating to the seam via DD-04 closure (`deployment_ref=work_item.deployment_ref.deployment_name` str); judge-independence assertion (Steps 1.4/1.7; C1, C3, C10, DD-04).
* src/evaluator/redteam_runner.py - Added `LiveRedTeamRunner` (own-deployment scope-lock, Baseline+Jailbreak, skip_upload, block_rate=1-asr/100) (Step 1.5; C1, C3, C11 partial).
* src/evaluator/service.py - `--live` flag + `MUA_EVAL_MODE=live` env selection (flag wins; injected runners still override); live summary stamped `promotion_grade:false`/`advisory:true`/rationale + redacted; new audit keys (`classifier_available`/`canary_failures`) are additive and live-only, omitted on the default path (Steps 1.6/1.9; C4, RAI caveat).
* src/reporter/models.py - Added `promotion_grade`/`advisory` to BOTH CandidateArtifacts and CandidateComparison (defaults preserve non-live behavior) (Step 1.9; DR-03).
* src/reporter/artifact_loader.py - Reads `promotion_grade`/`advisory` from summary JSON (Step 1.9; DR-03).
* src/reporter/aggregator.py - Carries advisory flags into CandidateComparison in `aggregate_reporter_run()` (Step 1.9; DR-03).
* src/reporter/decision_engine.py - Advisory short-circuit -> `needs_human_review` verdict (never winner/runner-up); None-safe custom_overall/block_rate; new sort bucket (Step 1.9; C13, DR-03).
* tests/unit/test_reporter_decision_engine.py - Advisory-summary yields needs_human_review + flag survives aggregate_reporter_run().

### Removed

* (none)

### Added (Phase 2)

* datasets/adversarial_probes.jsonl - Versioned adversarial probe set: 5 categories x 5 probes (jailbreak/instruction-override, harmful-content, PII-extraction, prompt-injection incl. indirect, TOS/CoC) + 2 tagged canary rows; disjoint from general_qa; no real PII (Step 2.1; C11).
* src/evaluator/probe_set_loader.py - Probe-set loader returning rows + SHA-256 + `PROBE_SET_VERSION="v1"`, mirroring dataset_loader hashing (Step 2.1; C11).
* src/evaluator/block_judge.py - Fail-closed block-signal combination: Content Safety classifier PRIMARY + optional judge + keyword corroboration; both-unavailable and disagreement resolve to NOT blocked (fail-closed, RAI-safe direction) (Step 2.2; C11, C12).
* docs/live-eval-human-gate.md - Runbook documenting the human-in-the-loop gate, rubric versioning, and uniformity flags (Step 2.6; C13).
* tests/unit/test_evaluator_probe_set_loader.py - Probe-set hash/version/disjointness tests.
* tests/unit/test_evaluator_block_judge.py - Fail-closed combination truth-table tests.
* tests/unit/test_evaluator_canaries.py - Poison + discrimination canary tests against real block_judge functions.
* tests/unit/test_evaluator_service.py - Relative-gate skip/None, uniformity flag, and audit-bundle tests.

### Modified (Phase 2)

* config/evaluation.yaml - Additive `relative_gate{quality_epsilon, redteam_epsilon}`; absolute `quality_gates` floor preserved (Step 2.3; RAI relative).
* src/evaluator/redteam_runner.py - `LiveRedTeamRunner` wires classifier+judge+keyword per probe with segregated transcripts; `LocalRedTeamRunner` nano rule REMOVED, replaced by category/canary-tag-driven fixture (Step 2.2; C11, C12, DD-02).
* src/evaluator/service.py - `detect_suspicious_uniformity()`; relative-to-retiring comparison (skipped/None when no baseline, never fabricated); audit provenance bundle in summary (Steps 2.3/2.4/2.5; RAI relative+audit).
* src/evaluator/config_loader.py - `load_relative_gate_config()`, `load_audit_provenance()` loaders (Steps 2.3/2.5).
* src/evaluator/result_writer.py - Additive audit bundle persistence; default fake summary shape unchanged (Step 2.5; RAI audit).
* src/evaluator/models.py - Retiring-baseline + audit fields on work item/result contracts (Steps 2.3/2.5).

### Added (Phase 3 — tests only)

* tests/unit/test_redaction.py - First-ever coverage for src/shared/redaction.py: bearer tokens, URLs, key-value secrets, sensitive-key drop, deployment-name preservation, recursive nesting (Step 3.1; C6-C9).

### Modified (Phase 3 — tests only)

* tests/unit/test_evaluator_custom_runner.py - Added `ImportModuleTests` guard-import + `LiveCustomRunnerStubClientTests` (scored mapping + all-UNSCORED -> overall None) via injectable stub seam (Step 3.1; C1, C3, C10).
* tests/unit/test_evaluator_redteam_runner.py - Added guard-import + `LiveRedTeamRunnerStubClientTests` (probe mapping, UNSCORED-probe exclusion, delegation to real combine_block_signals) (Step 3.1; C1, C3, C11).
* tests/unit/test_evaluator_block_judge.py - Added `ImportModuleTests` + `BuildContentSafetyClassifierImportGuardTests` (lazy-import raise without extra) (Step 3.1; C11).
* tests/unit/test_evaluator_probe_set_loader.py - Added guard-import test (Step 3.1).
* tests/unit/test_evaluator_service.py - Added default-path omission assertion: default non-live summary omits live-only keys (`promotion_grade`/`advisory`/`advisory_rationale`) (Step 3.1; live-only keys omitted on the default path).

## Additional or Deviating Changes

* decision_engine.py None-safety guard on `custom_overall`/`redteam_block_rate` is defense-in-depth; the advisory short-circuit intercepts advisory candidates before rejection logic. Retained for robustness.
  * Reason: guard against future callers that bypass the advisory flag.
* Phase 2 was found already implemented and uncommitted in the working tree at Phase 2 dispatch time (implemented alongside Phase 1). The Phase Implementor verified each step against the details spec line-by-line rather than re-implementing; independent grep verification by the parent confirmed fail-closed block judging, nano-rule removal from all live paths, and relative-gate correctness.
  * Reason: prior-session implementation; verification-only pass was the correct action.

## Release Summary

All three phases complete; offline unit suite green at **232 passed, 0 failed** (`.venv/Scripts/python.exe -m pytest tests/unit -q`). Lint/type is **N/A** (no `[tool.mypy]`/`[tool.ruff]`/`mypy.ini`/`ruff.toml`/`setup.cfg` in the repo). No `src/` files changed in Phase 3 — all Step 3.1 gaps were closed with test-only coverage against already-correct implementation.

**Files affected (working tree, uncommitted):**

* Source added (5): src/evaluator/aoai_client.py, src/evaluator/probe_set_loader.py, src/evaluator/block_judge.py, src/shared/redaction.py, datasets/adversarial_probes.jsonl.
* Source modified (11): src/evaluator/{custom_runner,redteam_runner,service,config_loader,result_writer,models}.py, src/reporter/{models,artifact_loader,aggregator,decision_engine}.py.
* Config modified (3): config/models.yaml, config/evaluation.yaml, .gitignore.
* Docs added (1): docs/live-eval-human-gate.md.
* Tests added (7): test_evaluator_{aoai_client,custom_runner,redteam_runner,probe_set_loader,block_judge,canaries,service}.py, test_redaction.py; plus test_reporter_decision_engine.py modified.

**Runner selection & judge config (PD-01 Option A):** Fakes (`LocalCustomRunner`/`LocalRedTeamRunner`) remain the DEFAULT. Live runners activate only via `--live` flag or `MUA_EVAL_MODE=live` (flag wins; explicitly injected runners still override). Quality judging uses a dedicated pinned non-candidate judge deployment (`JUDGE_MODEL` env; `assert_independent_judge` refuses judge==candidate/family); red-team block-judging uses Azure AI Content Safety as the PRIMARY deterministic fail-closed classifier with the judge as a secondary corroborating signal. Judge/classifier are configurable via config/env; the judge deployment need not exist (the gate fails closed if unset).

**Additive live-only keys & no auto-promotion (verified):** New evaluator result fields and summary audit keys are additive with neutral defaults; the live-only summary keys are omitted on the default (non-live) path (absent unless `live_enabled`), so the default summary contract is preserved. Every live output is stamped `promotion_grade:false` / `advisory:true`; the reporter decision engine short-circuits advisory candidates to `needs_human_review` (never `winner`/runner-up). Nothing in any code path auto-promotes.

**Deployment notes:** No Azure resources were created, enabled, or mutated. No live inference/judging ran. `.venv-live` was never used. Changes remain in the working tree, uncommitted, per the STOP-AND-GATE mandate. The opt-in live validation (Step 3.2 sub-bullet) is deferred pending explicit user cost acknowledgment.
