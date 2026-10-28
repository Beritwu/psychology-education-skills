"""Public evaluation boundaries: provenance, frozen kits and human-only metrics."""
from __future__ import annotations

import pytest

from conftest import FakeLLM, FakeResearch, REQUEST_1, run_dynamic_build
from test_benchmark_evaluation import _valid_payload, client  # noqa: F401

pytestmark = pytest.mark.benchmark_smoke


@pytest.fixture(autouse=True)
def isolated_performance_registry(registry_env):
    """Every submission, including failed repros, stays outside the real registry."""


def _prepared_project(client, name, *, artifact_type="lesson_plan"):
    """A completed local run, without network/model/renderer dependencies."""
    from pebs import server

    client.post("/api/projects", json={"project_id": name})
    engine = server.get_engine(name)
    run_id = engine.store.create_run(environment="test_fixture", inputs={"planner": "dynamic"})
    revision = engine.store.add_revision(
        artifact_id=f"{artifact_type}:sec1", artifact_type=artifact_type,
        content={"section_id": "sec1", "title": "Frozen lesson", "units": []},
        produced_by="lesson-designer", run_id=run_id, fixture=True,
    )
    engine.store.set_accepted(f"{artifact_type}:sec1", revision["revision_id"])
    engine.store.set_run_status(run_id, "succeeded")
    return engine, run_id


def test_api_preserves_the_evaluated_run_and_mode(client, registry_env):
    from pebs import server

    client.post("/api/projects", json={"project_id": "bound-evaluation"})
    engine = server.get_engine("bound-evaluation")
    engine.llm = FakeLLM()
    engine.research = FakeResearch()
    start, status = run_dynamic_build(engine, REQUEST_1)
    assert status["run"]["status"] == "succeeded"
    engine.accept(start["changeset_id"])
    payload = _valid_payload(run_id=start["run_id"], mode="dynamic",
        target=client.get("/api/projects/bound-evaluation/evaluation").json()["evaluation_target"])
    payload["scores"]["spoken_naturalness"] = 4
    response = client.post(
        "/api/projects/bound-evaluation/evaluation",
        json=payload,
    )
    assert response.status_code == 200, response.text
    assert response.json()["run_id"] == start["run_id"]
    assert response.json()["mode"] == "dynamic"
    saved = client.get("/api/projects/bound-evaluation/evaluation").json()["human_eval"]
    assert saved["run_id"] == start["run_id"]


@pytest.mark.parametrize("source", [{"role": "ai"}, {"evaluation_kind": "ai"}])
def test_ai_review_cannot_be_submitted_as_a_teacher_score(client, source):
    client.post("/api/projects", json={"project_id": "human-only"})
    response = client.post(
        "/api/projects/human-only/evaluation", json=_valid_payload(**source)
    )
    assert response.status_code == 409
    assert client.get("/api/projects/human-only/evaluation").json()["human_eval"] is None


def test_incomplete_scores_cannot_enter_the_human_report(client):
    client.post("/api/projects", json={"project_id": "complete-rubric"})
    response = client.post(
        "/api/projects/complete-rubric/evaluation",
        json=_valid_payload(scores={"goal_clarity": 5}),
    )
    assert response.status_code == 409
    assert "subject_accuracy" in response.json()["reason"]


def test_report_reloads_teacher_evidence_instead_of_trusting_embedded_scores(client):
    from pebs.benchmark import report

    _, run_id = _prepared_project(client, "report-source")
    run = {"project_id": "report-source", "run_id": run_id, "case_id": "A",
           "mode": "dynamic", "run_status": "succeeded",
           "human_eval": _valid_payload(role="ai", edit_ratio=0.0)}
    row = report.summarize([run])["rows"][0]
    assert row["human_score"] is None
    assert row["edit_ratio"] is None


def test_non_script_optional_score_is_nullable_and_does_not_change_core_average(client):
    _, run_id = _prepared_project(client, "optional-score")
    payload = _valid_payload(run_id=run_id, mode="dynamic",
        target=client.get("/api/projects/optional-score/evaluation").json()["evaluation_target"])
    payload["scores"]["spoken_naturalness"] = None
    response = client.post("/api/projects/optional-score/evaluation", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["overall"] == 3.857
    payload["scores"]["spoken_naturalness"] = 1
    response = client.post("/api/projects/optional-score/evaluation", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["overall"] == 3.857


@pytest.mark.parametrize("run_id", ["", "run_from_another_project"])
def test_api_rejects_scores_without_a_run_in_this_project(client, run_id):
    _prepared_project(client, "bound-only")
    response = client.post(
        "/api/projects/bound-only/evaluation", json=_valid_payload(run_id=run_id)
    )
    assert response.status_code == 409, response.text


def test_scores_become_stale_when_the_reviewed_content_changes(client, registry_env):
    from pebs.benchmark import report

    engine, run_id = _prepared_project(client, "revision-bound")
    target = client.get("/api/projects/revision-bound/evaluation").json()["evaluation_target"]
    assert target["artifacts"]["lesson_plan:sec1"]["revision_id"] == "lesson_plan:sec1@r1"
    payload = _valid_payload(run_id=run_id, mode="dynamic", target=target)
    response = client.post("/api/projects/revision-bound/evaluation", json=payload)
    assert response.status_code == 200, response.text
    changed = engine.store.add_revision(
        artifact_id="lesson_plan:sec1", artifact_type="lesson_plan",
        content={"title": "Changed after evaluation"}, produced_by="lesson-designer",
        run_id=run_id, fixture=True,
    )
    engine.store.set_accepted("lesson_plan:sec1", changed["revision_id"])
    saved = client.get("/api/projects/revision-bound/evaluation").json()["human_eval"]
    assert saved["stale"] is True
    summary = report.summarize([{
        "case_id": "A", "project_id": engine.project_id, "run_id": run_id,
        "mode": "dynamic", "run_status": "succeeded",
    }])
    assert summary["rows"][0]["human_score"] is None
    assert summary["rows"][0]["human_eval_stale"] is True
    assert client.post("/api/projects/revision-bound/evaluation", json=payload).status_code == 409


def test_kit_regeneration_preserves_the_entire_filled_run_package(client, tmp_path):
    import json
    from pathlib import Path
    import yaml
    from pebs.benchmark import evaluation

    engine, first_run = _prepared_project(client, "frozen-kit")
    def run(rid):
        return {"case_id": "A", "mode": "dynamic", "project_id": engine.project_id,
                "run_id": rid, "run_status": "succeeded", "artifact_hashes": {"lesson_plan:sec1":
                    engine.store.accepted_revision("lesson_plan:sec1")["content_hash"]}}
    first_record = run(first_run)
    first = evaluation.export_kit([first_record], directory=tmp_path / "kit")[0]
    worksheet = Path(first["worksheet"])
    contents = yaml.safe_load(worksheet.read_text(encoding="utf-8"))
    contents["reviewer"] = "Teacher already working"
    worksheet.write_text(yaml.safe_dump(contents), encoding="utf-8")
    original = {p.name: p.read_bytes() for p in Path(first["dir"]).iterdir() if p.is_file()}
    second_run = engine.store.create_run(environment="test_fixture", inputs={"planner": "dynamic"})
    changed = engine.store.add_revision(
        artifact_id="lesson_plan:sec1", artifact_type="lesson_plan", content={"title": "New lesson"},
        produced_by="lesson-designer", run_id=second_run, fixture=True,
    )
    engine.store.set_accepted("lesson_plan:sec1", changed["revision_id"])
    engine.store.set_run_status(second_run, "succeeded")
    second = evaluation.export_kit([run(second_run)], directory=tmp_path / "kit")[0]
    assert first["dir"] != second["dir"]
    assert json.loads((Path(second["dir"]) / "run.json").read_text(encoding="utf-8"))["run_id"] == second_run
    evaluation.export_kit([first_record], directory=tmp_path / "kit")
    assert {p.name: p.read_bytes() for p in Path(first["dir"]).iterdir() if p.is_file()} == original


def test_binding_failure_is_visible_and_resubmission_is_idempotent(client, registry_env):
    from pebs import config

    engine, run_id = _prepared_project(client, "binding-failure")
    # An invalid filesystem destination exercises the real persistence failure.
    path = config.REGISTRY_DIR / "performance.json"
    if path.exists():
        path.unlink()
    path.mkdir()
    payload = _valid_payload(run_id=run_id, mode="dynamic",
        target=client.get("/api/projects/binding-failure/evaluation").json()["evaluation_target"])
    response = client.post("/api/projects/binding-failure/evaluation", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["binding"]["status"] == "FAILED"
    assert client.get("/api/projects/binding-failure/evaluation").json()["human_eval"]["binding"]["status"] == "FAILED"
    path.rmdir()
    retried = client.post("/api/projects/binding-failure/evaluation", json=payload)
    assert retried.status_code == 200, retried.text
    assert retried.json()["binding"]["status"] == "BOUND"
    saved = path.read_bytes()
    again = client.post("/api/projects/binding-failure/evaluation", json=payload)
    assert again.json()["evaluation_id"] == retried.json()["evaluation_id"]
    assert path.read_bytes() == saved


def test_teacher_must_submit_the_snapshot_they_reviewed(client):
    _, run_id = _prepared_project(client, "explicit-snapshot")
    response = client.post("/api/projects/explicit-snapshot/evaluation",
                           json=_valid_payload(run_id=run_id, mode="dynamic"))
    assert response.status_code == 409
    assert "target" in response.json()["reason"]


def test_script_evaluation_requires_spoken_naturalness(client):
    _, run_id = _prepared_project(client, "script-rubric", artifact_type="script")
    target = client.get("/api/projects/script-rubric/evaluation").json()["evaluation_target"]
    payload = _valid_payload(run_id=run_id, mode="dynamic", target=target)
    payload["scores"].pop("spoken_naturalness")
    response = client.post("/api/projects/script-rubric/evaluation", json=payload)
    assert response.status_code == 409
    assert "spoken_naturalness" in response.json()["reason"]


def test_cli_submission_reports_binding_failure_and_can_retry(client, tmp_path, capsys):
    from pathlib import Path
    import json
    import yaml
    from pebs import cli, config
    from pebs.benchmark import evaluation

    engine, run_id = _prepared_project(client, "cli-evaluation")
    artifact = engine.store.accepted_revision("lesson_plan:sec1")
    run = {"project_id": engine.project_id, "run_id": run_id, "case_id": "A", "mode": "dynamic",
           "run_status": "succeeded", "artifact_hashes": {"lesson_plan:sec1": artifact["content_hash"]}}
    package = evaluation.export_kit([run], directory=tmp_path / "kit")[0]
    sheet = Path(package["worksheet"])
    data = yaml.safe_load(sheet.read_text(encoding="utf-8"))
    data.update(_valid_payload())
    sheet.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    path = config.REGISTRY_DIR / "performance.json"
    if path.exists():
        path.unlink()
    path.mkdir()
    args = ["benchmark", "--submit-eval", str(sheet), "--project", engine.project_id]
    assert cli.main(args) != 0
    assert json.loads(capsys.readouterr().out)["binding"]["status"] == "FAILED"
    path.rmdir()
    assert cli.main(args) == 0
    saved = json.loads(capsys.readouterr().out)
    assert saved["run_id"] == run_id
    assert saved["binding"]["status"] == "BOUND"


def test_direct_baseline_kit_has_complete_content_and_a_submittable_identity(client, tmp_path, capsys):
    from pathlib import Path
    import yaml
    from pebs import cli
    from pebs.benchmark import evaluation, report

    run_dir = tmp_path / "direct"
    run_dir.mkdir()
    original = "Direct baseline lesson\n" * 1200 + "END OF ORIGINAL"
    (run_dir / "direct_output.md").write_text(original, encoding="utf-8")
    run = {"project_id": "direct-evaluation", "run_id": "", "run_dir": str(run_dir),
           "case_id": "A", "mode": "direct_codex", "run_status": "succeeded", "artifact_hashes": {}}
    exported = evaluation.export_kit([run], directory=tmp_path / "kit")[0]
    assert original in (Path(exported["dir"]) / "course.md").read_text(encoding="utf-8")
    path = Path(exported["worksheet"])
    sheet = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert sheet["run"]["run_id"]
    sheet.update(_valid_payload())
    path.write_text(yaml.safe_dump(sheet, allow_unicode=True), encoding="utf-8")
    assert cli.main(["benchmark", "--submit-eval", str(path), "--project", run["project_id"]]) == 0
    row = report.summarize([run])["rows"][0]
    assert row["human_score"] == 3.857
    assert not row["human_eval_stale"]


def test_teacher_binding_keeps_build_time_skill_version_after_registry_upgrade(client):
    import json
    from pebs import config

    engine, run_id = _prepared_project(client, "skill-provenance")
    engine.store.add_step(run_id, "script-writer", "Script", status="SUCCEEDED")
    before = client.get("/api/projects/skill-provenance/evaluation").json()
    version = before["trace"]["skills"][0]["version"]
    path = config.REGISTRY_DIR / "skills.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    registry["script-writer"]["version"] = "999.0-upgraded"
    registry["script-writer"]["pinned_version"] = "999.0-upgraded"
    path.write_text(json.dumps(registry), encoding="utf-8")
    response = client.post("/api/projects/skill-provenance/evaluation", json=_valid_payload(
        target=before["evaluation_target"], run_id=run_id, mode="dynamic"))
    assert response.status_code == 200, response.text
    assert response.json()["binding"]["status"] == "BOUND"
    stored = client.get("/api/projects/skill-provenance/evaluation").json()
    assert stored["trace"]["skills"][0]["version"] == version
    assert stored["performance"]["script-writer"]["version"] == version


def test_new_skill_build_does_not_inherit_an_older_versions_teacher_score(client):
    from pebs.benchmark import performance

    engine, run_id = _prepared_project(client, "new-skill-score")
    engine.store.add_step(run_id, "script-writer", "Script", status="SUCCEEDED")
    before = client.get("/api/projects/new-skill-score/evaluation").json()
    response = client.post("/api/projects/new-skill-score/evaluation", json=_valid_payload(
        target=before["evaluation_target"], run_id=run_id, mode="dynamic"))
    assert response.json()["binding"]["status"] == "BOUND"
    # A newly recorded build is the event that changes the displayed skill version.
    performance.record_run(skill="script-writer", version="999.0", success=True)
    current = client.get("/api/projects/new-skill-score/evaluation").json()["performance"]["script-writer"]
    assert current["version"] == "999.0"
    assert current["human_score"] is None
    assert current["teacher_edit_ratio"] is None


def test_evaluation_api_can_retrieve_an_older_run_without_using_the_latest_score(client):
    engine, first_run = _prepared_project(client, "history-evaluation")
    target = client.get("/api/projects/history-evaluation/evaluation").json()["evaluation_target"]
    response = client.post("/api/projects/history-evaluation/evaluation", json=_valid_payload(
        run_id=first_run, mode="dynamic", target=target))
    assert response.status_code == 200
    second_run = engine.store.create_run(inputs={"planner": "dynamic"})
    engine.store.set_run_status(second_run, "succeeded")
    assert client.get("/api/projects/history-evaluation/evaluation").json()["human_eval"] is None
    historical = client.get("/api/projects/history-evaluation/evaluation", params={"run_id": first_run})
    assert historical.status_code == 200
    assert historical.json()["run"]["run_id"] == first_run
    assert historical.json()["human_eval"]["run_id"] == first_run
    assert not historical.json()["human_eval"]["stale"]


def test_cli_rejects_a_material_package_changed_after_export(client, tmp_path, capsys):
    from pathlib import Path
    import yaml
    from pebs import cli
    from pebs.benchmark import evaluation

    engine, run_id = _prepared_project(client, "changed-package")
    artifact = engine.store.accepted_revision("lesson_plan:sec1")
    run = {"project_id": engine.project_id, "run_id": run_id, "case_id": "A", "mode": "dynamic",
           "run_status": "succeeded", "artifact_hashes": {"lesson_plan:sec1": artifact["content_hash"]}}
    package = evaluation.export_kit([run], directory=tmp_path / "kit")[0]
    sheet = Path(package["worksheet"])
    data = yaml.safe_load(sheet.read_text(encoding="utf-8"))
    data.update(_valid_payload())
    sheet.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    (Path(package["dir"]) / "course.md").write_text("Replaced after export", encoding="utf-8")
    assert cli.main(["benchmark", "--submit-eval", str(sheet), "--project", engine.project_id]) != 0
    assert client.get("/api/projects/changed-package/evaluation").json()["human_eval"] is None


def test_plain_worksheet_export_resolves_the_reviewed_target(client, tmp_path):
    from pebs.benchmark import report

    engine, run_id = _prepared_project(client, "plain-worksheet")
    artifact = engine.store.accepted_revision("lesson_plan:sec1")
    run = {"project_id": engine.project_id, "run_id": run_id, "case_id": "A", "mode": "dynamic",
           "run_status": "succeeded", "artifact_hashes": {"lesson_plan:sec1": artifact["content_hash"]}}
    paths = report.write_worksheets([run], directory=tmp_path / "worksheets")
    payload = report.load_worksheet(paths[0])
    assert payload["target"] == client.get("/api/projects/plain-worksheet/evaluation").json()["evaluation_target"]


@pytest.mark.parametrize("field,value", [("must_fix", ["Keep this feedback"]), ("evidence_errors", 2), ("invalid_yaml", "scores: [")])
def test_worksheet_export_preserves_partial_or_malformed_teacher_input(client, tmp_path, field, value):
    import yaml
    from pebs.benchmark import report

    engine, run_id = _prepared_project(client, "partial-feedback")
    artifact = engine.store.accepted_revision("lesson_plan:sec1")
    run = {"project_id": engine.project_id, "run_id": run_id, "case_id": "A", "mode": "dynamic",
           "run_status": "succeeded", "artifact_hashes": {"lesson_plan:sec1": artifact["content_hash"]}}
    path = report.write_worksheets([run], directory=tmp_path / "worksheets")[0]
    sheet = yaml.safe_load(path.read_text(encoding="utf-8"))
    sheet[field] = value
    path.write_text(value if field == "invalid_yaml" else yaml.safe_dump(sheet), encoding="utf-8")
    before = path.read_bytes()
    report.write_worksheets([run], directory=path.parent)
    assert path.read_bytes() == before


def test_historical_evaluation_trace_reads_that_runs_route(client):
    engine, run_id = _prepared_project(client, "historical-route")
    for rid, intent in [(run_id, "Original course"),
                        (engine.store.create_run(inputs={"planner": "dynamic"}), "New course")]:
        revision = engine.store.add_revision(artifact_id="router_result", artifact_type="router_result",
            content={"task_intent": intent}, produced_by="dynamic-planner", run_id=rid)
        engine.store.set_accepted("router_result", revision["revision_id"])
        engine.store.set_run_status(rid, "succeeded")
    historical = client.get("/api/projects/historical-route/evaluation", params={"run_id": run_id})
    assert historical.json()["trace"]["route"]["task_intent"] == "Original course"


def test_rendered_report_keeps_the_same_run_set_as_its_summary(tmp_path, monkeypatch):
    import json
    from pebs.benchmark import report, cases

    run_dir = tmp_path / "runs" / "20261028-010000-A-dynamic"
    run_dir.mkdir(parents=True)
    global_run = {"case_id": "A", "mode": "dynamic", "run_status": "succeeded",
                  "automatic_issues": {"counts": {"UNRELATED_GLOBAL_FAILURE": 1}}}
    (run_dir / "run.json").write_text(json.dumps(global_run), encoding="utf-8")
    monkeypatch.setattr(cases, "runs_dir", lambda: run_dir.parent)
    local_run = {**global_run, "automatic_issues": {"counts": {"LOCAL_ONLY_FAILURE": 1}}}
    rendered = report.render_markdown(report.summarize([local_run]))
    assert "LOCAL_ONLY_FAILURE" in rendered
    assert "UNRELATED_GLOBAL_FAILURE" not in rendered


@pytest.mark.parametrize("damage", ["missing_manifest", "invalid_yaml"])
def test_cli_reports_damaged_evaluation_packages_without_recording_scores(client, tmp_path, capsys, damage):
    from pathlib import Path
    import yaml
    from pebs import cli
    from pebs.benchmark import evaluation

    engine, run_id = _prepared_project(client, "damaged-evaluation")
    artifact = engine.store.accepted_revision("lesson_plan:sec1")
    run = {"project_id": engine.project_id, "run_id": run_id, "case_id": "A", "mode": "dynamic",
           "run_status": "succeeded", "artifact_hashes": {"lesson_plan:sec1": artifact["content_hash"]}}
    package = evaluation.export_kit([run], directory=tmp_path / "kit")[0]
    path = Path(package["worksheet"])
    sheet = yaml.safe_load(path.read_text(encoding="utf-8"))
    sheet.update(_valid_payload())
    path.write_text(yaml.safe_dump(sheet), encoding="utf-8")
    if damage == "missing_manifest":
        (path.parent / "manifest.json").unlink()
    else:
        path.write_text("scores: [", encoding="utf-8")
    assert cli.main(["benchmark", "--submit-eval", str(path), "--project", engine.project_id]) != 0
    assert client.get("/api/projects/damaged-evaluation/evaluation").json()["human_eval"] is None


def test_replaying_a_build_trace_does_not_inflate_displayed_skill_runs(client):
    from pebs.benchmark import performance

    engine, run_id = _prepared_project(client, "trace-retry")
    engine.store.add_step(run_id, "script-writer", "Script", status="SUCCEEDED")
    trace = client.get("/api/projects/trace-retry/evaluation").json()["trace"]
    performance.record_trace(trace)
    performance.record_trace(trace)
    result = client.get("/api/projects/trace-retry/evaluation").json()
    assert result["performance"]["script-writer"]["runs"] == 1


def test_partial_identity_update_preserves_known_skill_identity(client):
    from pebs.benchmark import performance

    _prepared_project(client, "partial-identity")
    performance.record_run(skill="external-lesson", version="v1", provider_sha="upstream",
        package_sha256="package", patch="patch1", success=True, human_score=4.0)
    performance.record_run(skill="external-lesson", version="v1", success=True)
    record = client.get("/api/projects/partial-identity/evaluation").json()["performance"]["external-lesson"]
    assert record["runs"] == 2
    assert record["provider_sha"] == "upstream"
    assert record["human_score"] == 4.0


def test_resumed_build_updates_performance_without_counting_another_run(client):
    from pebs.benchmark import performance

    engine, run_id = _prepared_project(client, "resumed-trace")
    engine.store.add_step(run_id, "script-writer", "Script", status="BLOCKED")
    performance.record_trace(client.get("/api/projects/resumed-trace/evaluation").json()["trace"])
    engine.store.set_step(run_id, "script-writer", status="SUCCEEDED", note="Schema 修复 1 次")
    performance.record_trace(client.get("/api/projects/resumed-trace/evaluation").json()["trace"])
    record = client.get("/api/projects/resumed-trace/evaluation").json()["performance"]["script-writer"]
    assert record["runs"] == 1
    assert record["success_rate"] == 1.0
    assert record["schema_repair_rate"] == 1.0


def test_historical_trace_keeps_the_review_from_that_run(client):
    engine, run_id = _prepared_project(client, "review-history")
    for rid, reviewer in [(run_id, "First teacher"),
                          (engine.store.create_run(inputs={"planner": "dynamic"}), "Later teacher")]:
        revision = engine.store.add_revision(artifact_id="review_record", artifact_type="review_record",
            content={"reviewer": reviewer, "basis": "Reviewed the materials"}, produced_by="teacher", run_id=rid)
        engine.store.set_accepted("review_record", revision["revision_id"])
    response = client.get("/api/projects/review-history/evaluation", params={"run_id": run_id})
    assert [item["reviewer"] for item in response.json()["trace"]["human_review"]] == ["First teacher"]
