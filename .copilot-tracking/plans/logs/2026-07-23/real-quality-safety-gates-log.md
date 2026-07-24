<!-- markdownlint-disable-file -->
# Planning Log: Make the Evaluator's Quality + Safety Gates Real

## Condition-to-Task Traceability (Council Decision #51)

Exact Decision #51 condition numbers mapped to plan tasks. Tags: A=Architect, S=Security, R=RAI.

| Condition | Tag | Text (abridged) | Owning Task(s) |
|-----------|-----|-----------------|----------------|
| C1 | A | Reuse validated quality_safety_eval_client seam (no forking) | 1.4, 1.5 |
| C2 | A | Thin aoai_client.py provider (import-guarded, method-body DefaultAzureCredential) | 1.1, 1.2 |
| C3 | A | LiveCustomRunner/LiveRedTeamRunner same signature as stubs; delegate | 1.4, 1.5 |
| C4 | A | Local*Runner remain DEFAULT; live opt-in via --live | 1.6 |
| C5 | S | Keyless AAD DefaultAzureCredential -> cognitiveservices.azure.com/.default | 1.2 |
| C6 | S | Logging redaction (tokens, API keys, endpoint FQDNs) | 1.8 |
| C7 | S | Red-team transcripts segregated as sensitive evidence | 1.8 |
| C8 | S | Content boundary: model output as DATA only | 1.8 |
| C9 | S | Injection boundary: probes/dataset/output untrusted DATA | 1.8 |
| C10 | R | Quality scoring: independent judge + versioned rubric (never candidate/family) | 1.7, 1.4 |
| C11 | R | Red-team: separate versioned hashed probe set + classifier + judge; fail-closed | 2.1, 2.2 |
| C12 | R | Anti-regression: poison + discrimination canaries; ban constant returns | 2.4, 2.2 |
| C13 | R | Human-in-the-loop for auto-promotion until track record | 2.6, 1.9 |

WI-01/WI-02 seam conditions (import-guard, own-deployment scope-lock, bounded execution Baseline+Jailbreak, skip_upload, provenance stamps, min-sample-size, no-key, redaction) are preserved by reusing the existing `quality_safety_eval_client.py` and are exercised in Tasks 1.4, 1.5, 1.8, 2.5.

## Discrepancy Log

### Unaddressed Research Items

* DR-01: config/models.yaml has no per-model capability/API-shape section today.
  * Source: config/models.yaml (only `use_official_sources` + `watch_list`).
  * Reason: Not excluded — ADDED additively in Task 1.1. Logged because it is a required precondition the codebase does not yet provide.
  * Impact: medium (o3 vs gpt-5.1 request shaping is required for correct live calls).

* DR-02: The 20-row `general_qa.jsonl` has no gold answers, so groundedness stays UNSCORED under the string-only probe seam.
  * Source: research doc (seam facts); datasets/general_qa.jsonl.
  * Reason: Accepted as expected seam behavior; quality score derives from the other Likert dims. Documented so implementers do not treat groundedness None as an error.
  * Impact: low.

* DR-03: Neither the research doc nor the plan/details examine `src/reporter/decision_engine.py`, `src/reporter/artifact_loader.py`, or `src/reporter/models.py` — the existing consumer that reads `summary.json`'s `custom_overall`/`redteam_block_rate` and computes a `verdict: "winner"` purely from numeric threshold comparisons (verified: `decision_engine.py` lines 16-22, 92; `artifact_loader.py` lines 165-166; `CandidateArtifacts`/`ReporterThresholds` in `models.py` carry no `promotion_grade`/`advisory` field).
  * Source: src/reporter/decision_engine.py; src/reporter/artifact_loader.py; src/reporter/models.py.
  * Reason: Plan Tasks 1.9/2.6 stamp `promotion_grade: false` / `advisory: true` only on the summary dict built in `service.py`; no task propagates that flag into `CandidateArtifacts`/`CandidateComparison` or teaches `decide_recommendation()`/`markdown_report.py`/`remediation_payload.py` to suppress or caveat a "winner" verdict when the underlying signals are live-advisory or Phase-2-incomplete (e.g., pre-PD-01, pre-probe-set). The existing `draft=True` + `needs-human-review` label on the remediation payload softens but does not close this gap, since the rendered report's "## Recommendation: X" text and `winners` map carry no advisory caveat for a human reviewer to see.
  * Impact: high (this is the concrete mechanism by which C13 human-in-the-loop / no-auto-promotion must hold end-to-end; currently the flag added by 1.9/2.6 has no reader).
  * Resolution (PARTIALLY ADDRESSED - re-opened 2026-07-24 re-validation): Step 1.9 adds `src/reporter/artifact_loader.py` (read + carry `promotion_grade`/`advisory`) and `src/reporter/decision_engine.py` (suppress `winner`; emit `needs_human_review`) as file targets, and Step 2.6 references `decision_engine.py` consuming the flag - but the wiring does NOT actually reach `decision_engine.py` as scoped. Verified: `decision_engine.decide_recommendation()` reads only `CandidateComparison` objects (src/reporter/decision_engine.py); `CandidateComparison` is constructed at exactly one site, `src/reporter/aggregator.py::aggregate_reporter_run()` (line ~63), which explicitly enumerates every field from a `CandidateArtifacts` instance with no passthrough for an advisory/promotion_grade flag; `src/reporter/models.py`'s `CandidateArtifacts` and `CandidateComparison` (both `@dataclass(slots=True)`) carry no `promotion_grade`/`advisory` field today. Neither `src/reporter/models.py` nor `src/reporter/aggregator.py` appear in Step 1.9's or Step 2.6's file-target lists, so even if `artifact_loader.py` reads the flag onto `CandidateArtifacts`, there is no field to hold it (dataclass has `slots=True`) and no code forwards it into the `CandidateComparison` that `decision_engine.py` actually consumes. The C13 human-gate signal does NOT have a working downstream reader end-to-end as currently scoped.
  * Remaining fix direction (not applied - read-only validation): add `src/reporter/models.py` and `src/reporter/aggregator.py` to Step 1.9's (or a new step's) file targets; add `promotion_grade: bool` / `advisory: bool` fields to both `CandidateArtifacts` and `CandidateComparison`; forward the fields in `aggregator.py`'s `CandidateComparison(...)` construction so `decision_engine.py` can read them.
  * Resolution (ADDRESSED - applied 2026-07-24 after re-validation): Step 1.9 now lists the full verified chain as file targets: `src/reporter/models.py` (add `promotion_grade`/`advisory` to BOTH `CandidateArtifacts` AND `CandidateComparison`, defaults preserving existing non-live behavior), `src/reporter/artifact_loader.py` (populate from summary JSON), `src/reporter/aggregator.py` (`aggregate_reporter_run()` forwards the flag from `CandidateArtifacts` into `CandidateComparison`), and `src/reporter/decision_engine.py` (reads `CandidateComparison`, emits `needs_human_review` when advisory). Step 1.9 success criterion now requires a reporter unit test asserting the flag survives `aggregate_reporter_run()`. This closes the C13 end-to-end reader gap that the prior partial fix left open.
  * Re-confirmed (THIRD re-validation, 2026-07-23 pass 3): Details Step 1.9's Files list (lines 220-225) still names all four: `src/reporter/artifact_loader.py`, `src/reporter/models.py` (BOTH `CandidateArtifacts` and `CandidateComparison`), `src/reporter/aggregator.py`, `src/reporter/decision_engine.py`. Re-verified against live source: `CandidateArtifacts` at src/reporter/models.py:31, `CandidateComparison` at src/reporter/models.py:83 (both `@dataclass(slots=True)`), `aggregate_reporter_run()` at src/reporter/aggregator.py:25 constructing `CandidateComparison(` at line 63, and `decision_engine.decide_recommendation()` at src/reporter/decision_engine.py:45 consuming only `CandidateComparison` objects and computing `verdict = "winner"` at line 82. Step 1.9's success criterion (reporter unit test asserting the flag survives `aggregate_reporter_run()`) remains intact. No regression from the prior fix — DR-03 stays CLOSED.

### Plan Deviations from Research

* DD-01: Research allows either an absolute floor OR relative-to-retiring gate; the plan implements BOTH (absolute `quality_gates` retained AND additive `relative_gate` epsilon).
  * Research recommends: relative-to-retiring comparison (candidate >= retiring - epsilon).
  * Plan implements: absolute floor kept + relative gate added (Task 2.3).
  * Rationale: retaining the existing absolute floor avoids a silent regression path if the retiring baseline itself is weak; belt-and-suspenders for a HIGH-risk RAI surface.

* DD-02: The nano rule removal (OD-2) is scheduled in Phase 2 (Task 2.2) rather than Phase 1, and the fake is RE-SHAPED (probe-category-driven) rather than deleted.
  * Research recommends: remove hard-coded nano rule from the live path.
  * Plan implements: live path never contains it (built clean in 1.5); the FAKE's nano rule is replaced with a deterministic category-driven pattern in 2.2 so canary tests remain meaningful.
  * Rationale: deleting the fake's only differentiating logic would make canaries trivial; a category-driven fixture preserves meaningful offline tests without arbitrary model-name coupling.

* DD-03 (CRITICAL): Research documents the seam's `response_provider` callback is invoked as `self.response_provider(model_id, prompt)` (verified: `quality_safety_eval_client.py` lines 360, 452 both call `self.response_provider(model_id, prompt)`); the plan's Task 1.2/1.4 design `aoai_client.chat_completion(deployment_name: str, prompt: str) -> str | None` and wire it directly as `response_provider=aoai_client.chat_completion` with no adapter.
  * Research recommends (verified fact): the callback's first argument at call time is `model_id` (e.g. `"gpt-4.1"`), a value distinct from `EvaluatorWorkItem.deployment_ref.deployment_name` (both fields are modeled separately throughout the codebase — see `service.py`'s summary dict and `reporter/models.py`'s `CandidateArtifacts`, which carry `model_id` and `deployment_name` as independent fields).
  * Plan implements: a provider function whose sole parameter is named/typed for `deployment_name`, bound bare as `response_provider`, so at runtime it silently receives `model_id` where `deployment_name` is required for real Azure OpenAI data-plane routing. Task 1.2 also states model_api_shapes (Task 1.1, keyed by model_id/family, e.g. `o3`, `gpt-5.1`) must be "applied ... for deployment_name," compounding the same identity confusion — capability-shape matching cannot key off an arbitrary deployment alias.
  * Rationale: none stated in the plan/details; this reads as an unaddressed implementation gap rather than a deliberate choice. Left unresolved, `LiveCustomRunner`/`LiveRedTeamRunner` (Tasks 1.4/1.5, mapped to C1/C3) will route live inference calls to the wrong deployment (or fail resolution entirely) and/or silently skip capability-shape adaptation for o3 vs gpt-5.1, undermining the reused-seam guarantee (C1) at the exact plug-in point research called out as load-bearing.
  * Recommended fix direction (not applied — read-only validation): wire an adapter closure/`functools.partial` in Task 1.4/1.5 that captures `work_item.deployment_ref.deployment_name` and validates/ignores the seam's `model_id` argument, rather than binding `aoai_client.chat_completion` bare as `response_provider`; have `aoai_client` accept a `model_id` parameter (or receive the resolved shape pre-selected by the caller) so Task 1.1's `model_api_shapes` matching is keyed correctly.
  * Resolution (ADDRESSED - re-confirmed 2026-07-24 re-validation): Step 1.2 now defines `chat_completion(model_id, prompt, *, deployment_ref=None)`, treats arg 1 as the CANDIDATE `model_id`, resolves the deployment (explicit `deployment_ref` closure kwarg -> additive `deployments:` map in config/models.yaml -> model_id fallback), and keys `model_api_shapes` by `model_id`. Steps 1.4 and 1.5 bind a DD-03 closure `lambda model_id, prompt: aoai_client.chat_completion(model_id, prompt, deployment_ref=work_item.deployment_ref)`, preserving the two-positional-arg `response_provider` contract while routing to the candidate's owned deployment. Independently verified against source: `FoundryQualitySafetyEvalClient.response_provider: Callable[[str, str], str | None]` (quality_safety_eval_client.py:210) and both call sites `self.response_provider(model_id, prompt)` (lines 360, 452) match the closure's two-positional-arg shape exactly. Tagged DD-03 on plan Steps 1.2/1.4.

* DD-04 (NEW - found during 2026-07-24 re-validation of DD-03): the Steps 1.4/1.5 closure binds `deployment_ref=work_item.deployment_ref`, but `EvaluatorWorkItem.deployment_ref` is typed `DeploymentRef` (src/shared/contracts.py:104), a dataclass with fields `resource_id`/`deployment_name`/`region`/`deployment_type` - not a `str`. `aoai_client.chat_completion`'s `deployment_ref` parameter (Step 1.2) is typed `str | None`, so the closure passes a `DeploymentRef` object where a deployment-name string is required.
  * Research recommends: N/A (discovered during Details re-validation, not present in original research doc).
  * Plan implements (Details Steps 1.4/1.5): `deployment_ref=work_item.deployment_ref` (whole object) instead of `deployment_ref=work_item.deployment_ref.deployment_name` (the string field `chat_completion` actually expects).
  * Rationale: none stated; reads as a copy-paste/shorthand slip in the Details text rather than a deliberate design choice.
  * Impact: medium (would be caught by Step 3.2's mypy/lint pass before merge, but as written the Details text does not compile/type-check against the real `DeploymentRef`/`chat_completion` contracts).
  * Resolution (ADDRESSED - applied 2026-07-24): Details Steps 1.4 and 1.5 closures now bind `deployment_ref=work_item.deployment_ref.deployment_name` (the `str` field), matching `chat_completion`'s `deployment_ref: str | None` parameter; Step 1.2 clarifies arg 1 is `model_id` and the closure passes the deployment-name string. Step 1.4 Discrepancy references now include DD-04; plan Steps 1.4/1.5 tagged DD-04.
  * Re-confirmed (THIRD re-validation, 2026-07-23 pass 3): Details Step 1.4 (line 93) still reads `lambda model_id, prompt: aoai_client.chat_completion(model_id, prompt, deployment_ref=work_item.deployment_ref.deployment_name)`; Step 1.5 (line 117) still reads `deployment_ref=work_item.deployment_ref.deployment_name`. Re-verified against live source: `EvaluatorWorkItem.deployment_ref` is typed `DeploymentRef` (src/evaluator/models.py:67); `DeploymentRef.deployment_name` is a `str` field (src/shared/contracts.py:104-108, `@dataclass(slots=True)`). Both closures pass the `str` field, not the `DeploymentRef` object. No regression — DD-04 stays CLOSED.

### Reference Integrity

* RI-01: Step 3.1's details citation ("Lines 368-386" in the plan's Implementation Checklist) overruns the actual Step 3.1 section, which spans details-file lines 368-382 (Step 3.2's header is verified at line 383); the cited range bleeds 4 lines into Step 3.2's own content.
  * Source: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Step headers verified at lines 368, 383, 392 via grep).
  * Citation: Plan Implementation Checklist Step 3.1 cites "(Lines 368-386)"; correct range is approximately 368-382.
  * Impact: low (misleads a reader jumping straight to the cited range; does not change task substance).
  * Re-verified (THIRD re-validation, 2026-07-23 pass 3): Step 1.9's growth (adding `src/reporter/models.py`/`aggregator.py`/`decision_engine.py` to its Files list) shifted every subsequent header by +2 lines versus the pass-2 state above. Re-grepped all 24 headers (Phase 1/2/3 section headers + Steps 1.1-1.10, 2.1-2.7, 3.1-3.3) against the CURRENT Plan citations: Step 3.1 header is now at details-file line 379 (next header 394), and the Plan's checklist cites "(Lines 379-393)" - an exact match, correctly re-synced from the pass-2 value (377-391). All 20 step citations (1.1 through 3.3) match their current verified header boundaries exactly; no new drift was introduced. Note: this Discrepancy Log's own resolution text above (377-391) is now stale relative to the current re-synced value (379-393) - this is historical narrative describing the pass-2 state, not a live citation an implementer follows (the Plan's own citation is current and correct), so it is not logged as a new RI; see the pass-3 note added to the Planning Log's closing summary for the historical-narrative caveat.

* RI-02: Step 3.2's details citation ("Lines 388-397") both skips the first 5 lines of its own section (header at verified line 383) and overruns 5 lines into Step 3.3 (header verified at line 392).
  * Source: .copilot-tracking/details/2026-07-23/real-quality-safety-gates-details.md (Step headers verified at lines 383, 392 via grep).
  * Citation: Plan Implementation Checklist Step 3.2 cites "(Lines 388-397)"; correct range is approximately 383-391.
  * Impact: low.
  * Resolution (ADDRESSED - re-confirmed 2026-07-24 re-validation): Step 3.2 now spans details lines 392-400 and the plan citation was updated to "(Lines 392-400)"; Step 3.3 to "(Lines 401-403)" to match the current verified header boundaries. Note: Step 3.3's actual section (header at 401, next "## Dependencies" heading at 405) technically spans 401-404 including its trailing blank separator line; the cited "401-403" excludes only that trailing blank line and captures all substantive content (header, blank, and the one content line) - negligible, not logged as a new RI since it does not misdirect a reader.
  * Re-verified (THIRD re-validation, 2026-07-23 pass 3): Same +2 shift as RI-01 above. Step 3.2 header is now at details-file line 394 (next header 403); Plan cites "(Lines 394-402)" - exact match. Step 3.3 header is now at line 403 (next heading "## Dependencies" at line 407); Plan cites "(Lines 403-405)", which correctly excludes the trailing blank separator line 406 (same negligible pattern noted in the pass-2 resolution, now at the shifted position) - not logged as a new RI. All Plan-to-Details citations for Steps 1.9 through 3.3 are confirmed re-synced and accurate as of this pass
  * Resolution (ADDRESSED - re-confirmed 2026-07-24 re-validation): Step 3.2 now spans details lines 392-400 and the plan citation was updated to "(Lines 392-400)"; Step 3.3 to "(Lines 401-403)" to match the current verified header boundaries. Note: Step 3.3's actual section (header at 401, next "## Dependencies" heading at 405) technically spans 401-404 including its trailing blank separator line; the cited "401-403" excludes only that trailing blank line and captures all substantive content (header, blank, and the one content line) - negligible, not logged as a new RI since it does not misdirect a reader.

## Implementation Paths Considered

### Selected: Reuse the validated quality_safety_eval_client seam via a thin provider

* Approach: New `aoai_client.chat_completion` feeds `FoundryQualitySafetyEvalClient.response_provider`; new `Live*Runner` classes adapt `RawEvalSignals` into existing result contracts. No new client.
* Rationale: Council C1 + Decision #48 de-risker; lowest risk, reuses live-validated code, matches the injectable seam already in service.py.
* Evidence: research doc (seam facts); src/evaluator/quality_safety_eval_client.py (response_provider callback).

### IP-01: Greenfield live evaluation client

* Approach: Write a fresh Foundry-backed evaluator client dedicated to the promotion gate.
* Trade-offs: Full control over shape, but duplicates validated logic, re-opens the AOAI-route class of bugs Decision #48 fixed, and violates C1.
* Rejection rationale: Explicitly barred by Council C1 (no forking); higher risk on a HIGH-risk RAI surface.

### IP-02: Absolute-threshold-only gate (no relative-to-retiring)

* Approach: Keep only the existing `quality_gates` floors.
* Trade-offs: Simpler, but cannot express "candidate must not regress vs the retiring model" and misses the RAI relative-comparison intent.
* Rejection rationale: User + RAI require relative-to-retiring scoring; superseded by the selected BOTH approach (DD-01).

## Suggested Follow-On Work

* WI-01: Extend live coverage beyond Baseline+Jailbreak attack strategies once the initial gate has a production track record — (low)
  * Source: Council bounded-execution condition (currently pinned to two strategies).
  * Dependency: Human-gate track record (C13) proven.
* WI-02: Add gold-answer references to a QA fixture to enable real groundedness scoring — (low)
  * Source: DR-02.
  * Dependency: none (independent data work).
* WI-03: Auto-promotion enablement (remove human gate) after judge/probe-set/canary track record is proven — (medium)
  * Source: C13 (explicitly deferred until track record).
  * Dependency: WI in production for a proving period; RAI sign-off.
* WI-04: CI wiring for the opt-in live path (workflow_dispatch, OIDC, cost gate) mirroring WI-02 CI posture — (medium)
  * Source: WI-01/WI-02 STOP-AND-GATE (no cost-manager seat in current roster).
  * Dependency: explicit cost acknowledgment + user approval.

## Open Decision Pending User Input

* PD-01: Independent judge deployment source AND safety classifier backend. Blocks Task 2.2 (and finalizes Task 1.7 judge wiring). Presented to the user in the response; default recommendation recorded there. Until resolved, Task 2.2 remains blocked and Task 1.7 uses a placeholder pinned judge from config.
