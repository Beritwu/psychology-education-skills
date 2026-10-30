"""Public contracts for the two additional psychology teaching units."""

import pytest
from fastapi.testclient import TestClient

from pebs.server import app
from test_benchmark_evaluation import client  # noqa: F401


@pytest.mark.parametrize(
    ("unit_id", "concept_ids"),
    [
        ("operant-conditioning", {"positive-reinforcement", "negative-reinforcement", "positive-punishment", "negative-punishment"}),
        ("research-methods", {"operational-definition", "correlation", "random-assignment", "confounding-variable"}),
    ],
)
def test_new_unit_exposes_teaching_and_review_materials(unit_id, concept_ids):
    with TestClient(app) as client:
        response = client.get(f"/api/psychology/units/{unit_id}")
        assert response.status_code == 200, response.text
        unit = response.json()
        assert unit["unit_id"] == unit_id
        assert unit["teacher_review"]["status"] == "PENDING"
        assert {concept["concept_id"] for concept in unit["concepts"]} == concept_ids
        for concept in unit["concepts"]:
            assert concept["source_refs"]
            assert len(concept["misconceptions"]) >= 2
            assert all(concept["terms"][lang]["full"] for lang in ("zh-CN", "en", "ja", "ko"))
            questions = [q for q in unit["assessments"] if q["concept_ref"] == concept["concept_id"]]
            assert {q["kind"] for q in questions} == {"diagnostic", "retest"}
        student = client.get(f"/api/psychology/units/{unit_id}/materials?audience=student")
        assert student.status_code == 200, student.text
        assert len(student.json()["questions"]) == 10
        assert all("answer" not in q and "rationale" not in q for q in student.json()["questions"])


@pytest.mark.parametrize(
    ("unit_id", "concept_id", "source_title"),
    [
        ("operant-conditioning", "negative-reinforcement", "Operant Conditioning"),
        ("research-methods", "correlation", "Analyzing Findings"),
    ],
)
def test_project_freezes_unit_source_and_provides_safe_remediation(client, unit_id, concept_id, source_title):
    project = f"unit-{unit_id}"
    assert client.post("/api/projects", json={"project_id": project}).status_code == 200
    base = f"/api/projects/{project}/psychology/units/{unit_id}"
    pinned = client.post(base)
    assert pinned.status_code == 200, pinned.text
    revision_id = pinned.json()["revision_id"]
    artifact = client.get(f"/api/projects/{project}/artifacts/psychology_unit:{unit_id}", params={"rev": revision_id})
    assert artifact.status_code == 200, artifact.text
    assert source_title in artifact.json()["content"]["frozen_source"]["metadata"]["title"]
    materials = client.get(base + "/materials", params={"revision_id": revision_id, "audience": "student"})
    assert materials.status_code == 200, materials.text
    assert materials.json()["target"]["content_hash"] == pinned.json()["content_hash"]
    response = client.post(base + "/diagnose", json={"revision_id": revision_id,
                           "assessment_id": concept_id + "-diagnostic", "option_id": concept_id + "-diagnostic-b"})
    assert response.status_code == 200, response.text
    assert response.json()["correct"] is False
    assert response.json()["remediation"]
    assert "scoring_guidance" not in response.json()["retest"]
    exported = client.get(base + "/export", params={"revision_id": revision_id})
    assert exported.status_code == 200, exported.text
    assert unit_id in exported.headers["content-disposition"]


def test_research_unit_remediation_addresses_the_selected_error():
    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/research-methods').json()
        concepts = {concept['concept_id']: concept for concept in unit['concepts']}
        assert '不能单独确立因果关系' in concepts['correlation']['definition']
        cases = {
            'operational-definition-diagnostic-b': ('operational-definition-diagnostic', '测量'),
            'random-assignment-diagnostic-b': ('random-assignment-diagnostic', '抽样'),
            'confounding-variable-diagnostic-c': ('confounding-variable-diagnostic', '不能'),
        }
        for option_id, (assessment_id, expected) in cases.items():
            response = client.post('/api/psychology/units/research-methods/diagnose',
                                   json={'assessment_id': assessment_id, 'option_id': option_id})
            assert response.status_code == 200, response.text
            assert expected in response.json()['remediation']


@pytest.mark.parametrize('unit_id', ['operant-conditioning', 'research-methods'])
def test_frozen_new_unit_materials_survive_unavailable_catalog_and_source(client, monkeypatch, tmp_path, unit_id):
    from pebs import psychology

    project = 'frozen-' + unit_id
    assert client.post('/api/projects', json={'project_id': project}).status_code == 200
    base = f'/api/projects/{project}/psychology/units/{unit_id}'
    pinned = client.post(base)
    assert pinned.status_code == 200, pinned.text
    monkeypatch.setattr(psychology, 'CONTENT_PATH', tmp_path / 'missing.json')
    monkeypatch.setattr(psychology, 'SOURCE_DIRECTORY', tmp_path / 'missing-sources')
    result = client.get(base + '/materials', params={'revision_id': pinned.json()['revision_id'], 'audience': 'teacher'})
    assert result.status_code == 200, result.text
    assert result.json()['unit_id'] == unit_id
    assert result.json()['target']['content_hash'] == pinned.json()['content_hash']
    assert result.json()['teacher_review']['status'] == 'PENDING'
    exported = client.get(base + '/export', params={'revision_id': pinned.json()['revision_id'], 'audience': 'teacher'})
    assert exported.status_code == 200, exported.text
    assert pinned.json()['content_hash'] in exported.text


@pytest.mark.parametrize('planner', ['static', 'dynamic'])
@pytest.mark.parametrize(('unit_id', 'source_title'), [
    ('operant-conditioning', 'Psychology 2e, 6.3 Operant Conditioning'),
    ('research-methods', 'Psychology 2e, 2.3 Analyzing Findings'),
])
def test_fixture_build_binds_the_right_frozen_unit_and_source(client, planner, unit_id, source_title):
    from conftest import FakeLLM, FakeResearch, run_build, run_dynamic_build
    from pebs import server

    project = 'build-' + unit_id
    assert client.post('/api/projects', json={'project_id': project}).status_code == 200
    pinned = client.post(f'/api/projects/{project}/psychology/units/{unit_id}').json()
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    request = 'Create one introductory psychology lesson. No PPT. No animation. 学科修订=' + pinned['revision_id']
    if planner == 'dynamic':
        start, status = run_dynamic_build(engine, request, environment='test_fixture')
    else:
        run_id, _ = run_build(engine, request, environment='test_fixture')
        status = engine.run_status(run_id)
    assert status['run']['status'] == 'succeeded'
    rev = engine.store.revisions_of('materials')[-1]
    material = client.get(f'/api/projects/{project}/artifacts/materials', params={'rev': rev}).json()['content']
    assert material['psychology_target']['content_hash'] == pinned['content_hash']
    assert material['psychology_unit']['unit_id'] == unit_id
    assert len(material['psychology_source']['concept_anchors']) == 4
    evidence = client.get(f'/api/projects/{project}/evidence').json()
    assert any(source['title'] == source_title for source in evidence['sources'])


@pytest.mark.parametrize('unit_id', ['operant-conditioning', 'research-methods'])
def test_teacher_review_and_feedback_bind_to_new_unit_revision(client, unit_id):
    project = 'teacher-' + unit_id
    assert client.post('/api/projects', json={'project_id': project}).status_code == 200
    base = f'/api/projects/{project}/psychology/units/{unit_id}'
    pinned = client.post(base).json()
    target = {'revision_id': pinned['revision_id'], 'content_hash': pinned['content_hash']}
    before = client.get(base + '/materials', params={'revision_id': pinned['revision_id'], 'audience': 'teacher'}).json()
    assert before['teacher_review']['status'] == 'PENDING'
    feedback = client.post(base + '/feedback', json={**target, 'reviewer': '测试教师',
                           'comment': '请核对例题表述。', 'category': 'assessment correction', 'basis': '教学材料检查'})
    assert feedback.status_code == 200, feedback.text
    assert feedback.json()['status'] == 'SUBMITTED'
    invalid = client.post(base + '/review', json={**target, 'content_hash': 'incorrect', 'reviewer': '测试教师',
                          'decision': 'CHANGES_REQUIRED', 'basis': '需核对例题'})
    assert invalid.status_code == 409
    review = client.post(base + '/review', json={**target, 'reviewer': '测试教师',
                         'decision': 'CHANGES_REQUIRED', 'basis': '需核对例题'})
    assert review.status_code == 200, review.text
    assert review.json()['target']['content_hash'] == pinned['content_hash']
    after = client.get(base + '/materials', params={'revision_id': pinned['revision_id'], 'audience': 'teacher'}).json()
    assert after['teacher_review']['status'] == 'CHANGES_REQUIRED'
