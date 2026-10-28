# Configuration and secrets

| Name | Used by | Scope / source | Rotation / operational concern |
|---|---|---|---|
| `PEBS_LLM_API_KEY` | OpenAI-compatible model client | Server process environment | Rotate at model service; restart process; never commit |
| `PEBS_RESEARCH_API_KEY` | Configured research client | Server process environment | Rotate at research service; do not include in prompts |
| `PEBS_COMMIT` | Benchmark trace | Server/CI environment | Non-secret revision override; use a truthful commit |
| `config/providers.yaml` | Providers | Local file | Endpoint/model/contact metadata; keys must remain external |
| `config/rules.yaml` | Engine and gates | Local file | Budgets/import limits; edits change rules-version identity |
| `config/skills_sources.yaml` | Skill importer/sandbox | Local file | Source allowlist and sandbox limits; review changes |
| `registry/*.json` | Planner and lifecycle | Local files | Mutable installation state; do not treat machine paths as portable |
| Codex login | External Codex CLI | CLI-managed credential store | Manage with Codex; PEBS does not extract its secret |

The shipped browser example and frontend assets contain no provider secret.
PEBS does not automatically parse `.env`. The public repository excludes project
databases and installed skill caches. Before sharing new material: inspect the
staged diff, scan for credentials and identifiers, and keep real course data out
of version control. Repository Actions secrets are separate from runtime secrets.
