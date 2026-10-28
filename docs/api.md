# REST API map

[Usage guide](usage.md) · [Security scope](../SECURITY.md)

Start `python -m pebs.cli serve --port 8710`. The authoritative generated schema is at `http://127.0.0.1:8710/openapi.json`; interactive field descriptions and request examples are at `http://127.0.0.1:8710/docs`. The application has no user authentication and should remain local.

| Method | Route | Operation |
|---|---|---|
| GET | `/api/registry` | Registry Report |
| GET | `/api/sandbox` | Sandbox Status |
| POST | `/api/sandbox/probe` | Sandbox Probe |
| POST | `/api/skills/import` | Skills Import |
| POST | `/api/skills/review` | Skills Review |
| POST | `/api/skills/publish` | Skills Publish |
| GET | `/api/status` | Status |
| GET | `/api/projects` | List Projects |
| POST | `/api/projects` | Create Project |
| GET | `/api/projects/{project_id}/files` | List Files |
| POST | `/api/projects/{project_id}/upload` | Upload |
| POST | `/api/projects/{project_id}/build` | Build |
| GET | `/api/projects/{project_id}/runs/{run_id}` | Run Status |
| POST | `/api/projects/{project_id}/runs/{run_id}/cancel` | Cancel Run |
| GET | `/api/projects/{project_id}/plan` | Get Plan |
| POST | `/api/projects/{project_id}/plan/edit` | Edit Plan |
| POST | `/api/projects/{project_id}/conversation` | Conversation |
| GET | `/api/projects/{project_id}/patch-plan` | Get Patch Plan |
| GET | `/api/projects/{project_id}/dynamic-plan` | Get Dynamic Plan |
| GET | `/api/projects/{project_id}/trace` | Get Trace |
| GET | `/api/projects/{project_id}/evaluation` | Get Evaluation |
| POST | `/api/projects/{project_id}/evaluation` | Record Evaluation |
| GET | `/api/projects/{project_id}/artifacts` | List Artifacts |
| GET | `/api/projects/{project_id}/artifacts/{artifact_id}` | Get Artifact |
| GET | `/api/projects/{project_id}/changesets` | List Changesets |
| GET | `/api/projects/{project_id}/changesets/{changeset_id}/diff` | Changeset Diff |
| POST | `/api/projects/{project_id}/changesets/{changeset_id}/accept` | Accept |
| POST | `/api/projects/{project_id}/changesets/{changeset_id}/reject` | Reject |
| GET | `/api/projects/{project_id}/gates` | Gate Report |
| GET | `/api/projects/{project_id}/evidence` | Evidence Report |
| GET | `/api/projects/{project_id}/memory` | Memory Report |
| GET | `/api/projects/{project_id}/rules` | Rules Report |
| GET | `/api/projects/{project_id}/preview` | Preview |
| GET | `/api/projects/{project_id}/outputs` | Outputs |
| POST | `/api/projects/{project_id}/case-replace` | Case Replace |
| POST | `/api/projects/{project_id}/export` | Export |
| GET | `/api/projects/{project_id}/artifact-json/{artifact_id}` | Artifact Json |
| DELETE | `/api/projects/{project_id}` | Delete Project |
| POST | `/api/projects/{project_id}/plan/rerun` | Rerun |
| GET | `/api/projects/{project_id}/file` | Project File |
| GET | `/api/projects/{project_id}/media` | Media Report |
| POST | `/api/projects/{project_id}/slide-edit` | Slide Edit |
| POST | `/api/projects/{project_id}/signoff` | Signoff |
| POST | `/api/projects/{project_id}/claim-review` | Claim Review |
| GET | `/` | Index |

## Typical sequence

1. `POST /api/projects` with `{"project_id":"demo"}`.
2. `POST /api/projects/demo/build` with `{"request":"A fictional introductory lesson","planner":"dynamic"}`.
3. Poll the returned run through `GET /api/projects/demo/runs/{run_id}`.
4. Inspect changesets, artifacts, evidence and gates. Accept or reject a real returned changeset ID.
5. `POST /api/projects/demo/export` with `{"mode":"draft"}`; formal mode applies its own checks.
6. For human evaluation, first GET the run-specific evaluation target, then submit the real teacher rating with that exact target. See the evaluation guide.

Use actual IDs returned by the server. Teacher-role labels do not authenticate identity. Validation, conflicts and unavailable prerequisites are errors to handle, not reasons to edit stored state directly.
