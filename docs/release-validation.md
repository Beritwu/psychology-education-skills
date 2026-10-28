# Public snapshot validation

This record describes the source and example prepared for the initial public
snapshot. It records checks performed, not educational-outcome claims.

| Check | Result |
|---|---|
| Compile `pebs` | Passed |
| Fresh-clone external provider installation | All 14 skills installed from the pinned archive; `verify()` returned true |
| Fresh Python environment | `requirements.txt` installed successfully; 75 targeted lifecycle/evaluation/registry tests passed |
| Public documentation links | 135 local links checked, no missing targets |
| Deterministic Python suite | 526 passed; 7 integration/live checks deselected |
| Renderer/integration suite | 5 passed; 528 other checks deselected |
| Browser example | Passed in headless Chrome: four languages, seven states, phase navigation, play/pause/reset, static transcript |
| Mobile and accessibility behavior | 390px layout without horizontal overflow; reduced-motion transitions disabled; native controls |
| Browser runtime | No JavaScript errors; no network requests during example interaction |
| Published example | Homepage, JavaScript, CSS, diagram, course and provenance return HTTP 200 |

The browser was also visually inspected at desktop size. The verification script
was run from release preparation tooling; it is not an application dependency.
`python scripts/check_public_docs.py` checks local links in the public entry points.

## Runtime example provenance

The actual dynamic build executed the external backwards-design skill, then
remained blocked because the research budget did not permit claim verification.
The published lesson and HTML sequence are explicitly documented as a separate
assistant application of three pinned teaching skills. See the example's
`runtime-attempt.json`, `skill-trace.json`, and `design-record.md`.

## Publication boundary

The public initial commit is a clean source snapshot of the working project,
including its existing evaluation-integrity changes. Original development history
and the existing `pebs` remote are preserved locally. Installed caches, project
databases, credentials and release scratch files are excluded. Registry runtime
paths are made relative in the public snapshot and must be materialized by the
documented provider installer on a new computer.
