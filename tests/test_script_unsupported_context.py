from test_benchmark_evaluation import client  # noqa: F401


def test_script_does_not_receive_unsupported_claims_as_material_to_restate(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class UnsupportedLLM(FakeLLM):
        script_prompt = ''

        def generate_json(self, **kwargs):
            task = kwargs['task']
            if task == 'claims':
                result = super().generate_json(**kwargs)
                result['claims'].append({'text': 'UNSUPPORTED_FACT_MARKER_835', 'claim_type': 'descriptive',
                                         'population': '学生', 'usage': '讲解'})
                return result
            if task == 'evidence_review' and 'UNSUPPORTED_FACT_MARKER_835' in kwargs['prompt']:
                return {'found': False}
            if task == 'script':
                self.script_prompt = kwargs['prompt']
            return super().generate_json(**kwargs)

    project = 'unsupported-script-context'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = UnsupportedLLM(), FakeResearch()
    run_id, _ = run_build(engine, '生成教案和讲稿，不要PPT，不要动画。', environment='test_fixture')
    result = client.get(base + f'/runs/{run_id}').json()
    assert result['run']['status'] == 'succeeded', [(x['step_id'], x.get('error')) for x in result['steps'] if x['status'] == 'FAILED']
    assert engine.llm.script_prompt
    assert 'UNSUPPORTED_FACT_MARKER_835' not in engine.llm.script_prompt
