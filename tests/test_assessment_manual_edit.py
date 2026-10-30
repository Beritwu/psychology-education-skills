from test_api import client  # noqa: F401


def test_teacher_can_revise_one_assessment_without_rewriting_other_items(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'manual-assessment-revision'
    base = '/api/projects/' + project
    assert client.post('/api/projects', json={'project_id': project}).status_code == 200
    engine = server.get_engine(project)
    class TwoItemLLM(FakeLLM):
        def generate_json(self, *, task, system, prompt, temperature=None, timeout=None):
            import copy
            result = super().generate_json(task=task, system=system, prompt=prompt,
                                           temperature=temperature, timeout=timeout)
            if task == 'assessment':
                second = copy.deepcopy(result['items'][0])
                second['assessment_id'] = 'a2'
                result['items'].append(second)
            return result

    engine.llm, engine.research = TwoItemLLM(), FakeResearch()
    _, changeset = run_build(engine, '生成教案和学习单，不要PPT，不要动画。', environment='test_fixture')
    assert client.post(base + f'/changesets/{changeset}/accept').status_code == 200
    original = client.get(base + '/artifacts/assessment:sec1').json()
    items = original['content']['items']
    assert len(items) >= 2
    target = items[0]['assessment_id']
    revised_answer = '教师修订：按题干记录判断，缺少的事实保持待核验。'
    payload = {'assessment_id': target, 'expected_revision': original['revision_id'],
               'fields': {'answer': revised_answer}}
    res = client.post(base + '/assessment-edit/sec1', json=payload)
    assert res.status_code == 200, res.text
    candidate = res.json()
    assert client.get(base + '/artifacts/assessment:sec1').json() == original
    assert client.post(base + '/changesets/' + candidate['changeset_id'] + '/accept').status_code == 200
    updated = client.get(base + '/artifacts/assessment:sec1').json()
    assert updated['revision_id'] != original['revision_id']
    assert updated['content']['items'][0]['answer'] == revised_answer
    assert updated['content']['items'][1:] == items[1:]
    assert client.post(base + '/assessment-edit/sec1', json=payload).status_code == 409
    artifacts = client.get(base + '/artifacts').json()['artifacts']
    assert any(a['artifact_id'] == 'worksheet:sec1' and a['stale'] for a in artifacts)


def test_assessment_edit_rejects_invalid_fields_and_locked_artifacts(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'assessment-edit-validation'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, changeset = run_build(engine, '生成教案和学习单，不要PPT，不要动画。', environment='test_fixture')
    assert client.post(base + f'/changesets/{changeset}/accept').status_code == 200
    original = client.get(base + '/artifacts/assessment:sec1').json()
    item = original['content']['items'][0]['assessment_id']
    payload = {'assessment_id': item, 'expected_revision': original['revision_id']}
    bad = client.post(base + '/assessment-edit/sec1', json={**payload, 'fields': {'assessment_id': 'another'}})
    assert bad.status_code == 400, bad.text
    invalid = client.post(base + '/assessment-edit/sec1', json={**payload, 'fields': {'answer': []}})
    assert invalid.status_code == 400, invalid.text
    missing = client.post(base + '/assessment-edit/sec1', json={**payload, 'assessment_id': 'missing', 'fields': {'answer': 'B'}})
    assert missing.status_code == 400, missing.text
    engine.store.set_locked('assessment:sec1', True)
    locked = client.post(base + '/assessment-edit/sec1', json={**payload, 'fields': {'answer': 'B'}})
    assert locked.status_code == 409, locked.text
    assert client.get(base + '/artifacts/assessment:sec1').json() == original


def test_assessment_edit_preserves_fixture_environment(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'assessment-edit-fixture'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, changeset = run_build(engine, '生成教案和学习单，不要PPT，不要动画。', environment='test_fixture')
    assert client.post(base + f'/changesets/{changeset}/accept').status_code == 200
    old = client.get(base + '/artifacts/assessment:sec1').json()
    res = client.post(base + '/assessment-edit/sec1', json={
        'assessment_id': old['content']['items'][0]['assessment_id'],
        'expected_revision': old['revision_id'], 'fields': {'answer': '修订答案'},
    })
    assert res.status_code == 200, res.text
    assert client.post(base + '/changesets/' + res.json()['changeset_id'] + '/accept').status_code == 200
    revision = engine.store.get_revision(res.json()['revision_id'])
    assert revision['fixture'] == 1
    response = client.post(base + '/export', json={'mode': 'formal'})
    assert response.status_code == 200, response.text
    assert response.json()['ok'] is False or response.json().get('mode') == 'draft'


def test_assessment_edit_cannot_accept_after_its_case_changes(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'assessment-edit-stale-upstream'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, cs = run_build(engine, '生成教案和学习单，不要PPT，不要动画。', environment='test_fixture')
    assert client.post(base + '/changesets/' + cs + '/accept').status_code == 200
    old = client.get(base + '/artifacts/assessment:sec1').json()
    edit = client.post(base + '/assessment-edit/sec1', json={
        'assessment_id': old['content']['items'][0]['assessment_id'],
        'expected_revision': old['revision_id'], 'fields': {'answer': '修订答案'},
    })
    assert edit.status_code == 200, edit.text
    replacement = client.post(base + '/case-replace', json={
        'case_artifact_id': 'case:sec1:1', 'instruction': '修改案例中的课堂情境。',
    })
    assert replacement.status_code == 200, replacement.text
    accepted = client.post(base + '/changesets/' + replacement.json()['changeset_id'] + '/accept')
    assert accepted.status_code == 200, accepted.text
    conflict = client.post(base + '/changesets/' + edit.json()['changeset_id'] + '/accept')
    assert conflict.status_code == 200 and conflict.json()['ok'] is False, conflict.text
    assert 'stale' in conflict.json()['reason']
    assert client.get(base + '/artifacts/assessment:sec1').json()['revision_id'] == old['revision_id']


def test_two_edits_from_same_baseline_cannot_overwrite_each_other(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'assessment-edit-conflicting-candidates'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, cs = run_build(engine, '生成教案和学习单，不要PPT，不要动画。', environment='test_fixture')
    assert client.post(base + '/changesets/' + cs + '/accept').status_code == 200
    old = client.get(base + '/artifacts/assessment:sec1').json()
    payload = {'assessment_id': old['content']['items'][0]['assessment_id'], 'expected_revision': old['revision_id']}
    first = client.post(base + '/assessment-edit/sec1', json={**payload, 'fields': {'answer': '修订甲'}})
    second = client.post(base + '/assessment-edit/sec1', json={**payload, 'fields': {'answer': '修订乙'}})
    assert first.status_code == second.status_code == 200
    a = client.post(base + '/changesets/' + first.json()['changeset_id'] + '/accept')
    assert a.status_code == 200 and a.json().get('status') == 'accepted'
    b = client.post(base + '/changesets/' + second.json()['changeset_id'] + '/accept')
    assert b.status_code == 200 and b.json()['ok'] is False
    assert client.get(base + '/artifacts/assessment:sec1').json()['content']['items'][0]['answer'] == '修订甲'
