from test_benchmark_evaluation import client  # noqa: F401


def test_conversation_preserves_specified_case_and_assessment(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'preserve-course-artifacts'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, changeset = run_build(engine, '生成教案和学习单，不要PPT，不要动画。', environment='test_fixture')
    assert client.post(base + f'/changesets/{changeset}/accept').status_code == 200
    result = client.post(base + '/conversation', json={
        'message': '修改第1节教案和讲稿，保留案例和评价题不变：调整教案时间。不要动画。', 'execute': False,
    })
    assert result.status_code == 200, result.text
    plan = result.json()
    assert 'lesson_plan:sec1' in plan['affected_artifacts']
    assert 'script:sec1' in plan['affected_artifacts']
    for artifact in ['case:sec1:1', 'assessment:sec1']:
        assert artifact in plan['locked_artifacts']
        assert artifact not in plan['affected_artifacts']
    assert 'cases' not in plan['step_order']
    assert 'assessments' not in plan['step_order']
    assert 'storyboard:sec1' in plan['affected_artifacts']
    assert 'storyboard:sec1' not in plan['locked_artifacts']
    before = {artifact: engine.store.accepted_rev_id(artifact)
              for artifact in ['case:sec1:1', 'assessment:sec1']}
    result = client.post(base + '/conversation', json={
        'message': '修改第1节教案和讲稿，保留案例和评价题不变：调整教案时间。不要动画。', 'execute': True,
    })
    assert result.status_code == 200, result.text
    operation = result.json()
    assert operation['run_status'] == 'succeeded', operation
    assert engine.store.is_locked('case:sec1:1')
    preview = client.post(base + '/conversation', json={
        'message': '修改第1节讲稿，保留案例不变。', 'execute': False,
    })
    assert preview.status_code == 409, preview.text
    accepted = client.post(base + f"/changesets/{operation['changeset_id']}/accept")
    assert accepted.status_code == 200, accepted.text
    assert not engine.store.is_locked('case:sec1:1')
    assert all(engine.store.accepted_rev_id(artifact) == revision for artifact, revision in before.items())


def test_conversation_preserves_claims_and_evidence_when_revising_case(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server
    project = 'preserve-evidence-for-case'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, cs = run_build(engine, '生成教案和学习单，不要PPT，不要动画。', environment='test_fixture')
    assert client.post(base + f'/changesets/{cs}/accept').status_code == 200
    message = '修改第1节案例，明确记录时点。保留主张和证据索引不变。'
    plan = client.post(base + '/conversation', json={'message': message, 'execute': False})
    assert plan.status_code == 200, plan.text
    for artifact in ('claims', 'evidence_index'):
        assert artifact in plan.json()['locked_artifacts']
        assert artifact not in plan.json()['affected_artifacts']
    assert 'claims' not in plan.json()['step_order'] and 'evidence' not in plan.json()['step_order']
    before = {a: engine.store.accepted_rev_id(a) for a in ('claims', 'evidence_index', 'case:sec1:1')}
    result = client.post(base + '/conversation', json={'message': message, 'execute': True})
    assert result.status_code == 200, result.text
    assert result.json()['run_status'] == 'succeeded', result.text
    assert client.post(base + '/changesets/' + result.json()['changeset_id'] + '/accept').status_code == 200
    assert all(engine.store.accepted_rev_id(a) == before[a] for a in ('claims', 'evidence_index'))
    assert engine.store.accepted_rev_id('case:sec1:1') != before['case:sec1:1']
