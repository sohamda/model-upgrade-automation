# Model Upgrade Automation

Automates the model lifecycle check for Azure Foundry: detect retiring models, evaluate top replacement candidates, and publish decision-ready results on a schedule.

## Purpose

This repository helps platform and AI engineering teams:

1. Detect model retirement risk early.
2. Compare replacement candidates with repeatable quality and safety checks.
3. Produce auditable outputs for go/no-go decisions.

The canonical requirements are in [requirements/plan.md](requirements/plan.md).

## What It Does

On each run, the workflow:

1. Reads configured model and evaluation settings.
2. Detects retirement candidates and proposes alternatives.
3. Runs evaluation orchestration and reliability/quality gates.
4. Publishes machine-readable artifacts and human-readable summaries.

Primary workflows:

1. [Detect and Evaluate](.github/workflows/detect-and-eval.yml)
2. [Sweep Orphans](.github/workflows/sweep-orphans.yml)
3. [CI](.github/workflows/ci.yml)

## How It Works

Architecture pattern:

1. GitHub Actions orchestrates control-plane operations.
2. Azure hosts the runtime and storage surfaces.
3. Reliability, quality, and release decisions are emitted as artifact packages.

Key artifact outputs:

1. TG8 quality gate package (generated per workflow run and downloadable from Actions artifacts)
2. TG9 release readiness package (generated per workflow run and downloadable from Actions artifacts)
3. Azure gate checkpoints: [.copilot-tracking/squad/](.copilot-tracking/squad/)

## Use in Your Org

### 1) Configure Azure prerequisites

1. Provision baseline infra from [infra/main.bicep](infra/main.bicep).
2. Configure OIDC app registration and federated credentials for GitHub Actions.
3. Ensure the target Foundry account has a project for evaluation runs.

Reference docs:

1. [docs/setup-guide.md](docs/setup-guide.md)
2. [docs/oidc-setup.md](docs/oidc-setup.md)
3. [docs/tg2-operator-evidence.md](docs/tg2-operator-evidence.md)

### 2) Configure repository variables

At minimum for non-dry-run execution:

1. AZURE_CLIENT_ID
2. AZURE_TENANT_ID
3. AZURE_SUBSCRIPTION_ID
4. RESOURCE_GROUP
5. FOUNDRY_ACCOUNT_NAME
6. FOUNDRY_PROJECT_NAME
7. ACA_ENVIRONMENT_NAME
8. ACA_JOB_NAME
9. STORAGE_ACCOUNT_NAME
10. KEY_VAULT_NAME

Optional toggles:

1. ENABLE_SCHEDULED_EVALS=true
2. ENABLE_ORPHAN_SWEEP=true
3. ENABLE_AUTO_PR=false

### 3) Run end-to-end checks

Recommended order:

1. Run CI.
2. Run Detect and Evaluate with dry_run=true.
3. Run Detect and Evaluate with dry_run=false.
4. Run Sweep Orphans with dry_run=true.

### 4) Read results

1. Workflow run page Summary tab now shows compact report output.
2. Download run artifacts for raw JSON evidence.
3. See a committed sample output summary in [docs/demo-results.md](docs/demo-results.md).

## Current Status

Implementation is complete through TG9 with validated gate and release artifacts. See the squad decision trail in [.copilot-tracking/squad/decisions.md](.copilot-tracking/squad/decisions.md).

