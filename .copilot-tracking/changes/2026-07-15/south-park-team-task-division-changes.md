<!-- markdownlint-disable-file -->
# Release Changes: south-park-team-task-division

**Related Plan**: south-park-team-task-division-plan.instructions.md
**Implementation Date**: 2026-07-15

## Summary

Consolidated the TG2 operator and evidence guidance by introducing a single TG2 reference document, tightened the TG3-facing setup and OIDC guidance to consume that contract, completed a substantial local TG2 infra-hardening pass that removes the current Bicep warning set while preserving deployment intent, and added a shared TG3 contract validator so workflow, config, and documentation checks can run locally and inside the delivery workflows.

Expanded TG4 dry-run staging contract coverage with focused unit tests that validate manifest relative-path expectations and on-disk staged artifact coherence beyond the single existing orchestrator staging check.

## Changes

### Added

* docs/tg2-operator-evidence.md - Canonical TG2 operator evidence package covering identity inputs, governance expectations, cleanup tags, and minimum evidence before live TG3 runs
* scripts/validate_tg3_contracts.py - Shared local validator for TG3 workflow, config, and documentation contracts used by CI and workflow preflight

### Modified

* infra/main.bicep - Removed an unused parameter and normalized TG3 validation outputs to environment-aware storage DNS suffixes
* infra/modules/networking.bicep - Replaced hardcoded storage DNS suffixes and simplified DNS link child resources with parent syntax
* infra/modules/monitoring.bicep - Replaced manual `listKeys` call with a resource-symbol method reference
* infra/modules/container-apps.bicep - Replaced `reference()` output lookup with a direct resource-symbol property reference
* infra/modules/foundry.bicep - Simplified private DNS zone group declaration with parent syntax
* infra/modules/keyvault.bicep - Simplified private DNS zone group declaration with parent syntax
* infra/modules/storage.bicep - Replaced hardcoded storage endpoints and simplified private DNS zone group declarations with parent syntax
* docs/oidc-setup.md - Reduced repeated TG2 contract detail and pointed operators to the canonical TG2 evidence package
* docs/setup-guide.md - Clarified that TG2 readiness inputs come from the TG2 evidence package and frozen handoff contract
* docs/tg2-operator-evidence.md - Added explicit local source-controlled evidence references and a local-versus-live-Azure readiness split for TG3 consumers
* docs/troubleshooting.md - Tightened TG2 dependency guidance and pointed unresolved placeholder handling to the TG2 evidence package
* .github/workflows/ci.yml - Replaced embedded TG3 contract checks with the shared validator script for local and CI reuse
* .github/workflows/detect-and-eval.yml - Added shared TG3 contract validation to preflight before placeholder orchestration runs
* .github/workflows/sweep-orphans.yml - Added checkout and shared TG3 contract validation before cleanup execution
* tests/unit/test_history_preview.py - Added manifest relative-path contract coverage for staged dry-run artifacts
* tests/unit/test_orchestrator_cli.py - Added staged artifact materialization and dry-run summary/history coherence coverage

### Removed

* None

## Additional or Deviating Changes

* No changes were made to docs/tg3-handoff-contract.md
  * The file already serves as the frozen contract surface and changing it would increase TG3 regression risk without improving operator clarity
* No Azure-side evidence was added this round
  * The requested TG2 push was constrained to local-completable work without live Azure access
* Live detect-and-eval invoke, poll, and teardown behavior remain scaffolded
  * Those execution paths require TG4 and TG5 code surfaces plus Azure-backed runtime verification and were intentionally not implemented in this TG3-local round
* No implementation changes were required in src/orchestrator/pipeline.py
  * The stronger staging-coherence tests passed against the current local dry-run implementation

## Release Summary

TG2 local infrastructure contract hardening is now in place. The Bicep entrypoint and module graph compile cleanly with `az bicep build --file infra/main.bicep`. TG3 now has a repo-executable validation contract shared by CI and both delivery workflows, improving local readiness without Azure access. The main remaining TG2 and TG3 gaps are live Azure verifications: real OIDC federation state, effective RBAC assignments, deployed policy assignment enforcement, private endpoint DNS or data-plane validation from runtime subnets, and non-dry-run orchestration evidence for ACA invoke, poll, and teardown.

TG4 dry-run artifact staging now has broader unit-level evidence: manifest relative paths are asserted to remain aligned with the `artifacts/<run_id>/` contract, and orchestrator staging is verified end-to-end for exact materialized files plus coherence between staged `dry_run_output.json`, `history_preview.json`, and the manifest-advertised payload files.