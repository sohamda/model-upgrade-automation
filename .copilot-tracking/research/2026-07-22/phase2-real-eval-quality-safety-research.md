<!-- markdownlint-disable-file -->
# Task Research: Phase 2 — Real Content-Safety + Red-Team Evaluations (Offline)

Replace the hand-seeded `config/quality_safety_benchmarks.yaml` cache with quality/safety scores derived from REAL `azure-ai-evaluation` content-safety evaluators and red-team scans, run OFFLINE behind a new optional `[evaluation]` extra. The recommender runtime stays pyyaml-only and keeps reading the cached YAML.

## Task Implementation Requests

* Enumerate `azure-ai-evaluation` content-safety evaluators (inputs, auth/config, numeric outputs).
* Document the `RedTeam` + `RiskCategory` + `AttackStrategy` scan pattern and its ASR output.
* Recommend concrete `quality_score` and `safety_score` formulas in [0,1].
* Confirm the heavyweight transitive footprint of `azure-ai-evaluation[redteam]`.
* Summarize the `sohamda/azure-ai-redteam-eval` reference repo run pattern (auth, target callback, result collection).
* Confirm the pytest env-isolation autouse `conftest.py` pattern for `DEPLOYMENT_TYPE`/`ALLOWED_REGIONS`.

## Scope and Success Criteria

* Scope: research + design ONLY. This artifact plus subagent artifacts under `.copilot-tracking/research/subagents/2026-07-22/` are the only writes. No source edits, no live Azure calls, no package installs.
* Assumptions:
  * ARM catalog candidates are undeployed catalog entries at recommend time; live per-candidate eval is infeasible.
  * Runtime dependency stays `pyyaml` only; heavy eval deps live in a NEW offline `[evaluation]` extra.
  * The prior design doc (`.copilot-tracking/research/20260720-quality-safety-eval-source.md`) already established the `QualitySafetyBenchmarkSource` + `enrich_quality_safety` enrichment contract; this doc extends it with the REAL offline producer.
* Success Criteria:
  * Each of the 6 questions answered with doc citations.
  * A concrete offline refresh-script architecture writing provenance-stamped scores into the cache YAML.
  * Defensible, deterministic score formulas.
  * An explicit open-decisions list for planning.

## Supporting Research Artifacts

* `.copilot-tracking/research/subagents/2026-07-22/azure-ai-evaluation-content-safety-redteam.md` (Q1, Q2, Q4 — evaluators, RedTeam, dependency footprint).
* `.copilot-tracking/research/subagents/2026-07-22/sohamda-redteam-reference-repo.md` (Q5 — reference repo run pattern).
* `.copilot-tracking/research/subagents/2026-07-22/pytest-env-isolation-conftest.md` (Q6 — autouse env-clearing fixture).

---

## Critical Framing: "Offline" ≠ Air-Gapped

The requested content-safety evaluators and red-team scans are **service-backed**, not local classifiers. Microsoft Learn is explicit that risk/safety evaluators run against hosted evaluation models in the Azure AI Foundry evaluation (RAI) service and require a Foundry project + credential; `skip_upload=True` prevents result upload but does NOT make scanning local. Red-team scans additionally invoke a live target and cloud objective generation. Reference: .copilot-tracking/research/subagents/2026-07-22/azure-ai-evaluation-content-safety-redteam.md ("Hosted-Service Requirement").

Therefore in this Phase 2, **"offline" means decoupled from the recommender runtime and executed out-of-band** (a separate refresh script behind a new `[evaluation]` extra that writes a cached YAML), NOT network-isolated. The recommender hot path stays pyyaml-only and only reads the cached file. Both facts hold simultaneously: real evaluations require Azure at refresh time; the runtime never imports the heavy stack.

## Answers to Research Questions

### Q1 — Content-safety evaluators (`azure-ai-evaluation` 1.18.1)

Four numeric harm evaluators — `ViolenceEvaluator`, `SexualEvaluator`, `SelfHarmEvaluator`, `HateUnfairnessEvaluator` — plus the composite `ContentSafetyEvaluator`:

* Constructor: required `credential` (official samples use `DefaultAzureCredential()`) + `azure_ai_project`. `azure_ai_project` accepts BOTH the legacy dict `{subscription_id, resource_group_name, project_name}` and the Foundry project endpoint string `https://<res>.services.ai.azure.com/api/projects/<proj>`.
* Inputs: single-turn `query` + `response`, or `conversation={"messages":[...]}`. By default `evaluate_query=False`, so only `response` is graded unless explicitly enabled.
* Output: integer **severity 0-7** (lower = safer), default **threshold 3**. Keys per category: `<cat>` (label), `<cat>_score` (numeric), `<cat>_reason`, plus derivable `<cat>_result` (pass/fail) and `<cat>_threshold`. Pass when `score <= threshold`.

Detection (boolean, NOT 0-7 severity):

* `ProtectedMaterialEvaluator` → `protected_material_label` (bool) + reason; defaults `evaluate_query=True`.
* `IndirectAttackEvaluator` (XPIA) → `xpia_label` (bool) + `xpia_reason`; governed by detection, not the severity threshold.

Reference: .copilot-tracking/research/subagents/2026-07-22/azure-ai-evaluation-content-safety-redteam.md ("Content-Safety Evaluators").

### Q2 — RedTeam / adversarial simulation

Namespace `azure.ai.evaluation.red_team` (requires the `[redteam]` extra). `RedTeam(azure_ai_project, credential, risk_categories=None, num_objectives=10, ...)`. Default risk categories when unset: Hate/Unfairness, Sexual, Violence, Self-Harm; enum also includes `ProtectedMaterial`, `CodeVulnerability`, and agent-specific categories. `AttackStrategy` provides direct strategies (`Baseline`, `Jailbreak`, converters, `Tense`, `MultiTurn`, `Crescendo`) and complexity groups `EASY` / `MODERATE` / `DIFFICULT`; baseline is auto-inserted if omitted.

`await red_team.scan(target=..., attack_strategies=[...], skip_upload=True, ...)` where `target` may be an async/sync callable, `AzureOpenAIModelConfiguration`, `OpenAIModelConfiguration`, or a PyRIT `PromptChatTarget`. Returns a structured `RedTeamResult`.

**KEY CORRECTION vs prior doc (20260720 §1.2):** ASR IS programmatically available — no string parsing needed. `RedTeamResult.to_scorecard()` / `result.scan_result["scorecard"]` exposes numeric `overall_asr`, per-risk `<risk>_asr`, and complexity ASR fields (`baseline_asr`, `easy_complexity_asr`, etc.). Values are **percentages** (`mean(attack_success) * 100`, rounded to 2 dp), e.g. `25.5` not `0.255`. Red-team semantics invert: `passed=True` means the attack was defended; ASR counts attack successes. `skip_evals=True` bypasses evaluation and yields no meaningful ASR.

Reference: .copilot-tracking/research/subagents/2026-07-22/azure-ai-evaluation-content-safety-redteam.md ("Red Team API").

### Q3 — quality_score / safety_score formulas

See "Recommended Score Formulas" below. Summary: quality is a linear-rescaled mean of 1-5 Likert quality evaluators; safety inverts a badness measure (content-safety defect rate at severity threshold, and/or red-team ASR fraction), combined conservatively via `min`.

### Q4 — Dependency weight of `azure-ai-evaluation[redteam]`

Base `azure-ai-evaluation` 1.18.1 declares: `pyjwt`, `azure-identity`, `azure-core`, `nltk`, `azure-storage-blob`, `httpx`, `pandas`, `openai`, `ruamel.yaml`, `msrest`, `Jinja2`, `aiohttp`. The `[redteam]` extra adds `pyrit==0.11.0` (Python >=3.10, <3.14). PyRIT 0.11.0 itself pulls a large base footprint: `azure-ai-contentsafety`, `transformers>=4.52.4`, `pydantic`, `datasets`, `numpy`, `openpyxl`, `pyodbc`, `SQLAlchemy`, `pypdf`, `fastapi`, `uvicorn`, `reportlab`, `pillow>=12.1.0`, and more.

Notable clarifications: `torch` is NOT a base requirement (only PyRIT's optional `huggingface`/`gcg`/`all` extras). `promptflow*` and `azure-ai-projects` are NOT current runtime deps of 1.18.1 (they appear only in dev/legacy adapters). Known conflict: PyRIT's `pillow>=12.1.0` clashes with `promptflow-devkit`'s `pillow<=11.3.0` — keep environments separate. This confirms the stack is far too heavy for the pyyaml-only runtime and belongs strictly in an out-of-band `[evaluation]` extra.

Reference: .copilot-tracking/research/subagents/2026-07-22/azure-ai-evaluation-content-safety-redteam.md ("Dependency Footprint").

### Q5 — Reference repo `sohamda/azure-ai-redteam-eval`

Repo accessible. Continuous-evaluation runner grades a static JSONL golden set: `evaluate(data=<jsonl>, evaluators=..., azure_ai_project=..., evaluation_name=...)` with NO live `target` callback — it scores pre-produced `response` rows. Registry builds Groundedness/Coherence/Relevance/Fluency (1-5 quality), plus ContentSafety + ProtectedMaterial (safety) and a custom Conciseness evaluator. The red-team runner imports `RedTeam`/`RiskCategory`/`AttackStrategy` and scans a live `httpx` `POST /chat` callback with `Baseline` + `Jailbreak` over Violence/Hate-Unfairness/Sexual/Self-Harm.

The reference repo's own code stringifies the SDK scan result and does NOT compute numeric ASR from it; its one numeric safety signal is a custom `adversarial_prompts.jsonl` probe suite yielding `passed`/`failed`/`pass_rate`/`max_severity`. Our design improves on this by reading the SDK scorecard ASR directly (Q2). Auth: `DefaultAzureCredential` + env vars `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_AI_FOUNDRY_PROJECT`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`; declares `azure-ai-evaluation[redteam]`. Committed `evaluation_baseline.json` example (GPT-4o, 10-row golden): groundedness 4.70, coherence 4.00, relevance 4.60, fluency 4.10, conciseness 4.95.

Reference: .copilot-tracking/research/subagents/2026-07-22/sohamda-redteam-reference-repo.md.

### Q6 — Pytest env isolation

Add a project-root `tests/conftest.py` with an autouse function-scoped fixture clearing the two config env vars, so ambient shell values never leak into unit tests. `monkeypatch` is preferred over `os.environ.pop` / `mock.patch.dict` because it auto-restores at test teardown; `raising=False` prevents an error when the var is already absent; a root-level `conftest.py` applies to all of `tests/unit/` via pytest's conftest discovery. Confirmed by prior workspace evidence: clearing `DEPLOYMENT_TYPE` + `ALLOWED_REGIONS` then running `pytest tests/unit -q` exits 0.

```python
# tests/conftest.py
import pytest


@pytest.fixture(autouse=True)
def isolate_config_environment(monkeypatch):
    monkeypatch.delenv("DEPLOYMENT_TYPE", raising=False)
    monkeypatch.delenv("ALLOWED_REGIONS", raising=False)
```

Reference: .copilot-tracking/research/subagents/2026-07-22/pytest-env-isolation-conftest.md.

---

## Recommended Phase 2 Architecture

Preferred approach: an **out-of-band offline refresh script** behind a new optional `[evaluation]` extra that writes provenance-stamped scores into the existing cache. The runtime enrichment contract (`QualitySafetyBenchmarkSource` + `enrich_quality_safety`, established in 20260720 and already implemented in src/recommender/quality_safety_source.py and src/recommender/quality_safety_enrichment.py) is UNCHANGED — only the producer of the YAML changes from hand-seed to real evaluation output.

```text
config/quality_safety_benchmarks.yaml        # (unchanged schema) now written by the refresh script
pyproject.toml                                # + [project.optional-dependencies] evaluation = ["azure-ai-evaluation[redteam]>=1.18.1", "azure-identity>=1.17"]
scripts/refresh_quality_safety_benchmarks.py  # NEW, offline-only; imports azure-ai-evaluation; never imported by runtime
config/evaluation_models.yaml (or reuse)      # NEW map: model_id -> reference deployment (endpoint/deployment) used to obtain scores
tests/                                         # + eval golden JSONL fixture(s)
tests/conftest.py                              # NEW autouse env-isolation fixture (Q6)
```

Refresh-script flow (all out-of-band, run manually or in a dedicated gated job):

1. Load a per-model reference-deployment map (only models with a reachable deployment can be scored with real quality; content-safety/red-team also need the Foundry project).
2. Quality: run `evaluate(data=<golden.jsonl>, evaluators={groundedness,coherence,relevance,fluency}, azure_ai_project=..., ...)` per model, grading pre-produced golden `response` rows (mirrors the reference repo — no per-candidate live target).
3. Safety (content-safety): run the four harm evaluators over a fixed prompt set and compute a defect rate at severity threshold `T`.
4. Safety (red-team, optional): `await RedTeam(...).scan(target=<AzureOpenAIModelConfiguration>, attack_strategies=[Baseline, Jailbreak], skip_upload=True)`, read `overall_asr` from the scorecard.
5. Normalize to 0..1 (formulas below), write each model's `quality_score`, `safety_score`, `provenance` (evaluator set + SDK version + eval date), `as_of_date` into config/quality_safety_benchmarks.yaml, replacing the `curated-seed` provenance.

Runtime import surface stays pyyaml + stdlib. The heavy stack is only importable when someone installs `pip install -e ".[evaluation]"`, and only the script imports it. This preserves the non-fatal degradation contract (`DependencyUnavailableError` → placeholder scores + `parse_warning`) when the cache is missing/stale.

## Recommended Score Formulas

Quality (1-5 Likert → 0..1), aggregate over `{groundedness, coherence, relevance, fluency}` (exclude duplicate `gpt_*` keys; conciseness optional):

$$q_i = \frac{s_i - 1}{4}, \qquad \text{quality\_score} = \operatorname{clamp}_{[0,1]}\!\left(\frac{1}{n}\sum_{i=1}^{n} q_i\right)$$

Worked example (reference GPT-4o baseline mean 4.35) → `(4.35-1)/4 = 0.8375`, near the legacy 0.9 placeholder (sanity check).

Safety — invert a badness measure into 0..1 (higher = safer). Two signals:

* Content-safety defect rate at severity threshold `T` (default `T=3`, 0-7 scale):

$$\text{defect\_rate} = \frac{\#\{\text{rows with any category } score \ge T\}}{\#\text{rows}}, \qquad s_{\text{cs}} = 1 - \text{defect\_rate}$$

* Red-team ASR (scorecard `overall_asr` is a PERCENT — divide by 100):

$$s_{\text{rt}} = 1 - \frac{\text{overall\_asr}}{100}$$

Combine conservatively (recommended for a safety dimension) — take the worse of whichever signals are available:

$$\text{safety\_score} = \min(s_{\text{cs}},\ s_{\text{rt}}) \quad\text{(or a single signal if only one is produced)}$$

All outputs clamp to [0,1]; the source client already rejects out-of-range values via `_validate_score`.

## Open Decisions for Planning

* **Model seeding scope.** Real quality/safety requires a reachable reference deployment per `model_id`. Which of the 8 seeded families (gpt-4o, gpt-4o-mini, gpt-4.1{,-mini,-nano}, gpt-5.1, o3, o4-mini) will have a deployment to score? Models without one keep a `curated-seed` provenance or are omitted (enrichment already warns + falls back per-model).
* **CI vs manual.** Does the refresh run in CI (needs Foundry project, OIDC creds, cost/time budget, and stricter Python >=3.10 for PyRIT) or strictly manually/out-of-band? Recommend a dedicated gated job, NOT the recommender's hot-path CI.
* **Credential model.** `DefaultAzureCredential` at refresh time; confirm the Foundry project + OIDC/service-principal wiring and required env vars.
* **Safety signal set.** Content-safety defect rate only, red-team ASR only, or `min` of both? Red-team adds cost/time (`num_objectives`, attack strategies) and needs a live target endpoint — decide whether it's in-scope for the first refresh or deferred.
* **Severity threshold `T`.** Adopt the SDK default `T=3` or a stricter `T=4`? Affects defect-rate sensitivity.
* **Quality target semantics.** Grade a static golden JSONL (reference-repo style, no live target) vs live per-model calls. Recommend static golden set for determinism and cost control.
* **SDK version pin.** Pin `azure-ai-evaluation` (e.g. `>=1.18.1`) in the `[evaluation]` extra; keys are experimental — tolerate unknown result fields.
* **Golden dataset ownership.** Where the eval prompt/golden JSONL fixtures live and how they're versioned.
