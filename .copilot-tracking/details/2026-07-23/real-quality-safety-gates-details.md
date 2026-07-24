<!-- markdownlint-disable-file -->
# Implementation Details: Make the Evaluator's Quality + Safety Gates Real

## Context Reference

Sources: .copilot-tracking/research/2026-07-23/real-quality-safety-gates-research.md (verified codebase facts, Council #51 conditions, open decisions); /memories/repo/squad-decision-51-council-verdict-eval-runners.md (13 binding conditions); /memories/repo/squad-council-verdict-wi01-wi02-foundry-eval.md (WI-01/WI-02 seam posture). Governing verdict: Council Decision #51 Go-With-Conditions, RAI HIGH-risk caveat controls the human gate.

Global rules for every step:
* Live SDKs (`openai`, `azure-identity`, `azure-ai-evaluation`) imported INSIDE method bodies or under `TYPE_CHECKING` only; module import must succeed with the `[evaluation]` extra absent. Missing extra -> raise `src.shared.errors.DependencyUnavailableError`.
* No API keys anywhere; keyless AAD only. Never log or serialize credentials, tokens, or endpoint FQDNs.
* Fakes (`LocalCustomRunner`/`LocalRedTeamRunner`) stay DEFAULT; live is opt-in only.
* Every live output is explicitly labeled NON-promotion-grade / advisory; nothing auto-promotes.
* Right-size for the 20-row dev-hub dataset: sequential rows, bounded objectives, no concurrency/queues.

## Implementation Phase 1: Live-Backed Runners (Make the Signal Real)

<!-- parallelizable: false -->

### Step 1.1: Add additive per-model API-shape config to config/models.yaml + loader

Add a new top-level `model_api_shapes:` section to config/models.yaml (additive; `watch_list` untouched). Encode capability-driven request shaping so the provider adapts per candidate:
* `o3` (and reasoning family): omit `temperature`, omit `system` role (fold system guidance into the user turn), use `max_completion_tokens` (not `max_tokens`).
* `gpt-5.1` (and standard chat family): standard chat messages, `temperature: 0`, `seed` set for reproducibility, `max_tokens`.
Provide a `default` shape and a documented match order (exact model_id -> family prefix -> default).

Files:
* config/models.yaml - add `model_api_shapes` section with `default`, `o3`, `gpt-5.1` entries and inline comments.
* src/evaluator/aoai_client.py (created in 1.2) reads this via a small loader helper (or add to src/shared/config.py if a config loader already centralizes YAML reads — confirm during implementation and prefer the existing loader).

Discrepancy references:
* Addresses C2 (thin provider must shape requests per capability). DR-01 notes models.yaml lacks this section today.

Success criteria:
* `model_api_shapes` present and parseable; runtime recommender/detector unaffected (additive keys ignored elsewhere).
* Match order documented; `default` shape defined.

Dependencies:
* None (config + pure loader).

### Step 1.2: Create src/evaluator/aoai_client.py — candidate response provider

Create a thin, import-guarded Azure OpenAI chat client exposing exactly:
`chat_completion(model_id: str, prompt: str, *, deployment_ref: str | None = None) -> str | None`.

CRITICAL (DD-03): the seam invokes `self.response_provider(model_id, prompt)` (verified quality_safety_eval_client.py:360,452) — the FIRST positional arg is the CANDIDATE `model_id`, NOT an AOAI deployment name. `chat_completion` must therefore treat arg 1 as `model_id` and RESOLVE the actual deployment before the HTTP call.

Behavior:
* Resolve `deployment_name` from, in order: the explicit `deployment_ref` keyword (bound by the runner closure, Step 1.4/1.5), else a `model_id -> deployment` map read from config (additive `deployments:` block in config/models.yaml, Step 1.1), else `model_id` itself as a last resort. Fail to `None` (never a fabricated response) if no owned deployment resolves.
* Look up the Step 1.1 `model_api_shapes` keyed by `model_id` (the model family drives request shape: o3 vs gpt-5.1), and target the RESOLVED `deployment_name` in the request path.
* Construct `DefaultAzureCredential` INSIDE the method body; acquire a bearer token for scope `https://cognitiveservices.azure.com/.default`. No key path; if a key ever exists it comes only from Key Vault/env and is redacted (out of scope here — keyless only).
* Import `openai` (or `azure.ai.evaluation` inference helper) inside the method; on ImportError raise `DependencyUnavailableError` with a sanitized message (no stderr echo of secrets).
* Derive the AOAI endpoint from the owned Foundry project via `derive_aoai_endpoint` (reuse the seam helper); never accept a third-party endpoint.
* Return the assistant message string, or `None` on any failure (after the Step 1.3 resilience wrapper is exhausted) — never a fabricated/default response.
* The seam-facing signature `(model_id, prompt) -> str | None` MUST match `FoundryQualitySafetyEvalClient.response_provider`'s `Callable[[str, str], str | None]`. The runner supplies `deployment_ref` by binding a closure/partial (Step 1.4/1.5) so the two-positional-arg contract is preserved.

Files:
* src/evaluator/aoai_client.py - new module.
* config/models.yaml - additive `deployments:` map (model_id -> owned deployment name), alongside Step 1.1 `model_api_shapes`.

Discrepancy references:
* Addresses C2, C5, DD-03.

Success criteria:
* Module imports with `[evaluation]` absent (guard test green).
* Seam-facing signature matches `response_provider` (two positional args); `model_id` resolves to an owned deployment before any call.
* No key args/env; credential built in-method; endpoint owned-only.

Dependencies:
* Step 1.1 (API-shape config).

### Step 1.3: Resilience wrapper for provider calls

Wrap the network call in `aoai_client.chat_completion` with bounded retry:
* Exponential backoff + full jitter, 3-5 attempts, on 429 / 5xx / timeout only.
* Honor `Retry-After` when present.
* Per-request timeout 30-60s.
* Rows processed sequentially (no concurrency).
* On exhaustion: return `None` (UNSCORED) for that item — never a default pass. Non-retryable errors (4xx auth/validation except 429) fail fast to `None`.

Files:
* src/evaluator/aoai_client.py - internal `_with_retry` helper (private).

Discrepancy references:
* Addresses Architect resilience condition; complements C10/C11 UNSCORED-not-pass semantics (already the seam's per-(row,dim) behavior).

Success criteria:
* Retries only on 429/5xx/timeout; respects Retry-After; deterministic UNSCORED on exhaustion.
* Unit test with a fake transport asserts backoff attempts and `None` on exhaustion (no live calls).

Dependencies:
* Step 1.2.

### Step 1.4: Create LiveCustomRunner (delegates to the seam)

Create `LiveCustomRunner` in src/evaluator/custom_runner.py (alongside `LocalCustomRunner`) with the SAME contract: `run(work_item, dataset) -> CustomEvaluationResult`.

Behavior:
* Construct a `FoundryQualitySafetyEvalClient` (import-guarded) with `azure_ai_project` from config, a PINNED independent `judge_model` (see Step 1.7), `probe_prompts` = dataset prompts, and `response_provider` = a closure that binds the CANDIDATE deployment NAME (a `str`, DD-04): `lambda model_id, prompt: aoai_client.chat_completion(model_id, prompt, deployment_ref=work_item.deployment_ref.deployment_name)` (DD-03 adapter — preserves the two-positional-arg seam contract while routing to the candidate's owned deployment; `deployment_ref` is typed `str | None`, so pass `.deployment_name`, NOT the `DeploymentRef` object).
* Call `evaluate_model(work_item.candidate_model_id)` -> `RawEvalSignals`.
* Map signals into `CustomEvaluationResult`: build per-row `rows` from the dataset + captured responses; derive quality via `derive_quality_score`; set `aggregates["overall"]` from the normalized quality score so `service.py`'s summary contract (`aggregates["overall"]`) is honored. Preserve `dataset_sha256`.
* UNSCORED (`None`) dims are recorded as `null` in rows and EXCLUDED from `overall` (never coerced to 0 or 1). If `overall` is UNSCORED, emit an advisory `overall: null` and mark the summary NON-promotion-grade (Step 1.9) rather than a passing float.

Files:
* src/evaluator/custom_runner.py - add `LiveCustomRunner`.

Discrepancy references:
* Addresses C1, C3, C10, DD-04.

Success criteria:
* Same `run` signature as `LocalCustomRunner`; returns a valid `CustomEvaluationResult`.
* Delegates to `quality_safety_eval_client.py` (no forked scoring).
* UNSCORED handled without fabricating a pass.

Dependencies:
* Steps 1.2, 1.7.

### Step 1.5: Create LiveRedTeamRunner (delegates to the seam)

Create `LiveRedTeamRunner` in src/evaluator/redteam_runner.py (alongside `LocalRedTeamRunner`) with the SAME contract: `run(work_item, dataset) -> RedTeamEvaluationResult`.

Behavior:
* Reuse the seam's red-team path (`FoundryQualitySafetyEvalClient` red-team scan): own-deployment scope-lock (`assert_owned_target`), `ALLOWED_ATTACK_STRATEGIES=("Baseline","Jailbreak")`, bounded `num_objectives`, `skip_upload=True`. Bind the same DD-03 candidate-deployment closure for `response_provider` as Step 1.4, passing the deployment NAME string (DD-04): `deployment_ref=work_item.deployment_ref.deployment_name`.
* Convert `overall_asr` (0..100) into `block_rate = 1 - asr/100` and build the `attacks` list from `per_risk_asr` (per-category block rates). Preserve `dataset_sha256`.
* In Phase 1 this consumes the seam's aggregate ASR. Phase 2 (Step 2.2) layers the separate probe set + classifier-based block judging on top; keep the Phase 1 code structured so Step 2.2 slots in without a rewrite.
* UNSCORED ASR -> advisory `block_rate: null`, NON-promotion-grade summary (never a passing 1.0).

Files:
* src/evaluator/redteam_runner.py - add `LiveRedTeamRunner`.

Discrepancy references:
* Addresses C1, C3, C11 (partial — probe set + classifier completed in Phase 2).

Success criteria:
* Same `run` signature as `LocalRedTeamRunner`; returns a valid `RedTeamEvaluationResult`.
* Own-deployment scope-lock enforced; bounded objectives; `skip_upload=True`.

Dependencies:
* Steps 1.2, 1.7.

### Step 1.6: Wire --live / MUA_EVAL_MODE into service.py runner selection

Add opt-in live selection to `execute_local_evaluation` / its CLI:
* CLI: add `--live` flag to the argparse parser in src/evaluator/service.py.
* Env: `MUA_EVAL_MODE=live` also enables live (CLI flag wins over env).
* When live: inject `LiveCustomRunner()` / `LiveRedTeamRunner()`; otherwise keep the `None`-default fakes. The injectable `custom_runner`/`redteam_runner` params still override both (for tests).
* Default and CI path: fakes; no Azure creds required.

Files:
* src/evaluator/service.py - add `--live` arg, env read, runner selection branch.

Discrepancy references:
* Addresses C4.

Success criteria:
* No flag/env -> fakes (unchanged behavior); `--live` or `MUA_EVAL_MODE=live` -> live runners; explicit injected runners still win.

Dependencies:
* Steps 1.4, 1.5.

### Step 1.7: Enforce independent judge (judge != candidate)

Add a pinned, INDEPENDENT judge configuration and an assertion:
* Source the judge deployment name + pinned model + version from config (env `JUDGE_MODEL` already exists in azure.env.example; add pinned `judge_model_version` + `rubric_version` keys additively to config/evaluation.yaml).
* Assert `judge_model != work_item.candidate_model_id` AND judge is not in the candidate's model family; refuse (raise) when violated so a candidate can never grade itself.
* Publish the rubric version alongside scores (feeds Step 2.5 auditability).

Files:
* src/evaluator/custom_runner.py (LiveCustomRunner) - judge-independence assertion.
* config/evaluation.yaml - additive `judge_model_version`, `rubric_version` keys (does not alter existing `quality_gates`).

Discrepancy references:
* Addresses C10.

Success criteria:
* Judge is fixed, independent, pinned (model+version); self-grading is refused.
* Rubric version recorded.

Dependencies:
* Step 1.4.

### Step 1.8: Security redaction + red-team transcript segregation

Add a redaction pass and segregate sensitive evidence:
* Redaction helper applied to all logs AND result JSON: strip/replace bearer tokens, any key material, and endpoint FQDNs; log deployment NAMES only, never URLs. Sanitize `DependencyUnavailableError` messages (no stderr echo of secrets).
* Red-team raw transcripts (prompts + responses + rationale) written ONLY to `results/redteam/{run_id}/...` and ensure that path is git-ignored and NOT matched by any `.github/workflows/detect-and-eval.yml` upload glob (verified today it uploads only `.artifacts/*` + run-context/finalize). Public summary keeps aggregates only.

Files:
* src/evaluator/redteam_runner.py (LiveRedTeamRunner) - transcript sink to results/redteam/.
* src/shared/ (new small redaction util, or extend an existing logging util — confirm during implementation) - redaction helper.
* .gitignore - ensure results/redteam/ is ignored (add if absent).

Discrepancy references:
* Addresses C6, C7, C8, C9.

Success criteria:
* No credential/endpoint/token appears in logs or result JSON (unit-tested with a redaction fixture).
* Red-team transcripts land only in git-ignored results/redteam/ and are absent from CI artifact globs.
* Model output and probes handled as DATA only (no eval/exec/control-flow use).

Dependencies:
* Steps 1.4, 1.5.

### Step 1.9: Label live outputs NON-promotion-grade (advisory)

Every live summary/result carries an explicit advisory flag AND the downstream reporter must honor it (DR-03):
* Add `promotion_grade: false` and `advisory: true` (or equivalent) plus a short rationale string to the live summary dict in service.py's live branch.
* Live runners NEVER return a promotion decision; they return measurements the human gate (Step 2.6) interprets.
* Thread the flag through the FULL reporter pipeline so a live/advisory run can never emit an automatic `verdict: "winner"`. The verified chain is: `src/reporter/artifact_loader.py` reads `summary.json` -> builds `CandidateArtifacts` (`src/reporter/models.py`) -> `src/reporter/aggregator.py::aggregate_reporter_run()` folds `CandidateArtifacts` into `CandidateComparison` (`src/reporter/models.py`) -> `src/reporter/decision_engine.py` reads ONLY `CandidateComparison`. Therefore the flag must be added as a field on BOTH `CandidateArtifacts` AND `CandidateComparison` in `models.py`, populated by `artifact_loader.py`, carried across by `aggregator.py`, and finally consumed by `decision_engine.py` which, when `advisory`/`promotion_grade == false`, downgrades its verdict to a non-promoting `needs_human_review` state instead of a `winner` computed from raw `custom_overall`/`redteam_block_rate`.

Files:
* src/evaluator/service.py - stamp advisory flags on the live summary.
* src/reporter/artifact_loader.py - read `promotion_grade`/`advisory` from summary JSON and populate the new `CandidateArtifacts` field.
* src/reporter/models.py - add `promotion_grade`/`advisory` (advisory defaults preserving existing behavior for non-live summaries) to BOTH `CandidateArtifacts` and `CandidateComparison`.
* src/reporter/aggregator.py - carry the flag from `CandidateArtifacts` into `CandidateComparison` in `aggregate_reporter_run()`.
* src/reporter/decision_engine.py - suppress `winner` verdict when advisory; emit `needs_human_review`.

Discrepancy references:
* Addresses RAI HIGH-risk caveat + C13 (no auto-promotion) + DR-03.

Success criteria:
* Live summary is unambiguously advisory; no code path (service OR reporter) promotes on a live score.
* Reporter unit test: an advisory summary yields `needs_human_review`, never `winner`; verify the flag survives `aggregate_reporter_run()` (CandidateArtifacts -> CandidateComparison).

Dependencies:
* Step 1.6.

### Step 1.10: Validate Phase 1 changes

Run the import-guard test (module imports with `[evaluation]` absent) and the fake-injected unit tests; run a `--live` smoke ONLY in `.venv-live` behind explicit approval (Council STOP-AND-GATE for live Azure execution). Do not run live in CI.

Validation commands:
* `.venv/Scripts/python.exe -m pytest tests/unit -q` - offline suite green (fakes, no creds).
* `.venv/Scripts/python.exe -c "import src.evaluator.aoai_client"` - guard import succeeds without the extra.

## Implementation Phase 2: Real Adversarial Gate (Judgment Integrity)

<!-- parallelizable: false -->

### Step 2.1: Create the versioned, hashed adversarial probe set

Author a SEPARATE probe dataset (NOT `general_qa.jsonl`) with 5 categories, 5-10 probes each:
1. jailbreak / instruction-override
2. harmful-content elicitation
3. PII extraction
4. prompt-injection (including indirect/embedded)
5. TOS / CoC-violating requests
Requirements:
* New file, e.g. datasets/adversarial_probes.jsonl (or a versioned dir), each row tagged with `category` + stable `id`.
* Compute and record a SHA-256 over the file content; version the set (e.g. `probe_set_version`).
* No real PII in fixtures (regulated-data hygiene); probes describe intent without operational harmful payloads where feasible; transcripts stay in results/redteam/ (Step 1.8).

Files:
* datasets/adversarial_probes.jsonl - new versioned probe set.
* (loader) src/evaluator/ - a small probe-set loader returning rows + sha256 + version (mirror existing dataset_loader conventions).

Discrepancy references:
* Addresses C11 (separate versioned hashed probe set).

Success criteria:
* 5 categories x 5-10 probes; SHA-256 + version recorded; disjoint from general_qa.

Dependencies:
* None (data + loader).

### Step 2.2: Real block-judging (classifier primary + optional judge; fail-closed)

Replace synthetic block logic with real judging in `LiveRedTeamRunner`:
* PRIMARY: a deterministic, INDEPENDENT safety classifier decides blocked/not-blocked per probe response (choice pending PD-01: Azure AI Content Safety evaluators vs azure-ai-evaluation RedTeam ASR).
* OPTIONAL: a judge model as a secondary signal.
* Keyword heuristics MAY contribute but are NEVER the sole judge.
* Combine signals; on disagreement, resolve to NOT blocked (fail-closed) so ambiguity counts against the candidate.
* Remove the hard-coded nano rule from `LocalRedTeamRunner` (OD-2): replace with a probe-category-driven deterministic fixture pattern so canary tests stay meaningful without arbitrary model-name coupling.

Files:
* src/evaluator/redteam_runner.py - LiveRedTeamRunner real judging; LocalRedTeamRunner fixture rework.

Discrepancy references:
* Addresses C11 (classifier + judge, fail-closed) and DR/OD-2 (nano rule removal).

Success criteria:
* Classifier is primary + deterministic + independent; keywords not sole; disagreement -> NOT blocked.
* Nano rule gone; fake produces deterministic, category-driven results.

Dependencies:
* Steps 1.5, 2.1, PD-01 resolution.

### Step 2.3: Relative-to-retiring scoring (candidate >= retiring - epsilon)

Make the gate relative rather than absolute-only:
* For quality and block-rate, compare the candidate against the retiring baseline (`gpt-5.6-sol` per user; `work_item.retiring_model_id`/`retiring_model_version`).
* Gate condition: `candidate_metric >= retiring_metric - epsilon`.
* Add additive `epsilon` (quality + redteam) keys to config/evaluation.yaml alongside the existing absolute `quality_gates` (both may apply: absolute floor AND relative-to-retiring).
* Record the retiring baseline value used in the summary/audit bundle.

Files:
* config/evaluation.yaml - additive `relative_gate` block (`quality_epsilon`, `redteam_epsilon`).
* src/evaluator/service.py - relative comparison in the live summary; keep absolute thresholds too.

Discrepancy references:
* Addresses RAI relative-comparison condition.

Success criteria:
* Gate evaluates `candidate >= retiring - epsilon`; retiring baseline captured; absolute floor preserved.

Dependencies:
* Steps 1.4, 1.5.

### Step 2.4: Anti-regression canaries

Add automated canaries that fail the run when scoring is untrustworthy:
* POISON canary: a known-healthy model MUST refuse a known-bad probe; if it "passes" everything, the scorer is broken -> fail.
* DISCRIMINATION canary: a known-bad response MUST score below threshold; if it passes, the judge is broken -> fail.
* SUSPICIOUS-UNIFORMITY flag: `block_rate == 1.0` exactly, or identical `custom_overall` across all candidates, is flagged as likely stubbed/constant output (bans constant returns).

Files:
* tests/unit/ (canary tests) + a runtime uniformity check in src/evaluator/service.py (or the live runners) that surfaces the flag in the summary.

Discrepancy references:
* Addresses C12.

Success criteria:
* Poison + discrimination canaries present as automated tests; uniformity flag surfaces on constant/1.0 outputs.

Dependencies:
* Steps 2.2, 2.3.

### Step 2.5: Per-run auditability bundle

Emit a complete audit bundle per run (to results/, transcripts under results/redteam/):
* Raw prompts, responses, judge/classifier rationale (redteam sink only).
* Scorer/judge version + deployment ID + temperature + rubric version.
* Dataset SHA-256 for BOTH the QA set and the adversarial probe set + probe_set_version.
* Thresholds (absolute + epsilon), scores, per-item pass/fail, retiring baseline used.
* Decision + authorizer + timestamp fields (populated by the human gate, Step 2.6).

Files:
* src/evaluator/service.py + result_writer.py - extend the summary/audit payload with the above fields (additive to the existing summary contract).

Discrepancy references:
* Addresses RAI auditability + WI-02 RAI-7 (auditable entries).

Success criteria:
* Audit bundle contains all listed fields; both dataset hashes present; per-item pass/fail recorded.

Dependencies:
* Steps 2.2, 2.3, 2.4.

### Step 2.6: Human-in-the-loop gate (RECOMMENDS, human confirms)

Make promotion a human action:
* The live runner/service RECOMMENDS (advisory verdict + rationale); it does not promote.
* A human confirmation step records `decision`, `authorizer`, `timestamp` into the audit bundle; no auto-promotion until the judge/probe-set/canary track record is proven in production.
* Rubric is versioned (Step 1.7) and referenced in the recommendation.

Files:
* src/evaluator/service.py - advisory recommendation + audit fields for human decision; document the gate in docs/ (e.g. a short runbook note).
* src/reporter/decision_engine.py - consumes the advisory flag (Step 1.9 wiring) to emit `needs_human_review` instead of `winner` (DR-03).

Discrepancy references:
* Addresses C13, DR-03.

Success criteria:
* No code path auto-promotes; recommendation + human decision fields present; rubric versioned.

Dependencies:
* Steps 2.4, 2.5, 1.9.

### Step 2.7: Validate Phase 2 changes

Run canary tests + fake-injected unit tests offline; live probe-set + classifier validation runs opt-in in `.venv-live` against the two live deployments behind explicit approval, then deployments torn down.

Validation commands:
* `.venv/Scripts/python.exe -m pytest tests/unit -q` - green offline (canaries as automated tests).

## Implementation Phase 3: Test Strategy + Full Validation

<!-- parallelizable: false -->

### Step 3.1: Unit tests (fakes injected; no Azure creds)

* Guard-import test: all new modules import with `[evaluation]` absent.
* `aoai_client` retry/UNSCORED tests via a fake transport (no network).
* Live runner adaptation tests via a Stub `QualitySafetyEvalClient` injected in place of Foundry (deterministic RawEvalSignals -> result mapping).
* Redaction test: no token/key/FQDN in emitted logs/JSON.
* Canary tests (poison, discrimination, uniformity).
* Judge-independence refusal test.

Files:
* tests/unit/test_aoai_client.py, tests/unit/test_live_runners.py, tests/unit/test_redaction.py, tests/unit/test_canaries.py (names indicative).

Success criteria:
* All new behavior covered offline with fakes/stubs; CI needs no Azure creds.

### Step 3.2: Full validation + opt-in live check

* Run full unit suite; run `python -m mypy`/lint per repo config on changed files.
* Live opt-in check in `.venv-live` against the independent judge + candidate deployments (STOP-AND-GATE: explicit user approval + cost ack), capturing an audit bundle; then tear down the two live deployments.

Validation commands:
* `.venv/Scripts/python.exe -m pytest tests/unit -q`
* repo lint/type commands on changed files.

### Step 3.3: Report blocking issues

Document any issue needing more research; provide next steps rather than large inline fixes.

## Dependencies

* Python 3.12; `.venv` (offline, default) and `.venv-live` (has `[evaluation]` extra).
* Existing `src/evaluator/quality_safety_eval_client.py` seam (validated, Decision #48).
* Two live Azure OpenAI deployments (independent judge + candidate) for opt-in live tests only; torn down after.

## Success Criteria

* Live runners produce real quality + red-team signals via the reused seam; fakes remain default; live is opt-in.
* All 13 Council #51 conditions have a mapped, verifiable task; nothing auto-promotes; no Azure resources mutated (inference only).
