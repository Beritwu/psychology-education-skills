# Contributing

Thank you for helping make course production more inspectable.

1. Read [architecture](documentation/architecture.md), [usage](docs/usage.md),
   [security](SECURITY.md) and the project rules in [AGENTS.md](AGENTS.md).
2. Create a branch, install Python 3.11+ dependencies, and reproduce the issue.
3. Keep changes focused. Preserve uncommitted work from other contributors.
4. For behavior changes, test the public API/CLI or artifact contract, including
   the relevant rejection path. Documentation-only changes need link checks.
5. Run `python -m compileall -q pebs` and
   `python -m pytest tests -q -m "not integration and not live_research"`.
6. Describe the problem, resulting behavior, validation and remaining limitations
   in the pull request. Never attach private course files, credentials or student PII.

## Non-negotiable integrity rules

- Missing providers are BLOCKED/PENDING; never manufacture research or model output.
- AI feedback must never be submitted as human teacher evaluation.
- Artifact revisions are immutable. Respect preserved/locked artifacts.
- Formal export requires current applicable gates and required teacher review.
- Imported code must not execute during skill import. External scripts require
  the verified sandbox path; no host fallback for sandbox-only candidates.
- Research and audit tasks report findings; implementation is a separate task.

## Translations and licenses

Keep `README.md`, `README.zh-CN.md`, `README.ja.md`, and `README.ko.md` consistent.
Document new commands in the usage guide. Original code contributions are MIT;
changes to the Education Agent Skills adaptations retain CC BY-SA 4.0 and must
preserve attribution and modification notices. See [notices](THIRD_PARTY_NOTICES.md).

## Tests requiring external services

`live_research` calls real research services. Full benchmarks consume model quota.
Renderer integration needs LibreOffice or PowerPoint. Do not silently substitute
fixtures for real evidence. CI job success does not establish classroom efficacy.
