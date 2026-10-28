# Embedded agents and automation

| Trigger / owner | Inputs and permitted surfaces | Output and side effects |
|---|---|---|
| Build requested by local operator | Requirements, declared materials; configured model/research clients | Candidate revisions, traces and gates |
| Dynamic runtime node | `requires` artifacts; registered agent and handler | Only declared `produces`/`emits` artifacts |
| External prompt skill | RestrictedContext with declared inputs | Validated output contract; no raw Store/evidence/LLM access |
| External sandbox skill | Verified adapter and declared files | Bounded sandbox outputs; denied when controls fail |
| Conversation edit | User message and existing artifact relationships | Patch plan, preservation locks and affected revisions |
| Benchmark command | Case definition, mode, provider/skill versions | Run records, metrics, reports; real runs spend quota |
| Evaluation submission | Frozen package and actual teacher input | Immutable rating plus generation-time performance binding |

Prompts guide pedagogical content; code enforces lifecycle checks, schemas,
permissions, budgets, locks and revision validity. External artifacts and source
documents cannot grant new permissions. Approval of a changeset is separate from
the automatic production steps. Review records capture actual actions; AI output
must not impersonate teacher approval.

Controls live in `config/rules.yaml`, the registry, runtime executor and Store.
Budget exhaustion pauses work. The API exposes run cancellation. Logs and run
records identify failed/blocked steps; retry/resume should address the actual cause.
Cross-model audit is an operator-run documented procedure, not an autonomous
background dispatcher. No provider credentials belong in the audit packet.
