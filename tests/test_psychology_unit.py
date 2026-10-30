"""Psychology unit contracts through the public HTTP interface."""
from fastapi.testclient import TestClient
import pytest

from pebs.server import app


def test_classical_conditioning_exposes_versioned_concepts_and_review_path():
    with TestClient(app) as client:
        response = client.get('/api/psychology/units/classical-conditioning')
    assert response.status_code == 200, response.text
    unit = response.json()
    assert unit['unit_id'] == 'classical-conditioning'
    assert unit['version']
    assert unit['teacher_review']['status'] == 'PENDING'
    concepts = {item['concept_id']: item for item in unit['concepts']}
    assert set(concepts) == {'conditioning', 'acquisition', 'extinction', 'generalization'}
    for concept in concepts.values():
        assert concept['terms']['zh-CN']['full']
        assert concept['source_refs']
        assert len(concept['misconceptions']) >= 2
        for misconception in concept['misconceptions']:
            assert misconception['basis']
            assert misconception['remediation']
            assert misconception['retest_goal']


def test_each_core_goal_has_a_diagnostic_and_followup_question():
    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
    assert len(unit['assessments']) == 10
    for concept in unit['concepts']:
        questions = [q for q in unit['assessments'] if q['concept_ref'] == concept['concept_id']]
        assert {q['kind'] for q in questions} == {'diagnostic', 'retest'}
        diagnostic = next(q for q in questions if q['kind'] == 'diagnostic')
        assert diagnostic['answer'] in diagnostic['options']
        assert diagnostic['rationale']
        assert diagnostic['misconception_ref'] in {m['misconception_id'] for m in concept['misconceptions']}
        assert diagnostic['followup_ref'] == next(q['assessment_id'] for q in questions if q['kind'] == 'retest')


def test_student_materials_exclude_teacher_fields_and_formal_export_is_blocked():
    with TestClient(app) as client:
        response = client.get('/api/psychology/units/classical-conditioning/materials?audience=student')
        assert response.status_code == 200
        materials = response.json()
        assert materials['status'] == 'draft'
        assert len(materials['questions']) == 10
        for question in materials['questions']:
            assert set(question) <= {'assessment_id', 'question', 'options', 'kind', 'option_details'}
        assert client.get('/api/psychology/units/classical-conditioning/materials?audience=teacher').json()['teacher_review']['status'] == 'PENDING'
        assert client.get('/api/psychology/units/classical-conditioning/materials?mode=formal').status_code == 409
        assert client.get('/api/psychology/units/classical-conditioning/materials?audience=invalid').status_code == 422


def test_content_package_rejects_dangling_source_references(monkeypatch, tmp_path):
    import json
    from pebs import psychology

    with TestClient(app) as client:
        original = client.get('/api/psychology/units/classical-conditioning').json()
    original['concepts'][0]['source_refs'] = ['missing-source']
    package = tmp_path / 'classical-conditioning.json'
    package.write_text(json.dumps(original), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', package)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/psychology/units/classical-conditioning')
    assert response.status_code == 503
    assert 'missing-source' in response.json()['detail']


def test_content_rejects_missing_teacher_review_contract(monkeypatch, tmp_path):
    import json
    from pebs import psychology

    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
    del unit['teacher_review']
    package = tmp_path / 'unit.json'
    package.write_text(json.dumps(unit), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', package)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/psychology/units/classical-conditioning')
    assert response.status_code == 503


def test_wrong_answer_returns_remediation_and_a_student_safe_retest():
    with TestClient(app) as client:
        response = client.post('/api/psychology/units/classical-conditioning/diagnose', json={
            'assessment_id': 'extinction-diagnostic', 'option_id': 'extinction-diagnostic-b'})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['correct'] is False
        assert result['misconception_ref'] == 'extinction-1'
        assert result['remediation']
        assert result['retest']['assessment_id'] == 'extinction-retest'
        assert 'scoring_guidance' not in result['retest']
        assert result['interpretation'] == 'needs_followup'
        invalid = client.post('/api/psychology/units/classical-conditioning/diagnose', json={
            'assessment_id': 'extinction-diagnostic', 'option_id': 'nonexistent'})
        assert invalid.status_code == 422


def test_student_can_submit_only_the_option_identifiers_in_the_materials():
    with TestClient(app) as client:
        materials = client.get('/api/psychology/units/classical-conditioning/materials').json()
        question = next(q for q in materials['questions'] if q['assessment_id'] == 'extinction-diagnostic')
        assert len(question['option_details']) == 3
        for option in question['option_details']:
            assert set(option) == {'option_id', 'text'}
            response = client.post('/api/psychology/units/classical-conditioning/diagnose', json={
                'assessment_id': question['assessment_id'], 'option_id': option['option_id']})
            assert response.status_code == 200


def test_invalid_option_mapping_is_rejected_before_a_student_answers(monkeypatch, tmp_path):
    import json
    from pebs import psychology

    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
    unit['assessments'][0]['option_details'][1]['misconception_ref'] = 'missing-misconception'
    package = tmp_path / 'unit.json'
    package.write_text(json.dumps(unit), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', package)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/psychology/units/classical-conditioning/materials')
    assert response.status_code == 503


def test_project_can_pin_a_unit_snapshot_and_read_its_revision(client):
    client.post('/api/projects', json={'project_id': 'psychology-course'})
    response = client.post('/api/projects/psychology-course/psychology/units/classical-conditioning')
    assert response.status_code == 200, response.text
    pinned = response.json()
    assert pinned['artifact_id'] == 'psychology_unit:classical-conditioning'
    assert pinned['content_hash']
    revision = client.get(f"/api/projects/psychology-course/artifacts/{pinned['artifact_id']}", params={'rev': pinned['revision_id']})
    assert revision.status_code == 200, revision.text
    assert revision.json()['content']['teacher_review']['status'] == 'PENDING'


from test_benchmark_evaluation import client  # noqa: E402,F401


def test_project_materials_use_the_frozen_revision_when_catalog_is_unavailable(client, monkeypatch, tmp_path):
    from pebs import psychology

    client.post('/api/projects', json={'project_id': 'frozen-unit'})
    pinned = client.post('/api/projects/frozen-unit/psychology/units/classical-conditioning').json()
    monkeypatch.setattr(psychology, 'CONTENT_PATH', tmp_path / 'missing.json')
    response = client.get('/api/projects/frozen-unit/psychology/units/classical-conditioning/materials',
                          params={'revision_id': pinned['revision_id'], 'audience': 'teacher'})
    assert response.status_code == 200, response.text
    assert response.json()['target']['content_hash'] == pinned['content_hash']
    assert response.json()['teacher_review']['status'] == 'PENDING'
    assert len(response.json()['questions']) == 10


def test_repeated_unit_import_reuses_identical_snapshot(client):
    client.post('/api/projects', json={'project_id': 'repeat-unit'})
    path = '/api/projects/repeat-unit/psychology/units/classical-conditioning'
    first = client.post(path).json()
    second = client.post(path).json()
    assert first['revision_id'] == second['revision_id']


def test_project_diagnosis_uses_same_revision_as_student_materials(client, monkeypatch, tmp_path):
    from pebs import psychology

    client.post('/api/projects', json={'project_id': 'answer-unit'})
    pinned = client.post('/api/projects/answer-unit/psychology/units/classical-conditioning').json()
    monkeypatch.setattr(psychology, 'CONTENT_PATH', tmp_path / 'missing.json')
    path = '/api/projects/answer-unit/psychology/units/classical-conditioning/diagnose'
    payload = {'revision_id': pinned['revision_id'], 'assessment_id': 'extinction-diagnostic',
               'option_id': 'extinction-diagnostic-b'}
    response = client.post(path, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()['target']['content_hash'] == pinned['content_hash']
    assert response.json()['correct'] is False
    client.post('/api/projects', json={'project_id': 'other-unit'})
    other = client.post('/api/projects/other-unit/psychology/units/classical-conditioning/diagnose', json=payload)
    assert other.status_code == 404


def test_teacher_feedback_is_bound_to_exact_unit_and_does_not_approve_it(client):
    client.post('/api/projects', json={'project_id': 'teacher-feedback'})
    base = '/api/projects/teacher-feedback/psychology/units/classical-conditioning'
    pinned = client.post(base).json()
    payload = {'revision_id': pinned['revision_id'], 'content_hash': pinned['content_hash'],
               'reviewer': '测试教师', 'role': 'teacher', 'comment': '消退题需要增加学习历史说明。',
               'category': 'assessment correction', 'basis': '题干需明确习得阶段。'}
    response = client.post(base + '/feedback', json=payload)
    assert response.status_code == 200, response.text
    saved = response.json()
    record = client.get('/api/projects/teacher-feedback/artifacts/' + saved['artifact_id'],
                        params={'rev': saved['revision_id']}).json()['content']
    assert record['target']['content_hash'] == pinned['content_hash']
    assert record['status'] == 'SUBMITTED'
    assert record['comment'] == payload['comment']
    materials = client.get(base + '/materials', params={'revision_id': pinned['revision_id'], 'audience': 'teacher'}).json()
    assert materials['teacher_review']['status'] == 'PENDING'
    payload['content_hash'] = 'incorrect'
    assert client.post(base + '/feedback', json=payload).status_code == 409
    payload['content_hash'] = pinned['content_hash']
    payload['role'] = 'ai'
    assert client.post(base + '/feedback', json=payload).status_code == 422


def test_feedback_decision_preserves_submission_and_requires_matching_unit(client):
    client.post('/api/projects', json={'project_id': 'feedback-decision'})
    base = '/api/projects/feedback-decision/psychology/units/classical-conditioning'
    pinned = client.post(base).json()
    submitted = client.post(base + '/feedback', json={
        'revision_id': pinned['revision_id'], 'content_hash': pinned['content_hash'],
        'reviewer': '测试教师', 'comment': '补充情境', 'category': 'case replacement', 'basis': '便于辨认刺激关系'}).json()
    payload = {'feedback_id': submitted['artifact_id'], 'decision': 'MORE_EVIDENCE',
               'expected_revision_id': submitted['revision_id'],
               'reviewer': '审核教师', 'basis': '同意在本课程加入比较情境'}
    decision = client.post(base + '/feedback/decide', json=payload)
    assert decision.status_code == 200, decision.text
    assert decision.json()['status'] == 'MORE_EVIDENCE'
    old = client.get('/api/projects/feedback-decision/artifacts/' + submitted['artifact_id'],
                     params={'rev': submitted['revision_id']}).json()['content']
    assert old['status'] == 'SUBMITTED'
    stale = client.post(base + '/feedback/decide', json=payload)
    assert stale.status_code == 409
    payload['expected_revision_id'] = decision.json()['revision_id']
    payload['decision'] = 'ACCEPTED'
    assert client.post(base + '/feedback/decide', json=payload).status_code == 409
    supplement = client.post(base + '/feedback/supplement', json={
        'feedback_id': submitted['artifact_id'], 'expected_revision_id': decision.json()['revision_id'],
        'reviewer': '测试教师', 'basis': '增加两个对照情境并说明刺激关系，作为本课程修改依据。'})
    assert supplement.status_code == 200, supplement.text
    payload['expected_revision_id'] = supplement.json()['revision_id']
    accepted = client.post(base + '/feedback/decide', json=payload)
    assert accepted.status_code == 200
    sensitive = client.post(base + '/rules', json={
        'feedback_id': submitted['artifact_id'], 'feedback_revision_id': accepted.json()['revision_id'],
        'concept_refs': ['extinction'], 'recommendation': '联系学生电话 13800138000 核对答案。',
        'reviewer': '测试教师', 'basis': '测试隐私边界。'})
    assert sensitive.status_code == 422
    candidate = client.post(base + '/rules', json={
        'feedback_id': submitted['artifact_id'], 'feedback_revision_id': accepted.json()['revision_id'],
        'concept_refs': ['extinction'], 'recommendation': '复测先交代既往习得和不再配对的条件。',
        'reviewer': '测试教师', 'basis': '由本次已采纳反馈起草，等待回归和发布审核。'})
    assert candidate.status_code == 200, candidate.text
    assert candidate.json()['status'] == 'DRAFT'
    draft_publish = client.post(base + '/rules/decide', json={
        'rule_id': candidate.json()['artifact_id'], 'expected_revision_id': candidate.json()['revision_id'],
        'decision': 'PUBLISHED', 'reviewer': '审核教师', 'basis': '未验证，不应通过。'})
    assert draft_publish.status_code == 409
    failed = client.post(base + '/rules/verify', json={
        'rule_id': candidate.json()['artifact_id'], 'expected_revision_id': candidate.json()['revision_id'],
        'reviewer': '测试教师', 'role': 'teacher', 'basis': '反例未通过，应阻止发布。',
        'cases': [
            {'kind': 'positive', 'text': '消退复测', 'passed': True, 'rationale': '范围匹配。'},
            {'kind': 'counterexample', 'text': '其他单元', 'passed': False, 'rationale': '未证明不会误套用。'}]})
    assert failed.status_code == 200
    assert failed.json()['status'] == 'VERIFICATION_FAILED'
    assert client.post(base + '/rules/decide', json={
        'rule_id': candidate.json()['artifact_id'], 'expected_revision_id': failed.json()['revision_id'],
        'decision': 'PUBLISHED', 'reviewer': '审核教师', 'basis': '失败候选不应发布。'}).status_code == 409
    verified = client.post(base + '/rules/verify', json={
        'rule_id': candidate.json()['artifact_id'], 'expected_revision_id': failed.json()['revision_id'],
        'reviewer': '测试教师', 'role': 'teacher', 'basis': '核对适用范围及反例。',
        'cases': [
            {'kind': 'positive', 'text': '消退复测需交代既往习得。', 'passed': True, 'rationale': '适用于当前单元。'},
            {'kind': 'counterexample', 'text': '介绍刺激泛化的术语题。', 'passed': True, 'rationale': '不要求套用消退的条件。'}]})
    assert verified.status_code == 200, verified.text
    assert verified.json()['status'] == 'VERIFIED'
    published = client.post(base + '/rules/decide', json={
        'rule_id': candidate.json()['artifact_id'], 'expected_revision_id': verified.json()['revision_id'],
        'decision': 'PUBLISHED', 'reviewer': '审核教师', 'basis': '同意限定在消退复测使用。'})
    assert published.status_code == 200, published.text
    active = client.get(base + '/rules', params={'revision_id': pinned['revision_id']})
    assert active.status_code == 200, active.text
    assert active.json()['rules'][0]['revision_id'] == published.json()['revision_id']
    from conftest import FakeLLM, FakeResearch, REQUEST_1, run_dynamic_build
    from pebs import server

    engine = server.get_engine('feedback-decision')
    engine.llm = FakeLLM()
    engine.research = FakeResearch()
    _, run_status = run_dynamic_build(engine, REQUEST_1 + '\n学科修订=' + pinned['revision_id'], environment='test_fixture')
    assert run_status['run']['status'] == 'succeeded'
    material_revision = engine.store.revisions_of('materials')[-1]
    frozen_materials = client.get('/api/projects/feedback-decision/artifacts/materials',
                                  params={'rev': material_revision}).json()['content']
    assert frozen_materials['psychology_rules'][0]['revision_id'] == published.json()['revision_id']
    assert any('复测先交代既往习得和不再配对的条件' in prompt for prompt in engine.llm.prompts)
    withdrawn = client.post(base + '/rules/decide', json={
        'rule_id': candidate.json()['artifact_id'], 'expected_revision_id': published.json()['revision_id'],
        'decision': 'WITHDRAWN', 'reviewer': '审核教师', 'basis': '测试撤回流程。'})
    assert withdrawn.status_code == 200
    assert withdrawn.json()['status'] == 'WITHDRAWN'
    assert client.get(base + '/rules', params={'revision_id': pinned['revision_id']}).json()['rules'] == []
    history = client.get('/api/projects/feedback-decision/artifacts/materials', params={'rev': material_revision}).json()['content']
    assert history['psychology_rules'] == frozen_materials['psychology_rules']
    wrong = client.post(base.replace('classical-conditioning', 'other') + '/feedback/decide', json=payload)
    assert wrong.status_code == 409


def test_all_eight_misconceptions_have_an_executable_remediation_path():
    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
        expected = {m['misconception_id']: m['remediation']
                    for c in unit['concepts'] for m in c['misconceptions']}
        observed = {}
        for question in unit['assessments']:
            if question['kind'] != 'diagnostic':
                continue
            for option in question['option_details']:
                if option['misconception_ref'] is None:
                    continue
                response = client.post('/api/psychology/units/classical-conditioning/diagnose', json={
                    'assessment_id': question['assessment_id'], 'option_id': option['option_id']})
                assert response.status_code == 200
                result = response.json()
                observed[result['misconception_ref']] = result['remediation']
        assert len(expected) == 8
        assert observed == expected


@pytest.mark.parametrize('planner', ['dynamic', 'static'])
@pytest.mark.parametrize('misconception_field', ['linked_misconception', 'linked_misconceptions'])
def test_course_build_consumes_explicit_frozen_unit(client, planner, misconception_field, monkeypatch, tmp_path):
    from conftest import FakeLLM, FakeResearch, REQUEST_1, run_dynamic_build, run_build
    from pebs import server

    client.post('/api/projects', json={'project_id': 'unit-build'})
    pinned = client.post('/api/projects/unit-build/psychology/units/classical-conditioning').json()
    from pebs import psychology
    monkeypatch.setattr(psychology, 'SOURCE_DIRECTORY', tmp_path / 'missing-sources')
    engine = server.get_engine('unit-build')
    class StructuredDistractors(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'assessment' and result.get('items'):
                result['items'][0]['distractors'] = [
                    {'option': 'A', misconception_field: ('把任何行为改变都归为经典条件作用'
                         if misconception_field == 'linked_misconception'
                         else ['把任何行为改变都归为经典条件作用', '忽略刺激配对']),
                     'basis': 'model_hypothesis'}]
            return result

    engine.llm = StructuredDistractors()
    engine.research = FakeResearch()
    request = REQUEST_1 + '\n学科修订=' + pinned['revision_id']
    if planner == 'dynamic':
        start, status = run_dynamic_build(engine, request, environment='test_fixture')
        changeset_id = start['changeset_id']
    else:
        run_id, changeset_id = run_build(engine, request, environment='test_fixture')
        status = engine.run_status(run_id)
    assert status['run']['status'] == 'succeeded'
    accepted = client.post(f'/api/projects/unit-build/changesets/{changeset_id}/accept')
    assert accepted.status_code == 200, accepted.text
    assert 'teaching_plan:sec1' not in accepted.json()['stale_artifacts']

    materials = client.get('/api/projects/unit-build/artifacts/materials',
                           params={'rev': engine.store.revisions_of('materials')[-1]}).json()['content']
    assert materials['psychology_target']['revision_id'] == pinned['revision_id']
    assert materials['psychology_target']['content_hash'] == pinned['content_hash']
    assert materials['budget_report']['material_chars'] > 1000
    assert any('刺激泛化' in prompt and 'model_hypothesis' in prompt for prompt in engine.llm.prompts)
    assert any('单有行为改变不足以分类' in prompt and '不等于完全没有辨别' in prompt
               for prompt in engine.llm.prompts)
    evidence = client.get('/api/projects/unit-build/evidence').json()
    assert any(source['title'] == 'Psychology 2e, 6.2 Classical Conditioning' for source in evidence['sources'])
    assert len(materials['psychology_source']['concept_anchors']) == 4
    assert materials['psychology_source']['source_version'] >= 1
    assert all(anchor['verification_status'] == 'LOCATED_ONLY'
               for anchor in materials['psychology_source']['concept_anchors'])
    assert any('来源标题：Psychology 2e, 6.2 Classical Conditioning' in prompt
               for prompt in engine.llm.prompts)
    assert any('来源标题：Psychology 2e, 6.2 Classical Conditioning' in prompt
               and 'When an organism learns to respond differently' in prompt for prompt in engine.llm.prompts)
    if planner == 'static':
        assert any('任务：为本节生成形成性评价' in prompt and 'model_hypothesis' in prompt
                   and '补救' in prompt for prompt in engine.llm.prompts)
        assert any('任务：生成一节在线课程脚本' in prompt and '无需学习' in prompt
                   and '获得引出条件反应的能力' in prompt for prompt in engine.llm.prompts)
        assessment_revision = engine.store.revisions_of('assessment:sec1')[-1]
        assessment = client.get('/api/projects/unit-build/artifacts/assessment:sec1',
                                params={'rev': assessment_revision}).json()['content']
        assert assessment['items'][0]['distractors'] == ['A']
        assert assessment['items'][0]['distractors_detail'][0]['basis'] == 'model_hypothesis'
        if misconception_field == 'linked_misconceptions':
            assert assessment['items'][0]['distractors_detail'][0]['linked_misconceptions'] == [
                '把任何行为改变都归为经典条件作用', '忽略刺激配对']


def test_downloadable_student_and_teacher_materials_use_same_frozen_revision(client):
    client.post('/api/projects', json={'project_id': 'unit-export'})
    base = '/api/projects/unit-export/psychology/units/classical-conditioning'
    pinned = client.post(base).json()
    student = client.get(base + '/export', params={'revision_id': pinned['revision_id'], 'audience': 'student'})
    assert student.status_code == 200, student.text
    assert 'attachment' in student.headers['content-disposition']
    assert '草稿—未通过 QA' in student.text
    assert pinned['content_hash'] in student.text
    assert '评分依据' not in student.text
    assert '误解关联' not in student.text
    assert '辅助缩写：US' in student.text
    teacher = client.get(base + '/export', params={'revision_id': pinned['revision_id'], 'audience': 'teacher'})
    assert teacher.status_code == 200
    assert pinned['content_hash'] in teacher.text
    assert '评分依据' in teacher.text
    assert '待真人教师审核' in teacher.text
    assert '单有行为改变不足以分类' in teacher.text
    assert 'https://openstax.org/books/psychology-2e/pages/6-2-classical-conditioning' in teacher.text
    assert '来源核验状态：PENDING' in teacher.text
    assert 'CC-BY-4.0' in teacher.text
    assert 'Access for free at openstax.org.' in teacher.text
    assert client.get(base + '/export', params={
        'revision_id': pinned['revision_id'], 'mode': 'formal'}).status_code == 409


def test_diagnostics_do_not_all_reveal_the_answer_by_option_position():
    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
    positions = {q['options'].index(q['answer']) for q in unit['assessments'] if q['kind'] == 'diagnostic'}
    assert len(positions) >= 2


def test_unit_has_hash_bound_locatable_concept_anchors():
    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
    assert len(unit['sources'][0]['snapshot_sha256']) == 64
    for concept in unit['concepts']:
        anchor = concept['evidence_anchor']
        assert anchor['source_ref'] == unit['sources'][0]['source_id']
        assert anchor['start_char'] >= 0
        assert anchor['end_char'] > anchor['start_char']
        assert len(anchor['text']) > 80, 'a keyword match is not an explanatory passage'
        assert anchor['verification_status'] == 'LOCATED_ONLY'


def test_overbudget_unit_does_not_write_a_source_snapshot(client, monkeypatch):
    from conftest import FakeLLM, FakeResearch, REQUEST_1, run_dynamic_build
    from pebs import config, server

    client.post('/api/projects', json={'project_id': 'budget-unit'})
    pinned = client.post('/api/projects/budget-unit/psychology/units/classical-conditioning').json()
    engine = server.get_engine('budget-unit')
    engine.llm = FakeLLM()
    engine.research = FakeResearch()
    monkeypatch.setitem(config.RULES, 'input_budget', {'max_material_chars': 1000, 'on_exceed': 'reject'})
    _, status = run_dynamic_build(engine, REQUEST_1 + '\n学科修订=' + pinned['revision_id'], environment='test_fixture')
    assert status['run']['status'] != 'succeeded'
    assert client.get('/api/projects/budget-unit/evidence').json()['sources'] == []


def test_diagnostic_cannot_refer_to_another_concepts_retest(monkeypatch, tmp_path):
    import json
    from pebs import psychology

    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
    question = next(q for q in unit['assessments'] if q['assessment_id'] == 'extinction-diagnostic')
    question['followup_ref'] = 'acquisition-retest'
    package = tmp_path / 'unit.json'
    package.write_text(json.dumps(unit), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', package)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/psychology/units/classical-conditioning')
    assert response.status_code == 503


def test_legacy_invalid_stored_unit_is_rejected_at_project_read_boundary(client):
    from pebs import server

    client.post('/api/projects', json={'project_id': 'legacy-invalid'})
    base = '/api/projects/legacy-invalid/psychology/units/classical-conditioning'
    pinned = client.post(base).json()
    store = server.get_engine('legacy-invalid').store
    content = store.get_revision(pinned['revision_id'])['content']
    next(q for q in content['assessments'] if q['kind'] == 'diagnostic')['followup_ref'] = 'missing'
    legacy = store.add_revision(artifact_id=pinned['artifact_id'], artifact_type='psychology_unit',
                                content=content, produced_by='legacy-import', fixture=True)
    response = client.get(base + '/materials', params={'revision_id': legacy['revision_id']})
    assert response.status_code == 409


def test_teacher_review_is_version_bound_and_does_not_release_formal_export(client):
    client.post('/api/projects', json={'project_id': 'unit-review'})
    base = '/api/projects/unit-review/psychology/units/classical-conditioning'
    pinned = client.post(base).json()
    response = client.post(base + '/review', json={
        'revision_id': pinned['revision_id'], 'content_hash': pinned['content_hash'],
        'reviewer': '测试教师', 'role': 'teacher', 'decision': 'CHANGES_REQUIRED',
        'basis': '需在复测中要求解释依据，不能只判断术语。'})
    assert response.status_code == 200, response.text
    materials = client.get(base + '/materials', params={'revision_id': pinned['revision_id'], 'audience': 'teacher'}).json()
    assert materials['teacher_review']['status'] == 'CHANGES_REQUIRED'
    assert materials['teacher_review']['target']['content_hash'] == pinned['content_hash']
    downloaded = client.get(base + '/export', params={'revision_id': pinned['revision_id'], 'audience': 'teacher'})
    assert 'CHANGES_REQUIRED' in downloaded.text
    assert '需在复测中要求解释依据' in downloaded.text
    assert materials['status'] == 'draft'
    assert client.get(base + '/export', params={'revision_id': pinned['revision_id'], 'mode': 'formal'}).status_code == 409


def test_two_queries_degrade_to_affordable_search_instead_of_skipping(client):
    from conftest import FakeLLM, FakeResearch, REQUEST_1, run_dynamic_build
    from pebs import config, server

    class TwoQueries(FakeLLM):
        def generate_json(self, **kwargs):
            if kwargs['task'] == 'research_query':
                return {'queries': ['observation evidence first query', 'observation evidence second query']}
            return super().generate_json(**kwargs)

    class TwoSources(FakeResearch):
        def sources(self):
            return ['crossref', 'openalex']

    client.post('/api/projects', json={'project_id': 'query-budget'})
    engine = server.get_engine('query-budget')
    engine.llm = TwoQueries()
    engine.research = TwoSources()
    budgets = dict(config.RULES['budgets'])
    budgets['research_requests'] = 4
    run_dynamic_build(engine, REQUEST_1, environment='test_fixture', budgets=budgets)
    assert engine.research.queries, 'remaining research budget should allow a single query'


def test_concept_cards_include_boundaries_examples_and_four_language_terms():
    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
    for concept in unit['concepts']:
        assert set(concept['terms']) == {'zh-CN', 'en', 'ja', 'ko'}
        assert concept['boundary']
        assert concept['examples']['positive']['fictional'] is True
        assert concept['examples']['counterexample']['text']
        assert set(concept['prerequisites']) <= {'conditioning', 'acquisition', 'extinction', 'generalization'}


def test_concept_prerequisite_cycle_blocks_materials(monkeypatch, tmp_path):
    import json
    from pebs import psychology

    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
    unit['concepts'][0]['prerequisites'] = ['acquisition']
    path = tmp_path / 'cycle.json'
    path.write_text(json.dumps(unit), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/psychology/units/classical-conditioning/materials')
    assert response.status_code == 503
    assert 'cycle' in response.json()['detail']


def test_empty_localized_full_term_is_rejected(monkeypatch, tmp_path):
    import json
    from pebs import psychology

    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
    unit['concepts'][0]['terms']['ja']['full'] = ''
    path = tmp_path / 'invalid-term.json'
    path.write_text(json.dumps(unit), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', path)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get('/api/psychology/units/classical-conditioning').status_code == 503


@pytest.mark.parametrize('defect', ['anchor_source', 'diagnostic_ref', 'correct_option_ref', 'embedded_approval'])
def test_catalog_rejects_audit_integrity_defects(monkeypatch, tmp_path, defect):
    import json
    from pebs import psychology

    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
    question = next(q for q in unit['assessments'] if q['kind'] == 'diagnostic')
    if defect == 'anchor_source':
        unit['concepts'][0]['evidence_anchor']['source_ref'] = 'missing'
    elif defect == 'diagnostic_ref':
        question['misconception_ref'] = 'missing'
    elif defect == 'correct_option_ref':
        next(o for o in question['option_details'] if o['text'] == question['answer'])['misconception_ref'] = 'missing'
    else:
        unit['teacher_review'] = {'status': 'APPROVED', 'reviewer': 'self', 'basis': 'self'}
    path = tmp_path / 'invalid-unit.json'
    path.write_text(json.dumps(unit), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', path)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get('/api/psychology/units/classical-conditioning').status_code == 503


def test_legacy_published_rule_without_verification_is_not_active(client):
    from pebs import server

    client.post('/api/projects', json={'project_id': 'legacy-rule'})
    base = '/api/projects/legacy-rule/psychology/units/classical-conditioning'
    pinned = client.post(base).json()
    store = server.get_engine('legacy-rule').store
    store.add_revision(artifact_id='psychology_rule:invalid', artifact_type='psychology_rule',
                       content={'status': 'PUBLISHED', 'unit_id': 'classical-conditioning',
                                'target': {'content_hash': pinned['content_hash']},
                                'concept_refs': ['missing'], 'recommendation': 'unverified'},
                       produced_by='legacy-import', fixture=True)
    response = client.get(base + '/rules', params={'revision_id': pinned['revision_id']})
    assert response.status_code == 409


def test_unspecified_word_range_is_not_sent_to_model_as_zero_words(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    client.post('/api/projects', json={'project_id': 'no-word-range'})
    engine = server.get_engine('no-word-range')
    engine.llm = FakeLLM()
    engine.research = FakeResearch()
    run_build(engine, '生成一节经典条件作用课程讲稿，不要PPT，不要动画。', environment='test_fixture')
    prompts = [p for p in engine.llm.prompts if p.startswith('任务：生成一节在线课程脚本')]
    assert prompts
    assert all('字数要求：0–0' not in p for p in prompts)


@pytest.mark.parametrize('narration', ['', '\u200b'])
def test_empty_narration_cannot_pass_g1_without_a_word_range(client, narration):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class EmptyNarration(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] in ('script', 'script_fix'):
                result['units'] = [{'unit_id': 'u1', 'kind': 'title', 'text': '空正文'},
                                   {'unit_id': 'u2', 'kind': 'narration', 'text': narration}]
            return result

    client.post('/api/projects', json={'project_id': 'empty-narration'})
    engine = server.get_engine('empty-narration')
    engine.llm = EmptyNarration()
    engine.research = FakeResearch()
    run_build(engine, '生成一节课程讲稿，不要PPT，不要动画。', environment='test_fixture')
    artifact = 'gate:G1:script:sec1'
    revision = engine.store.revisions_of(artifact)[-1]
    result = client.get('/api/projects/empty-narration/artifacts/' + artifact, params={'rev': revision}).json()['content']
    assert result['status'] == 'FAIL'
    assert any('正文为空' in issue['reason'] for issue in result['issues'])


@pytest.mark.parametrize('planner', ['static', 'dynamic'])
@pytest.mark.parametrize('language', ['zh-CN', 'en'])
def test_build_honors_no_ppt_and_no_animation(client, planner, language):
    from conftest import FakeLLM, FakeResearch, run_build, run_dynamic_build
    from pebs import server

    client.post('/api/projects', json={'project_id': 'english-constraints'})
    engine = server.get_engine('english-constraints')
    engine.llm = FakeLLM()
    engine.research = FakeResearch()
    request = ('生成课程讲稿，不要PPT，不要动画。' if language == 'zh-CN'
               else 'Create a lesson script. No PPT. No animation.')
    if planner == 'static':
        run_build(engine, request, environment='test_fixture')
    else:
        run_dynamic_build(engine, request, environment='test_fixture')
    artifacts = client.get('/api/projects/english-constraints/artifacts').json()['artifacts']
    requirements_revision = engine.store.revisions_of('requirements')[-1]
    requirements = client.get('/api/projects/english-constraints/artifacts/requirements',
                              params={'rev': requirements_revision}).json()['content']
    assert all('animation' not in section['required_components'] for section in requirements['sections'])
    assert not any(a['artifact_type'] == 'pptx_deck' for a in artifacts)
    assert 'animation_gate' not in engine.llm.calls
    for artifact in artifacts:
        if artifact['artifact_type'] == 'media_plan':
            revision = engine.store.revisions_of(artifact['artifact_id'])[-1]
            plan = client.get('/api/projects/english-constraints/artifacts/' + artifact['artifact_id'],
                              params={'rev': revision}).json()['content']
            assert not any(item['recommended_medium'] == 'animation' for item in plan['items'])


@pytest.mark.parametrize('planner', ['static', 'dynamic'])
@pytest.mark.parametrize('returned_count', [2, 5])
def test_explicit_four_questions_rejects_wrong_count(client, planner, returned_count):
    from conftest import FakeLLM, FakeResearch, run_build, run_dynamic_build
    from pebs import server

    class CountLLM(FakeLLM):
        def generate_json(self, **kwargs):
            import copy
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'assessment':
                examples = result['items']
                result['items'] = [copy.deepcopy(examples[i % len(examples)]) for i in range(returned_count)]
                for i, item in enumerate(result['items']):
                    item['assessment_id'] = f'question-{i + 1}'
            return result

    client.post('/api/projects', json={'project_id': 'question-count'})
    engine = server.get_engine('question-count')
    engine.llm = CountLLM()
    engine.research = FakeResearch()
    build = run_build if planner == 'static' else run_dynamic_build
    run_id, _ = build(engine, '生成课程讲稿和四道形成性评价题。不要PPT，不要动画。', environment='test_fixture')
    if planner == 'dynamic':
        run_id = run_id['run_id']
    assert engine.run_status(run_id)['run']['status'] == 'failed'
    assert engine.store.revisions_of('assessment:sec1') == []


@pytest.mark.parametrize('planner', ['static', 'dynamic'])
@pytest.mark.parametrize('minutes,expected_status', [(15, 'succeeded'), (20, 'failed')])
def test_explicit_lesson_duration_checks_total(client, planner, minutes, expected_status):
    from conftest import FakeLLM, FakeResearch, run_build, run_dynamic_build
    from pebs import server

    client.post('/api/projects', json={'project_id': 'lesson-duration'})
    engine = server.get_engine('lesson-duration')
    engine.llm = FakeLLM()
    engine.research = FakeResearch()
    build = run_build if planner == 'static' else run_dynamic_build
    run_id, _ = build(engine, f'生成{minutes}分钟课程教案和讲稿，不要PPT，不要动画。', environment='test_fixture')
    if planner == 'dynamic':
        run_id = run_id['run_id']
    assert engine.run_status(run_id)['run']['status'] == expected_status
    if expected_status == 'failed':
        assert engine.store.revisions_of('lesson_plan:sec1') == []
    else:
        revision = engine.store.revisions_of('lesson_plan:sec1')[-1]
        lesson = client.get('/api/projects/lesson-duration/artifacts/lesson_plan:sec1',
                            params={'rev': revision}).json()['content']
        assert [stage['minutes'] for stage in lesson['process']] == [5, 10]


@pytest.mark.parametrize('contains_answer_block', [False, True])
def test_student_export_distinguishes_reflection_from_answer_block(client, contains_answer_block):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class ReflectionLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'worksheet':
                result['reflection_questions'] = ['回看你的答案：哪些判断有观察证据？']
                if contains_answer_block:
                    result['instructions'] = '**答案：** 这里是误放入学生材料的教师答案。'
            return result

    client.post('/api/projects', json={'project_id': 'student-reflection'})
    engine = server.get_engine('student-reflection')
    engine.llm = ReflectionLLM()
    engine.research = FakeResearch()
    run_build(engine, '生成教案、学习单与讲稿，不要PPT，不要动画。', environment='test_fixture')
    revision = engine.store.revisions_of('gate:G8:export_manifest')[-1]
    gate = client.get('/api/projects/student-reflection/artifacts/gate:G8:export_manifest',
                      params={'rev': revision}).json()['content']
    assert any('包含教师答案' in issue['reason'] for issue in gate['issues']) == contains_answer_block


def test_unchanged_evidence_topup_does_not_stale_teaching_plan(client):
    import time
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    client.post('/api/projects', json={'project_id': 'evidence-idempotent'})
    engine = server.get_engine('evidence-idempotent')
    engine.llm = FakeLLM()
    engine.research = FakeResearch()
    _, changeset = run_build(engine, '生成教案和讲稿，不要PPT，不要动画。', environment='test_fixture')
    base = '/api/projects/evidence-idempotent'
    assert client.post(base + f'/changesets/{changeset}/accept').status_code == 200
    response = client.post(base + '/plan/rerun', json={'step_id': 'evidence_topup'})
    assert response.status_code == 200, response.text
    rerun = response.json()
    deadline = time.monotonic() + 30
    while engine.run_status(rerun['run_id'])['run']['status'] == 'running' and time.monotonic() < deadline:
        time.sleep(.05)
    assert engine.run_status(rerun['run_id'])['run']['status'] == 'succeeded'
    accepted = client.post(base + f"/changesets/{rerun['changeset_id']}/accept")
    assert accepted.status_code == 200, accepted.text
    assert 'teaching_plan:sec1' not in accepted.json()['stale_artifacts']

def test_script_repair_invalidates_earlier_load_review(client):
    import time
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    client.post('/api/projects', json={'project_id': 'review-revision'})
    engine = server.get_engine('review-revision')
    engine.llm = FakeLLM(undershoot_first=1)
    engine.research = FakeResearch()
    _, changeset = run_build(engine, '生成一节讲稿，每节100–200字。不要PPT，不要动画。', environment='test_fixture')
    assert len(engine.store.revisions_of('script:sec1')) == 2
    revision = engine.store.revisions_of('gate:G6:script:sec1')[-1]
    gate = client.get('/api/projects/review-revision/artifacts/gate:G6:script:sec1',
                      params={'rev': revision}).json()['content']
    assert gate['status'] in {'NEEDS_REVIEW', 'FAIL'}
    assert any('讲稿修订' in issue['reason'] for issue in gate['issues'])
    base = '/api/projects/review-revision'
    assert client.post(base + f'/changesets/{changeset}/accept').status_code == 200
    rerun = client.post(base + '/plan/rerun', json={'step_id': 'load_review'}).json()
    deadline = time.monotonic() + 30
    while engine.run_status(rerun['run_id'])['run']['status'] == 'running' and time.monotonic() < deadline:
        time.sleep(.05)
    assert engine.run_status(rerun['run_id'])['run']['status'] == 'succeeded'
    revision = engine.store.revisions_of('gate:G6:script:sec1')[-1]
    gate = client.get(base + '/artifacts/gate:G6:script:sec1', params={'rev': revision}).json()['content']
    assert not any('讲稿修订' in issue['reason'] for issue in gate['issues'])
    revision = engine.store.revisions_of('load_review:sec1')[-1]
    review = client.get(base + '/artifacts/load_review:sec1', params={'rev': revision}).json()['content']
    assert review['reviewed_script']['revision_id'] == engine.store.revisions_of('script:sec1')[-1]


def test_load_reviewer_receives_actual_lecture_text(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    marker = '审阅时必须可见的实际讲解正文'

    class TextAwareReviewer(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'load_review':
                result['cognitive_load']['reasons'] = ['已收到正文' if marker in kwargs['prompt'] else '未收到正文']
            return result

    client.post('/api/projects', json={'project_id': 'review-input'})
    engine = server.get_engine('review-input')
    engine.llm = TextAwareReviewer(extra_text=marker)
    engine.research = FakeResearch()
    run_build(engine, '生成课程讲稿，不要PPT，不要动画。', environment='test_fixture')
    revision = engine.store.revisions_of('load_review:sec1')[-1]
    review = client.get('/api/projects/review-input/artifacts/load_review:sec1',
                        params={'rev': revision}).json()['content']
    assert review['cognitive_load']['reasons'] == ['已收到正文']


def test_unit_distinguishes_unlearned_neutral_and_learned_stimuli():
    with TestClient(app) as client:
        response = client.get('/api/psychology/units/classical-conditioning')
    assert response.status_code == 200, response.text
    terms = {entry['term_id']: entry for entry in response.json()['terminology']}
    assert terms['unconditioned-stimulus']['learning_status'] == 'unlearned'
    assert '无需学习' in terms['unconditioned-stimulus']['definition']
    assert terms['unconditioned-response']['learning_status'] == 'unlearned'
    assert terms['neutral-stimulus']['learning_status'] == 'neutral'
    assert terms['conditioned-stimulus']['learning_status'] == 'learned'
    assert '获得' in terms['conditioned-stimulus']['definition']
    assert terms['conditioned-response']['learning_status'] == 'learned'
    for entry in terms.values():
        assert set(entry['terms']) == {'zh-CN', 'en', 'ja', 'ko'}
        assert entry['evidence_anchor']['text']
        assert entry['evidence_anchor']['verification_status'] == 'LOCATED_ONLY'


def test_terminology_anchor_must_match_frozen_source(monkeypatch, tmp_path):
    import json
    from pebs import psychology

    content = json.loads(psychology.CONTENT_PATH.read_text(encoding='utf-8'))
    content['terminology'][0]['evidence_anchor']['end_char'] += 1
    path = tmp_path / 'invalid-terminology.json'
    path.write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', path)
    with TestClient(app) as client:
        response = client.get('/api/psychology/units/classical-conditioning')
    assert response.status_code == 503


def test_student_handout_includes_full_terminology_without_review_fields():
    with TestClient(app) as client:
        response = client.get('/api/psychology/units/classical-conditioning/materials', params={'audience': 'student'})
    assert response.status_code == 200, response.text
    terms = {entry['term_id']: entry for entry in response.json()['terminology']}
    assert terms['unconditioned-stimulus']['terms']['zh-CN']['full'] == '无条件刺激'
    assert '无需学习' in terms['unconditioned-stimulus']['definition']
    assert 'evidence_anchor' not in terms['unconditioned-stimulus']


def test_worksheet_uses_complete_canonical_assessment(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    marker = '主评价题的唯一解析内容'

    class CanonicalAssessmentLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'assessment':
                result['items'][0]['rationale'] = marker
            if kwargs['task'] == 'worksheet':
                result['instructions'] = '已读主评价完整内容' if marker in kwargs['prompt'] else '仅有题干'
            return result

    client.post('/api/projects', json={'project_id': 'canonical-worksheet'})
    engine = server.get_engine('canonical-worksheet')
    engine.llm = CanonicalAssessmentLLM()
    engine.research = FakeResearch()
    run_build(engine, '生成教案、形成性评价、学习单与讲稿，不要PPT，不要动画。', environment='test_fixture')
    revision = engine.store.revisions_of('worksheet:sec1')[-1]
    worksheet = client.get('/api/projects/canonical-worksheet/artifacts/worksheet:sec1',
                           params={'rev': revision}).json()['content']
    assert worksheet['instructions'] == '已读主评价完整内容'
    assert worksheet['source_assessment']['revision_id'] == engine.store.revisions_of('assessment:sec1')[-1]


def test_worksheet_rejects_unknown_canonical_question_reference(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class InvalidReferenceLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'worksheet':
                result['tasks'][0]['assessment_refs'] = ['missing-question']
            return result

    client.post('/api/projects', json={'project_id': 'worksheet-reference'})
    engine = server.get_engine('worksheet-reference')
    engine.llm = InvalidReferenceLLM()
    engine.research = FakeResearch()
    run_id, _ = run_build(engine, '生成学习单与讲稿，不要PPT，不要动画。', environment='test_fixture')
    assert engine.run_status(run_id)['run']['status'] == 'failed'
    assert engine.store.revisions_of('worksheet:sec1') == []


def test_assessment_worksheet_task_exports_the_canonical_question(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    marker = '系统已保存的唯一主评价题干'
    conflicting_answer = '模型重复生成的错误答案'

    class ReferencedTaskLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'assessment':
                result['items'][0]['question'] = marker
            if kwargs['task'] == 'worksheet':
                result['tasks'] = [{'task_id': 'canonical-task', 'kind': 'practice', 'task_role': 'assessment',
                                    'assessment_refs': ['a1'], 'prompt': '完成主评价题并写出依据。',
                                    'answer': conflicting_answer}]
            return result

    client.post('/api/projects', json={'project_id': 'canonical-export'})
    engine = server.get_engine('canonical-export')
    engine.llm = ReferencedTaskLLM()
    engine.research = FakeResearch()
    run_build(engine, '生成学习单和讲稿，不要PPT，不要动画。', environment='test_fixture')
    base = '/api/projects/canonical-export'
    revision = engine.store.revisions_of('export_manifest')[-1]
    manifest = client.get(base + '/artifacts/export_manifest', params={'rev': revision}).json()['content']
    for role in ('worksheet', 'worksheet_teacher'):
        entry = next(f for f in manifest['files'] if f['role'] == role and f['kind'] == 'markdown')
        output = client.get(base + '/file', params={'path': entry['path']})
        assert output.status_code == 200, output.text
        assert marker in output.text
        assert conflicting_answer not in output.text
        if role == 'worksheet':
            assert '**答案：**' not in output.text


def test_script_receives_and_binds_canonical_teaching_materials(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    markers = ('教案唯一主线标识', '主评价唯一解析标识', '学习单唯一任务标识')

    class LinkedMaterialLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'lesson_plan':
                result['board_design'] = markers[0]
            elif kwargs['task'] == 'assessment':
                result['items'][0]['rationale'] = markers[1]
            elif kwargs['task'] == 'worksheet':
                result['instructions'] = markers[2]
            elif kwargs['task'] == 'script':
                result['units'][1]['text'] += ('完整主材料可见' if all(marker in kwargs['prompt'] for marker in markers)
                                              else '主材料缺失')
            return result

    client.post('/api/projects', json={'project_id': 'canonical-script'})
    engine = server.get_engine('canonical-script')
    engine.llm = LinkedMaterialLLM()
    engine.research = FakeResearch()
    run_build(engine, '生成教案、评价、学习单和讲稿，不要PPT，不要动画。', environment='test_fixture')
    revision = engine.store.revisions_of('script:sec1')[-1]
    script = client.get('/api/projects/canonical-script/artifacts/script:sec1',
                        params={'rev': revision}).json()['content']
    assert any('完整主材料可见' in unit['text'] for unit in script['units'])
    for kind in ('lesson_plan', 'assessment', 'worksheet'):
        assert script['source_materials'][kind]['revision_id'] == engine.store.revisions_of(kind + ':sec1')[-1]


def test_lesson_plan_rejects_a_second_lecture_body(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class DuplicateLectureLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'lesson_plan':
                result['process'][0]['teacher_activity'] = '讲稿正文：这里重新生成另一套讲解和另一套问题。'
            return result

    client.post('/api/projects', json={'project_id': 'duplicate-lecture'})
    engine = server.get_engine('duplicate-lecture')
    engine.llm = DuplicateLectureLLM()
    engine.research = FakeResearch()
    run_id, _ = run_build(engine, '生成教案和讲稿，不要PPT，不要动画。', environment='test_fixture')
    assert engine.run_status(run_id)['run']['status'] == 'failed'
    assert engine.store.revisions_of('lesson_plan:sec1') == []


@pytest.mark.parametrize('persistent', [False, True])
def test_teaching_plan_cannot_invent_claim_statuses(client, persistent):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class IncorrectStatusLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'teaching_plan' or (persistent and kwargs['task'] == 'teaching_plan_fix'):
                result['pck_notes'] = ['这些已经核验的陈述状态均为PENDING。']
            return result

    client.post('/api/projects', json={'project_id': 'claim-status-source'})
    engine = server.get_engine('claim-status-source')
    engine.llm = IncorrectStatusLLM()
    engine.research = FakeResearch()
    run_id, _ = run_build(engine, '生成教案和讲稿，不要PPT，不要动画。', environment='test_fixture')
    if persistent:
        assert engine.run_status(run_id)['run']['status'] == 'failed'
        assert engine.store.revisions_of('teaching_plan:sec1') == []
    else:
        assert engine.run_status(run_id)['run']['status'] == 'succeeded'
        revision = engine.store.revisions_of('teaching_plan:sec1')[-1]
        plan = client.get('/api/projects/claim-status-source/artifacts/teaching_plan:sec1',
                          params={'rev': revision}).json()['content']
        assert all('PENDING' not in note for note in plan['pck_notes'])
        assert plan['evidence_status']
        assert set(plan['evidence_status'].values()) == {'SUPPORTED'}


def test_assessment_status_comes_from_evidence_records(client):
    import re
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class AssessmentStatusLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'assessment':
                result['items'][0]['source_status'] = 'PENDING'
                claim = re.search(r'clm_[a-z0-9]+', kwargs['prompt'])
                if claim:
                    result['items'][0]['claim_refs'] = [claim.group() + '@v1']
            return result

    client.post('/api/projects', json={'project_id': 'assessment-status'})
    engine = server.get_engine('assessment-status')
    engine.llm = AssessmentStatusLLM()
    engine.research = FakeResearch()
    run_build(engine, '生成形成性评价与讲稿，不要PPT，不要动画。', environment='test_fixture')
    revision = engine.store.revisions_of('assessment:sec1')[-1]
    assessment = client.get('/api/projects/assessment-status/artifacts/assessment:sec1',
                            params={'rev': revision}).json()['content']
    item = assessment['items'][0]
    assert 'source_status' not in item
    assert item['evidence_status']
    assert set(item['evidence_status'].values()) == {'SUPPORTED'}


def test_student_observation_table_contains_all_requested_stages(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class ObservationTableLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'worksheet':
                result['tasks'] = [{'task_id': 'observation', 'kind': 'record_table', 'prompt': '填写观察记录。',
                                    'fields': ['观察阶段', '呈现的刺激', '观察到的反应'],
                                    'row_labels': ['配对前', '配对过程', '配对后']}]
            return result

    client.post('/api/projects', json={'project_id': 'table-stages'})
    engine = server.get_engine('table-stages')
    engine.llm = ObservationTableLLM()
    engine.research = FakeResearch()
    run_build(engine, '生成学习单与讲稿，不要PPT，不要动画。', environment='test_fixture')
    base = '/api/projects/table-stages'
    revision = engine.store.revisions_of('export_manifest')[-1]
    manifest = client.get(base + '/artifacts/export_manifest', params={'rev': revision}).json()['content']
    file = next(f for f in manifest['files'] if f['role'] == 'worksheet' and f['kind'] == 'markdown')
    output = client.get(base + '/file', params={'path': file['path']})
    assert output.status_code == 200
    for stage in ('配对前', '配对过程', '配对后'):
        assert '| ' + stage + ' |' in output.text


def test_course_worksheet_contains_the_frozen_terminology_card(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    client.post('/api/projects', json={'project_id': 'worksheet-terms'})
    base = '/api/projects/worksheet-terms'
    pinned = client.post(base + '/psychology/units/classical-conditioning').json()
    engine = server.get_engine('worksheet-terms')
    engine.llm = FakeLLM()
    engine.research = FakeResearch()
    run_build(engine, '生成学习单和讲稿，不要PPT，不要动画。学科修订=' + pinned['revision_id'], environment='test_fixture')
    revision = engine.store.revisions_of('export_manifest')[-1]
    manifest = client.get(base + '/artifacts/export_manifest', params={'rev': revision}).json()['content']
    file = next(f for f in manifest['files'] if f['role'] == 'worksheet' and f['kind'] == 'markdown')
    output = client.get(base + '/file', params={'path': file['path']})
    assert output.status_code == 200
    assert '无条件刺激' in output.text
    assert '无需学习' in output.text
    assert '辅助缩写：US' in output.text


def test_open_response_patterns_are_preserved_as_teacher_diagnostics(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    pattern = {'response_pattern': '把有限测试扩大为所有刺激',
               'linked_misconception': '过度推广未观察的刺激范围', 'basis': 'model_hypothesis'}

    class OpenResponseLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'assessment':
                item = result['items'][0]
                item['kind'] = 'reflection_prompt'
                item['question'] = '请说明对有限观察应如何限制结论。'
                item['answer'] = '开放'
                item.pop('options', None)
                item['distractors'] = [dict(pattern)]
            return result

    client.post('/api/projects', json={'project_id': 'open-response-pattern'})
    engine = server.get_engine('open-response-pattern')
    engine.llm = OpenResponseLLM()
    engine.research = FakeResearch()
    run_id, _ = run_build(engine, '生成评价、学习单和讲稿，不要PPT，不要动画。', environment='test_fixture')
    status = engine.run_status(run_id)
    assert status['run']['status'] == 'succeeded', [(s['step_id'], s.get('error')) for s in status['steps'] if s['status'] == 'FAILED']
    revision = engine.store.revisions_of('assessment:sec1')[-1]
    assessment = client.get('/api/projects/open-response-pattern/artifacts/assessment:sec1',
                            params={'rev': revision}).json()['content']
    assert assessment['items'][0]['response_patterns'] == [pattern]
    assert not assessment['items'][0].get('distractors')


@pytest.mark.parametrize('row_list', [False, True])
def test_structured_observation_answers_export_only_to_teacher(client, row_list):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class TableAnswerLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'worksheet':
                result['tasks'] = [{'task_id': 'baseline', 'kind': 'record_table',
                                   'prompt': '根据记录填写观察表。',
                                   'fields': ['观察阶段', '观察'], 'row_labels': ['配对前'],
                                   'answer': {'配对前': {'观察': '独立测试未观察到唾液反应'}}}]
                if row_list:
                    result['tasks'][0]['answer'] = [{'row_label': '配对前', '观察': '独立测试未观察到唾液反应'}]
            return result

    client.post('/api/projects', json={'project_id': 'table-answer'})
    engine = server.get_engine('table-answer')
    engine.llm, engine.research = TableAnswerLLM(), FakeResearch()
    run_id, _ = run_build(engine, '生成学习单和讲稿，不要PPT，不要动画。', environment='test_fixture')
    status = engine.run_status(run_id)
    assert status['run']['status'] == 'succeeded', [(s['step_id'], s.get('error')) for s in status['steps'] if s['status'] == 'FAILED']
    base = '/api/projects/table-answer'
    revision = engine.store.revisions_of('export_manifest')[-1]
    manifest = client.get(base + '/artifacts/export_manifest', params={'rev': revision}).json()['content']
    outputs = [client.get(base + '/file', params={'path': f['path']}).text
               for f in manifest['files'] if f['role'] == 'worksheet' and f['kind'] == 'markdown']
    assert outputs
    assert all('独立测试未观察到唾液反应' not in text for text in outputs)
    teacher_files = [f for f in manifest['files'] if 'worksheet' in f['role'] and f['kind'] == 'markdown' and f['role'] != 'worksheet']
    assert teacher_files
    teacher = client.get(base + '/file', params={'path': teacher_files[0]['path']}).text
    assert teacher.count('| 观察阶段 | 观察 |') == 2
    assert '| 配对前 | 独立测试未观察到唾液反应 |' in teacher
    assert "{'配对前'" not in teacher


def test_ordinary_english_teaching_note_is_not_a_fabricated_evidence_status(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    note = 'Students are supported by a worked example before independent practice.'

    class EnglishNoteLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] in ('teaching_plan', 'teaching_plan_fix'):
                result['pck_notes'] = [note]
            return result

    client.post('/api/projects', json={'project_id': 'english-note'})
    engine = server.get_engine('english-note')
    engine.llm, engine.research = EnglishNoteLLM(), FakeResearch()
    run_id, _ = run_build(engine, '生成课程讲稿，不要PPT，不要动画。', environment='test_fixture')
    status = engine.run_status(run_id)
    assert status['run']['status'] == 'succeeded', [(s['step_id'], s.get('error')) for s in status['steps'] if s['status'] == 'FAILED']
    revision = engine.store.revisions_of('teaching_plan:sec1')[-1]
    plan = client.get('/api/projects/english-note/artifacts/teaching_plan:sec1', params={'rev': revision}).json()['content']
    assert note in plan['pck_notes']


@pytest.mark.parametrize('bad_goal_ref', ['missing-goal', ['g1'], {'goal_id': 'g1'}])
def test_unknown_teaching_goal_cannot_be_authorized_by_model_allowed_set(client, bad_goal_ref):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class UnknownGoalLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] in ('teaching_plan', 'teaching_plan_fix'):
                result['strategies'][0].update(goal_ref=bad_goal_ref, allowed_set=['invented-strategy'],
                                               strategy='invented-strategy')
            return result

    client.post('/api/projects', json={'project_id': 'unknown-teaching-goal'})
    engine = server.get_engine('unknown-teaching-goal')
    engine.llm, engine.research = UnknownGoalLLM(), FakeResearch()
    run_id, _ = run_build(engine, '生成课程讲稿，不要PPT，不要动画。', environment='test_fixture')
    status = engine.run_status(run_id)
    step = next(s for s in status['steps'] if s['step_id'] == 'teaching_plan')
    assert step['status'] == 'FAILED'
    assert '目标引用不存在' in step['error']
    assert not engine.store.revisions_of('teaching_plan:sec1')


def test_case_edit_rebuilds_the_assessment_that_used_its_observations(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    base = '/api/projects/case-assessment-dependency'
    client.post('/api/projects', json={'project_id': 'case-assessment-dependency'})
    engine = server.get_engine('case-assessment-dependency')
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, changeset = run_build(engine, '生成案例、教案、评价、学习单和讲稿，不要PPT，不要动画。', environment='test_fixture')
    accepted = client.post(base + f'/changesets/{changeset}/accept')
    assert accepted.status_code == 200, accepted.text
    result = client.post(base + '/conversation', json={'message': '第1节案例换成大学宿舍里的情境', 'execute': False})
    assert result.status_code == 200, result.text
    patch = result.json()
    assert 'case:sec1:1' in patch['affected_artifacts']
    assert 'assessment:sec1' in patch['affected_artifacts']
    assert 'worksheet:sec1' in patch['affected_artifacts']
    assert 'script:sec1' in patch['affected_artifacts']


def test_malformed_auxiliary_abbreviation_is_rejected_before_export(monkeypatch, tmp_path):
    import json
    from pebs import psychology

    unit = json.loads(psychology.CONTENT_PATH.read_text(encoding='utf-8'))
    unit['terminology'][0]['auxiliary_abbreviations'] = [None]
    path = tmp_path / 'bad-abbreviation.json'
    path.write_text(json.dumps(unit, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(psychology, 'CONTENT_PATH', path)
    with TestClient(app) as client:
        response = client.get('/api/psychology/units/classical-conditioning')
    assert response.status_code == 503


@pytest.mark.parametrize('multiline', [False, True])
def test_load_reviewer_receives_generated_svg_source(client, multiline):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class SvgAwareReviewer(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if multiline and kwargs['task'] in ('diagram_svg', 'diagram_svg_fix'):
                for diagram in result['diagrams']:
                    diagram['svg'] = diagram['svg'].replace('><', '>\n<')
            if kwargs['task'] == 'load_review':
                result['cognitive_load']['reasons'] = ['已收到实际SVG' if '<svg ' in kwargs['prompt'] and '直接观察' in kwargs['prompt'] else 'SVG缺失']
            return result

    base = '/api/projects/review-svg'
    client.post('/api/projects', json={'project_id': 'review-svg'})
    engine = server.get_engine('review-svg')
    engine.llm, engine.research = SvgAwareReviewer(), FakeResearch()
    run_id, _ = run_build(engine, '生成课程讲稿和静态图示，不要PPT，不要动画。', environment='test_fixture')
    status = engine.run_status(run_id)
    assert status['run']['status'] == 'succeeded', [(s['step_id'], s.get('error')) for s in status['steps'] if s['status'] == 'FAILED']
    revision = engine.store.revisions_of('load_review:sec1')[-1]
    review = client.get(base + '/artifacts/load_review:sec1', params={'rev': revision}).json()['content']
    assert review['cognitive_load']['reasons'] == ['已收到实际SVG']


def test_assessment_does_not_create_a_second_lesson_or_lecture(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class ExtraCourseLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'assessment':
                result['teacher_script'] = {'text': '第二套讲稿不应成为课程输入'}
                result['lesson_plan'] = {'activities': ['第二套课堂流程']}
            if kwargs['task'] == 'worksheet':
                result['instructions'] = '发现重复课程' if '第二套讲稿不应成为课程输入' in kwargs['prompt'] else '只使用主评价'
            return result

    base = '/api/projects/assessment-scope'
    client.post('/api/projects', json={'project_id': 'assessment-scope'})
    engine = server.get_engine('assessment-scope')
    engine.llm, engine.research = ExtraCourseLLM(), FakeResearch()
    run_id, _ = run_build(engine, '生成评价、教案、学习单和讲稿，不要PPT，不要动画。', environment='test_fixture')
    status = engine.run_status(run_id)
    assert status['run']['status'] == 'succeeded', [(s['step_id'], s.get('error')) for s in status['steps'] if s['status'] == 'FAILED']
    revision = engine.store.revisions_of('assessment:sec1')[-1]
    assessment = client.get(base + '/artifacts/assessment:sec1', params={'rev': revision}).json()['content']
    assert 'teacher_script' not in assessment
    assert 'lesson_plan' not in assessment
    revision = engine.store.revisions_of('worksheet:sec1')[-1]
    worksheet = client.get(base + '/artifacts/worksheet:sec1', params={'rev': revision}).json()['content']
    assert worksheet['instructions'] == '只使用主评价'


@pytest.mark.parametrize('unknown_question', [False, True])
def test_structured_diagnostic_guidance_is_preserved_for_the_teacher(client, unknown_question):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    guidance = {'administration': '仅在指定错误出现时启动补救分支',
                'decision_rules': [{'assessment_ref': 'a1', 'trigger': '选择错误选项', 'action': '先追问依据，再使用对应复测'}],
                'interpretation_boundary': '一次答错不能形成稳定学生标签'}
    if unknown_question:
        guidance['decision_rules'][0]['assessment_ref'] = 'missing-question'

    class GuidanceLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'assessment':
                result['diagnostic_use'] = guidance
            return result

    base = '/api/projects/structured-diagnostic-guidance'
    client.post('/api/projects', json={'project_id': 'structured-diagnostic-guidance'})
    engine = server.get_engine('structured-diagnostic-guidance')
    engine.llm, engine.research = GuidanceLLM(), FakeResearch()
    run_id, _ = run_build(engine, '生成评价、学习单和讲稿，不要PPT，不要动画。', environment='test_fixture')
    status = engine.run_status(run_id)
    if unknown_question:
        step = next(step for step in status['steps'] if step['step_id'] == 'assessments')
        assert step['status'] == 'FAILED'
        assert '诊断说明引用' in step['error']
        assert not engine.store.revisions_of('assessment:sec1')
        return
    assert status['run']['status'] == 'succeeded', [(s['step_id'], s.get('error')) for s in status['steps'] if s['status'] == 'FAILED']
    revision = engine.store.revisions_of('assessment:sec1')[-1]
    assessment = client.get(base + '/artifacts/assessment:sec1', params={'rev': revision}).json()['content']
    assert assessment['diagnostic_use'] == guidance
    revision = engine.store.revisions_of('export_manifest')[-1]
    manifest = client.get(base + '/artifacts/export_manifest', params={'rev': revision}).json()['content']
    for file in manifest['files']:
        if file['role'] not in ('worksheet', 'worksheet_teacher') or file['kind'] != 'markdown':
            continue
        output = client.get(base + '/file', params={'path': file['path']}).text
        if file['role'] == 'worksheet_teacher':
            assert guidance['administration'] in output
            assert guidance['decision_rules'][0]['action'] in output
            assert guidance['interpretation_boundary'] in output
        else:
            assert all(text not in output for text in (guidance['administration'], guidance['decision_rules'][0]['action'], guidance['interpretation_boundary']))


@pytest.mark.parametrize('missing_answer', [False, True])
def test_legacy_retest_is_bound_to_its_answer_before_worksheet_export(client, missing_answer):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    question, answer = '在新情境中说明哪项观察支持学习后的变化。', '比较同一目标反应的学习前后记录，不能补造未给观察。'

    class LegacyRetestLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'assessment':
                result['items'][0]['retest_question'] = question
                if not missing_answer:
                    result['items'][0]['retest_answer'] = answer
                    result['items'][0]['retest_rationale'] = None
                    result['items'][0]['retest_options'] = None
            if kwargs['task'] == 'worksheet':
                result['tasks'] = [{'task_id': 'canonical', 'kind': 'practice', 'prompt': '完成主问题。',
                                    'task_role': 'assessment', 'assessment_refs': ['a1']}]
            return result

    base = '/api/projects/legacy-retest'
    client.post('/api/projects', json={'project_id': 'legacy-retest'})
    engine = server.get_engine('legacy-retest')
    engine.llm, engine.research = LegacyRetestLLM(), FakeResearch()
    run_id, _ = run_build(engine, '生成评价、学习单和讲稿，不要PPT，不要动画。', environment='test_fixture')
    status = engine.run_status(run_id)
    if missing_answer:
        step = next(s for s in status['steps'] if s['step_id'] == 'assessments')
        assert step['status'] == 'FAILED'
        assert '复测题缺少答案' in step['error']
        assert not engine.store.revisions_of('assessment:sec1')
        return
    assert status['run']['status'] == 'succeeded', [(s['step_id'], s.get('error')) for s in status['steps'] if s['status'] == 'FAILED']
    revision = engine.store.revisions_of('assessment:sec1')[-1]
    assessment = client.get(base + '/artifacts/assessment:sec1', params={'rev': revision}).json()['content']
    assert assessment['items'][0]['retest_question'] == {'question': question, 'answer': answer}
    assert 'retest_answer' not in assessment['items'][0]
    revision = engine.store.revisions_of('export_manifest')[-1]
    manifest = client.get(base + '/artifacts/export_manifest', params={'rev': revision}).json()['content']
    for file in manifest['files']:
        if file['kind'] == 'markdown' and file['role'] in ('worksheet', 'worksheet_teacher'):
            output = client.get(base + '/file', params={'path': file['path']}).text
            assert (answer in output) == (file['role'] == 'worksheet_teacher')


def test_diagram_uses_frozen_terminology_and_actual_observations(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    observations = '六次结果依次为：有、有、有、无、无、无；未记录反应强度'
    narration = '只比较是否出现目标反应，不据此绘制强度曲线'

    class GroundedDiagramLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'case':
                result['text'] += '。' + observations
            if kwargs['task'] in ('script', 'script_fix'):
                next(unit for unit in result['units'] if unit['kind'] == 'narration')['text'] += narration
            if kwargs['task'] in ('diagram_svg', 'diagram_svg_fix'):
                grounded = all(text in kwargs['prompt'] for text in (observations, narration, '无需学习'))
                result['diagrams'][0]['svg'] = "<svg viewBox='0 0 960 540'><text x='20' y='40'>" + ('有、有、有、无、无、无' if grounded else '缺少实际教学输入') + '</text></svg>'
            return result

    base = '/api/projects/grounded-diagram'
    client.post('/api/projects', json={'project_id': 'grounded-diagram'})
    pinned = client.post(base + '/psychology/units/classical-conditioning').json()
    engine = server.get_engine('grounded-diagram')
    engine.llm, engine.research = GroundedDiagramLLM(), FakeResearch()
    run_id, _ = run_build(engine, '生成讲稿和静态图示，不要PPT，不要动画。学科修订=' + pinned['revision_id'], environment='test_fixture')
    status = engine.run_status(run_id)
    assert status['run']['status'] == 'succeeded', [(s['step_id'], s.get('error')) for s in status['steps'] if s['status'] == 'FAILED']
    revision = engine.store.revisions_of('diagrams:sec1')[-1]
    diagrams = client.get(base + '/artifacts/diagrams:sec1', params={'rev': revision}).json()['content']['diagrams']
    svg = client.get(base + '/file', params={'path': diagrams[0]['svg_path']})
    assert svg.status_code == 200
    assert '有、有、有、无、无、无' in svg.text


def test_accepted_export_manifest_paths_remain_downloadable(client, tmp_path):
    import hashlib
    from pathlib import Path
    from conftest import FakeLLM, FakeResearch, run_build, REQUEST_1
    from pebs import server

    base = '/api/projects/published-download'
    client.post('/api/projects', json={'project_id': 'published-download'})
    engine = server.get_engine('published-download')
    engine.llm, engine.research = FakeLLM(animation_item=False), FakeResearch()
    _, changeset = run_build(engine, REQUEST_1 + ' 不要PPT，不要动画。')
    revision = engine.store.revisions_of('export_manifest')[-1]
    manifest = client.get(base + '/artifacts/export_manifest', params={'rev': revision}).json()['content']
    gate_revision = engine.store.revisions_of('gate:G6:script:sec1')[-1]
    gate = client.get(base + '/artifacts/gate:G6:script:sec1', params={'rev': gate_revision}).json()['content']
    assert manifest['mode'] == 'formal', [issue['reason'] for issue in gate['issues']]
    accepted = client.post(base + f'/changesets/{changeset}/accept')
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['published']
    for file in manifest['files']:
        response = client.get(base + '/file', params={'path': file['path']})
        assert response.status_code == 200, file['path']
        assert hashlib.sha256(response.content).hexdigest() == file['sha256']
    published = Path(accepted.json()['published'][0]).resolve()
    assert published.is_relative_to(tmp_path.resolve())
    published.write_bytes(b'changed after publication')
    original = next(file for file in manifest['files']
                    if f"{changeset}_{Path(file['path']).name}" == published.name)
    response = client.get(base + '/file', params={'path': original['path']})
    assert response.status_code == 200
    assert hashlib.sha256(response.content).hexdigest() == original['sha256']


def test_generalization_bank_questions_state_the_test_stimulus_training_history():
    with TestClient(app) as client:
        response = client.get('/api/psychology/units/classical-conditioning')
    assert response.status_code == 200, response.text
    questions = {item['assessment_id']: item for item in response.json()['assessments']}
    diagnostic = questions['generalization-diagnostic']['question']
    assert '1100赫兹音调从未与食物配对' in diagnostic
    assert '配对前' in diagnostic and '配对后' in diagnostic
    retest = questions['generalization-retest']['question']
    assert '从未与食物配对' in retest
    assert '配对前' in retest and '配对后' in retest


def test_conditioning_bank_explicitly_stipulates_the_unlearned_reflex():
    with TestClient(app) as client:
        unit = client.get('/api/psychology/units/classical-conditioning').json()
    questions = {item['assessment_id']: item for item in unit['assessments']}
    for question_id in ('conditioning-diagnostic', 'conditioning-retest'):
        assert '未经学习的反射' in questions[question_id]['question']
    concept = next(c for c in unit['concepts'] if c['concept_id'] == 'conditioning')
    assert '配对前有效' in concept['boundary']
    assert '未经学习' in concept['examples']['positive']['text']


def test_case_generation_receives_the_users_exact_observation_record(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    observation = '六次结果为：有、有、有、无、无、无；次数与顺序不得改写'

    class UserCaseLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'case' and observation in kwargs['prompt']:
                result['text'] = '虚构教学记录。' + observation
            return result

    base = '/api/projects/user-observation'
    client.post('/api/projects', json={'project_id': 'user-observation'})
    engine = server.get_engine('user-observation')
    engine.llm, engine.research = UserCaseLLM(), FakeResearch()
    run_build(engine, '生成案例与讲稿，不要PPT，不要动画。用户给定虚构观察：' + observation, environment='test_fixture')
    revision = engine.store.revisions_of('case:sec1:1')[-1]
    case = client.get(base + '/artifacts/case:sec1:1', params={'rev': revision}).json()['content']
    assert observation in case['text']

