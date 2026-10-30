import time
from pathlib import Path

from test_benchmark_evaluation import client  # noqa: F401


def test_reexport_preserves_previous_manifest_files(client):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'export-history'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, changeset = run_build(engine, '生成讲稿和学习单，不要PPT，不要动画。', environment='test_fixture')
    rev = engine.store.revisions_of('export_manifest')[-1]
    old = client.get(base + '/artifacts/export_manifest', params={'rev': rev}).json()['content']
    old_file = next(f for f in old['files'] if f['role'] == 'lesson_script' and f['kind'] == 'markdown')
    old_bytes = Path(old_file['path']).read_bytes()
    assert client.post(base + f'/changesets/{changeset}/accept').status_code == 200
    rerun = client.post(base + '/plan/rerun', json={'step_id': 'export'})
    assert rerun.status_code == 200
    run_id = rerun.json()['run_id']
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        result = client.get(base + f'/runs/{run_id}').json()
        if result['run']['status'] != 'running':
            break
        time.sleep(0.05)
    assert result['run']['status'] == 'succeeded'
    rev = engine.store.revisions_of('export_manifest')[-1]
    new = client.get(base + '/artifacts/export_manifest', params={'rev': rev}).json()['content']
    new_file = next(f for f in new['files'] if f['role'] == 'lesson_script' and f['kind'] == 'markdown')
    assert old_file['path'] != new_file['path']
    assert Path(old_file['path']).read_bytes() == old_bytes


def test_accepted_formal_manifest_files_survive_later_export(engine, no_pptx):
    from conftest import REQUEST_1, run_build
    from pebs.store import file_hash

    _, changeset = run_build(engine, REQUEST_1)
    engine.accept(changeset)
    first = engine.export_now('formal')
    assert first['ok']
    assert engine.accept(first['changeset_id'])['status'] == 'accepted'
    for entry in first['manifest']['files']:
        path = Path(entry['path'])
        assert path.is_file() and file_hash(path) == entry['sha256']
    second = engine.export_now('formal')
    assert second['ok']
    assert engine.accept(second['changeset_id'])['status'] == 'accepted'
    for entry in first['manifest']['files']:
        assert file_hash(Path(entry['path'])) == entry['sha256']
