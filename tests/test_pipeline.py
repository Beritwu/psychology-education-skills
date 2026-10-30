from __future__ import annotations

import json
from pathlib import Path
import pytest

from conftest import REQUEST_1, REQUEST_2, FakeLLM, FakeResearch, MissingLLM, run_build
from test_benchmark_evaluation import client  # noqa: F401

from pebs import gates

def _step_statuses(engine, run_id):
    return {s["step_id"]: s["status"] for s in engine.store.get_steps(run_id)}


def test_full_build_produces_formal_ready_artifacts(engine):
    run_id, changeset_id = run_build(engine, REQUEST_1)
    statuses = _step_statuses(engine, run_id)
    assert statuses["parse_inputs"] == "SUCCEEDED"
    assert statuses["learning_design"] == "SUCCEEDED"
    assert statuses["scripts"] == "SUCCEEDED"
    assert statuses["gates"] == "SUCCEEDED"
    assert statuses["export"] == "SUCCEEDED"
    assert engine.store.get_run(run_id)["status"] == "succeeded"

    claims = engine.evidence.claims()
    assert claims and all(c["status"] == "SUPPORTED" for c in claims)

    candidate_script = engine.store.revisions_of("script:sec1")[-1]
    assert engine.store.get_revision(candidate_script)["content"]["word_count"]["in_range"] is True

    result = engine.accept(changeset_id)
    assert result["status"] == "accepted"
    readiness = gates.export_readiness(engine.store)
    assert readiness["ready"] is True, readiness["blocking"]


def test_failed_provider_call_is_still_counted_as_consumption(engine):
    """§35 Cost / Quota Consumption：请求已发出但 provider 报错（如配额打满）也要记账。

    否则一次真实的配额耗尽会被记成 0 次调用，成本口径失真。
    """
    from pebs.providers import ProviderError

    class FlakyLLM(FakeLLM):
        def generate_json(self, *, task, system, prompt):
            self._bump(task)
            if task == "learning_design":
                raise ProviderError("codex exec 失败：usage limit")
            return super().generate_json(task=task, system=system, prompt=prompt)

    engine.llm = FlakyLLM()
    run_id, _ = run_build(engine, REQUEST_1)
    step = next(s for s in engine.store.get_steps(run_id) if s["step_id"] == "learning_design")
    assert step["status"] == "FAILED"
    assert int(step["model_calls"]) == 1, "失败的调用也要记到该步骤"
    assert int(engine.store.get_run(run_id)["calls_used"]) >= 1


def test_slide_plan_enforcement_survives_list_typed_model_fields(engine):
    """真实 run 缺陷：模型把 section_id 返回成数组时，`x not in set` 抛 unhashable，
    整条运行判 failed。归一化后应正常降级而不是崩溃。"""
    from pebs import pipeline

    class _Ctx:
        outputs = {"requirements": "requirements@r1", "diagrams:sec1": "diagrams:sec1@r1"}

        def content(self, artifact_id):
            if artifact_id == "requirements":
                return {"sections": [{"section_id": "sec1", "title": "t"}]}
            if artifact_id == "diagrams:sec1":
                return {"diagrams": [{"diagram_id": "d1"}]}
            return None

    data = {
        "rows": [
            {
                "slide": 1,
                "title": "标题",
                "narrative_section": "s",
                "communication_task": "c",
                "core_message": "m",
                "layout_archetype": ["bullets"],
                "density": ["medium"],
                "section_id": ["sec1"],
                "diagram_id": ["d1"],
                "claim_refs": [],
            }
        ]
    }
    notes = pipeline._enforce_slide_plan(_Ctx(), data)
    row = data["rows"][0]
    assert row["section_id"] == ""
    assert row["layout_archetype"] == "bullets"
    assert row["density"] == "medium"
    assert isinstance(notes, list)


@pytest.mark.parametrize('malformed_refs', [
    [{'id': 'clm_deadbeef', 'version': 1}],
    ['clm_1@v1', ['clm_2@v1'], ''],
])
def test_claim_refs_returned_as_objects_do_not_crash_the_script(client, malformed_refs):
    """真实 run 缺陷：模型把 claim_refs 返回成对象时，`set(...)` 抛 unhashable dict。

    归一化后按"未获支持"处理（保守：标为待核验占位），而不是让整条运行 failed。
    """
    from pebs import server

    class MalformedRefsLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] in ('script', 'script_fix'):
                narration = next(unit for unit in result['units'] if unit['kind'] == 'narration')
                narration['claim_refs'] = malformed_refs
            return result

    base = '/api/projects/malformed-script-refs'
    client.post('/api/projects', json={'project_id': 'malformed-script-refs'})
    engine = server.get_engine('malformed-script-refs')
    engine.llm, engine.research = MalformedRefsLLM(), FakeResearch()
    run_id, _ = run_build(engine, REQUEST_1, environment='test_fixture')
    status = engine.run_status(run_id)
    assert status['run']['status'] == 'succeeded', [(s['step_id'], s.get('error')) for s in status['steps'] if s['status'] == 'FAILED']
    revision = engine.store.revisions_of('script:sec1')[-1]
    response = client.get(base + '/artifacts/script:sec1', params={'rev': revision})
    assert response.status_code == 200, response.text
    units = response.json()['content']['units']
    assert all(isinstance(ref, str) for unit in units for ref in unit.get('claim_refs', []))
    narration = next(unit for unit in units if unit['kind'] == 'narration')
    assert narration['placeholder'] is True
    if isinstance(malformed_refs[0], str):
        assert narration['claim_refs'] == ['clm_1@v1', "['clm_2@v1']"]
    else:
        assert narration['claim_refs'] == ["{'id': 'clm_deadbeef', 'version': 1}"]


def test_unexpected_step_error_records_the_offending_frame(engine, monkeypatch):
    """未预期错误的 step error 要带定位信息，否则只有 `unhashable type` 无从排查。"""
    from pebs import pipeline

    def boom(ctx):
        raise TypeError("unhashable type: 'list'")

    monkeypatch.setitem(pipeline.STEPS, "requirements", boom)
    run_id, _ = run_build(engine, REQUEST_1)
    step = next(s for s in engine.store.get_steps(run_id) if s["step_id"] == "requirements")
    assert step["status"] == "FAILED"
    assert "unhashable type" in step["error"]
    assert ":32" in step["error"] or "boom" in step["error"]


def test_malformed_json_response_is_retried_once_then_fails(engine):
    """A14：畸形 JSON（长输出被截断）应有界重试一次；再失败则如实失败，不伪造内容。"""
    from pebs.providers import ProviderError

    class TruncatingLLM(FakeLLM):
        def __init__(self, fail_times: int):
            super().__init__()
            self.remaining = fail_times

        def generate_json(self, *, task, system, prompt):
            self._bump(task)
            if task == "storyboard" and self.remaining > 0:
                self.remaining -= 1
                raise ProviderError("provider JSON parse error: Unterminated string")
            return super().generate_json(task=task, system=system, prompt=prompt)

    # 第一次畸形、第二次正常 → 运行继续，且两次调用都被记账
    engine.llm = TruncatingLLM(fail_times=1)
    run_id, _ = run_build(engine, REQUEST_1)
    steps = {step["step_id"]: step for step in engine.store.get_steps(run_id)}
    assert steps["storyboard"]["status"] == "SUCCEEDED", steps["storyboard"]["error"]
    assert engine.store.get_run(run_id)["calls_used"] >= 2

    # 连续畸形 → 有界重试后失败，且没有产出伪造成品
    engine2 = type(engine)(engine.project_id + "-retry2", base_dir=engine.base.parent / "proj2")
    engine2.llm = TruncatingLLM(fail_times=99)
    engine2.research = engine.research
    run_id2, _ = run_build(engine2, REQUEST_1)
    steps2 = {step["step_id"]: step for step in engine2.store.get_steps(run_id2)}
    assert steps2["storyboard"]["status"] == "FAILED"
    assert "JSON parse error" in (steps2["storyboard"]["error"] or "")
    engine2.close()


def test_offline_without_provider_reports_unavailable_and_never_fabricates(engine):
    engine.llm = MissingLLM()
    run_id, changeset_id = run_build(engine, REQUEST_1)
    statuses = _step_statuses(engine, run_id)
    assert statuses["parse_inputs"] == "SUCCEEDED"
    assert statuses["requirements"] == "SUCCEEDED"
    assert statuses["learning_design"] == "BLOCKED"
    assert statuses["scripts"] == "BLOCKED"
    assert engine.store.get_run(run_id)["status"] == "blocked"
    step = next(s for s in engine.store.get_steps(run_id) if s["step_id"] == "learning_design")
    assert "Provider" in (step["error"] or "")
    assert engine.store.revisions_of("script:sec1") == []
    assert engine.store.revisions_of("claims") == []


def test_fixture_environment_is_recorded_in_runs_and_gate_results(engine):
    run_id, changeset_id = run_build(engine, REQUEST_1, environment="test_fixture")
    run = engine.store.get_run(run_id)
    assert run["environment"] == "test_fixture"
    gate_artifacts = [a for a in engine.store.list_artifacts() if a["artifact_type"] == "gate_result"]
    assert gate_artifacts
    for artifact in gate_artifacts:
        revision = engine.store.get_revision(artifact["accepted_rev"] or engine.store.revisions_of(artifact["artifact_id"])[-1])
        assert revision["fixture"] == 1
        assert revision["content"]["run_environment"] == "test_fixture"


def test_export_draft_label_when_gates_fail(engine):
    engine.research = FakeResearch(available=False)
    run_id, changeset_id = run_build(engine, REQUEST_1)
    engine.accept(changeset_id)
    readiness = gates.export_readiness(engine.store)
    assert readiness["ready"] is False
    result = engine.export_now("draft")
    assert result["ok"] is True
    files = result["manifest"]["files"]
    assert files
    labeled_roles = {"lesson_script", None}
    for entry in files:
        assert entry["label"] == "草稿—未通过 QA"
        role = entry.get("role", "lesson_script")
        if entry["kind"] == "docx" and role in labeled_roles:
            import docx

            document = docx.Document(entry["path"])
            text = "\n".join(p.text for p in document.paragraphs)
            assert "草稿—未通过 QA" in text
        elif entry["kind"] == "markdown" and role in labeled_roles:
            assert "草稿—未通过 QA" in Path(entry["path"]).read_text(encoding="utf-8")
        else:
            assert Path(entry["path"]).exists()


def test_formal_export_blocked_when_gates_fail(engine):
    engine.research = FakeResearch(available=False)
    run_id, changeset_id = run_build(engine, REQUEST_1)
    engine.accept(changeset_id)
    result = engine.export_now("formal")
    assert result["ok"] is False
    assert "正式导出被阻止" in result["reason"]


def test_docx_export_publishes_only_after_accept(engine, no_pptx):
    run_id, changeset_id = run_build(engine, REQUEST_1)
    engine.accept(changeset_id)
    formal_dir = Path(engine.store.base_dir) / "outputs" / "formal"
    before = sorted(p.name for p in formal_dir.iterdir()) if formal_dir.exists() else []

    result = engine.export_now("formal")
    assert result["ok"] is True
    staged_paths = [f["path"] for f in result["manifest"]["files"]]
    assert staged_paths and all("staging" in path for path in staged_paths)
    during = sorted(p.name for p in formal_dir.iterdir()) if formal_dir.exists() else []
    assert during == before

    accept = engine.accept(result["changeset_id"])
    assert accept["status"] == "accepted"
    published = {p.name for p in formal_dir.iterdir()}
    assert {f"{result['changeset_id']}_{Path(p).name}" for p in staged_paths} <= published
    import docx

    docx_file = next(f for f in result["manifest"]["files"] if f["kind"] == "docx")
    document = docx.Document(str(formal_dir / f"{result['changeset_id']}_{Path(docx_file['path']).name}"))
    assert any("测试节" in p.text for p in document.paragraphs)
    assert all(Path(p).exists() for p in staged_paths)
    script = engine.store.accepted_content("script:sec1")
    assert script["word_count"]["count"] > 0


def test_rejecting_formal_export_discards_staging(engine):
    run_id, changeset_id = run_build(engine, REQUEST_1)
    engine.accept(changeset_id)
    result = engine.export_now("formal")
    reject = engine.reject(result["changeset_id"])
    assert reject["status"] == "rejected"
    staging = Path(engine.store.base_dir) / "outputs" / "staging" / result["changeset_id"]
    assert not staging.exists()


def test_formal_export_downgraded_by_g8_never_publishes_staged_formal_files(engine, no_pptx, monkeypatch):
    from pebs import gates
    _, changeset = run_build(engine, REQUEST_1)
    engine.accept(changeset)
    # Cross the r9/r10 boundary to catch lexicographic revision ordering.
    while len(engine.store.revisions_of('export_manifest')) < 8:
        engine.store.add_revision(artifact_id='export_manifest', artifact_type='export_manifest',
                                  content={'mode': 'seed'}, produced_by='fixture')
    original = gates.g8_artifact
    count = 0
    def fail_first(ctx, target):
        nonlocal count
        count += 1
        result = original(ctx, target)
        if count == 1:
            result['status'] = 'NEEDS_REVIEW'
            result['issues'] = [{'location': 'test', 'reason': 'forced failure', 'next_step': 'review'}]
        return result
    monkeypatch.setattr(gates, 'g8_artifact', fail_first)
    export = engine.export_now('formal')
    assert export['ok'] and export['mode'] == 'draft'
    accepted = engine.accept(export['changeset_id'])
    assert accepted['published'] == []
    assert engine.store.accepted_content('export_manifest')['mode'] == 'draft'
