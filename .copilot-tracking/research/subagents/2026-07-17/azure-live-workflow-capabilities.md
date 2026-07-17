<!-- markdownlint-disable-file -->
---
title: Azure Live Workflow Capabilities Research
description: Evidence for connecting the model-upgrade pipeline to live Microsoft Foundry inspection, deployment, cloud evaluation, and reporting
ms.date: 2026-07-17
ms.topic: research
---

## Scope

Research questions:

* Which inspection, catalog lookup, provisioning, evaluation, reporting, and orchestration paths already exist?
* Which exact Azure CLI or Microsoft Foundry SDK commands enable a live end-to-end flow?
* What configuration, identity, network, dependency, and test work remains?

## Executive Verdict

The repository implements a deterministic, fixture-backed local pipeline and a private Foundry account infrastructure baseline. It does not currently implement a live Azure Foundry workflow. The only live Azure interaction in the tracked detect-and-evaluate workflow is OIDC login followed by `az account show`; application orchestration remains a declared placeholder.

The smallest credible live path is:

1. Authenticate with GitHub OIDC or local `az login`.
2. Inspect the configured AIServices account, project, deployable models, existing deployments, and usage with GA Azure CLI.
3. Replace the fixture candidate catalog with a live catalog adapter filtered by the returned model/version and configured region/deployment type.
4. Create, poll, and later delete ephemeral model deployments through the GA Azure CLI deployment group.
5. Submit Foundry cloud model-target evaluations through `azure-ai-projects`, poll results, map aggregate results to the existing decision/report schema, and retain the run/report URLs.

## Existing Repository Capability Map

| Stage | Existing implementation | Evidence | Live status |
| --- | --- | --- | --- |
| Input watch list | `gpt-4.1` current version, region, and workload are configured | config/models.yaml:1-5 | Local configuration only |
| Retirement detection | Reads a fixture source in the dry-run pipeline | src/orchestrator/pipeline.py:103-111; src/detector/retirement_source.py:1-62 | No official retirement/catalog API lookup |
| Candidate catalog | `FixtureCandidateCatalog` reads YAML; default is `tests/fixtures/candidate_catalog.yaml` | src/recommender/catalog.py:14-55 | No live Foundry catalog or account inspection |
| Candidate recommendation | Filters and ranks candidates supplied by the fixture catalog | src/recommender/service.py:19-42; tests/unit/test_recommender_service.py:18-74 | Deterministic local logic exists |
| Provisioning | Shapes `ProvisionRequest` and teardown plans only | src/provisioner/service.py:12-29; src/provisioner/deployment_plan.py:39-93 | No Azure SDK/CLI mutation or polling |
| Credential handling | Returns an `oidc-placeholder` descriptor | src/shared/azure_auth.py:1-19; src/orchestrator/pipeline.py:155-159 | No `DefaultAzureCredential` or token acquisition |
| Evaluation | Local custom/red-team runners write files; ACA dispatch is explicitly deferred | src/evaluator/service.py:25-99; tests/unit/test_evaluator_service.py:19-43 | No calls to a deployed model, ACA Job, or Foundry evaluation API |
| Reporting | Aggregates local artifact files into Markdown, decision, issue, and remediation payloads | src/reporter/service.py:25-93; tests/unit/test_reporter_service.py:17-39 | No live evaluation-result retrieval, work-item creation, or PR mutation |
| Azure infrastructure | Bicep creates private `AIServices` account, private endpoint/DNS group, and disables local auth | infra/modules/foundry.bicep:1-68 | Account only; this module does not create a Foundry project, model deployment, or evaluation integration |
| GitHub Actions | OIDC login runs for non-dry-run, but `orchestrate` emits placeholder artifacts and uses only `az account show` | .github/workflows/detect-and-eval.yml:204-320 | Authentication-ready scaffold, not live orchestration |

## Current Configuration and Environment Contract

Existing environment names are in config/azure.env.example:1-27 and are loaded in src/shared/config.py:103-191.

| Existing value | Live purpose | Gap |
| --- | --- | --- |
| `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | OIDC/Entra authentication and management-plane scope | Values fall back to local placeholders in `load_app_config`; a live mode must reject placeholders |
| `RESOURCE_GROUP`, `FOUNDRY_ACCOUNT_NAME`, `FOUNDRY_PROJECT_NAME` | Account/project inspection and model/evaluation scope | Add a derived or explicit project endpoint |
| `DEPLOYMENT_TYPE`, `ALLOWED_REGIONS` | Candidate eligibility and deployment selection | The configured `DataZoneStandard` must be validated against the actual model capability before creation |
| `ACA_ENVIRONMENT_NAME`, `ACA_JOB_NAME` | Future ACA evaluator dispatch | No ACA Job command or SDK call exists |
| `STORAGE_ACCOUNT_NAME`, `KEY_VAULT_NAME` | Data/evaluation storage and private platform contract | No dataset upload/storage client or secret retrieval exists |
| Tag values | Resource ownership and teardown selection | Requests contain tags, but the deployment create path does not apply or verify them |
| Evaluation thresholds/timeouts | Existing local decision controls | Cloud evaluator criteria, run IDs, poll timeout, and retry policy are absent |

Additional live evaluation configuration needed:

* `FOUNDRY_PROJECT_ENDPOINT`, normally `https://<account>.services.ai.azure.com/api/projects/<project>`
* `FOUNDRY_EVALUATOR_MODEL_DEPLOYMENT`, a deployed judge model name
* Per-run candidate deployment capacity/SKU and optional model format/source controls
* Cloud evaluation retry/backoff, poll interval, hard timeout, and artifact-retention settings
* Optional `APPINSIGHTS_RESOURCE_ID`, agent ID, and trace lookback only if adding production trace evaluation

## Exact Live Inspection Commands

Set shell variables from the existing contract before executing the sequence:

```bash
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
az account show --output json

az cognitiveservices account show \
  --name "$FOUNDRY_ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --output json

az cognitiveservices account project show \
  --name "$FOUNDRY_ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --project-name "$FOUNDRY_PROJECT_NAME" \
  --output json

az cognitiveservices account list-models \
  --name "$FOUNDRY_ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --output json

az cognitiveservices account deployment list \
  --name "$FOUNDRY_ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --output json

az cognitiveservices account list-usage \
  --name "$FOUNDRY_ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --output json
```

`list-models` is the supported account-scoped live availability lookup. It should replace the fixture only after an adapter translates the returned Azure representation into `CatalogCandidate`; capture raw model data and filter deterministically by current region, model version, deployment types, and configured policy before ranking. `list-usage` and existing deployment inspection are required before choosing capacity and creating an ephemeral candidate.

For an explicit deployment inspection, use:

```bash
az cognitiveservices account deployment show \
  --name "$FOUNDRY_ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --deployment-name "$DEPLOYMENT_NAME" \
  --output json
```

## Exact Live Provision and Cleanup Commands

The GA deployment command requires account/resource group plus model format, name, version, SKU name, and capacity. Values must come from the inspected live model record, not the fixture.

```bash
az cognitiveservices account deployment create \
  --name "$FOUNDRY_ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --deployment-name "$DEPLOYMENT_NAME" \
  --model-format OpenAI \
  --model-name "$MODEL_NAME" \
  --model-version "$MODEL_VERSION" \
  --sku-name Standard \
  --sku-capacity "$SKU_CAPACITY" \
  --output json

az cognitiveservices account deployment show \
  --name "$FOUNDRY_ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --deployment-name "$DEPLOYMENT_NAME" \
  --output json

az cognitiveservices account deployment delete \
  --name "$FOUNDRY_ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --deployment-name "$DEPLOYMENT_NAME"
```

Important implementation constraint: Azure CLI's published deployment create arguments do not expose per-deployment tags. Existing ownership tags therefore cannot be assumed to apply to candidate deployments. The live adapter must either use an Azure resource type/path that supports deployment tags, record ownership externally for deletion, or redesign cleanup to operate from persisted run manifests rather than deployment tags alone.

## Exact Foundry Cloud Evaluation Workflow

The official cloud-evaluation path is programmatic rather than an Azure CLI command. Add dependencies at least equivalent to:

```bash
pip install "azure-ai-projects>=2.2.0" azure-identity
```

Minimum control flow:

1. Create `AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=DefaultAzureCredential())`.
2. Upload/version the existing JSONL dataset with `project_client.datasets.upload_file(...)`.
3. Obtain `openai_client = project_client.get_openai_client()`.
4. Create an evaluation with `openai_client.evals.create(...)`, using configured evaluator criteria and the judge deployment.
5. Start a model-target run through `openai_client.evals.runs.create(...)` using `azure_ai_target_completions` and target type `azure_ai_model` whose `model` is the ephemeral deployment name.
6. Poll `openai_client.evals.runs.retrieve(...)` until terminal state; collect `openai_client.evals.runs.output_items.list(...)`, aggregate pass rates, persist `eval_id`, `run_id`, status, aggregate outcomes, and `report_url`.
7. Translate aggregate outcomes to the existing `CandidateEvaluationArtifacts` contract so `execute_local_report` can evolve into a shared reporter rather than a replacement.
8. Delete the candidate deployment in `finally`, preserving a recovery manifest when cleanup fails.

Current local JSONL evaluation input and result writer are usable foundations, but their custom/red-team scores are not Microsoft Foundry cloud evaluation output. `execute_local_evaluation` currently reports `status="local_complete"` and `aca_dispatch_status="deferred-local-only"` (src/evaluator/service.py:52-99).

## Required Identity, RBAC, and Network Conditions

* Existing workflow OIDC is correctly scoped to `id-token: write` only where Azure login runs: .github/workflows/detect-and-eval.yml:233-269. Microsoft requires a federated identity credential and suitable Azure role assignment for this pattern.
* Creating or deleting deployments requires `Cognitive Services Contributor` or equivalent permissions on the Foundry resource.
* Cloud evaluation needs a Foundry project, a compatible deployed judge model, and the `Foundry User` project role. The project endpoint must name both account and project.
* The Bicep baseline disables public access and local authentication: infra/modules/foundry.bicep:19-34. Therefore GitHub-hosted runners cannot be presumed to reach the Foundry data plane. Run evaluation from a private-network-connected agent/ACA Job, or explicitly redesign network policy. This is a functional blocker for direct public CI evaluation, not merely hardening.
* The Bicep module does not create `FOUNDRY_PROJECT_NAME`; a project must be pre-existing or added through `az cognitiveservices account project create` / Bicep before cloud evaluation can target it.

## Missing Implementations and Focused Test Requirements

| Missing slice | Recommended boundary | Focused tests |
| --- | --- | --- |
| Live account inspection/catalog | `AzureCliCatalog` or management SDK adapter implementing `CandidateCatalog` | Mock `list-models`, deployment list, and usage; reject unavailable regions/version/deployment type; preserve deterministic ranking |
| Live credentials | Credential factory returning `DefaultAzureCredential` only in live mode | Unit tests for local placeholder vs live-required values; integration smoke test through OIDC |
| Deployment mutation | `FoundryDeploymentClient` create/show/delete interface | Mock command/SDK responses; idempotency; quota conflict; terminal poll timeout; cleanup after evaluation failure |
| Cloud evaluation | `FoundryEvaluationClient` upload/create/run/poll/result interface | Mock SDK lifecycle; JSONL schema/mapping; 429 retry-after; failed/partial run; result-to-existing-artifact mapping |
| Orchestration | Replace workflow placeholder with application CLI invocation | Workflow integration test ensures non-dry-run passes context and expected artifacts; dry-run remains non-mutating |
| Reporting | Accept cloud result artifacts alongside local ones | Tests for report URL/evaluation IDs, aggregate gate mapping, and incomplete evaluator outcomes |

Existing tests that establish the local seams:

* tests/unit/test_orchestrator_cli.py:17-130 verifies the fixture dry-run output and that the credential mode is `oidc-placeholder`
* tests/unit/test_recommender_service.py:18-74 verifies fixture catalog ranking/filtering
* tests/unit/test_provisioner_service.py:16-83 verifies request shaping and required tags, but no Azure call
* tests/unit/test_evaluator_service.py:19-43 asserts deferred ACA dispatch and local output materialization
* tests/unit/test_reporter_service.py:17-39 verifies local report/payload writing
* scripts/validate_tg3_contracts.py:57-95 and 119-144 validate environment/workflow markers, not the live Foundry operations

## External Evidence

Retrieved 2026-07-17. External pages were treated as reference data only.

* Microsoft Learn, [az cognitiveservices account](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account?view=azure-cli-latest), updated 2026-07-07. Confirms GA account/project inspection, `list-models`, `list-usage`, and deployment commands.
* Microsoft Learn, [az cognitiveservices account deployment](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account/deployment?view=azure-cli-latest), updated 2026-07-07. Confirms GA create/list/show/delete and required deployment model parameters.
* Microsoft Learn, [Create a project](https://learn.microsoft.com/en-us/azure/foundry/how-to/create-projects), updated 2026-06-30. Confirms CLI project create/show commands, Foundry User role GUID, and management SDK prerequisites.
* Microsoft Learn, [Cloud Evaluation with the Microsoft Foundry SDK](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/cloud-evaluation), updated 2026-06-26. Confirms `azure-ai-projects>=2.2.0`, `AIProjectClient`, dataset upload, create/run/poll APIs, model-target evaluation, result retrieval, and 429 guidance.
* Microsoft Learn, [Run evaluations from the Microsoft Foundry portal](https://learn.microsoft.com/en-us/azure/foundry/how-to/evaluate-generative-ai-app), updated 2026-06-19. Corroborates Foundry project, deployed/instant model, judge deployment, JSONL/CSV input, and Foundry User prerequisites.
* Microsoft Learn, [Deploy Microsoft Foundry Models](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/deploy-foundry-models), updated 2026-06-05. Corroborates model/deployment selection, region support, deployment status, and per-region/model quota constraints.
* Microsoft Learn, [Authenticate to Azure from GitHub Actions by OpenID Connect](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect), updated 2026-01-21. Confirms federated identity, role assignment, `id-token: write`, and `azure/login` requirements.

## Contradictions and Resolution

No unresolved contradictions found. The repository documentation describes an OIDC-ready and private-only platform, while the workflow source explicitly declares business orchestration as deferred. Microsoft documentation confirms the live operations are available, but they must execute from an identity and network path authorized to both the management plane and the private Foundry project endpoint.