# Architecture

PEBS is a local Python/FastAPI course authoring application. The browser workbench
and CLI call the same engine. SQLite stores revisions, runs, changesets and
dependency edges. `registry/skills.json` describes executable skill contracts.

| Component | Responsibility | Source |
|---|---|---|
| UI / API / CLI | Project operations and user review | `pebs/static/`, `pebs/server.py`, `pebs/cli.py` |
| Engine / Store | Runs, candidate changes, immutable revisions, acceptance | `pebs/engine.py`, `pebs/store.py` |
| Planner / runtime | Static steps or contract-derived dynamic DAG | `pebs/runtime/`, `pebs/registry.py` |
| Agents | Artifact ownership and restricted skill context | `pebs/agents/` |
| Evidence / providers | Search, model calls and source-grounded assessment | `pebs/providers.py` |
| Conversation | Edit intent, affected artifacts and preserve locks | `pebs/conversation/` |
| Media / delivery | SVG, storyboard, PPT, render and export checks | `pebs/pipeline.py`, `pebs/render.py`, `pebs/pptx_foundry.py` |
| Evaluation | Benchmark records, teacher ratings and version binding | `pebs/benchmark/` |

## Trust boundaries and assumptions

The server has no user authentication/session system. OS access to the local
process and files is the primary user boundary. Teacher role fields do not
authenticate identity. Server-to-provider calls cross an external-service boundary;
PII checks and input budgets apply, while provider credentials stay in environment
variables. External skills receive declared inputs and restricted output contracts.
Artifact acceptance, evidence support and formal export are separate decisions.

Known operational assumptions are visible in code: source-relative mutable paths
(`pebs/config.py`), local trusted-user routes (`pebs/server.py`), model/network
availability (`pebs/providers.py`), verified sandbox requirements (`pebs/sandbox.py`),
and independent PPT checker availability (`pebs/pptx_foundry.py`).

GitHub Pages serves only the static demonstration. No app backend, source database,
credentials, or private project outputs belong in the Pages deployment.
No transactional email subsystem — no `emails.md`. No public dynamic app SEO
surface — no `seo.md`. Scheduled CI checks are described in `cron.md`.

## Related documents

- [Operational flows](flows.md)
- [Permissions and identity](permissions.md)
- [Configuration and secrets](variables.md)
- [Test coverage and gaps](tests.md)
- [Embedded agents and automation](automation.md)
- [Scheduled CI](cron.md)
- [Usage](../docs/usage.md), [API](../docs/api.md), [Security](../SECURITY.md)
