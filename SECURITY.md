# Security and deployment scope

PEBS is currently a **trusted-user, local workstation application**. Its FastAPI
service does not provide user login, tenant isolation, or teacher identity
verification. `python -m pebs.cli serve` binds to `127.0.0.1` by default.
Do not expose this server directly to the Internet. Public GitHub Pages hosts
only the static example, never the PEBS backend or project database.

## Reporting a vulnerability

Use the repository's **Security → Report a vulnerability** feature if enabled.
If unavailable, open an issue containing only a request for a private reporting
channel. Do not post exploit details, secrets, student data, or private materials.
Maintainers review reports on a best-effort basis; no response-time SLA is promised.

## Data and credentials

- Provider keys belong in environment variables, never YAML, prompts or issues.
- `projects/`, installed skill caches, `.env*`, and database files are ignored.
- Student-data scanning reduces exposure but is not a substitute for manually
  checking and de-identifying materials before sharing them.
- Local orchestration does not mean offline generation: model/research requests
  may go to configured external providers.
- Teacher-role fields are provenance constraints, not proof of identity.
- Model-generated course content requires subject-matter review before use.

See [permissions](documentation/permissions.md), [flows](documentation/flows.md),
and [variables](documentation/variables.md) for implemented controls and gaps.
