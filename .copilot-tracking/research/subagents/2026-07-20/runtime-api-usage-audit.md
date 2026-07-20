---
title: Runtime API Usage Audit
description: Evidence audit of planned model data sources in executable runtime paths
ms.date: 2026-07-20
---
<!-- markdownlint-disable-file -->

## Scope

Audit only executable runtime paths in `src/` and the current orchestrator pipeline.
Documentation-only source references are not counted as runtime use. The audit covers
nine sources named in `requirements/plan.md` section 6 and default/fallback behavior
in the current code.

## Plan Intent

`requirements/plan.md` sections 6.1 through 6.8 define the following intended source
roles:

| Source | Planned role |
|---|---|
| ARM Models API | Primary lifecycle, availability, capabilities, and meter data |
| Azure OpenAI `/openai/models` | Secondary account-specific view, explicitly not used by the tool |
| Azure Retail Prices API | Primary per-token pricing |
| Retirement schedule markdown | Fallback replacement hints |
| Models-sold-directly markdown | Fallback capability metadata |
| HuggingFace model API | Fallback OSS metadata |
| HuggingFace Open LLM Leaderboard | Fallback OSS pre-filter benchmark signal |
| Resource SKUs API | Secondary subscription SKU availability pre-flight |
| CognitiveServices deployments list | Live deployed-model discovery used by the pipeline when requested |

## Runtime Evidence Matrix

| API/source name | Runtime use | Evidence | Notes |
|---|---|---|---|
| ARM Models API: `management.azure.com/.../locations/{loc}/models?api-version=2025-06-01` | No | No implementation was found under `src/` for this endpoint, `CognitiveServicesManagementClient`, or an ARM Models SDK equivalent | Mentioned as primary in `requirements/plan.md` section 6.1 and in repository-structure comments only. Current live catalog does not call it |
| Azure OpenAI data plane: `/openai/models` | No | No endpoint/client match under `src/` | `requirements/plan.md` section 6.2 explicitly says this tool does not use it. Documentation-only reference |
| Azure Retail Prices API: `https://prices.azure.com/api/retail/prices` | No | No HTTP client or pricing module exists under `src/`; `src/recommender/` contains only `catalog.py`, `foundry_catalog_source.py`, `models.py`, `service.py`, and `weights.py` | Planned in `requirements/plan.md` section 6.3. `pricing_client.py` is a planned repository-layout entry, not an implementation |
| Raw retirement schedule markdown | Yes | `src/detector/retirement_schedule_source.py`: `LearnRetirementScheduleSource._fetch_text()` creates `Request` and invokes `urlopen`; `load()` returns parsed live entries | Calls `https://raw.githubusercontent.com/MicrosoftDocs/azure-ai-docs-pr/live/articles/foundry/openai/concepts/model-retirement-schedule.md`. Used when the official-source branch is selected |
| Raw models-sold-directly markdown | Yes | `src/recommender/foundry_catalog_source.py`: `LearnFoundryCatalogSource._fetch()` creates `Request` and invokes `urlopen`; `load()` parses it into catalog candidates | Calls `https://raw.githubusercontent.com/MicrosoftDocs/azure-ai-docs-pr/live/articles/foundry/foundry-models/concepts/models-sold-directly-by-azure.md`. Current parser extracts model/version rows; it does not implement the full planned capability metadata cascade |
| HuggingFace model API | No | No `huggingface.co` endpoint/client match under `src/` | Planned fallback in `requirements/plan.md` section 6.6 only |
| HuggingFace Open LLM Leaderboard API | No | No leaderboard endpoint/client match under `src/` | Planned fallback in `requirements/plan.md` section 6.7 only |
| Resource SKUs API: `.../providers/Microsoft.CognitiveServices/skus?api-version=2025-06-01` | No | No endpoint/client or runtime script match found under `src/` or `scripts/` | Planned secondary pre-flight in `requirements/plan.md` section 6.8 only |
| CognitiveServices deployments list introspection | Yes, opt-in | `src/detector/deployed_introspector.py`: `discover_foundry_deployments()` executes `az cognitiveservices account deployment list --name <account> --resource-group <rg> --output json`; `src/orchestrator/pipeline.py`: `execute_dry_run()` calls it only when `RuntimeOptions.discover_from_azure` is true | Implemented through Azure CLI rather than a direct REST client. `src/orchestrator/cli.py` exposes the opt-in `--discover-from-azure` flag |

## Orchestrator Default and Fallback Verification

* Yes. Current default repository configuration selects official-source resolution: `config/models.yaml` sets `use_official_sources: true`, and `src/shared/config.py`: `load_app_config()` maps it to `AppConfig.use_official_sources` with a default of `True`.
* Yes. `src/orchestrator/pipeline.py`: `_should_use_official_sources()` selects official sources when `RuntimeOptions.live_catalog` is true; otherwise an explicit `RuntimeOptions.use_official_sources` value wins; otherwise the configuration value wins.
* Yes. Without explicit fixture paths and with official sources selected, `_resolve_source()` uses `_FallbackRetirementSource(LearnRetirementScheduleSource(), build_default_fixture(repo_root))` and `_resolve_catalog()` uses `_FallbackCatalogSource(LearnFoundryCatalogSource(), build_default_catalog(repo_root))`.
* Yes. Both fallback wrappers fall back only when the live source raises `DependencyUnavailableError`. The fallbacks are fixture files: `tests/fixtures/retirement_signals.yaml` through `src/detector/retirement_source.py`: `build_default_fixture()`, and `tests/fixtures/candidate_catalog.yaml` through `src/recommender/catalog.py`: `build_default_catalog()`.
* No. The default official-source branch does not default to the planned ARM Models, Retail Prices, HuggingFace, Resource SKUs, or Azure OpenAI data-plane sources. The only current live official-source calls are the two raw MicrosoftDocs markdown URLs.
* No. Deployment introspection is not part of the default path. `src/orchestrator/pipeline.py`: `execute_dry_run()` invokes `discover_foundry_deployments()` only when `RuntimeOptions.discover_from_azure` is true, which is set by `src/orchestrator/cli.py` only with `--discover-from-azure`.

## Test Evidence

* `tests/unit/test_pipeline_runtime_gates.py`: `test_given_runtime_override_when_resolving_source_then_official_source_is_enabled` asserts the official-source resolver uses `_FallbackRetirementSource`.
* `tests/unit/test_pipeline_runtime_gates.py`: `test_given_live_retirement_failure_when_loading_then_fixture_fallback_is_used` and `test_given_live_catalog_failure_when_loading_then_fixture_fallback_is_used` verify fallback to fixture data after `DependencyUnavailableError`.
* `tests/unit/test_retirement_schedule_source.py` and `tests/unit/test_foundry_catalog_source.py` cover parsing, not live network execution.

## Conclusion

Two of the nine named sources are currently executed in the normal official-source branch: the raw retirement schedule and models-sold-directly markdown URLs. A third, CognitiveServices deployment listing, is implemented behind an explicit opt-in. The other six sources are currently plan/documentation intent only, with no matching runtime HTTP, SDK, or CLI implementation found in the audited executable surfaces.
