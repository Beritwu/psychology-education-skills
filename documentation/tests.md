# Verification map

## Existing coverage

| Use case / rule | Expected behavior, including denial | Evidence | Status |
|---|---|---|---|
| Immutable revisions and changesets | Preserve revisions; reject invalid/conflicting changes | `tests/test_store.py` | Existing; Code CI |
| PII boundary | Identifiable data does not enter external prompts | `tests/test_pii.py`, `tests/test_pii_no_leak.py` | Existing; Code CI |
| Document import | Reject malicious paths and excessive decompression/size | `tests/test_document_security_limits.py` | Existing; Code CI |
| External skills | Deny disallowed/unpinned skill execution | `tests/test_external_skill_acceptance.py`, `tests/test_skills_mgr.py` | Existing; Code CI |
| Agent context | Restrict declared inputs and artifact writes | `tests/test_subagent_isolation.py`, `tests/test_context_minimization.py` | Existing; Code CI |
| Local edits | Preserve specified artifacts; invalidate affected dependents | `tests/test_locality.py`, `tests/test_impact_analysis.py` | Existing; Code CI |
| Human scores | Reject stale/mismatched targets and non-human submissions | `tests/test_evaluation_integrity.py`, `tests/test_benchmark_evaluation.py` | Existing; Code CI |
| PPT/rendering | Validate artifact and rendering behavior | `tests/test_pptx.py`, `tests/test_render.py` | Existing; renderer integration separately |
| Golden plans | Deterministic benchmark contracts without model calls | `tests/test_golden_benchmark_plan.py` | Existing; benchmark smoke |
| Research availability | Exercise real provider behavior | `tests/test_live_research.py` | Existing; scheduled/manual live job |

Code CI config is `.github/workflows/ci.yml`. Jobs run automatically, but branch
protection/required status checks are repository settings, not guaranteed by YAML.
The public-release check record is in `docs/release-validation.md`.

## Proposed tests

| Use case | Rule / evidence | Type | Status |
|---|---|---|---|
| Fresh installations on additional OS versions | Follow usage instructions without existing caches | Manual install review / automated environment matrix | Proposed extension |
| Course usability | Teachers can locate sources and complete revisions | Real-teacher observed task | Proposed |
| Localization | Technical terms and translated instructions are natural | Native-language manual review | Proposed |

## Gaps

| Priority | Unverified boundary | Consequence |
|---|---|---|
| High | Real teacher/classroom efficacy across three production courses | Cannot infer teaching outcomes from software tests |
| High | Multi-user deployment authorization | Backend is supported only for trusted local use |
| Medium | Complete comparable live benchmark matrix | Cost/quality superiority is not established |

The static animation has separate browser checks for language switching, stepping,
play/pause/reset, mobile layout and reduced-motion behavior. These are interaction
checks, not learning-outcome evidence.
