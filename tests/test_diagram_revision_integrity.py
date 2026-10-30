"""A published revision must retain its referenced visual bytes after rerun."""
import time

from test_benchmark_evaluation import client  # noqa: F401


def test_rerunning_diagrams_preserves_previous_revision_file(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    class DifferentDiagrams(FakeLLM):
        diagram_calls = 0

        def generate_json(self, **kwargs):
            result = super().generate_json(**kwargs)
            if kwargs['task'] == 'diagram_svg':
                self.diagram_calls += 1
                result['diagrams'][0]['svg'] = result['diagrams'][0]['svg'].replace(
                    '直接观察</text>', f'直接观察 {self.diagram_calls}</text>')
            return result

    project = 'diagram-history'
    base = f'/api/projects/{project}'
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = DifferentDiagrams(), FakeResearch()
    run_id, changeset = run_build(engine, '生成教案和图示，不要PPT，不要动画。', environment='test_fixture')
    initial_status = client.get(base + f'/runs/{run_id}').json()
    assert initial_status['run']['status'] == 'succeeded', [(s['step_id'], s.get('error')) for s in initial_status['steps'] if s['status'] == 'FAILED']
    revisions = engine.store.revisions_of('diagrams:sec1')
    old = client.get(base + '/artifacts/diagrams:sec1', params={'rev': revisions[-1]}).json()['content']['diagrams'][0]
    old_bytes = client.get(base + '/file', params={'path': old['svg_path']}).content
    assert old_bytes
    assert client.post(base + f'/changesets/{changeset}/accept').status_code == 200
    rerun = client.post(base + '/plan/rerun', json={'step_id': 'diagrams'})
    assert rerun.status_code == 200, rerun.text
    run_id = rerun.json()['run_id']
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        status = client.get(base + f'/runs/{run_id}').json()['run']['status']
        if status != 'running':
            break
        time.sleep(0.05)
    assert status == 'succeeded'
    assert engine.llm.diagram_calls >= 2
    old_again = client.get(base + '/file', params={'path': old['svg_path']})
    assert old_again.status_code == 200
    assert old_again.content == old_bytes
