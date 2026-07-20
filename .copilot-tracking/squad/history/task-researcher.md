# Task Researcher History

## Research + Design: Evaluation-Driven Quality & Safety Scoring Source (2026-07-20T11:30:00Z)

**Dispatch**: Task Researcher (Researcher Subagent) — research + design for real evaluation-driven quality/safety source to replace uniform 0.9 placeholders in recommender.

**Request**: Analyze reference repo (sohamda/azure-ai-redteam-eval continuous_evaluation + redteam), extract quality/safety metrics (ranges, aggregations, normalization), design integration pattern that mirrors pricing_enrichment.py (new QualitySafetyBenchmarkSource + enrich_quality_safety injected into recommend_candidates), determine dependency path (az-rest + stdlib vs. optional [evaluation] extra), handle not-yet-deployed-candidate caveat, produce design + phased plan + open questions.

**Output**: `.copilot-tracking/research/20260720-quality-safety-eval-source.md`
- Detailed metrics→scores mapping (quality: clamp((mean(groundedness,coherence,relevance,fluency)-1)/4); safety: 1 - defect_rate ∪ 1-ASR via conservative min)
- Integration design: new src/recommender/quality_safety_source.py (QualitySafetyBenchmarkSource, cached model_id-keyed YAML/JSON, DependencyUnavailableError on miss) + enrich_quality_safety(target, candidates, qs_client) injected into recommend_candidates only under official sources, non-fatal (retain 0.9 + parse_warning)
- Dependency strategy: keep runtime pyyaml-only; heavy azure-ai-evaluation[redteam]/PyRIT work deferred to optional [evaluation] refresh tool (out-of-band offline producer or future post-provisioning phase)
- Phased plan: Phase 1 (MVP): cache schema + source module + unit tests (mocked); Phase 2 (candidate): DependencyUnavailableError patterns + enrich injection; Phase 3 (deferred): live client swap + online redteam + continuous benchmarking
- Open questions: authoritative benchmark coverage, offline refresh-tool contract, validation against product metrics, integration with existing test harness

**Consumption**: claude-3-haiku (tier-1 / fast)
- Input tokens: 6000 (estimated, tier-default)
- Cached tokens: 0
- Output tokens: 3400 (estimated, tier-default)
- Input rate: $0.80 / MTok
- Output rate: $4.00 / MTok
- Est. cost USD: 0.0184
- Est. credits: 1.84
- Basis: tier-default

**Status**: ✓ Complete

**Next Steps**: Proceed to Phase 1 implementation (quality_safety_source.py module + cache schema) once Task Group sequencing allows (current: TG1–TG9 execution, live-mode core-pipeline transition, official-source activation, API audit).

---
