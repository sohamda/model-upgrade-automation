---
title: End-to-End Detector, Recommender, and Provisioner Audit
ms.date: 2026-07-17
ms.topic: research
---

<!-- markdownlint-disable-file -->

## Scope

Audit `src/detector`, `src/recommender`, and `src/provisioner` against the requested workflow:

1. Accept a retiring-model input or inspect Azure Foundry
2. Look up current official Azure documentation or catalog information live
3. Produce the three best replacement suggestions
4. Provision every recommendation

## Questions

* What classes and functions are implemented, and what do they actually do?
* Which components can be reused for the requested workflow?
* What exact implementation gaps prevent the workflow from working end to end?
* Does any code perform a live, official Azure documentation or model-catalog lookup?

## Investigation Status

Complete. Reviewed 15 implementation files, 3 focused unit-test files, the dry-run
orchestrator, shared contracts/configuration, fixture data, and the project dependency
manifest. The audit is read-only outside this research artifact.

## Evidence Log

### Requested Outcome Assessment

The repository implements a deterministic, fixture-backed dry-run slice. It can shape
retirement targets, rank locally supplied candidates, and create provision/teardown
request previews. It does not accept a direct retiring-model CLI input, inspect a
Foundry account, call an Azure official documentation or model catalog endpoint, or
provision any deployment. The top-three behavior is configuration-capped, but not
guaranteed when fewer than three fixture candidates pass filters.

### Detector Implementation

| Component | Location | Actual behavior |
| --- | --- | --- |
| `DetectorResult` | src/detector/models.py:11 | Holds normalized `retiring_targets` and non-fatal `parse_warnings` |
| `RetirementSource` protocol and `load` | src/detector/retirement_source.py:15 | Defines only a synchronous `load() -> list[RetiringModel]` seam |
| `FixtureRetirementSource` and `load` | src/detector/retirement_source.py:23 | Reads `retiring_models` from a caller-provided YAML file and maps fixed fields to `RetiringModel` |
| `build_default_fixture` | src/detector/retirement_source.py:50 | Hard-wires the default source to `tests/fixtures/retirement_signals.yaml` |
| `days_until` | src/detector/retirement_source.py:56 | Parses an ISO datetime string and returns whole calendar days from the reference time |
| `load_watch_list` | src/detector/watchlist.py:9 | Returns configured watch-list entries without external lookup or validation |
| `detect_retiring_targets` | src/detector/service.py:15 | Intersects fixture retirement signals with configured `(model_id, current_version)` pairs, emits an unmatched-signal warning, applies retirement horizon, and sorts qualifying targets |

`tests/unit/test_detector_service.py:18` verifies the fixture path produces one
configured target and one warning. It does not exercise Azure or Foundry inspection.

### Recommender Implementation

| Component | Location | Actual behavior |
| --- | --- | --- |
| `CatalogCandidate` and `to_candidate` | src/recommender/models.py:11 | Represents a local scored candidate and converts it to the smaller shared `Candidate` contract |
| `RecommenderResult` | src/recommender/models.py:36 | Holds ranked candidates plus string warnings |
| `CandidateCatalog` protocol and `load` | src/recommender/catalog.py:14 | Defines only a synchronous local candidate retrieval seam |
| `FixtureCandidateCatalog` and `load` | src/recommender/catalog.py:22 | Reads candidates and precomputed quality, safety, and cost scores from YAML |
| `build_default_catalog` | src/recommender/catalog.py:51 | Hard-wires the default catalog to `tests/fixtures/candidate_catalog.yaml` |
| `filter_candidates` | src/recommender/filters.py:11 | Filters by optional exact region, configured deployment type, exact workload, and optional replacement family/model ID |
| `validate_weights` | src/recommender/scorer.py:10 | Rejects configurations whose numeric weights do not sum to 1.0 |
| `score_candidate` | src/recommender/scorer.py:18 | Computes a weighted sum of fixture-supplied quality, safety, and cost fields; does not use the target after accepting it |
| `recommend_candidates` | src/recommender/service.py:15 | Loads the catalog, filters, scores, orders by descending score with deterministic tie-breakers, then slices to configured candidate count |

`tests/unit/test_recommender_service.py:17` verifies two fixture candidates rank in
a fixed order. The configured cap is three in `config/evaluation.yaml:2`, but the
fixture provides only two candidates that pass all filters for the test target.

### Provisioner Implementation

| Component | Location | Actual behavior |
| --- | --- | --- |
| `ProvisionPlanResult` | src/provisioner/models.py:11 | Holds in-memory provision requests and teardown previews; no execution result or failure field |
| `build_idempotency_key` | src/provisioner/deployment_plan.py:12 | SHA-256 hashes run scope and target/candidate/deployment identity |
| `build_required_tags` | src/provisioner/deployment_plan.py:34 | Produces governance tags from configuration plus fixed TG4 labels |
| `build_deployment_name` | src/provisioner/deployment_plan.py:47 | Builds a normalized, 63-character maximum name preview |
| `build_provision_request` | src/provisioner/deployment_plan.py:58 | Shapes a `ProvisionRequest` with target, candidate, region, type, tags, idempotency key, and name |
| `build_teardown_plan` | src/provisioner/deployment_plan.py:81 | Shapes a matching ephemeral teardown preview |
| `plan_provisioning` | src/provisioner/service.py:12 | Iterates every supplied ranked candidate and appends request and teardown-plan previews; it does not call Azure |

`tests/unit/test_provisioner_service.py:17` verifies idempotency-key stability, and
`tests/unit/test_provisioner_service.py:51` verifies one locally shaped request
includes expected tags. Neither test has Azure credentials, SDK calls, or deployment
assertions.

### End-to-End Wiring and External Lookup Evidence

`execute_dry_run` in src/orchestrator/pipeline.py:92 explicitly labels itself a
"minimal non-Azure TG4 slice." It selects `FixtureRetirementSource` and
`FixtureCandidateCatalog` at src/orchestrator/pipeline.py:96-97, calls detection,
recommendation, and planning at src/orchestrator/pipeline.py:98-102, then serializes
previews to local artifact JSON. The CLI only exposes `--fixture` and `--catalog`
path overrides at src/orchestrator/cli.py:27-37; it has no `--retiring-model`,
Azure subscription/project-selection, or live-mode option.

No external API/docs/catalog lookup is implemented in the audited modules:

* `FixtureRetirementSource.load` uses `yaml.safe_load` from a local path at
  src/detector/retirement_source.py:28-30
* `FixtureCandidateCatalog.load` uses `yaml.safe_load` from a local path at
  src/recommender/catalog.py:27-29
* The sole project dependency is `pyyaml>=6.0` in pyproject.toml:8-10; there is no
  Azure SDK, Foundry SDK, Azure CLI wrapper, or HTTP client dependency
* `create_credential_descriptor` is an explicitly local-test-safe descriptor with
  `mode="oidc-placeholder"` at src/shared/azure_auth.py:10-19, not an Azure credential
* Azure/Foundry identifiers are configuration values passed into `RunContext` at
  src/shared/run_context.py:58-96, without an SDK client or network call

Therefore there is no live lookup, and there is no official Azure documentation or
catalog source to assess as current, authoritative, or suitable for regional model
availability verification.

### Reusable Components

* `RetirementSource` and `CandidateCatalog` protocols are the immediate seams for
  Azure-backed implementations: src/detector/retirement_source.py:15 and
  src/recommender/catalog.py:14
* `detect_retiring_targets` provides useful watch-list intersection, date-horizon,
  unmatched-signal warnings, and stable ordering: src/detector/service.py:15
* `filter_candidates` is reusable for local policy constraints after a live catalog
  adapter normalizes regional availability and deployment types: src/recommender/filters.py:11
* `validate_weights`, `score_candidate`, and stable sort are reusable only after
  score inputs are replaced with sourced evaluation/cost/safety evidence:
  src/recommender/scorer.py:10 and src/recommender/service.py:15
* The request ID, tags, and naming helpers are reusable for an execution adapter:
  src/provisioner/deployment_plan.py:12, src/provisioner/deployment_plan.py:34, and
  src/provisioner/deployment_plan.py:58
* `plan_provisioning` already loops all candidates passed to it, so it can provide
  the planning half of a three-recommendation deployment loop: src/provisioner/service.py:12

### Exact Implementation Gaps

#### Input and Foundry Inspection

1. There is no direct retiring-model request contract. `RetiringModel` requires
	`model_id`, `current_version`, and `retirement_date` (src/shared/contracts.py:40),
	so a CLI caller cannot submit only a retiring model or a deployment identity and
	have the system resolve version, region, workload, or retirement status.
2. `detect_retiring_targets` discards every retirement signal absent from the local
	watch list (src/detector/service.py:30-41). This prevents a user-provided model or
	discovered Foundry deployment from entering recommendation unless preconfigured.
3. No Foundry inventory adapter exists. `RunContext` contains account/project names
	(src/shared/run_context.py:28-30), but no class queries deployments, model versions,
	SKU/deployment types, locations, quotas, or deployment configuration.
4. There is no live retirement-source implementation. The only concrete source is
	fixture YAML (src/detector/retirement_source.py:23), and no source metadata captures
	official URL, retrieval time, document version, or evidence of retirement.

#### Live Official Catalog and Recommendation Quality

1. No live official Azure model catalog or documentation client exists. The only
	concrete catalog is local YAML (src/recommender/catalog.py:22); it cannot verify
	that a model/version is current, supported, or available in the target region.
2. `CatalogCandidate` lacks catalog provenance, retrieval timestamp, publisher,
	model capabilities, context limits, modalities, pricing units, quota/capacity,
	lifecycle/support status, and Foundry compatibility fields (src/recommender/models.py:11).
	The shared `Candidate` contract removes even the local workload and score evidence
	(src/shared/contracts.py:62).
3. The scoring function explicitly ignores its `target` (`del target`) at
	src/recommender/scorer.py:23. Ranking has no compatibility metric for retiring
	model capabilities, version migration, context window, function/tool use,
	structured output, workload fit, region preference, or deployment migration risk.
4. Quality, safety, and cost are static fixture values; no evaluator, official price
	data, benchmark/evaluation result, or safety capability source produces them.
5. Candidate region filtering is disabled by default in
	config/recommender.yaml:6. A top-ranked candidate in a different region can be
	selected, even where the requested workflow requires Foundry availability and
	usually needs a deliberate cross-region policy.
6. `recommend_candidates` only caps an arbitrary supplied list at
	`candidates_per_retiring_model` (src/recommender/service.py:34-37). It does not
	ensure exactly three usable alternatives, explain insufficient availability, or
	explicitly designate the result as the requested top three.

#### Provisioning Each Recommendation

1. `plan_provisioning` only constructs local `ProvisionRequest` objects
	(src/provisioner/service.py:12-32). There is no provisioner protocol, Azure/Foundry
	SDK client, REST call, CLI invocation, polling, retry, or execution result.
2. `ProvisionRequest` lacks required deployment payload fields such as Foundry
	account/project endpoint or resource ID, model format/publisher, SKU/capacity,
	version selection semantics, request API version, and deployment properties
	(src/shared/contracts.py:78). It cannot be translated unambiguously into a real
	Foundry deployment operation.
3. The idempotency hash is local metadata only; no persistent idempotency store,
	existing-deployment lookup, or conflict behavior exists
	(src/provisioner/deployment_plan.py:12-31).
4. The provisioner loops all input candidates, but orchestrator passes whatever the
	recommender returned (src/orchestrator/pipeline.py:102). Because recommendation is
	not guaranteed to contain three valid options, there is no guaranteed provisioning
	loop for the top three recommendations.
5. Teardown is also a preview only. `TeardownPlan` lacks an executor or lifecycle
	state, and no code verifies created resources before cleanup
	(src/provisioner/deployment_plan.py:81 and src/shared/contracts.py:111).

### Test Coverage and Audit Limits

The three focused tests establish deterministic fixture behavior only:

* tests/unit/test_detector_service.py:18
* tests/unit/test_recommender_service.py:17
* tests/unit/test_provisioner_service.py:17

The research environment exposes no terminal execution tool, so this audit did not
run the test suite. A static diagnostic check found no errors in this research file.
No external web sources were used because the question was whether the repository
contains live official lookup code; the source and dependency inspection conclusively
show it does not.

## Conclusion

The requested outcome is not implemented end to end. The strongest reusable base is
the dry-run orchestration and its source/catalog/provisioning seams. Delivery requires
Azure-backed retirement and Foundry-inventory adapters, a live official catalog/docs
adapter and normalized evidence contract, compatibility-aware top-three ranking, and
an executing Foundry deployment adapter that provisions and reports each accepted
recommendation.
