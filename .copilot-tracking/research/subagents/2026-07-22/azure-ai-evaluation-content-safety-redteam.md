<!-- markdownlint-disable-file -->

# Azure AI Evaluation Content-Safety and Red-Team Research

## Research Scope

Investigate the `azure-ai-evaluation` Python SDK for content-safety evaluators, the `[redteam]` extension, scan output and Attack Success Rate (ASR) availability, and the transitive dependency footprint. Sources are limited to official Microsoft Learn documentation, the Azure SDK for Python repository, and PyPI. No Azure calls or package installation were performed.

Research date: 2026-07-22. The version-specific packaging findings use `azure-ai-evaluation` 1.18.1, released 2026-07-09, and its pinned Red Team dependency `pyrit` 0.11.0.

### Questions

1. Define constructor, invocation, output, and service-dependency contracts for the named content-safety evaluators.
2. Define `azure.ai.evaluation.red_team` types, scan targets, scan outputs, and whether ASR is programmatically available.
3. Establish the dependency footprint of `pip install "azure-ai-evaluation[redteam]"` and contrast it with a PyYAML-only runtime.

## Executive Conclusion

The requested evaluators are not offline classifiers. The SDK runs locally, but Microsoft Learn states that risk and safety evaluators use hosted evaluation language models in the Foundry evaluation service and access the backend through a Foundry project. Red Team likewise requires a Foundry project, invokes a target, and uses cloud-backed objective generation and evaluation. `skip_upload=True` avoids result upload; it does not make scanning or safety scoring offline.

The four content-harm evaluators report integer severity from 0 through 7, use a default threshold of 3, and treat lower values as safer. `RedTeam.scan()` returns a structured `RedTeamResult`; ASR is programmatically available as numeric percentage fields in its scorecard, not only in a rendered report.

## Configuration and Authentication

The content-safety evaluator constructors accept a required Azure TokenCredential and `azure_ai_project`. Official samples use `DefaultAzureCredential()` as the TokenCredential implementation. The SDK does not silently select it: package release history records that credentials became explicitly required for content-safety evaluators in 1.0.0b4.

`azure_ai_project` supports both forms below:

```python
azure_ai_project = {
	"subscription_id": "<subscription-id>",
	"resource_group_name": "<resource-group>",
	"project_name": "<project-name>",
}
```

```text
https://<resource-name>.services.ai.azure.com/api/projects/<project-name>
```

The current base implementation type is `Union[dict, str]`; the generated reference describes the typed dict form as `AzureAIProject`. The project endpoint is not optional for the requested RAI service evaluators.

## Content-Safety Evaluators

### Common Invocation Contract

The requested classes inherit the RAI service evaluator base and accept exactly one input mode:

* Single turn: `query` and `response`
* Conversation: `conversation={"messages": [...]}`

Each message has `content` and `role`, with optional `context`; a conversation can also carry global `context`. Public overloads present `query` and `response` together. Internally, `response` is required, while `query` is optional and is only included in service input when constructor keyword `evaluate_query=True` is used. Its default is `False`, so a supplied query is not evaluated by default in current versions.

For multi-turn harm evaluation, the four numeric harm evaluators aggregate to the maximum per-turn severity. Per-turn data remains available through the evaluator result's `evaluation_per_turn` structure when full-conversation evaluation is used.

### Numeric Harm Evaluators

| Evaluator | Constructor-specific setting | Inputs | Primary output fields | Decision rule |
|---|---|---|---|---|
| `ViolenceEvaluator` | `threshold=3` | `query` + `response`, or `conversation` | `violence`, `violence_score`, `violence_reason` | Severity 0-7; pass when score <= threshold |
| `SexualEvaluator` | `threshold=3` | `query` + `response`, or `conversation` | `sexual`, `sexual_score`, `sexual_reason` | Severity 0-7; pass when score <= threshold |
| `SelfHarmEvaluator` | `threshold=3` | `query` + `response`, or `conversation` | `self_harm`, `self_harm_score`, `self_harm_reason` | Severity 0-7; pass when score <= threshold |
| `HateUnfairnessEvaluator` | `threshold=3` | `query` + `response`, or `conversation` | `hate_unfairness`, `hate_unfairness_score`, `hate_unfairness_reason` | Severity 0-7; pass when score <= threshold |

The bare metric value is a severity label, such as `Very low`; the `*_score` field is the numeric score. Current source parsing also supplies token-usage fields such as `violence_prompt_tokens`, `violence_completion_tokens`, and `violence_total_tokens`. Generic evaluator infrastructure can derive `*_result` and `*_threshold` fields from a numeric score when they are absent from the immediate service parser.

The current 1.18.1 release history records a standardized evaluator field family: `{evaluator_name}` and `gpt_{evaluator_name}` score aliases, plus `*_result`, `*_reason`, `*_threshold`, token metadata, model, and sample fields. Consumers should treat the documented primary metric and `*_score`/`*_reason` names above as the stable content-safety contract, tolerate additional metadata, and pin the SDK version before hard-coding every key.

### Special Boolean Evaluators

`ProtectedMaterialEvaluator` and `IndirectAttackEvaluator` are detection evaluators, not 0-7 severity classifiers.

| Evaluator | Inputs | Output fields | Meaning |
|---|---|---|---|
| `ProtectedMaterialEvaluator` | `query` + `response`, or `conversation` | `protected_material_label`, `protected_material_reason`; optional `fictional_characters_label`, `logos_and_brands_label`, `artwork_label` and related reasons | Boolean detection of protected material |
| `IndirectAttackEvaluator` | `query` + `response`, or `conversation` | `xpia_label`, `xpia_reason` | Boolean detection of an indirect prompt-injection attack |

`ProtectedMaterialEvaluator` defaults `evaluate_query=True` in its concrete constructor, unlike the base's default. Its conversation aggregate can appear numeric because generic aggregation processes per-turn Boolean values; inspect per-turn labels when individual detections matter.

For XPIA, Learn defines pass/fail based on whether any manipulated-content, information-gathering, or intrusion attack is detected. It is not governed by the harm severity threshold 3. Current source comments describe a default threshold of 0 for the indirect-attack evaluator, but detection labels are the meaningful public result.

### Composite Evaluator

`ContentSafetyEvaluator` composes the four numeric harm evaluators. Its constructor exposes independent `violence_threshold`, `sexual_threshold`, `self_harm_threshold`, and `hate_unfairness_threshold` values, each defaulting to 3. It accepts the same single-turn or conversation inputs and returns the merged per-category output fields. It does not include Protected Material or Indirect Attack detection.

## Hosted-Service Requirement

Microsoft Learn explicitly distinguishes risk and safety evaluators from local code or NLP metrics: they use hosted evaluation language models in Foundry Evaluation service and require Foundry project information. The Azure SDK base class calls `evaluate_with_rai_service_sync`, passing the configured project and credential. Consequently:

* No supported configuration in this API surface performs the requested content-safety classification fully offline
* A local Python process still sends evaluator data to the Foundry/RAI evaluation backend
* The evaluator safety prompts are not open sourced, as the service is powered by Azure AI Content Safety
* The `evaluate()` orchestration function can execute locally but does not change this service dependency for these evaluators

## Red Team API

### Installation and Namespace

The experimental Red Team namespace is `azure.ai.evaluation.red_team`. Importing it without PyRIT raises an instruction to install the optional extra:

```text
pip install "azure-ai-evaluation[redteam]"
```

At version 1.18.1, this extra adds `pyrit==0.11.0` for Python >=3.10. Although the base SDK supports Python >=3.9, PyRIT 0.11.0 itself requires Python >=3.10 and <3.14. A Red Team installation therefore has a stricter practical interpreter requirement.

### Constructor

The current constructor is equivalent to:

```python
RedTeam(
	azure_ai_project,
	credential,
	risk_categories=None,
	num_objectives=10,
	application_scenario=None,
	custom_attack_seed_prompts=None,
	language=SupportedLanguages.English,
	output_dir=".",
	attack_success_thresholds=None,
	**kwargs,
)
```

When no risk category is configured, source defaults to Hate/Unfairness, Sexual, Violence, and Self Harm. The public risk category enum additionally includes `ProtectedMaterial`, `CodeVulnerability`, `UngroundedAttributes`, and the agent-specific `SensitiveDataLeakage`, `TaskAdherence`, and `ProhibitedActions` categories.

### Scan and Targets

`scan()` is asynchronous and returns `RedTeamResult`. Its supported target union is:

* An async or sync callable target
* `AzureOpenAIModelConfiguration`
* `OpenAIModelConfiguration`
* PyRIT `PromptChatTarget`

Its key arguments include `target`, optional `scan_name`, `attack_strategies`, `skip_upload`, `output_path`, `application_scenario`, `parallel_execution`, `max_parallel_tasks`, `timeout`, and `skip_evals`. If the selected strategies omit `AttackStrategy.Baseline`, the SDK inserts it. `skip_evals=True` bypasses evaluation, so it cannot produce meaningful ASR; `skip_upload=True` only prevents upload.

The strategy enum provides direct strategies and grouping values `EASY`, `MODERATE`, and `DIFFICULT`. The source maps baseline to `baseline`; converters, jailbreak, and indirect jailbreak to `easy`; Tense to `moderate`; and MultiTurn/Crescendo to `difficult`.

### Result Shape and ASR

`RedTeamResult` has programmatic properties and methods:

* `scan_result`: structured `ScanResult`
* `attack_details`: structured per-attack conversations
* `to_scorecard()`: returns the structured scorecard object
* `to_json()`: serializes `scan_result`
* `to_eval_qr_json_lines()` and `attack_simulation()`: exports

`scan_result` contains `scorecard`, `parameters`, `attack_details`, `AOAI_Compatible_Row_Results`, `AOAI_Compatible_Summary`, and optional `studio_url`. The scorecard provides:

* Overall and per-risk `overall_asr`, `<risk>_asr`, totals, and successful-attack counts
* Baseline, easy, moderate, and difficult complexity ASR fields
* Risk-by-complexity summary entries such as `baseline_asr` and `easy_complexity_asr`
* Detailed risk/complexity/converter ASR values

ASR is therefore available from the returned object without parsing a formatted string or output file. In current source, scorecard ASR values are calculated as `mean(attack_success) * 100` and rounded to two decimals, so the stored values are percentages, for example `25.5`, not fractions such as `0.255`.

Red Team reverses ordinary safety-result intuition: `passed=True` means the target defended successfully and the attack failed; `passed=False`/`label="fail"` means the attack succeeded. The package release history explicitly records this convention. Aggregate ASR counts attack successes, not evaluator passes.

## Dependency Footprint

### Direct Package Metadata

The published `azure-ai-evaluation` 1.18.1 metadata declares these base dependencies:

* `pyjwt`, `azure-identity`, `azure-core`, `nltk`, `azure-storage-blob`
* `httpx`, version-selected `pandas`, `openai`, `ruamel.yaml`, `msrest`, `Jinja2`, and `aiohttp`
* The `[redteam]` extra adds `pyrit==0.11.0` on Python >=3.10

The base package does not declare `promptflow`, `promptflow-core`, `promptflow-devkit`, `azure-ai-projects`, `pydantic`, or `torch` in current published `Requires-Dist`. Repository development requirements and legacy adapters mention Promptflow and Azure AI Projects, but they are not evidence of a runtime transitive dependency for 1.18.1.

### PyRIT Runtime Load

PyRIT 0.11.0's base metadata substantially expands the installed footprint. Direct requirements include:

* Azure and authentication: `azure-core`, `azure-identity`, `azure-ai-contentsafety`, `azure-storage-blob`
* HTTP, model, and schema: `httpx[http2]`, `openai>=2.2.0`, `pydantic>=2.11.5`, `transformers>=4.52.4`
* Data and persistence: `datasets`, `numpy`, `pandas` through the parent SDK, `openpyxl`, `pyodbc`, `SQLAlchemy`, `pypdf`
* API and reporting: `fastapi`, `uvicorn[standard]`, `aiofiles`, `websockets`, `reportlab`, `jinja2`, `tqdm`, `tenacity`
* Text/encoding utilities: `confusables`, `confusable-homoglyphs`, `ecoji`, `base2048`, `art`, `colorama`, `segno`, `termcolor`, and `treelib`
* Environment and image support: `python-dotenv` and `pillow>=12.1.0`

`torch` is not a base PyRIT requirement. It is brought in only by PyRIT's optional `huggingface`, `gcg`, or `all` extras. Similarly, packages such as `accelerate`, `azure-ai-ml`, MLflow, Playwright, Gradio, spaCy, OpenCV, and speech SDKs are optional PyRIT extras, not implied by `azure-ai-evaluation[redteam]` alone.

The Azure SDK changelog warns that PyRIT 0.11.0's `pillow>=12.1.0` conflicts with `promptflow-devkit`'s `pillow<=11.3.0`; use separate environments when both are required.

### Comparison with a PyYAML-Only Runtime

A PyYAML-only runtime is a lightweight local parsing dependency. It does not require Azure identity, a Foundry project, HTTP service clients, OpenAI clients, PyRIT, model/data libraries, or hosted safety scoring. It cannot substitute for these Azure content-safety or Red Team APIs because their classification and orchestration contracts are service-backed.

## Source Evidence

* Microsoft Learn, [Risk and safety evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/risk-safety-evaluators), retrieved 2026-07-22. Hosted service requirement, required inputs, numeric range, threshold behavior, and XPIA semantics.
* Microsoft Learn, [RedTeam class reference](https://learn.microsoft.com/en-us/python/api/azure-ai-evaluation/azure.ai.evaluation.red_team.redteam?view=azure-python-preview), retrieved 2026-07-22. Installation requirement and generated Red Team reference.
* PyPI, [azure-ai-evaluation 1.18.1 metadata](https://pypi.org/pypi/azure-ai-evaluation/1.18.1/json), retrieved 2026-07-22. Published version, Python requirement, package requirements, project shapes, and release-history semantics.
* PyPI, [pyrit 0.11.0 metadata](https://pypi.org/pypi/pyrit/0.11.0/json), retrieved 2026-07-22. Python requirement, direct runtime dependencies, and optional extras.
* Azure SDK for Python, [azure-ai-evaluation package source](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/evaluation/azure-ai-evaluation), retrieved 2026-07-22. Evaluator constructors, RAI service call path, output parsing, Red Team types, scorecard construction, and package metadata.

## Caveats

The Red Team and RAI evaluator surfaces are experimental and changed repeatedly in recent release history. Pin the SDK before productionizing exact keys or output models, retain unknown result keys during ingestion, and test output handling against the chosen package version. This research did not execute the SDK, contact Azure, or resolve dependencies, so it establishes declared contracts rather than runtime behavior under a specific tenant, target, or policy configuration.

## Follow-On Questions

* Which exact `azure-ai-evaluation` version will the consuming project pin?
* Is a fully local/offline safety gate required? If so, select a separate local classifier or rule-based design because these Foundry evaluators do not satisfy that constraint.

## Clarifying Questions

None blocking. The artifact uses current version 1.18.1 because no target SDK version was provided.
