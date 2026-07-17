<!-- markdownlint-disable-file -->
# Planning Log: GPT-4.1 Retirement Alternatives Live Foundry Flow

## Discrepancy Log

Gaps and differences identified between research findings and the implementation plan.

### Unaddressed Research Items

* DR-01: Microsoft Learn parser-update governance and ownership process is not yet codified in repository docs.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 582-584)
  * Reason: Operational process decision outside core implementation scope.
  * Impact: low

### Resolved by Planning Defaults

* RD-01: Candidate scope policy resolved.
  * Decision: v1 supports Azure OpenAI models sold by Azure only; partner/community models are excluded.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 554-557)
* RD-02: Baseline decision policy resolved.
  * Decision: Recommendation requires either baseline comparison against retiring deployment or explicit threshold-only mode flagged `advisory_only`; no automatic winner in advisory-only mode.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 577-578)
* RD-03: Data retention/PII baseline policy resolved.
  * Decision: Default retention 30 days for raw prompts/responses, 180 days for aggregate metrics; redact configured sensitive fields before persistence; encryption at rest required.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 574-576)
* RD-04: Candidate-count fallback policy resolved.
  * Decision: Attempt up to 3 ranked candidates; allow up to 2 replacement attempts for provision failures; if fewer than 2 successful evaluations, output `incomplete_comparison` and no winner.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 563-566)
* RD-05: GPT-4.1 compatibility profile resolved.
  * Decision: Required compatibility gates are `chat_completions`, `responses`, `function_calling`, `structured_outputs`, text input; optional gates are image input and fine-tuning. Missing required gates disqualifies candidate.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 558-562)
* RD-06: Budget and approval authority resolved.
  * Decision: Default limits are `max_cost_per_run_usd=30`, `max_cost_per_target_usd=12`, `max_cost_per_month_usd=250`; live provisioning requires GitHub protected environment approval by repository `CODEOWNERS` plus environment reviewers.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 567-568)
* RD-07: Data residency semantics resolved.
  * Decision: v1 enforces exact-region residency for discovered source deployment region and disallows Global deployments unless `allow_global_residency=true` is explicitly approved.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 569-570)
* RD-08: Quota substitution behavior resolved.
  * Decision: On quota/access failure, try next ranked candidate until attempt cap is reached; do not retry same candidate with different version automatically.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 571-573)
* RD-09: Durable evaluation result persistence ownership resolved.
  * Decision: `src/evaluator/result_writer.py` is explicitly implemented in Phase 5.1 to persist completion manifests and hash-verified result summaries to blob.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Line 265)
* RD-10: Manifest builder ownership resolved.
  * Decision: `src/history/manifest_builder.py` refactor is explicitly assigned to Phase 4.2.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Line 261)
* RD-11: Remediation scope guardrail resolved.
  * Decision: remediation generation is constrained to Bicep IaC files only and explicitly excludes APIM/routing or production traffic-switch edits.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 579-581)
* RD-12: Workflow confirmation-gate regression testing resolved.
  * Decision: Step 6.2 includes workflow-configuration tests that fail when protected-environment approval and `ENABLE_SCHEDULED_PROVISIONING` guards are absent for live provisioning jobs.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 462-464)

### Plan Deviations from Research

* DD-01: Integration test rollout is staged after domain/source/provisioning core changes.
  * Research recommends: Early integration tests in parallel with adapter introduction.
  * Plan implements: Unit-first, then integration tests once safety gates and adapters are stable.
  * Rationale: Reduces flakiness while API contracts are still evolving.
* DD-02: Docker evaluator image work is placed in Phase 5 instead of early infra phase.
  * Research recommends: Image scaffolding earlier to validate package compatibility.
  * Plan implements: Image and runtime introduced with actual ACA evaluator integration.
  * Rationale: Avoids maintaining placeholder image work before runner interface is finalized.

### Reference Integrity

* RI-01: DR-03 and DR-04 previously cited line ranges (569-572 and 557-562 respectively) that resolve to different "Risks and Product Decisions Required" items than the ones described (data residency/quota text and catalog-scope/GPT-4.1-policy text, not PII/retention or candidate-count). Citations corrected in this validation pass; see DR-03, DR-04, DR-05, DR-07, DR-08 above.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 554-584)
  * Citation: Prior DR-03 Source (Lines 569-572) and DR-04 Source (Lines 557-562)
  * Impact: resolved - originally high (miscitation concealed unresolved risks #2, #5, and #6); re-verified in this validation pass against research lines 554-584, all corrected citations confirmed accurate
* RI-02: DR-01 and DR-02 previously cited line ranges (547-555 and 573-578) that partially overlap unrelated content (Recommended Implementation Sequence items 5-8, and risks #6/#7) before reaching the correct topic. Citations narrowed in this validation pass.
  * Source: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 547-557, 573-578)
  * Citation: Prior DR-01 Source (Lines 547-555) and DR-02 Source (Lines 573-578)
  * Impact: resolved - originally low (topic assignment was still directionally correct, only line precision was off); re-verified in this validation pass, narrowed citations confirmed accurate
* RI-03: Follow-on work dependencies now reference resolved default policies instead of unresolved DR IDs.
  * Source: .copilot-tracking/plans/logs/2026-07-17/gpt-41-retirement-alternatives-live-foundry-log.md (Suggested Follow-On Work)
  * Impact: resolved

## Implementation Paths Considered

### Selected: Path A - SDK-first live orchestration with fixture-compatible fallback

* Approach: Keep existing module boundaries, add source/provisioning/evaluation adapters using Azure SDKs, preserve fixture implementations for deterministic tests.
* Rationale: Delivers requested behavior while minimizing architecture churn and preserving testability.
* Evidence: .copilot-tracking/research/subagents/2026-07-17/gpt-41-retirement-alternatives-repo-analysis.md (Lines 583-590)

### IP-01: Workflow-centric orchestration via Azure CLI scripts

* Approach: Implement most behavior directly in GitHub workflow steps and shell scripts.
* Trade-offs: Faster initial prototype, but brittle parsing, weak local testability, and business logic duplicated across workflow and Python.
* Rejection rationale: Conflicts with existing Python domain architecture and would reduce determinism and maintainability.

### IP-02: Replace existing services with full rewrite around new architecture

* Approach: Rebuild detector/recommender/provisioner/evaluator/reporter from scratch.
* Trade-offs: Cleaner initial design but high migration risk and loss of existing tested fixture workflow.
* Rejection rationale: Unnecessary risk for current objective; extension path is sufficient and safer.

## Suggested Follow-On Work

* WI-01: Add pricing API integration for stronger budget estimates - Integrate Azure retail pricing lookup with cached SKU pricing confidence levels. (medium)
  * Source: Research and budget-gate requirements.
  * Dependency: Phase 4 provisioning and policy gates complete.
* WI-02: Add model-family compatibility profile library - Encode workload-specific compatibility contracts (API/tooling/context window/latency) per retiring model family. (high)
  * Source: RD-05 compatibility defaults.
  * Dependency: Baseline production rollout of compatibility policy.
* WI-03: Add compliance retention automation - Implement automatic purge policies for blob/table artifacts aligned with approved retention durations. (high)
  * Source: RD-03 retention and redaction defaults.
  * Dependency: Security/privacy sign-off for automated purge enforcement.
* WI-04: Add provider expansion mode - Optional support for non-Azure OpenAI Foundry providers after Azure OpenAI path is stable. (low)
  * Source: Candidate-scope policy discussion.
  * Dependency: Path A production readiness and policy approval.