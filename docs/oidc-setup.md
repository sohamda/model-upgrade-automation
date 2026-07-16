---
title: OIDC Setup
description: Secretless GitHub Actions authentication setup for the TG3 delivery foundation
ms.date: 2026-07-15
ms.topic: how-to
---

## Overview

TG3 assumes GitHub Actions authenticates to Azure through workload identity federation.

No client secret is required or recommended.

Use [docs/tg2-operator-evidence.md](c:\Users\sohadasgupta\IdeaProjects\hve-squad\model-upgrade-automation\docs\tg2-operator-evidence.md) for the TG2-owned identity inputs and readiness evidence.

## Federated credential inputs

TG2 must publish the final workflow identity contract before TG3 moves beyond scaffold-first execution.

See [docs/tg2-operator-evidence.md](c:\Users\sohadasgupta\IdeaProjects\hve-squad\model-upgrade-automation\docs\tg2-operator-evidence.md) for the required input list and placeholder subject patterns.

At minimum, the final subject must replace the documented placeholder pattern `repo:<org>/<repo>:ref:refs/heads/main` with the repository-specific value approved by TG2.

## GitHub-side configuration

Store these as repository or environment variables:

* `AZURE_CLIENT_ID`
* `AZURE_TENANT_ID`
* `AZURE_SUBSCRIPTION_ID`

Use environment variables instead of repository secrets for these non-secret identifiers.

## Workflow permissions

Only jobs that authenticate to Azure request `id-token: write`.

Other jobs remain at `contents: read`.

This keeps the workflow aligned with least-privilege expectations while preserving the OIDC handshake required by `azure/login`.

## Validation path

Use this sequence after TG2 delivers the identity contract:

1. Set the required GitHub variables.
2. Run `Detect and Evaluate` with `dry_run=false`.
3. Confirm that the Azure login step succeeds and the placeholder orchestration reaches completion.
4. Run `Sweep Orphans` with `dry_run=true` to validate list access and tag filtering.

If any step fails, use [docs/troubleshooting.md](c:\Users\sohadasgupta\IdeaProjects\hve-squad\model-upgrade-automation\docs\troubleshooting.md) before changing workflow permissions or adding secret-based auth fallbacks.
