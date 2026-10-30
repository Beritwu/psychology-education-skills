from test_benchmark_evaluation import client  # noqa: F401


def test_teacher_only_question_cannot_enter_a_student_worksheet(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class TeacherOnlyLLM(FakeLLM):
        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'assessment':
                result['items'][0]['student_viewable'] = False
                result['items'][0]['question'] = 'TEACHER_ONLY_QUESTION_482'
            elif kwargs['task'] == 'worksheet':
                result['tasks'] = [{'task_id': 't1', 'kind': 'practice', 'task_role': 'assessment',
                                    'prompt': '练习题', 'assessment_refs': ['a1']}]
            return result

    project = 'teacher-only-question'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = TeacherOnlyLLM(), FakeResearch()
    run_id, _ = run_build(engine, '生成学习单与讲稿，不要PPT，不要动画。', environment='test_fixture')
    result = client.get(base + f'/runs/{run_id}').json()
    if result['run']['status'] == 'succeeded':
        rev = engine.store.revisions_of('export_manifest')[-1]
        manifest = client.get(base + '/artifacts/export_manifest', params={'rev': rev}).json()['content']
        student = next(f for f in manifest['files'] if f['role'] == 'worksheet' and f['kind'] == 'markdown')
        output = client.get(base + '/file', params={'path': student['path']}).text
        assert 'TEACHER_ONLY_QUESTION_482' not in output
    else:
        assert any(s['step_id'] == 'worksheets' and s['status'] == 'FAILED' for s in result['steps'])
