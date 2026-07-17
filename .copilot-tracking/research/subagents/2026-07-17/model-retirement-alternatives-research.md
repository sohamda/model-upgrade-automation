<!-- markdownlint-disable-file -->
---
title: Model Retirement Alternatives Research
ms.date: 2026-07-17
---

## Research Scope

Question: "gpt-4.1 is retiring, how can I use this repo to find the alternative?"

Required evidence:

* Detection and recommendation workflow
* Runnable local and GitHub Actions commands
* Model watch-list and retirement-horizon configuration
* Result locations
* Fixture/mock versus live-data caveats

## Executive Conclusion

The repository can produce a local, deterministic shortlist for a GPT-4.1 retirement, but
it cannot yet discover retirement notices, catalog candidates, Foundry availability, or
evaluation results from Azure. Its GitHub Actions `Detect and Evaluate` workflow is also
explicitly a scaffold: it emits context and placeholder artifacts, not recommendations.

On 2026-07-17, GPT-4.1 version `2025-04-14` is 89 days from the current official
retirement date, `2026-10-14`, so it falls inside the repository's default 90-day horizon.
Microsoft's schedule lists no replacement for that row. The right use of this repository
today is therefore to supply a curated, region-compatible candidate fixture and let its
scoring and optional local evaluation choose a candidate; it is not a live answer engine.

## Evidence-Backed Workflow

1. Keep the deployed model in `config/models.yaml` as a watch-list entry. The checked-in
	 entry is GPT-4.1 version `2025-04-14`, Sweden Central, and `general_qa`.
	 Evidence: config/models.yaml:1-5; src/shared/config.py:119-138.
2. Obtain the retirement date and any replacement hint from the official Foundry retirement
	 schedule. Save that information in a retirement-signals YAML file because the shipped
	 detector reads only `FixtureRetirementSource` data.
	 Evidence: src/detector/retirement_source.py:23-57; src/orchestrator/pipeline.py:97-110.
3. Supply a candidate catalog YAML containing only candidates that have already been checked
	 for compatible API surface, region, deployment type, quota, workload, and lifecycle.
	 The recommender uses only values from this local file; it does not query Foundry.
	 Evidence: src/recommender/catalog.py:22-55; src/recommender/filters.py:12-38.
4. Run `python -m src.orchestrator.cli`. The pipeline matches a retirement signal to the
	 watch list, excludes signals outside the horizon, filters candidates, scores them, and
	 stages the ranking.
	 Evidence: src/detector/service.py:17-64; src/recommender/service.py:15-43;
	 src/orchestrator/cli.py:19-81; src/orchestrator/pipeline.py:97-169.
5. Inspect `artifacts/<run-id>/recommender.json` for the ordered alternatives. Its ranking
	 is $0.5 * quality + 0.3 * safety + 0.2 * cost$; the values are fixture-provided scores.
	 Evidence: config/recommender.yaml:1-7; src/recommender/scorer.py:10-40;
	 src/orchestrator/pipeline.py:43-94.
6. For an evaluation-backed result, run the local evaluator against a JSONL dataset, then
	 run the reporter. The reporter produces a Markdown comparison, decision JSON, and issue/
	 remediation payloads, using both ranking and local evaluation results.
	 Evidence: src/evaluator/service.py:20-107; src/reporter/artifact_loader.py:43-201;
	 src/reporter/service.py:33-147.

## Fast Local Dry-Run

### Prerequisites

* Python 3.12 or later, per pyproject.toml:1-15
* Run from the repository root
* `pyyaml`; install the project and test dependency with the command below

```powershell
python -m pip install -e ".[test]"
```

Create a local retirement signal from the official schedule. This example uses the official
date as of 2026-07-17. The optional `replacement_family` is a local filtering label, not a
Microsoft recommendation; choose it to match candidate entries that the workload owner has
validated.

```powershell
@'
retiring_models:
	- model_id: gpt-4.1
		current_version: "2025-04-14"
		retirement_date: "2026-10-14"
		replacement_family: gpt-4.1-successor
		source: microsoft-foundry-retirement-schedule-2026-07-09
'@ | Set-Content .\retirement-signals-gpt41.yaml
```

Create a candidate catalog. Replace the illustrative model IDs, versions, and scores only
after validating their current availability in the intended region and deployment type. The
scores are the inputs to the deterministic rank, not externally measured facts.

```powershell
@'
candidates:
	- model_id: candidate-a
		version: "validated-version-a"
		region: swedencentral
		deployment_types: [DataZoneStandard]
		workloads: [general_qa]
		replacement_families: [gpt-4.1-successor]
		quality_score: 0.90
		safety_score: 0.96
		cost_score: 0.70
	- model_id: candidate-b
		version: "validated-version-b"
		region: swedencentral
		deployment_types: [DataZoneStandard]
		workloads: [general_qa]
		replacement_families: [gpt-4.1-successor]
		quality_score: 0.86
		safety_score: 0.94
		cost_score: 0.84
'@ | Set-Content .\candidate-catalog-gpt41.yaml
```

Run a deterministic dry-run. Pre-create the artifact directory because PowerShell opens the
`Tee-Object` output file before the Python program stages its artifacts.

```powershell
$runId = "gpt41-20260717"
New-Item -ItemType Directory -Force "artifacts/$runId" | Out-Null
python -m src.orchestrator.cli `
	--repo-root . `
	--fixture .\retirement-signals-gpt41.yaml `
	--catalog .\candidate-catalog-gpt41.yaml `
	--run-id $runId |
	Tee-Object "artifacts/$runId/cli-output.json"
```

Expected result: stdout and `artifacts/gpt41-20260717/recommender.json` contain one
recommendation whose `retiring_target` is GPT-4.1 and whose `ranked_candidates` are ordered
by score. The command also creates `detector.json`, `provisioner.json`,
`history_preview.json`, and `dry_run_output.json`.

Validation checks:

```powershell
Get-Content "artifacts/$runId/recommender.json"
Get-Content "artifacts/$runId/detector.json"
python -m pytest -q tests/unit/test_detector_service.py tests/unit/test_recommender_service.py tests/unit/test_orchestrator_cli.py
```

The unit tests establish the staging contract and show that the checked-in fixture ranking
returns GPT-4.1 before GPT-4.1-nano for the *GPT-4.1-mini* fixture scenario, not a GPT-4.1
retirement recommendation. Evidence: tests/unit/test_orchestrator_cli.py:19-114;
tests/unit/test_recommender_service.py:18-79.

## Evaluation And Final Local Report

The initial dry-run only ranks supplied candidates. To produce a local decision report,
execute the evaluator and reporter with the same run identifier.

```powershell
python -m src.evaluator.service `
	--repo-root . `
	--artifact-root "artifacts/$runId" `
	--dataset tests/fixtures/evaluator/dataset.sample.jsonl

python -m src.reporter.service `
	--repo-root . `
	--artifact-root "artifacts/$runId" `
	--output-root "artifacts/$runId/reporter-output"
```

Expected result locations:

* `results/<run-id>/<candidate-slug>/custom.json`, `redteam.json`, and `summary.json`: local
	evaluation outputs. Evidence: src/evaluator/service.py:20-107.
* `artifacts/<run-id>/reporter-output/<target>-report.md`: readable comparison and
	recommendation.
* `artifacts/<run-id>/reporter-output/<target>-decision.json`: chosen candidate and decision.
* `artifacts/<run-id>/reporter-output/<target>-issue-payload.json` and
	`<target>-remediation-payload.json`: draft downstream payloads.
	Evidence: src/reporter/service.py:33-94.

The local evaluator does not call Azure or deploy models. It returns `local_complete` and
`aca_dispatch_status: deferred-local-only`; the ACA adapter's dispatch method deliberately
raises a deferred dependency error. Evidence: src/evaluator/service.py:59-107;
src/evaluator/aca_job.py:20-40.

## Production Workflow Run

The intended GitHub entry point is `.github/workflows/detect-and-eval.yml`, scheduled each
Monday at 04:00 UTC and manually dispatchable with `dry_run`, `candidate_limit`, and
`enable_auto_pr` inputs. Evidence: .github/workflows/detect-and-eval.yml:1-27.

Use GitHub Actions: Actions > `Detect and Evaluate` > `Run workflow` > first use
`dry_run=true`. For a non-dry-run scaffold check, set `dry_run=false` only after configuring
the required GitHub variables and OIDC federation.

The required variables are `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`,
`AZURE_SUBSCRIPTION_ID`, `RESOURCE_GROUP`, `FOUNDRY_ACCOUNT_NAME`,
`FOUNDRY_PROJECT_NAME`, `ACA_ENVIRONMENT_NAME`, `ACA_JOB_NAME`,
`STORAGE_ACCOUNT_NAME`, and `KEY_VAULT_NAME`. Evidence: config/azure.env.example:4-16;
docs/setup-guide.md:17-34; .github/workflows/detect-and-eval.yml:161-192.

Optional variables include `ENABLE_SCHEDULED_EVALS=true`, `ENABLE_AUTO_PR=true`,
`RETIREMENT_HORIZON_DAYS`, `ALLOWED_REGIONS`, deployment and cleanup tags. Repository
variables override workflow defaults. Evidence: config/azure.env.example:18-30;
.github/workflows/detect-and-eval.yml:47-76 and 89-93.

Expected GitHub workflow artifacts today:

* `run-context-<run-id>`: `.artifacts/run-context.env` and `run-context.json`
* `detect-and-eval-<run-id>`: `orchestrator-summary.json` and `teardown-plan.json`
* `finalize-<run-id>`: `finalize-summary.md`, `cleanup-recovery.json`,
	`workflow-report.md`, and `workflow-report.json`

Evidence: .github/workflows/detect-and-eval.yml:212-221, 289-297, and 439-460.

Critical production caveat: this workflow does not invoke the detector, recommender,
provisioner, evaluator, or reporter. Its own summary says TG4/TG5 must replace the
placeholder; `docs/setup-guide.md` confirms this limitation. Therefore it cannot currently
produce alternative recommendations in a GitHub Actions run. Evidence:
.github/workflows/detect-and-eval.yml:251-286; docs/setup-guide.md:59-67.

## Configuration Map

| Need | Configuration surface | Current behavior |
| --- | --- | --- |
| Models to watch | `config/models.yaml` | Must be a non-empty `watch_list`; each entry has model ID, version, region, workload, and optional per-model `retirement_horizon_days` |
| Default horizon and candidate count | `config/evaluation.yaml` | Default horizon is 90 days and candidate count is 3 |
| Ranking and hard filters | `config/recommender.yaml` | Weights must sum to 1.0; supported deployment type is required by default; same-region is currently false |
| Local/Actions environment values | `config/azure.env.example` and process/GitHub variables | Local code has placeholder fallbacks for identifiers, while workflow non-dry-run rejects missing variables |
| Runtime override | `RETIREMENT_HORIZON_DAYS` | Overrides the workflow context horizon; local detector uses `config.azure.retirement_horizon_days` unless the model has its own horizon |

Relevant implementation details: src/shared/config.py:107-209; src/shared/run_context.py:49-96;
src/detector/service.py:25-46; scripts/validate_tg3_contracts.py:116-178.

## Important Caveats

* The checked-in retirement fixture is for `gpt-4.1-mini`, with an artificial retirement
	date of 2026-08-15. It does not detect the real GPT-4.1 retirement. The default candidate
	catalog is also a test fixture. Evidence: tests/fixtures/retirement_signals.yaml:1-11;
	tests/fixtures/candidate_catalog.yaml:1-43.
* Local scores are supplied by the catalog fixture. They are not capability, price, safety,
	quota, benchmark, or regional-availability measurements. Evidence:
	src/recommender/catalog.py:27-47; src/recommender/scorer.py:21-40.
* The requirements document plans live Foundry retirement-document parsing, ARM deployment
	introspection, and catalog scraping, but current source code contains none of those live
	implementations. Treat requirements/plan.md as target architecture, not available
	functionality. Evidence: requirements/plan.md:316-346; src/detector/retirement_source.py:1-57;
	src/recommender/catalog.py:1-55; src/shared/azure_auth.py:1-18.
* A true production recommendation requires current Microsoft documentation, actual regional
	availability and quota checks, workload/API compatibility review, and real evaluation.
	Do not migrate merely because the local rank is first.
* Runtime `artifacts/` and `results/` are intentionally gitignored. Copy or upload required
	evidence before cleaning the working tree. Evidence: .gitignore:12-18.

## External Sources

* Microsoft Learn, [Model retirement schedule](https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule), retrieved 2026-07-17, page dated 2026-07-09. GPT-4.1 `2025-04-14` is Deprecated, retires 2026-10-14, and has no listed replacement.
* Microsoft Learn, [Foundry Models sold by Azure](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure), retrieved 2026-07-17, page updated 2026-07-07. Provides current model capabilities and directs users to region availability documentation; it lists the GPT-4.1 family and newer GPT-5 series.

## Assumptions And Follow-On Questions

Assumptions:

* The user is retiring the standard Azure OpenAI deployment of GPT-4.1 version `2025-04-14`, not a fine-tuned deployment. Fine-tuned GPT-4.1 has a different deployment retirement date in the official schedule.
* The intended workload matches the current `general_qa` configuration and Sweden Central is the desired region. Change `config/models.yaml`, `config/evaluation.yaml`, and fixture metadata if either differs.
* The user will confirm candidate model availability, quota, commercial suitability, and API compatibility before assigning catalog scores.

Follow-on work needed for a real unattended production path:

* Implement the retirement schedule parser and source it from Microsoft Learn.
* Implement live Foundry catalog/region/quota and deployment introspection.
* Invoke the local CLI pipeline from `detect-and-eval.yml` and upload its staged outputs.
* Replace local evaluator adapters with ACA/Foundry execution and bind reporter delivery.
