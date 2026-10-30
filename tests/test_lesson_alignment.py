from test_benchmark_evaluation import client  # noqa: F401


def test_lesson_plan_uses_the_actual_case_and_assessment(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class ObserveLLM(FakeLLM):
        case = None
        assessment = None
        lesson_prompt = ''

        def generate_json(self, **kwargs):
            if kwargs['task'] == 'lesson_plan':
                self.lesson_prompt = kwargs['prompt']
                assert self.case is not None and self.assessment is not None
                assert self.case in self.lesson_prompt
                assert self.assessment in self.lesson_prompt
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'case':
                self.case = 'CASE_CANONICAL_47'
                result['title'] = self.case
            if kwargs['task'] == 'assessment':
                self.assessment = result['items'][0]['assessment_id']
            return result

    project = 'lesson-alignment'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = ObserveLLM(), FakeResearch()
    run_id, _ = run_build(engine, '生成教案与学习单，不要PPT，不要动画。', environment='test_fixture')
    result = client.get(base + f'/runs/{run_id}').json()
    assert result['run']['status'] == 'succeeded', [(x['step_id'], x.get('error')) for x in result['steps'] if x['status'] == 'FAILED']
    assert engine.llm.lesson_prompt
