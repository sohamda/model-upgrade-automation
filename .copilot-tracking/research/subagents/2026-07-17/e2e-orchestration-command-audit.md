<!-- markdownlint-disable-file -->
---
title: E2E Orchestration Command Audit
description: Read-only audit of pipeline entrypoints, commands, workflows, and Azure lookup integration points.
ms.date: 2026-07-17
---

## Research Scope

Audit the implemented orchestration and command/workflow entrypoints for this target flow:

1. Accept a supplied retiring model or inspect Azure Foundry
2. Look up live official Azure documentation and model catalog data
3. Select the top three suggestions
4. Provision each candidate
5. Run evaluations
6. Report results

The audit covers the detector, recommender, provisioner, evaluator, reporter, orchestrator, CLI/scripts, task runners, GitHub workflows, and Azure integration seams. This is a read-only review; no source code outside `.copilot-tracking/research/` will be changed.

## Research Questions

* Which commands, workflows, and task runners can execute all or part of the target flow?
* How are detector, recommender, provisioner, evaluator, and reporter connected today?
* Which required capabilities are implemented versus represented by local/dry-run seams?
* Does the repository currently perform live Azure Foundry inspection or official Azure documentation/catalog lookup?

## Evidence and Findings

### Executive Assessment

No current command or workflow executes the requested flow end-to-end. The
repository implements a local, manually chained three-stage proof path:

1. TG4 fixture-based detection, ranking, and provisioning-plan generation
2. TG5 local evaluation of the planned candidates
3. TG6 local report generation from the staged plans and local results

The sole scheduled/manual workflow is a run-context and authentication
scaffold. Its orchestration step emits a placeholder JSON document rather than
calling the Python stage CLIs. Non-dry-run execution validates Azure control
plane authentication only.

### Entrypoints and Command Capability

| Entrypoint | Invocation / Trigger | Current capability | Evidence |
| --- | --- | --- | --- |
| TG4 orchestrator CLI | `python -m src.orchestrator.cli` | Partial: loads a retirement fixture and candidate catalog fixture; ranks candidates; creates local provisioning and teardown plans; stages JSON artifacts. It does not inspect Foundry, query live docs/catalogs, create Azure deployments, evaluate, or report. | `src/orchestrator/cli.py:13-47`, `src/orchestrator/cli.py:50-78`, `src/orchestrator/pipeline.py:97-173` |
| TG5 evaluator CLI | `python -m src.evaluator.service` | Partial: reads TG4 output and runs deterministic local custom/red-team runners, writing results. ACA request creation is contract-only and its dispatch throws. | `src/evaluator/service.py:25-96`, `src/evaluator/service.py:99-145`, `src/evaluator/aca_job.py:27-43` |
| TG6 reporter CLI | `python -m src.reporter.service` | Partial: reads TG4/TG5 files and creates a local Markdown report, decision JSON, issue payload, and remediation payload. It does not create a GitHub issue, PR, or remote report. | `src/reporter/service.py:35-95`, `src/reporter/service.py:98-164`, `src/reporter/artifact_loader.py:45-166` |
| Detect and Evaluate workflow | Scheduled Monday 04:00 UTC or `workflow_dispatch` | Partial/scaffolding only: bootstraps variables and supports a `candidate_limit` input defaulting to 3, validates prerequisites, optionally logs into Azure, then creates placeholder artifacts. It never invokes TG4/TG5/TG6. | `.github/workflows/detect-and-eval.yml:3-19`, `.github/workflows/detect-and-eval.yml:31-216`, `.github/workflows/detect-and-eval.yml:273-320`, `.github/workflows/detect-and-eval.yml:345-436` |
| Sweep Orphans workflow | Daily schedule or `workflow_dispatch` | Implemented Azure cleanup only: authenticates through OIDC, lists tagged resources with `az resource list`, and optionally deletes stale IDs. It cannot execute any primary pipeline stage. | `.github/workflows/sweep-orphans.yml:3-17`, `.github/workflows/sweep-orphans.yml:70-171` |
| CI workflow | PR, main push, or manual | Validation only: TG3 contract validation, compilation, and tests; no pipeline execution. | `.github/workflows/ci.yml:3-15`, `.github/workflows/ci.yml:34-58` |
| APM task runner | `apm.yml` | No tasks are registered (`scripts: {}`). | `apm.yml:1-8` |
| TG8/TG9 scripts | `python scripts/run_tg8_full.py`; `python scripts/run_tg9_full.py` | Release/gate evidence generation. They consume existing artifacts and tests; they do not drive detector-to-reporter orchestration. | `scripts/run_tg8_full.py:2-9`, `scripts/run_tg8_full.py:148-240`, `scripts/run_tg9_full.py:2-8`, `scripts/run_tg9_full.py:39-75` |

### Implemented Integration Chain

The local stages are compatible through staged filesystem artifacts, but are not
composed by a top-level command:

1. `execute_dry_run` calls `detect_retiring_targets`, `recommend_candidates`,
	 and `plan_provisioning` for every detected target, then writes
	 `dry_run_output.json`, `history_preview.json`, and three preview manifests.
	 `src/orchestrator/pipeline.py:97-173`
2. The evaluator requires those TG4 staged files and derives work items from
	 the provisioner plans, recommender ranks, and history manifests.
	 `src/evaluator/input_builder.py:19-25`,
	 `src/evaluator/input_builder.py:103-198`
3. The evaluator writes `custom.json`, `redteam.json`, and `summary.json` per
	 candidate under `results/<run_id>/`.
	 `src/evaluator/service.py:62-83`
4. The reporter loads the TG4 plan plus each TG5 candidate result and produces
	 local Markdown/JSON decision outputs.
	 `src/reporter/artifact_loader.py:45-166`, `src/reporter/service.py:35-95`

The closest available full-pipeline procedure is therefore a manual local
sequence of the three module commands, with compatible `--run-id` /
`--artifact-root` values. It is not an end-to-end command, does not perform
Azure deployment, and is not wired into GitHub Actions.

### Target-Flow Capability Matrix

| Required capability | Implemented now | Missing or deferred behavior | Evidence |
| --- | --- | --- | --- |
| Supplied retiring model | Configuration declares a model watch list and the detector can parse a retirement fixture. | The TG4 CLI accepts a fixture file, not a direct retiring-model argument; it does not use `config/models.yaml` in the observed call path. | `config/models.yaml:1-5`, `src/orchestrator/cli.py:20-30`, `src/detector/retirement_source.py:25-53`, `src/orchestrator/pipeline.py:103-106` |
| Azure Foundry inspection | Foundry identifiers are carried in `RunContext`; workflow validates required variables for a non-dry run. | No deployed-model introspector, ARM SDK call, or `az cognitiveservices` inspection appears in the runtime code/workflow. | `.github/workflows/detect-and-eval.yml:231-263`, `src/evaluator/input_builder.py:24-55`, `src/detector/retirement_source.py:12-53`, `pyproject.toml:8-17` |
| Official retirement documentation lookup | Requirements name the official model retirement page and desired scraper. | Detector implementation is fixture-only; no HTTP client/Azure SDK dependency exists in the project dependencies. | `requirements/plan.md:317-319`, `src/detector/retirement_source.py:25-53`, `pyproject.toml:8-17` |
| Live Azure catalog/region/pricing lookup | Requirements name official Azure model capability, region availability, and pricing pages. | Recommender has only `FixtureCandidateCatalog`; no live catalog implementation or network lookup mechanism is present. | `requirements/plan.md:322-340`, `src/recommender/catalog.py:12-54`, `pyproject.toml:8-17` |
| Choose top 3 | Config defaults to `candidates_per_retiring_model: 3`; recommender sorts candidates and slices by that config. Workflow exposes `candidate_limit`, but does not pass it to Python execution. | Candidate limit is not an effective workflow-to-TG4 runtime parameter because the workflow never invokes TG4; the recommender uses config rather than the workflow input. | `config/evaluation.yaml:1-10`, `src/recommender/service.py:20-38`, `.github/workflows/detect-and-eval.yml:10-17`, `.github/workflows/detect-and-eval.yml:112-116`, `.github/workflows/detect-and-eval.yml:273-320` |
| Provision each candidate | Deterministic provision requests, tags, deployment names, and teardown plans are generated. | No ARM/SDK/CLI deploy or teardown action is called from the provisioner. | `src/provisioner/service.py:12-29`, `src/provisioner/deployment_plan.py:20-88`, `pyproject.toml:8-17` |
| Run evaluations | Local custom and red-team runners execute against a local JSONL dataset and write results. | No candidate deployment, Foundry inference, ACA dispatch, polling, or Azure AI Evaluation SDK is invoked. ACA dispatch explicitly raises a deferred-dependency error. | `src/evaluator/service.py:25-96`, `src/evaluator/aca_job.py:27-43`, `pyproject.toml:8-17` |
| Report results | Local Markdown/decision/issue/remediation payload artifacts are generated. | No GitHub API call, GitHub CLI call, pull request creation, issue submission, Blob publication, or workflow report integration uses those artifacts. | `src/reporter/service.py:35-95`, `.github/workflows/detect-and-eval.yml:358-436` |

### Azure and Live Lookup Mechanisms Found

* **Implemented control-plane authentication:** `azure/login` with GitHub OIDC
	is used by the detect/evaluate scaffold and the orphan sweeper.
	`.github/workflows/detect-and-eval.yml:283-291`,
	`.github/workflows/sweep-orphans.yml:70-79`
* **Implemented Azure CLI mutation path:** only the orphan sweeper uses Azure
	CLI, listing and optionally deleting tagged resources.
	`.github/workflows/sweep-orphans.yml:83-171`
* **Placeholder Azure credential boundary:** the Python orchestration output
	serializes an `oidc-placeholder`; it does not instantiate an Azure credential.
	`src/shared/azure_auth.py:1-19`, `src/orchestrator/pipeline.py:152-155`
* **No live Azure Foundry/catalog/documentation lookup mechanism was found** in
	the audited source, workflow, script, or project dependency surfaces. The
	only live official Azure documentation/catalog URLs found are requirements
	statements, not executable integrations.
	`requirements/plan.md:317-340`

### Requirement-to-Implementation Conflict

The authored requirements describe an intended GHA coordinator at
`src/orchestrator/main.py`, live retirement/catalog scrapers, a Foundry ARM
introspector/provisioner, ACA trigger/polling, Azure AI Evaluation execution,
and GitHub reporting integrations. The actual source tree instead contains
`src/orchestrator/cli.py` and `pipeline.py`, fixture-backed adapters, local
evaluators/reporting, and a workflow placeholder. This is a material gap between
planned architecture and runnable automation, not merely a missing command
alias.

Evidence: `requirements/plan.md:160-207`, `requirements/plan.md:317-372`,
`src/orchestrator/cli.py:1-78`, `src/orchestrator/pipeline.py:1-173`,
`.github/workflows/detect-and-eval.yml:273-320`.

## Follow-On Questions

* Should the intended primary entrypoint be a Python CLI coordinator, the
	existing GitHub Actions workflow, or both with one calling the other?
* Which authoritative source should resolve retirement and candidate availability
	when Azure documentation conflicts with Azure control-plane deployment data?
* Is the workflow `candidate_limit` input intended to override
	`config/evaluation.yaml`, and should this override be persisted into
	`RunContext`?
