<!-- markdownlint-disable-file -->
---
title: Core Pipeline Components Research
description: Evidence-based assessment of detector, recommender, provisioner, evaluator, and reporter behavior against the requested end-to-end retirement migration workflow.
ms.date: 2026-07-17
ms.topic: research
---

## Research Questions

* Which detector, recommender, provisioner, evaluator, and reporter components implement the requested retirement migration workflow?
* Can the system accept a supplied retiring model or inspect Azure Foundry, look up official catalog information, return three suggestions, provision them, evaluate them, and report the results?
* Which entrypoints, configuration, contracts, and tests are reusable, and where are the gaps?

## Working Hypothesis

The repository has reusable, tested local components for fixture-driven detection, ranking, planned provisioning, local evaluation, and reporting, but does not yet provide a composed live Azure Foundry workflow.

## Assessment Summary

The repository implements a deterministic, local-first proof-of-contract pipeline. It can
accept a supplied retirement YAML and a supplied candidate-catalog YAML, rank up to three
candidates, create provision and teardown request records, generate synthetic evaluation
results, and render local reports. It cannot currently inspect a Foundry account, retrieve
official retirement, catalog, availability, pricing, or quota data, create or delete a
Foundry deployment, dispatch an ACA job, or run evaluations against a deployed model.

The requested outcome therefore has partial implementation coverage. The data contracts,
artifact boundaries, local CLIs, deterministic ranking, and reporter surfaces are reusable.
The live Azure adapters and a composed end-to-end entrypoint remain missing.

## Requested Outcome Coverage

| Requested capability | Current status | Evidence | Primary gap |
| --- | --- | --- | --- |
| Accept a supplied retiring model | Partially implemented | `src/detector/retirement_source.py:24-57`, `src/orchestrator/cli.py:18-73` | Input is a YAML file, not a typed direct CLI model argument |
| Inspect Azure Foundry deployments | Not implemented | `src/shared/azure_auth.py:1-18`; source search found no Azure SDK or ARM client | No deployment-list adapter or `discover_from_azure` configuration |
| Look up official retirement schedule | Not implemented | `src/detector/retirement_source.py:24-57` | Fixture source only; no Learn-page parser, cache, or fail-closed handling |
| Look up live official catalog, region, deployment, price, or quota data | Not implemented | `src/recommender/catalog.py:22-55`; `src/recommender/models.py:10-39` | Local YAML score inputs replace live capability, availability, price, and quota evidence |
| Return top three suggestions | Partially implemented | `config/evaluation.yaml:1-10`; `src/recommender/service.py:20-48` | The configured limit is three, but only fixture candidates can be ranked and the code contains a truthiness coupling noted below |
| Provision each suggested candidate | Not implemented | `src/provisioner/service.py:12-30`; `src/provisioner/deployment_plan.py:17-88` | Generates `ProvisionRequest` and `TeardownPlan` only; no Azure control-plane call |
| Run evaluations against each provisioned candidate | Not implemented | `src/evaluator/service.py:25-105`; `src/evaluator/aca_job.py:25-45` | Uses deterministic synthetic runners; ACA dispatch always raises `DependencyUnavailableError` |
| Report comparison and decision results | Partially implemented | `src/reporter/service.py:30-102`; `src/reporter/decision_engine.py:8-103` | Writes useful local reports but lacks live cost, longevity, baseline, Blob links, and GitHub publication |
| One executable end-to-end live flow | Not implemented | `src/orchestrator/pipeline.py:93-170`; `.github/workflows/detect-and-eval.yml:251-286` | Dry-run pipeline stops after plan generation; Actions workflow uses an orchestration placeholder |

## Current Execution Paths

### Local TG4 dry run

`python -m src.orchestrator.cli` is the only core orchestrator entrypoint. Its parser
accepts `--fixture`, `--catalog`, and `--run-id` in
`src/orchestrator/cli.py:18-58`, then calls `execute_dry_run` in
`src/orchestrator/pipeline.py:93-170`.

`execute_dry_run` loads application configuration, unconditionally chooses
`FixtureRetirementSource` and `FixtureCandidateCatalog` when explicit paths are supplied,
or the checked-in test fixtures otherwise. For every detected target it invokes the
recommender and plan-only provisioner, writes JSON under `artifacts/<run-id>/`, and returns.
It does not call `execute_local_evaluation` or `execute_local_report`.

The staged artifacts are:

* `artifacts/<run-id>/detector.json`
* `artifacts/<run-id>/recommender.json`
* `artifacts/<run-id>/provisioner.json`
* `artifacts/<run-id>/history_preview.json`
* `artifacts/<run-id>/dry_run_output.json`

The focused contract test is `tests/unit/test_orchestrator_cli.py:20-147`. It verifies
fixture processing, staged artifact names, manifests, and the placeholder credential mode.

### Local TG5 evaluator

`python -m src.evaluator.service` invokes `execute_local_evaluation` in
`src/evaluator/service.py:25-105`. `build_work_items_from_artifacts` reads TG4 plan
artifacts and constructs `DeploymentRef` values in `src/evaluator/input_builder.py:111-253`.
The resource ID is deliberately `dryrun://<deployment-name>`, not an Azure resource ID.

`LocalCustomRunner` computes scores from the recommender's fixture score plus a fixed row
offset in `src/evaluator/custom_runner.py:10-71`. `LocalRedTeamRunner` emits fixed attack
categories and blocks every attack except the `nano`/`jailbreak` fixture condition in
`src/evaluator/redteam_runner.py:10-58`. Results are marked `local_complete` and the caller
returns `aca_dispatch_status: deferred-local-only`.

The ACA seam is intentionally non-operational. `AcaJobAdapter.build_request` preserves
candidate metadata, while `dispatch` always raises `DependencyUnavailableError` in
`src/evaluator/aca_job.py:25-45`. Tests explicitly assert that behavior in
`tests/unit/test_evaluator_aca_job.py:41-58`; `tests/unit/test_evaluator_service.py:22-46`
only asserts the materialization of synthetic JSON results.

### Local TG6 reporter

`python -m src.reporter.service` invokes `execute_local_report` in
`src/reporter/service.py:30-102`. The reporter reads the TG4 dry-run output and TG5 local
files from `results/<run-id>/<candidate>/` through
`src/reporter/artifact_loader.py:46-197`, then emits a Markdown report, decision JSON,
issue payload JSON, and remediation payload JSON for each target.

The winner policy applies hard safety, red-team, and custom-score gates in
`src/reporter/decision_engine.py:8-103`. The implementation explicitly states that cost
inputs are unavailable and default to zero, and that longevity is unavailable so recommender
rank and candidate slug become the tie-breaker. The aggregation layer confirms those fields
are `None` in `src/reporter/aggregator.py:25-104`. The rendered report labels cost as
`n/a (local placeholder)` in `src/reporter/markdown_report.py:8-159`.

`tests/unit/test_reporter_service.py:15-35` confirms output files are written from a
hermetic fixture run. Its expected winner is `None`, demonstrating the fixture candidates
do not satisfy the reporter's hard safety policy.

## Component Evidence

### Detector

`RetirementSource` is a useful protocol seam in `src/detector/retirement_source.py:13-20`.
`FixtureRetirementSource.load` parses only a local YAML `retiring_models` list, including a
user-provided `source` label. The contract does not include lifecycle state, modality,
capabilities, an official-document timestamp, raw-source hash, or deployment identity.

`detect_retiring_targets` in `src/detector/service.py:14-57` joins retirement signals to
`config/models.yaml` by exact `(model_id, current_version)`, applies a per-watch or default
horizon, and emits a `RetiringTarget`. This is reusable for merged supplied and live inputs.
It warns for unmatched signals, but cannot discover an unlisted Azure deployment.

The shipped watch list has only `gpt-4.1` version `2025-04-14` in Sweden Central with a
`general_qa` workload: `config/models.yaml:1-5`. The detector tests cover one fixture match
and one unmatched warning: `tests/unit/test_detector_service.py:20-65`.

### Recommender

`CandidateCatalog` is the corresponding reusable adapter boundary in
`src/recommender/catalog.py:13-20`, but its only implementation is
`FixtureCandidateCatalog`, which reads candidate ID, version, region, deployment types,
workloads, replacement families, and precomputed quality, safety, and cost scores from YAML.

`filter_candidates` in `src/recommender/filters.py:11-37` supports workload, optional
same-region, required deployment type, and replacement-family filtering. It lacks modality,
context-window, API compatibility, lifecycle/stability, quota, subscription eligibility,
and official region-availability checks. `score_candidate` in
`src/recommender/scorer.py:20-43` is a deterministic weighted sum of fixture inputs.

The nominal top-three limit is configured by `candidates_per_retiring_model: 3` in
`config/evaluation.yaml:1-10`, and applied by `recommend_candidates` in
`src/recommender/service.py:20-48`. The limit expression is
`run_context.allowed_regions and config.evaluation.candidates_per_retiring_model`; it
therefore relies on a non-empty allowed-regions list to produce an integer slice bound. This
does not change normal configured behavior but unnecessarily couples candidate count to a
separate field.

The tests prove stable ranking of two fixture candidates and no-match warning behavior:
`tests/unit/test_recommender_service.py:19-75`. The fixture is synthetic and includes model
versions that should not be treated as current catalog evidence:
`tests/fixtures/candidate_catalog.yaml:1-42`.

### Provisioner

`plan_provisioning` in `src/provisioner/service.py:12-30` only maps ranked candidates into
requests and teardown records. It makes no SDK, REST, CLI, ARM, or Bicep invocation.
`build_provision_request` in `src/provisioner/deployment_plan.py:50-72` creates a stable
SHA-256 idempotency key, a normalized 63-character maximum deployment name, and governance
tags. `build_teardown_plan` in `src/provisioner/deployment_plan.py:75-88` creates the
matching desired cleanup record.

These request and teardown contracts are useful inputs to a real Foundry deployment adapter.
They do not represent deployment completion, failure, resource ID, operation state, actual
capacity, or generated deployment settings. The only provisioner tests verify deterministic
key generation and tags, not Azure resource lifecycle behavior:
`tests/unit/test_provisioner_service.py:17-103`.

### Evaluator

The evaluator's artifact loading, data-set hashing, per-candidate result files, threshold
shape, and candidate work-item contracts are reusable. It currently evaluates no model
responses. The custom and red-team runners produce deterministic values from local fixtures,
so report decisions cannot establish performance or safety of a Foundry candidate.

`src/evaluator/aca_job.py:25-45` is the explicit replacement point for an ACA execution
adapter. A production implementation needs a deployment-ready reference from the provisioner,
secure data-plane identity, ACA dispatch and polling, result retrieval, timeouts, and
idempotent cleanup.

### Reporter

The reporter is the most complete downstream surface: it joins candidate plans, local
evaluation outputs, thresholds, hash integrity status, decision policy, Markdown rendering,
and machine-readable issue/remediation payloads. It cannot include a baseline deployment
evaluation, actual price deltas, longevity dates, blob artifact URLs, or GitHub issue/PR
publication because no upstream source supplies those facts and no GitHub client is present.

The report output can guide human review once the inputs become live; it should not be
presented as a migration recommendation under the requested outcome until that occurs.

## Configuration and Azure Readiness

`src/shared/config.py:94-207` loads watch, evaluation, recommender, and Azure environment
settings. `config/azure.env.example:1-30` names the intended OIDC, Foundry, ACA, Storage,
and Key Vault resources but supplies no credentials or clients. The credential factory is an
explicit serialization placeholder returning `mode="oidc-placeholder"` in
`src/shared/azure_auth.py:1-18`.

`pyproject.toml:1-22` declares only `pyyaml` at runtime. There are no Azure management,
Foundry, Azure AI evaluation, Azure Identity, HTTP, or data-plane SDK dependencies. A focused
source search found no Azure SDK import, ARM request, or subprocess invocation in `src/`.

The scheduled workflow, `.github/workflows/detect-and-eval.yml:1-288`, bootstraps context,
validates variables, performs OIDC login in non-dry-run mode, and writes a placeholder
summary. Its own notes state that TG4 and TG5 will replace the placeholder. Finalization at
`.github/workflows/detect-and-eval.yml:291-393` uploads only placeholder workflow artifacts.
It never invokes the Python detector, recommender, provisioner, evaluator, or reporter CLIs.

## Requirements-to-Code Delta

The intended component model already describes the missing adapters. In
`requirements/plan.md:316-346`, the intended detector fetches retirement schedules and
optionally lists `Microsoft.CognitiveServices/accounts/deployments`; the intended recommender
fetches the official catalog and regional availability, derives price and lifecycle evidence,
and applies compatibility filters. `requirements/plan.md:348-382` further calls for an Azure
SDK provisioner, ACA-hosted Azure AI evaluations, and result storage. These requirements are
not contradicted by the current implementation; they are deferred from it.

The smallest path to the requested outcome is to retain the five existing stage contracts and
replace their local adapters in this order:

1. Add a live retirement source and an optional Foundry/ARM deployment introspector, then
	merge their records with supplied model input before the existing detector join.
2. Add a live catalog/availability/pricing adapter that normalizes official facts into an
	expanded candidate contract, then extend filters and scoring with compatibility, stability,
	price, and quota evidence.
3. Replace plan-only provisioning with an idempotent deployment adapter that returns actual
	`DeploymentRef` values and records operation outcomes.
4. Implement ACA dispatch, polling, and cleanup; replace synthetic runners with Azure AI
	evaluation calls against each real deployment.
5. Pass actual cost, longevity, baseline, and artifact URLs to the existing reporter and add
	a composed orchestrator command before wiring that command into Actions.

## External Evidence

* Microsoft Learn, [Model retirement schedule](https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule), retrieved 2026-07-17, page dated 2026-07-09. The current Azure OpenAI table marks `gpt-4.1` version `2025-04-14` as Deprecated with a 2026-10-14 retirement date and no prescribed replacement. This supports a live schedule adapter rather than a hard-coded family hint.
* Microsoft Learn, [Foundry Models sold by Azure](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure), retrieved 2026-07-17, page dated 2026-07-07. It states that availability varies by region and cloud, directs readers to deployment-category region availability, and describes model capabilities. This corroborates the retirement schedule's model identity with the need for catalog, capability, and regional validation before recommendation or provisioning.

## Conclusions

The concrete, falsifiable conclusion is that a real Foundry model cannot be discovered,
provisioned, or evaluated by the repository as it exists: execution reaches local fixture
adapters and explicit deferred seams before any live Azure operation. The existing code is a
sound foundation for an end-to-end implementation, especially its contracts, deterministic
artifact flow, cleanup planning, reporter policy, and focused unit tests. It is not yet the
requested operating workflow.
