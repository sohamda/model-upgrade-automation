<!-- markdownlint-disable-file -->
---
title: Orchestration Command and Test Path Research
description: Research evidence for whether the model upgrade lifecycle is executable end to end
ms.date: 2026-07-17
---

## Scope

Research-only inspection of whether this repository can execute the full user journey:

1. Model input or Foundry inspection
2. Live catalog retrieval
3. Top-three candidate ranking
4. Provisioning all selected candidates
5. Evaluation
6. Reporting

## Questions

* Which user-facing commands and CI workflows compose the journey?
* Which stages are implemented, documented, or only stubbed?
* What exact commands, configuration, and credentials are required?
* Which existing scripts and tests can be reused?
* What integration coverage is missing?
* What is the minimum viable E2E path supported by current code?

## Executive Finding

The requested end-to-end user journey is **not executable against live Azure
Foundry today**. The repository supports a deterministic, local, fixture-backed
simulation from configured retirement signals through ranking, provisioning-plan
generation, local evaluation, and local reporting. These stages are separate
commands; neither local code nor GitHub Actions bridges them to Foundry
inspection, live catalog retrieval, ARM deployment creation, or ACA evaluation
execution.

The documented desired architecture is broader than the implementation.
requirements/plan.md:3 describes weekly unattended live detection, top 2-3
ephemeral provisions, evaluation, and reporting. requirements/plan.md:16-18
also requires user input plus optional live deployment introspection. The
current production workflow is expressly a placeholder.

## Lifecycle Assessment

| Requested stage | Current implementation | Executable now | Evidence |
| --- | --- | --- | --- |
| Model input | Configured watch list plus YAML retirement signals | Yes, fixture only | config/models.yaml:1-5; src/detector/retirement_source.py:23-57 |
| Foundry inspection | No subscription/deployment introspector implementation | No | requirements/plan.md:16; requirements/plan.md:166-167; src/detector/retirement_source.py:1-57 |
| Live catalog | No Foundry/model-availability client implementation | No | requirements/plan.md:171; src/recommender/catalog.py:22-55 |
| Rank top 3 | Deterministic fixture ranking, capped by config | Yes, with curated inputs | src/recommender/service.py:15-46; config/evaluation.yaml:1-9 |
| Provision all selected | Builds request/teardown plans only | Yes for plans; no for Azure deployments | src/provisioner/service.py:12-31; src/orchestrator/pipeline.py:113-140 |
| Evaluate | Runs deterministic local custom and red-team runners | Yes locally; no ACA/Foundry inference | src/evaluator/service.py:25-109; src/evaluator/aca_job.py:28-41 |
| Report | Generates Markdown, decision, issue, remediation payloads from local artifacts | Yes locally | src/reporter/service.py:35-117 |
| Scheduled/CI journey | Workflow validates context and emits placeholder summaries | No business lifecycle invocation | .github/workflows/detect-and-eval.yml:327-361; docs/setup-guide.md:10-15, 59-63 |

## Existing Reusable Commands and Entry Points

### Local Orchestrator: Fixture Input to Ranked Provisioning Plans

`python -m src.orchestrator.cli` is the local command surface. It accepts
`--repo-root`, `--fixture`, `--catalog`, and `--run-id`, but has no switch for
Azure access, a live catalog, actual provisioning, evaluation, reporting, or a
candidate limit. See src/orchestrator/cli.py:19-80.

The underlying `execute_dry_run` always constructs `FixtureRetirementSource`
and `FixtureCandidateCatalog`, invokes detection/ranking, then calls
`plan_provisioning` and stages JSON. It does not invoke an Azure SDK, Azure CLI,
ARM API, Foundry API, evaluator, or reporter. See src/orchestrator/pipeline.py:97-169.

The command produces the following reusable handoff artifacts:

```text
artifacts/<run-id>/detector.json
artifacts/<run-id>/recommender.json
artifacts/<run-id>/provisioner.json
artifacts/<run-id>/history_preview.json
artifacts/<run-id>/dry_run_output.json
```

The artifact contract is covered by tests/unit/test_orchestrator_cli.py:21-128.

### Local Evaluator: Staged Plans to Local Results

`python -m src.evaluator.service` takes `--artifact-root` and `--dataset`.
It derives one work item per provision request and writes deterministic custom,
red-team, and summary JSON under `results/<run-id>/<candidate-slug>/`. See
src/evaluator/service.py:112-171 and src/evaluator/input_builder.py:120-238.

It fabricates the deployment reference as `dryrun://<deployment-name>`;
therefore it cannot verify that a real deployment exists. See
src/evaluator/input_builder.py:199-204. It merely builds an ACA request and
returns `aca_dispatch_status: deferred-local-only`; `AcaJobAdapter.dispatch()`
unconditionally raises `DependencyUnavailableError`. See
src/evaluator/service.py:56-107 and src/evaluator/aca_job.py:28-41.

### Local Reporter: Evaluation Results to Decision Artifacts

`python -m src.reporter.service` loads the staged dry-run summary and local
evaluation result files, then writes a report, decision JSON, issue payload,
and remediation payload. See src/reporter/service.py:35-147 and
src/reporter/artifact_loader.py:53-197.

The reporter does not submit the issue, create a pull request, deploy a
recommendation, or validate a live model. It produces payload files only.

### CI and Gate Scripts

* `python scripts/validate_tg3_contracts.py` validates configuration and
  workflow contracts. It is run by CI and workflow preflight. See
  .github/workflows/ci.yml:37-53 and .github/workflows/detect-and-eval.yml:246-251.
* `python -m pytest -q tests/unit` is the CI unit-test command. See
  .github/workflows/ci.yml:66-76.
* `python scripts/run_tg8_full.py` runs TG8 evidence gates. Its integration
  gate validates pre-existing hermetic JSON artifacts and can invoke the
  reporter loader, not an end-to-end command sequence. See
  scripts/run_tg8_full.py:192-267.
* TG8's `QG-E2E-01` validates Gate B Markdown and optionally checks two fixed
  historical GitHub run IDs with `gh run view`; it does not run the local
  pipeline or access Azure. See scripts/run_tg8_full.py:53, 579-610.
* `python scripts/run_tg9_full.py` builds release-readiness material from TG8
  and TG9 artifact folders. It is a decision-packet generator, not a lifecycle
  execution command. See scripts/run_tg9_full.py:1-53, 290-357.

## Exact Command Capability Gaps

### Input and Foundry Inspection

1. There is no command to inspect configured model deployments in a Foundry
	account or subscription. `config/models.yaml` is the only model-input source
	in implementation, and `FixtureRetirementSource` only opens YAML. Evidence:
	config/models.yaml:1-5; src/detector/retirement_source.py:23-57.
2. There is no retirement schedule fetch/parser. The plan specifies a scraper
	at requirements/plan.md:317-322, but that module does not exist in `src/`.
3. There is no command or adapter to retrieve a live model catalog, regional
	availability, quotas, deployment-type availability, or price. The only
	catalog implementation reads YAML fixture candidates. Evidence:
	src/recommender/catalog.py:22-55.

### Ranking and Candidate Limit

1. Ranking is deterministic and reusable, but scores are caller-supplied
	fixture fields (`quality_score`, `safety_score`, `cost_score`) rather than
	evaluation or live catalog evidence. Evidence: tests/fixtures/candidate_catalog.yaml:1-41;
	src/recommender/service.py:15-46.
2. `config/evaluation.yaml:2` sets a maximum of three candidates. The local
	CLI does not expose `--candidate-limit`. The workflow takes `candidate_limit`
	but only copies it into a placeholder run-context; it never passes the value
	to `recommend_candidates`. Evidence: src/orchestrator/cli.py:19-52;
	.github/workflows/detect-and-eval.yml:13-17, 99-101, 327-361.
3. The shipped fixture catalog produces only two eligible candidates for the
	shipped watched target. The other catalog entries fail region or deployment
	type filtering. Therefore it cannot demonstrate a top-three / provision-all-
	three path without a custom catalog. Evidence:
	tests/fixtures/candidate_catalog.yaml:1-41;
	config/models.yaml:1-5; config/evaluation.yaml:1-9.

### Provisioning and Evaluation

1. `plan_provisioning` creates `ProvisionRequest` and `TeardownPlan` data;
	it does not create a Foundry deployment. No Azure SDK dependency is listed
	in pyproject.toml:1-18.
2. The GitHub workflow logs in to Azure only to run `az account show`; its
	business orchestration is intentionally deferred. Evidence:
	.github/workflows/detect-and-eval.yml:308-361.
3. ACA dispatch is explicitly deferred. Calling the available adapter's
	`dispatch()` fails intentionally. Evidence: src/evaluator/aca_job.py:34-41;
	tests/unit/test_evaluator_aca_job.py:39-48.
4. Local runners evaluate static dataset behavior rather than actual Foundry
	inference. This means their scores are useful for contract simulation only.
	Evidence: src/evaluator/service.py:25-109; tests/unit/test_evaluator_service.py:21-45.

### Report Delivery and Automation

1. Reporter output is local files; no GitHub issue/PR client is called. The
	implemented output ends at payload serialization. Evidence:
	src/reporter/service.py:56-97.
2. The `enable_auto_pr` workflow input is guarded and recorded but not wired
	to report generation or a PR action. Evidence:
	.github/workflows/detect-and-eval.yml:13-22, 103-110, 327-361.
3. README.md:16-24 and README.md:62-65 describe full lifecycle behavior and
	non-dry-run E2E checks, but docs/setup-guide.md:10-15 and 59-63 correctly
	describe this workflow slice as scaffold-first. The latter matches code.

## Existing Test Coverage

The repository has strong unit-level coverage for individual local contracts:

* Fixture detection: tests/unit/test_detector_service.py:20-55
* Fixture ranking: tests/unit/test_recommender_service.py:20-69
* Provision-request planning: tests/unit/test_provisioner_service.py:19-78
* Dry-run staging contract: tests/unit/test_orchestrator_cli.py:21-128
* Local evaluator result materialization: tests/unit/test_evaluator_service.py:21-45
* Reporter file generation: tests/unit/test_reporter_service.py:17-39
* Deferred ACA boundary behavior: tests/unit/test_evaluator_aca_job.py:19-48

Tests use isolated, prebuilt inputs rather than a single test that invokes the
three CLIs in sequence. In particular, the evaluator test consumes
tests/fixtures/hermetic_repo/artifacts/cli-test-run, while the reporter test
consumes pre-existing evaluation files for the same fixture run. See
tests/unit/test_evaluator_service.py:21-29 and
tests/unit/test_reporter_service.py:17-26.

## Missing Integration Tests

1. A local command-chain integration test: invoke orchestrator CLI with a
	temporary run ID, evaluator CLI against that exact artifact directory, and
	reporter CLI against the resulting `results/<run-id>` directory; assert one
	report/decision per provision request.
2. A top-three integration fixture containing three eligible candidates; assert
	rank ordering, exactly three provision requests, exactly three evaluation
	result sets, and report inclusion of all three.
3. A workflow integration test proving `.github/workflows/detect-and-eval.yml`
	calls the three lifecycle commands and uploads their real output. Current
	workflow testing only validates configuration/run-context structure.
4. A live Foundry smoke/integration suite against a scratch subscription:
	inspect deployment(s), retrieve live catalog/availability/quota, provision
	a candidate via ARM, invoke the ACA job, collect results, report, and
	teardown. The requirement explicitly calls for a scripted scratch-Azure
	test per slice at requirements/plan.md:736.
5. Failure-path integration coverage for partial provisioning/evaluation,
	teardown after evaluator failure, invalid catalog data, unavailable quota,
	and report delivery/PR failure.

## Minimum Viable E2E Path Available Today

This is a **local simulated E2E path**, not a Foundry E2E path. It can exercise
all available application stages in sequence with deterministic fixture data.

Prerequisites: Python 3.12 or later and dependencies from pyproject.toml:1-18.
Run from repository root:

```powershell
python -m pip install -e ".[test]"

$runId = "local-e2e-20260717"
python -m src.orchestrator.cli --repo-root . --run-id $runId

python -m src.evaluator.service `
  --repo-root . `
  --artifact-root "artifacts/$runId" `
  --dataset tests/fixtures/evaluator/dataset.sample.jsonl

python -m src.reporter.service `
  --repo-root . `
  --artifact-root "artifacts/$runId" `
  --output-root "artifacts/$runId/reporter"
```

Expected products are staged planning manifests in `artifacts/<run-id>/`, local
candidate results in `results/<run-id>/`, and reporter files in
`artifacts/<run-id>/reporter/`. This path uses
tests/fixtures/retirement_signals.yaml and
tests/fixtures/candidate_catalog.yaml by default; it is not live evidence.

To exercise three candidates, supply custom `--fixture` and `--catalog` YAML
files with exact watch-list identity and three candidates that satisfy the
configured filters. The local limit is changed in config/evaluation.yaml, not
by a CLI flag. It is still only a plan/evaluation simulation because
provisioning and ACA dispatch remain unavailable.

## Minimum Work Required for Live E2E

1. Implement authenticated Foundry deployment introspection and a retirement
	schedule adapter; feed their typed outputs to `detect_retiring_targets`.
2. Implement a live catalog/region/quota/deployment-type source conforming to
	`CandidateCatalog`, with evidence capture and failure-closed behavior.
3. Add an ARM provisioner/teardown executor that consumes `ProvisionRequest`
	and returns real `DeploymentRef` values.
4. Implement `AcaJobAdapter.dispatch()` plus polling/result retrieval. The ACA
	job must use the private endpoint for inference as required by
	requirements/plan.md:108 and 343-355.
5. Wire orchestration, evaluator, and reporter commands into
	`.github/workflows/detect-and-eval.yml`, including the workflow input
	candidate limit and output uploads.
6. Add scratch-Azure integration coverage and make CI/release gates evaluate
	the current run rather than prebuilt artifacts and historical run IDs.

## Conclusion

The application can currently be run as a reproducible local decision-support
simulation, and its components are reusable for the requested journey. It is
not yet executable as a full user journey from model input or Foundry inspection
to a live catalog, actual top-three provisioning, live evaluation, and delivered
report. The most material blocking gap is the absence of live adapters and the
fact that the only GitHub Actions orchestrator implementation is a declared
placeholder.
