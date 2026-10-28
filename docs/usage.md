# PEBS usage guide

[Home](../README.md) · [中文](usage.zh-CN.md) · [API reference](api.md)

## 1. Install and choose a starting path

Use Python 3.11+ (3.12 recommended), Git, and an isolated virtual environment.
Run commands from the repository root; PEBS resolves its configuration and data
directories relative to its source checkout. It is not currently a packaged CLI
that can be installed with `pip install pebs`.

```bash
git clone https://github.com/Beritwu/psychology-education-skills.git
cd psychology-education-skills
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` in PowerShell or
`source .venv/bin/activate` on macOS/Linux. If activation is restricted, invoke
`.venv\Scripts\python.exe` directly instead of changing machine security policy.

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m compileall -q pebs
```

Choose one of these paths:

- **No credentials:** open `examples/classical-conditioning/index.html` locally.
  The static example is fully independent of the Python backend.
- **Explore the application:** `python -m pebs.cli serve --port 8710`, then open
  http://127.0.0.1:8710. Provider-dependent actions remain unavailable until configured.
- **Generate a course:** configure a model and research services below.

The UI is primarily Chinese. Four translated README files and the example's
language switch do not imply full application localization.

## 2. Configure providers

Edit `config/providers.yaml` before starting the server; restart after changes.
The application reads this YAML at import time. It does **not** load `.env` files
automatically. Never put a secret directly in YAML.

### Locally logged-in Codex CLI (default)

```yaml
llm:
  id: default-llm
  kind: codex_exec
  enabled: true
  base_url: ""
  api_key_env: PEBS_LLM_API_KEY
  require_api_key: false
  model: ""
  reasoning_effort: low
  timeout_seconds: 480
  temperature: 0.2
```

Install and authenticate Codex using its own official instructions. PEBS invokes
the locally logged-in CLI; it does not extract the account's credentials. This
uses the account's quota. The process must be able to find `codex` on PATH.

### OpenAI-compatible endpoint

Replace the `llm` mapping with your service's settings; keep the existing
`send_scope` list where applicable. Supply the **API base URL**, normally ending
in `/v1`, and the exact model ID your service supports.

```yaml
llm:
  id: default-llm
  kind: openai_compatible
  enabled: true
  base_url: https://YOUR-PROVIDER.example/v1
  api_key_env: PEBS_LLM_API_KEY
  require_api_key: true
  model: YOUR_MODEL_ID
  timeout_seconds: 180
  temperature: 0.2
```

Set `PEBS_LLM_API_KEY` in the environment of the shell launching PEBS. Do not
paste real keys into issues, shared transcripts, scripts or committed files.

### Research

The configured composite research provider supports Crossref, OpenAlex, Semantic
Scholar and PubMed. Optional OA retrieval is bounded by file and request limits;
Unpaywall may be used for discovery. Set a suitable `contact_email` in the
research YAML. `PEBS_RESEARCH_API_KEY` is the optional configured research key.
ERIC, PsycINFO and CNKI are not implemented research connectors.

```bash
python -m pebs.cli status
```

Availability is preflight information; quota, network access and source coverage
can still prevent a build. A source's mere existence does not verify a claim.

## 3. Build and inspect a course

```bash
python -m pebs.cli build --project demo --planner dynamic --max-model-calls 20 --max-research 20 --max-seconds 1200 --request "设计一节心理学入门课，包含虚构案例与形成性评价题，不需要PPT，不要动画。"
```

`static` is the default planner. `dynamic` derives the dependency graph from
registered skill contracts and the router. Deterministic constraints such as
`不要动画`, `不需要 PPT`, and word limits outrank model routing. The constraint
parser is primarily designed for Chinese requests; do not assume translated
negations are all recognized. Review the resulting plan.

Add `--template path/to/template.docx` and/or repeat `--material path/to/material.md`
as needed. De-identify materials first. Templates and source materials are not
instructions to bypass privacy or quality controls.

The CLI prints a run ID and changeset ID. The web workbench exposes the plan,
artifacts, evidence, changesets, gates, preview and evaluation panels. Read the
candidate changes and source limitations before accepting them:

```bash
python -m pebs.cli decide --project demo --changeset cs_FROM_BUILD
# Or reject the candidate:
python -m pebs.cli decide --project demo --changeset cs_FROM_BUILD --reject
```

Builds can be `blocked` or `failed`. Never relabel these as successful. Missing
supported evidence can block pedagogical steps even when search itself completed.
Budget caps are ceilings, not guarantees of completion; evidence checking can
reserve multiple requests per claim.

## 4. Revise, resume and export

Preview a selective edit without applying it:

```bash
python -m pebs.cli conversation --project demo --message "第2节案例换成大学宿舍情境，第1节不要动" --plan-only
```

Remove `--plan-only` to execute the edit. Use this request only for a course that
actually has two sections. Preserved artifacts are locked while the patch is
active; dependent artifacts may become stale. Review and accept the new changeset.

```bash
python -m pebs.cli rerun --project demo --step gates
python -m pebs.cli resume --project demo --run run_FROM_BUILD --max-model-calls 40 --max-research-requests 40 --run-seconds 1800
python -m pebs.cli export --project demo --mode draft
```

`resume` addresses budget-blocked work; it does not repair missing credentials or
turn unsupported claims into supported ones. Rerun step IDs must exist in the plan.
Check command status and the actual new run state.

Draft outputs are labeled `草稿—未通过 QA`. They live under
`projects/<project_id>/outputs/draft/`. Formal output requires current applicable
G1–G8 checks, accepted appropriate revisions, and required teacher review. If a
formal request is denied, address the reported issues rather than editing gate files.

```bash
python -m pebs.cli signoff --project demo --changeset cs_ACCEPTED --reviewer "REAL_REVIEWER" --basis "Describe the actual review performed"
python -m pebs.cli export --project demo --mode formal
```

Do not run a sign-off using an invented reviewer. Signing is not a substitute for
evidence. Human claim review requires a quotation locatable in a saved source:

```bash
python -m pebs.cli claim-review --project demo --claim clm_ID --version 1 --decision supported --reviewer "REAL_REVIEWER" --basis "Actual rationale" --source src_ID --source-version 1 --quote "EXACT_SOURCE_QUOTE" --quote-location "Actual location"
```

Replace all placeholders with actual records. `qualify`, `unsupported`, `disputed`
and `human_review` are other available decisions.

## 5. PPT, diagrams and animation

PPTX uses editable native elements. Install LibreOffice (Impress) or a supported
PowerPoint renderer for thumbnails and formal presentation delivery. The runtime
checks for a renderer; missing rendering keeps PPT delivery in review/draft.

PPT Foundry is an optional separately distributed dependency for its delivery
checker. Import the trusted package through the skill lifecycle, review it, and
pin the intended revision. It must resolve under the name `ppt-foundry`, with
`scripts/pptx_delivery_check.py` at the runtime root or one child directory.
The original development revision is listed in the third-party notices. This
repository does not redistribute the upstream package or claim the checker is
available after a plain clone. Inspect actual gate results before formal export.

SVG diagrams are validated. Animation requires a pedagogical necessity decision
and a synchronized storyboard. PEBS marks storyboards `rendered=false` and does
not call video, TTS or ASR services. The included HTML animation is a separately
implemented demonstration with pause, step and static alternatives.

## 6. Skills and portability

Inspect the [catalog](skills.md), `registry/skills.json` and the provider manifest.
Built-ins run without downloading the external teaching package. To install the
14 pinned skills on a fresh clone:

```bash
python -c "from pebs.provider_edu import install; install()"
python -c "from pebs.provider_edu import verify; r=verify(); print(r); raise SystemExit(0 if r['ok'] else 1)"
```

Installation modifies the local registry and creates ignored runtime directories.
If replacing an existing provider installation, back up local changes first;
`install(force=True)` removes and recreates that provider's derived skill caches.
Never use it to discard custom edits without a backup.

Custom skill lifecycle (substitute real reviewed values):

```bash
python -m pebs.cli skills import https://TRUSTED-SOURCE.example/package.tar.gz --name example --sha FULL_COMMIT_SHA
python -m pebs.cli skills review example --decision in_review --reviewer "REVIEWER" --evidence "Review started"
python -m pebs.cli skills review example --decision approve --reviewer "REVIEWER" --evidence "Actual source and permission review" --adoption ADOPT
python -m pebs.cli skills publish example --version VERSION
python -m pebs.cli skills pin example --version VERSION
python -m pebs.cli skills enable example
python -m pebs.cli skills verify example
```

The example host above is a placeholder, not an allowlisted download source.
Use a reviewed source allowed by `config/skills_sources.yaml`. Explicit runtime
invocations also require approval in `registry/allowlist.json`. For patches use
`skills patch --help`; upstream SHA mismatches stop composition. Candidates with
scripts require `python -m pebs.cli sandbox --probe` to pass its controls.

On a new computer, clone the repository, install dependencies, configure a model,
install optional skills and a renderer, then verify. Do not migrate credentials
or machine-specific runtime paths through Git. **pi is not required.** An AI
cross-audit can use another CLI/API/interface; its findings remain separate from
teacher evaluation. See [evaluation workflow](evaluation-workflow.md).

## 7. Benchmarks and real teacher evaluation

Offline inspection:

```bash
python -m pebs.cli benchmark --cases A,B,C --modes builtin,dynamic --plan-only
python -m pytest tests -q -m benchmark_smoke
```

Real provider comparison (consumes quota):

```bash
python -m pebs.cli benchmark --cases B --modes direct_codex,builtin,dynamic --max-model-calls 40 --max-research 40 --max-seconds 1800 --strict
python -m pebs.cli benchmark --report
python -m pebs.cli benchmark --gate-audit
python -m pebs.cli benchmark --promotions
```

Use comparable budgets, commits, gates and provider versions. The full suite has
additional adversarial/media scenarios; read the case YAML rather than treating
all cases as identical course builds. `--promotions` observes; it does not change routing.

```bash
python -m pebs.cli benchmark --export-eval-kit
python -m pebs.cli benchmark --submit-eval path/to/FILLED-human_eval.yaml --project MATCHING_PROJECT
```

Give the frozen course package to a real teacher. Preserve `run`, `target` and
version fields; fill all required ratings and actual comments. Submit actual edit
records only. AI-generated scores are not human scores. Modified course versions
need a new package; old ratings become stale. Details and failure recovery are in
[the evaluation workflow](evaluation-workflow.md).

## 8. API, storage and backup

Run the server and open http://127.0.0.1:8710/docs for interactive OpenAPI docs, or
http://127.0.0.1:8710/openapi.json for the machine-readable schema. See [API map](api.md).
There is no built-in user authentication; operate on loopback under a trusted account.

`projects/<id>/` holds managed inputs, SQLite state, immutable artifacts, logs,
snapshots and outputs. Stop active builds and the server before making a consistent
filesystem backup. Preserve the whole project directory and relevant configuration,
provider/skill versions and license information. Keep backups private. Do not edit
SQLite or immutable artifact JSON to manufacture acceptance.

Deleting a project is destructive:

```bash
python -m pebs.cli delete --project PROJECT_TO_DELETE --yes
```

Check the ID and back up first. Static example files are outside managed projects.

## 9. Troubleshooting

| Symptom | Check / action |
|---|---|
| Missing provider | Check YAML, PATH, environment and authentication; restart the process |
| Quota/timeout | Inspect the failed step; adjust a justified budget or retry after service recovery |
| Skill listed but missing files | Install the pinned provider on this machine, then run `verify()` |
| Empty evidence index | Inspect pending/unsupported claims and source availability; do not bypass it |
| Request blocked as PII | Remove names/identifiers; if clearly a false positive, report a sanitized reproduction |
| Formal export denied | Read gate/version/sign-off reasons; draft remains the review path |
| No thumbnails | Install a renderer and inspect rendering errors |
| Old teacher score | Re-evaluate the correct frozen version; do not relabel old ratings |
| Garbled terminal text | Use UTF-8; PowerShell: `$env:PYTHONIOENCODING='utf-8'` |
| Port already occupied | Choose another `serve --port` value |

## 10. Verification and limits

```bash
python -m compileall -q pebs
python -m pytest tests -q -m "not integration and not live_research"
python -m pytest tests -q -m integration
python -m pytest tests -q -m live_research
```

The last two commands require appropriate external tools/services. Passing code
tests is distinct from a successful live build, a formal delivery, and classroom
effectiveness. Read [coverage](../documentation/tests.md) and [roadmap](roadmap.md).
