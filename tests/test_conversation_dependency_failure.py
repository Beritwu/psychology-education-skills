from test_benchmark_evaluation import client  # noqa: F401


def test_failed_assessment_blocks_all_selected_downstream_steps(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class InvalidAssessmentLLM(FakeLLM):
        fail_assessment = False

        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if self.fail_assessment and kwargs['task'] == 'assessment':
                result['diagnostic_use'] = {'decision_rules': [{
                    'assessment_ref': 'missing', 'trigger': '错误', 'action': '补救'}]}
            return result

    project = 'conversation-upstream-failure'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = InvalidAssessmentLLM(), FakeResearch()
    _, changeset = run_build(engine, '生成教案和学习单，不要PPT，不要动画。', environment='test_fixture')
    assert client.post(base + f'/changesets/{changeset}/accept').status_code == 200
    engine.llm.fail_assessment = True
    response = client.post(base + '/conversation', json={
        'message': '修改第1节评价题、教案、学习单、讲稿和图示，保留案例不变。不要PPT，不要动画。',
        'execute': True,
    })
    assert response.status_code == 200, response.text
    run = client.get(base + '/runs/' + response.json()['run_id']).json()
    steps = {step['step_id']: step for step in run['steps']}
    assert steps['assessments']['status'] == 'FAILED'
    assert steps['scripts']['status'] == 'BLOCKED'
    assert steps['export']['status'] == 'BLOCKED'
