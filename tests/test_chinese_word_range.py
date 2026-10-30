from test_benchmark_evaluation import client  # noqa: F401


def test_request_word_range_with_dao_is_preserved(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'chinese-word-range'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    run_build(engine, '生成教案和讲稿，讲稿1200到1800字，不要PPT，不要动画。', environment='test_fixture')
    rev = engine.store.revisions_of('requirements')[-1]
    req = client.get(base + '/artifacts/requirements', params={'rev': rev}).json()['content']
    assert req['word_rules']['min'] == 1200
    assert req['word_rules']['max'] == 1800
