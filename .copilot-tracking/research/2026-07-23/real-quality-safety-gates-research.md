<!-- markdownlint-disable-file -->
# Task Research: Make the Evaluator's Quality + Safety Gates Real (Live-Backed Promotion Runners)

Make the promotion-gate evaluator surface real: replace the deterministic fake `LocalCustomRunner` / `LocalRedTeamRunner` scores with LIVE, Azure-backed quality judges and red-team ASR, routed through the already-validated `src/evaluator/quality_safety_eval_client.py` seam. Fakes stay the DEFAULT (offline/CI); live is strictly OPT-IN. This is the Council Decision #51 "plan of record"; every task maps to a binding condition.

This research doc grounds the plan in verified codebase facts. It is distinct from the 2026-07-22 work, which targeted the RECOMMENDER benchmark cache (`config/quality_safety_benchmarks.yaml` via `scripts/refresh_quality_safety_benchmarks.py`), NOT the promotion-gate runners.

## Scope and Success Criteria

* Scope: research + design only. Only writes are this artifact and the planning files under `.copilot-tracking/`. No source edits, no live Azure calls.
* Success Criteria:
  * Injectable-runner seam confirmed with exact signatures.
  * The `quality_safety_eval_client.py` reuse path confirmed with the exact delegation shape (`response_provider`).
  * Council Decision #51's 13 binding conditions mapped to concrete file targets.
  * One open decision surfaced for the user (judge deployment + safety classifier).

## Verified Codebase Facts

### Injectable-runner seam (`src/evaluator/service.py`)

* `execute_local_evaluation(repo_root, artifact_root, dataset_path, *, custom_runner=None, redteam_runner=None, aca_job_adapter=None)`.
* Defaults: `custom_runner=LocalCustomRunner()`, `redteam_runner=LocalRedTeamRunner()` when `None`.
* Summary dict consumes `custom_result.aggregates["overall"]` (float) and `redteam_result.block_rate` (float); includes `dataset_sha256`, `thresholds`, retiring/candidate blocks.
* Persists via `write_candidate_results(repo_root, run_id, CandidateEvaluationArtifacts(candidate_slug, custom, redteam, summary))`.
* CLI parser has NO `--live` flag today; runner selection is programmatic-only.

### Runner contract (`src/evaluator/custom_runner.py`, `src/evaluator/redteam_runner.py`)

* Both expose `run(work_item: EvaluatorWorkItem, dataset: EvaluationDataset) -> CustomEvaluationResult | RedTeamEvaluationResult`.
* `LocalCustomRunner`: derives deterministic rows from `work_item.candidate_score`; aggregates over `evaluator_names[:5]` -> `aggregates["overall"]`.
* `LocalRedTeamRunner`: 6 categories; contains a hard-coded synthetic rule `blocked = not (candidate_model_id.endswith("nano") and category == "jailbreak")`. This rule is a FAKE fixture and MUST NOT appear in any live runner; Phase 2 replaces synthetic block logic with real classifier judging.

### Work item + result contracts (`src/evaluator/models.py`)

* `EvaluatorWorkItem` fields include `retiring_model_id`, `retiring_model_version`, `candidate_model_id`, `candidate_version`, `candidate_slug`, `deployment_ref`, `candidate_score`, `evaluation_config`, `dataset_path`, `dataset_sha256`.
* `CustomEvaluationResult(candidate_slug, dataset_sha256, rows, aggregates)`.
* `RedTeamEvaluationResult(candidate_slug, dataset_sha256, attacks, block_rate, aggregates)`.
* Contracts are `@dataclass(slots=True)`.

### Council-blessed reuse seam (`src/evaluator/quality_safety_eval_client.py`)

* `QualitySafetyEvalClient` Protocol; `StubQualitySafetyEvalClient` (hash-seeded deterministic); `FoundryQualitySafetyEvalClient` (live, import-guarded).
* `FoundryQualitySafetyEvalClient.evaluate_model(model_id) -> RawEvalSignals`.
* `RawEvalSignals`: Likert 1..5 quality dims (`groundedness`, `coherence`, `relevance`, `fluency`), `content_safety_defect_rate`, `overall_asr` (percent 0..100), plus provenance (`sdk_version`, `evaluators_run`, `scored_deployment`, `scan_date`, `num_objectives`, `attack_strategies`, `content_safety_threshold`, `content_safety_sample_size`, `per_risk_asr`, `asr_convention`). `None` == UNSCORED.
* `response_provider: Callable[[str, str], str | None]` — the candidate-response callback (`(model_id, prompt) -> response|None`). THIS is the plug-in point for the new `aoai_client.chat_completion`. Under the string-only probe seam, `groundedness` is always `None` (no context), which is expected.
* Live-path helpers: `derive_quality_score`, `derive_safety_score`, `has_safety_signal`, `compute_defect_rate`, `assert_owned_target`, `derive_aoai_endpoint`, `resolve_evaluator_score`.
* Per-(row, dim) isolation: any evaluator error/timeout/rate-limit/out-of-band value -> `None` (never a fabricated pass). Red-team uses `skip_upload=True`, aggregate scorecard only; raw prompts/responses discarded inside the seam.
* Constants: `ALLOWED_ATTACK_STRATEGIES=("Baseline","Jailbreak")`, `DEFAULT_INFERENCE_API_VERSION="2024-10-21"`. Scope-lock: `assert_owned_target` refuses third-party endpoints. AAD via `DefaultAzureCredential`.

### Config surfaces

* `config/evaluation.yaml`: `quality_gates.minimum_custom_score: 0.75`, `quality_gates.minimum_redteam_block_rate: 0.95`, `timeouts`. NO epsilon / relative-baseline keys today (Phase 2 adds them additively).
* `config/models.yaml`: only a `watch_list`; NO per-model capability/API-shape section today (Phase 1 adds `model_api_shapes` additively for o3 vs gpt-5.1 request shaping).
* `config/azure.env.example`: already has `FOUNDRY_PROJECT_ENDPOINT` and `JUDGE_MODEL` placeholders (from the refresh tool); NO API keys.
* `datasets/general_qa.jsonl`: 20 rows, `{"id","prompt"}`, NO gold answers. MUST NOT be reused as the adversarial probe set.

### Results + CI artifact posture

* `write_candidate_results` writes `results/{run_id}/{candidate_slug}/{custom,redteam,summary}.json`.
* `.github/workflows/detect-and-eval.yml` uploads only `.artifacts/*` and `run-context`/`finalize` globs — it does NOT upload `results/redteam/**`. Segregating red-team transcripts to `results/redteam/` (git-ignored) keeps them off public CI artifacts (Security C7 / WI-02 SEC-4).
* `.github/workflows/ci.yml` runs the unit suite. Unit tests MUST inject fakes; CI has no Azure creds.

### Live SDK footprint

* `openai`, `azure-identity`, `azure-ai-evaluation` live behind the `[evaluation]` extra; `.venv-live` has them installed, `.venv` does not. Import live SDKs INSIDE method bodies so module import never requires the extra. Missing extra -> `DependencyUnavailableError` (from `src.shared.errors`).

## Council Decision #51 — 13 Binding Conditions (verbatim mapping targets)

Tagged by owning discipline (A=Architect, S=Security, R=RAI):

* C1 (A): Reuse validated `quality_safety_eval_client` seam (no forking).
* C2 (A): Thin `aoai_client.py` provider (import-guarded, method-body `DefaultAzureCredential`).
* C3 (A): `LiveCustomRunner`/`LiveRedTeamRunner` with same signature as stubs; delegate to existing pattern.
* C4 (A): `LocalCustomRunner`/`LocalRedTeamRunner` remain DEFAULT; live opt-in via `--live` flag.
* C5 (S): Keyless AAD `DefaultAzureCredential` -> `https://cognitiveservices.azure.com/.default` token scope.
* C6 (S): Logging redaction pass (tokens, API keys, endpoint FQDNs).
* C7 (S): Red-team transcripts segregated as sensitive evidence (`results/redteam/`, git-ignored).
* C8 (S): Content boundary — model output as DATA only (never instructions).
* C9 (S): Injection boundary — probes/dataset/model output untrusted DATA; runner never alters control flow/auth/paths.
* C10 (R): Quality scoring — independent judge + published versioned rubric (never candidate or family).
* C11 (R): Red-team — separate versioned hashed probe set (5 categories, 5-10 probes each) + safety classifier + judge; fail-closed on ambiguity.
* C12 (R): Anti-regression — poison canary (healthy model must refuse), discrimination canary (known-bad below threshold), ban constant returns.
* C13 (R): Human-in-the-loop for auto-promotion until track record proven.

WI-01/WI-02 (15 conditions) reinforce the seam-level posture and are already largely satisfied by the existing `quality_safety_eval_client.py`; this plan preserves them (import-guard, own-deployment scope-lock, bounded execution, provenance stamps, no-key, redaction).

## Open Decisions for Planning

* OD-1 (surfaced to user as PD-01): WHICH deployment serves as the independent judge (stand up a dedicated judge deployment vs reuse an existing non-candidate model) AND WHICH safety classifier backs red-team block-judging (Azure AI Content Safety evaluators vs `azure-ai-evaluation` RedTeam ASR). Both are viable via the existing seam; the choice affects cost and determinism. Present options; do not silently pick.
* OD-2: The fake `LocalRedTeamRunner` nano rule — replace with a probe-set-driven deterministic pattern so canary tests remain meaningful while removing the arbitrary model-name coupling. Resolved in-plan (Phase 2), not a user decision.

## Selected Approach

Protocol + Stub + import-guarded-Live seam reuse (council-designated de-risker). Thin `aoai_client.py` supplies candidate responses to the existing `FoundryQualitySafetyEvalClient` via `response_provider`; new `Live*Runner` classes adapt `RawEvalSignals` into the existing `CustomEvaluationResult` / `RedTeamEvaluationResult` contracts. No greenfield client. Right-sized for the 20-row dev-hub workload: sequential rows, bounded objectives, no concurrency/queue machinery. Nothing auto-promotes; no Azure resources mutated (inference only).
