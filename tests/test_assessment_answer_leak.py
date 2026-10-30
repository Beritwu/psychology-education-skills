from test_benchmark_evaluation import client  # noqa: F401


def test_student_question_cannot_publish_correct_option_in_scoring(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class LeakyLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'assessment':
                item = result['items'][0]
                item['answer'] = 'B'
                item['question'] += ' 选择B得2分，其他选项0分。'
                item['student_viewable'] = True
            return result

    project = 'assessment-answer-leak'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = LeakyLLM(), FakeResearch()
    run_id, _ = run_build(engine, '生成评价与学习单，不要PPT，不要动画。', environment='test_fixture')
    run = client.get(base + f'/runs/{run_id}').json()
    assessment = next(step for step in run['steps'] if step['step_id'] == 'assessments')
    assert assessment['status'] == 'FAILED'
    assert '答案' in assessment['error']
