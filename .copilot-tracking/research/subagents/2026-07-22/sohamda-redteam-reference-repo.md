<!-- markdownlint-disable-file -->

# Azure AI Red-Team Evaluation Reference Repository

## Scope And Method

Research date: 2026-07-22

Repository investigated: [sohamda/azure-ai-redteam-eval](https://github.com/sohamda/azure-ai-redteam-eval), branch `main`.

The repository was accessible. This research used GitHub repository search and direct retrieval of public repository files only. No Azure calls were made and no dependencies were installed.

## Executive Summary

The repository has two materially different evaluation paths:

* Continuous evaluation grades pre-produced `response` values in static JSONL golden datasets. Its `evaluate(...)` calls have no `target` callback, so this runner does not exercise a live application endpoint.
* The Azure AI Evaluation RedTeam SDK path does exercise a live target: an async `httpx` callback posts each generated query to `POST /chat` and returns the `response` field. The SDK scan result is persisted only as `json.dumps(str(sdk_result))`; this path does not derive a numeric attack-success rate (ASR) or defect rate.
* The local custom-probe path, rather than the SDK result, computes numeric counts and a formatted `pass_rate`. It classifies a response as blocked by substring matching refusal/safety indicators, reports `max_severity`, and fails on failed high/critical probes.

## 1. Continuous Evaluation Runner And Evaluator Registry

### Evaluator Construction

`src/continuous_evaluation/evaluators.py` imports and constructs these Azure AI Evaluation SDK evaluators:

* Quality: `GroundednessEvaluator`, `CoherenceEvaluator`, `RelevanceEvaluator`, and `FluencyEvaluator`, each initialized with `model_config` containing `azure_endpoint`, `azure_deployment`, and `api_version`.
* Safety: `ContentSafetyEvaluator` and `ProtectedMaterialEvaluator`, each initialized with `credential=DefaultAzureCredential()` and `azure_ai_project`.
* Custom: `ConcisenessEvaluator`, a local word-count heuristic returning a 1-5 score.

`get_all_evaluators()` merges all three groups, so the full-run implementation constructs seven evaluators. The PR runner deliberately omits the safety group and builds only the four quality evaluators plus custom conciseness for speed.

Evidence:

* [evaluator registry source](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/src/continuous_evaluation/evaluators.py), retrieved 2026-07-22
* [full runner source](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/src/continuous_evaluation/run_evaluation.py), retrieved 2026-07-22
* [PR runner source](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/src/continuous_evaluation/run_pr_evaluation.py), retrieved 2026-07-22

### Invocation And Target Behavior

The full runner calls the SDK through `retry_with_backoff` with the following effective arguments:

```python
evaluate(
	data=str(DATASET_PATH),
	evaluators=evaluators,
	azure_ai_project=azure_ai_project,
	evaluation_name="ce-full-evaluation",
)
```

`DATASET_PATH` is `src/continuous_evaluation/datasets/eval_golden.jsonl`. The PR runner makes the same shape of call against `eval_golden_small.jsonl`, using `evaluation_name="ce-pr-evaluation"`.

Neither call passes `target`. The full golden JSONL itself contains `query`, `context`, `response`, and `ground_truth` fields. Therefore this evaluation runner grades pre-produced responses from a static golden set; it does not generate application responses or invoke a live `/chat` target.

The full runner creates an unused `DefaultAzureCredential()` immediately before calling `evaluate`; safety evaluator construction is the concrete code that supplies credentials to `ContentSafetyEvaluator` and `ProtectedMaterialEvaluator`.

Evidence:

* [full `evaluate` invocation](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/src/continuous_evaluation/run_evaluation.py), retrieved 2026-07-22
* [PR `evaluate` invocation](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/src/continuous_evaluation/run_pr_evaluation.py), retrieved 2026-07-22
* [golden static response dataset](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/src/continuous_evaluation/datasets/eval_golden.jsonl), retrieved 2026-07-22

### Output And Quality Gate

The full runner extracts mean metrics, saves `evaluation_results.json` as `{"scores": scores, "raw_results": str(results)}`, exports scores to telemetry, and exits nonzero where any configured threshold fails. Regression checking compares `evaluation_results.json` to `evaluation_baseline.json`, with a default allowed drop of 0.3 points.

## 2. Azure AI Evaluation Red-Team SDK Runner

### SDK Imports, Project, And Target

`src/redteam/run_redteam.py` imports `AttackStrategy`, `RedTeam`, and `RiskCategory` from `azure.ai.evaluation.red_team`, plus `DefaultAzureCredential` from `azure.identity`.

`run_redteam_sdk()` builds an `azure_ai_project` dictionary from the subscription ID, resource group, and Foundry project settings; then it constructs `RedTeam` with that project, `DefaultAzureCredential`, the selected risk categories, `num_objectives=5`, and an application scenario.

This is a live-target scan, not a model-config target. `_build_target_callback()` creates an async callback using `httpx.AsyncClient(timeout=60.0)` which executes:

```python
await client.post(endpoint, json={"query": query, "context": ""})
```

It returns `resp.json().get("response", "")`. The target endpoint is chosen in priority order: `--target-url`, `REDTEAM_TARGET_URL`, then `http://localhost:8000/chat`. The scheduled workflow supplies `REDTEAM_TARGET_URL` from `APP_SERVICE_ENDPOINT` and waits for its `/health` endpoint.

Evidence:

* [red-team runner](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/src/redteam/run_redteam.py), retrieved 2026-07-22
* [red-team GitHub Actions workflow](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/.github/workflows/redteam.yml), retrieved 2026-07-22

### Risks, Strategies, And Result Handling

The configured SDK risk categories are:

* `RiskCategory.Violence`
* `RiskCategory.HateUnfairness`
* `RiskCategory.Sexual`
* `RiskCategory.SelfHarm`

The configured strategies are `AttackStrategy.Baseline` and `AttackStrategy.Jailbreak`. Comments state that Crescendo and MultiTurn must run alone.

The SDK call is:

```python
await red_team.scan(
	target=target,
	scan_name="ce-redteam-scan",
	attack_strategies=ATTACK_STRATEGIES,
	output_path=str(REPORT_OUTPUT.parent),
	skip_upload=True,
)
```

The caller serializes the SDK outcome with `json.dumps(str(sdk_result), indent=2)` to `redteam_sdk_result.json`. It does not parse the result, compute an attack-success rate, calculate a defect rate, or use the SDK result for the pass/fail decision. SDK exceptions are explicitly non-blocking, allowing the custom-probe phase to continue.

## 3. Custom Adversarial-Probe Numeric Safety Signal

### Probe Dataset And Execution

`src/continuous_evaluation/datasets/adversarial_prompts.jsonl` contains ten static prompts across six categories: prompt injection (3), jailbreak (2), PII extraction (2), harmful content (1), social engineering (1), and misinformation (1). Each row has `query`, `category`, and `severity`.

`run_redteam_custom()` loads that JSONL and delegates to `run_adversarial_probes()`. The probe runner uses `httpx.AsyncClient(timeout=30.0)` to POST each query to the same live endpoint. It marks a result `PASS` only when `_is_blocked()` finds any configured refusal/redaction/safety substring in the response. Request exceptions count as blocked and therefore as `PASS`.

Evidence:

* [custom adversarial dataset](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/src/continuous_evaluation/datasets/adversarial_prompts.jsonl), retrieved 2026-07-22
* [custom probe execution and heuristic](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/src/redteam/attack_strategies.py), retrieved 2026-07-22

### Counts, Pass Rate, Severity, And CI Decision

This custom path is the only identified location that computes a numeric safety signal. `generate_report()` calculates, per category:

* `total_probes`
* `passed`
* `failed`
* `pass_rate` as formatted `(passed / total * 100)` percentage text
* `max_severity` across failed probes
* `status` as `PASS` only where `failed == 0`

It sets `has_critical_findings=True` if any high- or critical-severity probe fails. `run_redteam()` writes these custom results to `redteam_report.json` and `redteam_report.md`, then exits nonzero when `has_critical_findings` is true. The workflow separately reads this JSON boolean to fail CI.

This is a blocked-probe pass rate, not an explicitly calculated ASR. A numeric ASR could be derived as `failed / total`, but the repository does not implement or label that metric.

Evidence:

* [custom report computation](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/src/redteam/report.py), retrieved 2026-07-22
* [runner report and exit behavior](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/src/redteam/run_redteam.py), retrieved 2026-07-22
* [CI critical-finding gate](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/.github/workflows/redteam.yml), retrieved 2026-07-22

## 4. Authentication, Configuration, And Dependencies

### Authentication And Environment Variables

The repository uses `DefaultAzureCredential` in the safety evaluator factory and RedTeam SDK runner. Configuration is loaded by Pydantic settings classes from `.env` and environment variables:

* `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, and `AZURE_OPENAI_API_VERSION` populate the model configuration used by quality evaluators.
* `AZURE_AI_FOUNDRY_PROJECT` and `AZURE_AI_FOUNDRY_ENDPOINT` configure the Foundry project settings.
* `AZURE_SUBSCRIPTION_ID` and `AZURE_RESOURCE_GROUP` populate the `AzureAIProject` and RedTeam project configuration.

The evaluation workflow passes those values through GitHub secrets after Azure OIDC login. The red-team workflow does the same and also provides `REDTEAM_TARGET_URL`.

Evidence:

* [Pydantic configuration classes](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/src/config.py), retrieved 2026-07-22
* [environment template](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/.env.example), retrieved 2026-07-22
* [evaluation workflow configuration](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/.github/workflows/evaluate.yml), retrieved 2026-07-22

### Declared Dependencies

`pyproject.toml` declares `azure-identity>=1.19.0` and `azure-ai-evaluation[redteam]>=1.0.0`, alongside Agent Framework, FastAPI, OpenTelemetry, Pydantic, and dotenv dependencies. `httpx>=0.27.0` appears in the `dev` optional dependency group even though the red-team source imports it at runtime. The red-team workflow additionally runs `pip install "azure-ai-evaluation[redteam]"` after installing `requirements.txt`.

Evidence:

* [declared project dependencies](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/pyproject.toml), retrieved 2026-07-22
* [red-team workflow installation step](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/.github/workflows/redteam.yml), retrieved 2026-07-22

## 5. Committed Baseline And Report Outputs

`evaluation_baseline.json` is committed. Its top-level `scores` include:

| Metric | Baseline score |
| --- | ---: |
| Groundedness | 4.7 |
| Coherence | 4.0 |
| Relevance | 4.6 |
| Fluency | 4.1 |
| Conciseness | 4.95 |
| Binary aggregate | 1.0 |

The baseline's `raw_results` records static-input rows and aggregate metrics for the four quality evaluators plus conciseness. It does not show aggregate `content_safety` or `protected_material` scores, despite the current full evaluator registry constructing those evaluators. This is evidence of the committed baseline content, not proof of why the safety metrics are absent.

`redteam_report.md` is also committed and reports ten probes, with all six custom categories at 100% pass rate and no critical findings. The fallback report gives the same category totals. There is no committed `evaluation_results.json` or `redteam_report.json` at repository root as of retrieval; both raw URLs returned HTTP 404, consistent with their being generated run artifacts rather than committed files.

Evidence:

* [committed evaluation baseline](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/evaluation_baseline.json), retrieved 2026-07-22
* [committed red-team markdown report](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/redteam_report.md), retrieved 2026-07-22
* [fallback red-team report](https://github.com/sohamda/azure-ai-redteam-eval/blob/main/fallback/redteam_report.md), retrieved 2026-07-22

## Interpretation And Limitations

* Do not treat the full continuous-evaluation scores as evidence of a live application response quality measurement: they evaluate the checked-in `response` values in the golden JSONL.
* Do not treat the SDK red-team call as a numeric ASR/defect-rate implementation: its outcome is stringified and saved without aggregation or gating.
* The custom-probe report does provide numeric counts and a pass rate, but it relies on a response-text heuristic. It counts transport/runtime exceptions as safely blocked, which can inflate the apparent blocked-probe pass rate during an unavailable target.
* The safety-evaluator registry and the committed baseline do not fully align: current source includes `ContentSafetyEvaluator` and `ProtectedMaterialEvaluator`, but the committed baseline's aggregate score list does not include them.

## Follow-On Questions

* Is `requirements.txt`, referenced by the workflows, generated or intentionally absent from the repository? The package declaration itself is in `pyproject.toml`.
* Was the committed `evaluation_baseline.json` generated before safety evaluator outputs were added, or did those evaluators produce a result shape that `summarize_scores()` excludes?
