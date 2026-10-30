from test_benchmark_evaluation import client  # noqa: F401


def test_student_worksheet_includes_the_shared_case_when_tasks_need_it(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class SharedCaseLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'case':
                result['text'] = '虚构案例 CASE_CONTEXT_958，观察记录为一次。'
            elif kwargs['task'] == 'worksheet':
                result['tasks'] = [{'task_id': 't1', 'kind': 'practice', 'prompt': '请阅读案例并回答。'}]
            return result

    project = 'worksheet-case-material'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = SharedCaseLLM(), FakeResearch()
    run_id, _ = run_build(engine, '生成教案、案例和学习单，不要PPT，不要动画。', environment='test_fixture')
    assert client.get(base + f'/runs/{run_id}').json()['run']['status'] == 'succeeded'
    rev = engine.store.revisions_of('export_manifest')[-1]
    manifest = client.get(base + '/artifacts/export_manifest', params={'rev': rev}).json()['content']
    student = next(f for f in manifest['files'] if f['role'] == 'worksheet' and f['kind'] == 'markdown')
    output = client.get(base + '/file', params={'path': student['path']}).text
    assert 'CASE_CONTEXT_958' in output
