import pytest

from test_benchmark_evaluation import client  # noqa: F401


def test_conversation_keeps_original_media_exclusions(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'conversation-preserves-media-exclusions'
    base = '/api/projects/' + project
    assert client.post('/api/projects', json={'project_id': project}).status_code == 200
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, changeset = run_build(engine, '生成教案和学习单，不要PPT，不要动画。', environment='test_fixture')
    assert client.post(base + f'/changesets/{changeset}/accept').status_code == 200
    result = client.post(base + '/conversation', json={
        'message': '修改第1节教案和讲稿，调整教学时间。', 'execute': True,
    })
    assert result.status_code == 200, result.text
    assert result.json()['run_status'] == 'succeeded', result.text
    assert client.post(base + '/changesets/' + result.json()['changeset_id'] + '/accept').status_code == 200
    plan = client.get(base + '/artifacts/media_plan:sec1')
    assert plan.status_code == 200, plan.text
    assert all(item['recommended_medium'] != 'animation' for item in plan.json()['content']['items'])
    decisions = client.get(base + '/artifacts/animation_decisions:sec1')
    assert decisions.status_code == 200, decisions.text
    assert not decisions.json()['content']['decisions']
    assert client.get(base + '/artifacts/pptx_deck').status_code == 404


@pytest.mark.parametrize("restriction", ["不要生成动画", "不要使用动画", "无需动画"])
def test_conversation_recognizes_do_not_generate_animation(client, restriction):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'conversation-no-animation-verb'
    base = '/api/projects/' + project
    assert client.post('/api/projects', json={'project_id': project}).status_code == 200
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, changeset = run_build(engine, '生成教案和学习单。', environment='test_fixture')
    assert client.post(base + f'/changesets/{changeset}/accept').status_code == 200
    before = client.get(base + '/artifacts/media_plan:sec1')
    assert before.status_code == 200, before.text
    assert any(item['recommended_medium'] == 'animation' for item in before.json()['content']['items'])
    result = client.post(base + '/conversation', json={
        'message': f'修改第1节教案和讲稿，{restriction}。', 'execute': True,
    })
    assert result.status_code == 200, result.text
    assert result.json()['run_status'] == 'succeeded', result.text
    assert client.post(base + '/changesets/' + result.json()['changeset_id'] + '/accept').status_code == 200
    plan = client.get(base + '/artifacts/media_plan:sec1')
    assert plan.status_code == 200, plan.text
    assert all(item['recommended_medium'] != 'animation' for item in plan.json()['content']['items'])
