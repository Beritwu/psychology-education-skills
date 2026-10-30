import time
from pathlib import Path

from test_benchmark_evaluation import client  # noqa: F401


def test_export_rejects_a_diagram_changed_after_revision(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'diagram-export-integrity'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    run_id, changeset = run_build(engine, '生成图示和讲稿，不要PPT，不要动画。', environment='test_fixture')
    assert client.get(base + f'/runs/{run_id}').json()['run']['status'] == 'succeeded'
    revision = engine.store.revisions_of('diagrams:sec1')[-1]
    diagram = client.get(base + '/artifacts/diagrams:sec1', params={'rev': revision}).json()['content']['diagrams'][0]
    assert client.post(base + f'/changesets/{changeset}/accept').status_code == 200
    path = Path(diagram['svg_path'])
    path.write_text(path.read_text(encoding='utf-8').replace('直接观察', '被替换内容'), encoding='utf-8')
    rerun = client.post(base + '/plan/rerun', json={'step_id': 'export'})
    assert rerun.status_code == 200
    run_id = rerun.json()['run_id']
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        result = client.get(base + f'/runs/{run_id}').json()
        if result['run']['status'] != 'running':
            break
        time.sleep(0.05)
    assert result['run']['status'] == 'failed'
    assert any(s['step_id'] == 'export' and s['status'] == 'FAILED' for s in result['steps'])
