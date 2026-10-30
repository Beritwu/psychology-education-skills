import ast

from test_benchmark_evaluation import client  # noqa: F401


def test_assessment_uses_current_claims_after_qualification(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class HistoryPickingLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'assessment':
                line = next(line for line in kwargs['prompt'].splitlines()
                            if line.startswith('可引用的证据记录'))
                index = ast.literal_eval(line.split('：', 1)[1])
                current = index['claims']
                # A model can mistakenly pick the first historical claim revision.
                if index.get('assessments'):
                    ref = index['assessments'][0]['claim_rev']
                else:
                    ref = f"{current[0]['claim_id']}@v{current[0]['version']}"
                result['items'][0]['claim_refs'] = [ref]
            return result

    project = 'assessment-current-evidence'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = HistoryPickingLLM(qualify_flow=True), FakeResearch()
    run_id, _ = run_build(engine, '生成评价和学习单，不要PPT，不要动画。', environment='test_fixture')
    result = client.get(base + f'/runs/{run_id}').json()
    assert result['run']['status'] == 'succeeded', [
        (step['step_id'], step.get('error')) for step in result['steps'] if step['status'] == 'FAILED'
    ]
    index = client.get(base + '/artifacts/evidence_index', params={'rev': 'evidence_index@r1'}).json()['content']
    current = index['claims'][0]
    expected = f"{current['claim_id']}@v{current['version']}"
    assert index['assessments'][0]['claim_rev'] != expected
    assessment = client.get(base + '/artifacts/assessment:sec1', params={'rev': 'assessment:sec1@r1'}).json()['content']
    assert assessment['items'][0]['claim_refs'] == [expected]
