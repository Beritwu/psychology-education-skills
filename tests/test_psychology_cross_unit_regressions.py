"""Public regressions found during multi-unit cross audit."""

import json

import pytest
from fastapi.testclient import TestClient
from pebs.server import app
from test_benchmark_evaluation import client  # noqa: F401


@pytest.mark.parametrize(('unit_id', 'title'), [
    ('operant-conditioning', '操作性条件作用'),
    ('research-methods', '心理学研究方法'),
])
def test_export_heading_names_the_selected_unit(client, unit_id, title):
    project = 'title-' + unit_id
    client.post('/api/projects', json={'project_id': project})
    base = f'/api/projects/{project}/psychology/units/{unit_id}'
    pinned = client.post(base).json()
    exported = client.get(base + '/export', params={'revision_id': pinned['revision_id']})
    assert exported.status_code == 200, exported.text
    assert exported.text.splitlines()[0] == '# ' + title + '学习材料'


def test_missing_diagnostic_followup_is_reported_as_invalid_content(monkeypatch, tmp_path):
    from pebs import psychology
    with TestClient(app) as client:
        content = client.get('/api/psychology/units/classical-conditioning').json()
    content['assessments'][0]['followup_ref'] = None
    path = tmp_path / 'classical-conditioning.json'
    path.write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/psychology/units/classical-conditioning')
    assert response.status_code == 503, response.text


@pytest.mark.parametrize('mutation', ['identity', 'source_attribution'])
def test_catalog_rejects_mislabeled_unit_or_unpinned_anchor_source(monkeypatch, tmp_path, mutation):
    from pebs import psychology
    with TestClient(app) as client:
        content = client.get('/api/psychology/units/classical-conditioning').json()
    if mutation == 'identity':
        content['unit_id'] = 'operant-conditioning'
    else:
        content['sources'].append({'source_id': 'unverified-other', 'url': 'https://example.org/source',
                                   'verification_status': 'PENDING'})
        content['concepts'][0]['source_refs'] = ['unverified-other']
        content['concepts'][0]['evidence_anchor']['source_ref'] = 'unverified-other'
    path = tmp_path / 'classical-conditioning.json'
    path.write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/psychology/units/classical-conditioning')
    assert response.status_code == 503, response.text


def test_student_export_keeps_retest_options(client, monkeypatch, tmp_path):
    from pebs import psychology

    content = client.get('/api/psychology/units/classical-conditioning').json()
    retest = next(item for item in content['assessments'] if item['kind'] == 'retest')
    retest['options'] = ['选择甲', '选择乙']
    path = tmp_path / 'classical-conditioning.json'
    path.write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', path)
    client.post('/api/projects', json={'project_id': 'retest-options'})
    base = '/api/projects/retest-options/psychology/units/classical-conditioning'
    pinned = client.post(base)
    assert pinned.status_code == 200, pinned.text
    exported = client.get(base + '/export', params={'revision_id': pinned.json()['revision_id']})
    assert exported.status_code == 200, exported.text
    assert '选择甲' in exported.text and '选择乙' in exported.text


@pytest.mark.parametrize('unit_id', ['operant-conditioning', 'research-methods'])
def test_student_materials_include_each_units_full_terminology(unit_id):
    with TestClient(app) as client:
        response = client.get(f'/api/psychology/units/{unit_id}/materials?audience=student')
    assert response.status_code == 200, response.text
    terms = response.json()['terminology']
    assert len(terms) >= 4
    for term in terms:
        assert term['definition']
        assert all(term['terms'][lang]['full'] for lang in ('zh-CN', 'en', 'ja', 'ko'))


def test_remediation_retest_keeps_student_options_without_scoring(monkeypatch, tmp_path):
    from pebs import psychology
    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
    retest = next(q for q in unit['assessments'] if q['assessment_id'] == 'extinction-retest')
    retest['options'] = ['选项甲', '选项乙']
    path = tmp_path / 'classical-conditioning.json'
    path.write_text(json.dumps(unit, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', path)
    with TestClient(app) as client:
        result = client.post('/api/psychology/units/classical-conditioning/diagnose', json={
            'assessment_id': 'extinction-diagnostic', 'option_id': 'extinction-diagnostic-b'})
    assert result.status_code == 200, result.text
    assert result.json()['retest']['options'] == ['选项甲', '选项乙']
    assert 'scoring_guidance' not in result.json()['retest']


def test_teacher_review_cannot_rebind_a_revision_to_a_different_unit(client):
    project = 'cross-unit-review'
    client.post('/api/projects', json={'project_id': project})
    base = f'/api/projects/{project}/psychology/units'
    operant = client.post(base + '/operant-conditioning').json()
    client.post(base + '/research-methods')
    response = client.post(base + '/research-methods/review', json={
        'revision_id': operant['revision_id'], 'content_hash': operant['content_hash'],
        'reviewer': '测试教师', 'decision': 'CHANGES_REQUIRED', 'basis': '隔离测试'})
    assert response.status_code == 409, response.text


def test_assessment_task_discards_model_placeholder_answer_before_binding(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class WorksheetWithPlaceholder(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'worksheet':
                result['tasks'] = [{'task_id': 't1', 'kind': 'sorting', 'prompt': '依据评价题作答。',
                                    'task_role': 'assessment', 'assessment_refs': ['a1'],
                                    'answer': {'关联': '请引用主评价的答案'}}]
            return result

    client.post('/api/projects', json={'project_id': 'worksheet-placeholder'})
    engine = server.get_engine('worksheet-placeholder')
    engine.llm, engine.research = WorksheetWithPlaceholder(), FakeResearch()
    run_id, _ = run_build(engine, '生成学习单和讲稿，不要PPT，不要动画。', environment='test_fixture')
    status = engine.run_status(run_id)
    assert status['run']['status'] == 'succeeded', [(s['step_id'], s.get('error')) for s in status['steps'] if s['status'] == 'FAILED']
    revision = engine.store.revisions_of('worksheet:sec1')[-1]
    worksheet = client.get('/api/projects/worksheet-placeholder/artifacts/worksheet:sec1', params={'rev': revision}).json()['content']
    task = worksheet['tasks'][0]
    assert 'answer' not in task
    assert task['canonical_questions'][0]['assessment_id'] == 'a1'


def test_practice_answer_mapping_exports_only_to_teacher(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class PracticeMapping(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'worksheet':
                result['tasks'] = [{'task_id': 't1', 'kind': 'sorting', 'prompt': '比较两项。',
                                    'answer': {'相关判断': '只支持关联', '分配判断': '随机分配不等于抽样'}}]
            return result

    client.post('/api/projects', json={'project_id': 'worksheet-mapping'})
    engine = server.get_engine('worksheet-mapping')
    engine.llm, engine.research = PracticeMapping(), FakeResearch()
    run_id, _ = run_build(engine, '生成学习单和讲稿，不要PPT，不要动画。', environment='test_fixture')
    status = engine.run_status(run_id)
    assert status['run']['status'] == 'succeeded', [(s['step_id'], s.get('error')) for s in status['steps'] if s['status'] == 'FAILED']
    revision = engine.store.revisions_of('export_manifest')[-1]
    base = '/api/projects/worksheet-mapping'
    manifest = client.get(base + '/artifacts/export_manifest', params={'rev': revision}).json()['content']
    files = [f for f in manifest['files'] if 'worksheet' in f['role'] and f['kind'] == 'markdown']
    student = next(client.get(base + '/file', params={'path': f['path']}).text for f in files if f['role'] == 'worksheet')
    teacher = next(client.get(base + '/file', params={'path': f['path']}).text for f in files if f['role'] != 'worksheet')
    assert '只支持关联' not in student and '随机分配不等于抽样' not in student
    assert '只支持关联' in teacher and '随机分配不等于抽样' in teacher
