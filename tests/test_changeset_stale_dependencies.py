"""Accepting a mixed-version changeset must not advertise stale outputs as current."""

from test_api import client  # noqa: F401
from pebs import server


def test_accept_marks_outputs_stale_if_same_changeset_supersedes_their_input(client):
    project = 'mixed-revision-candidate'
    base = '/api/projects/' + project
    assert client.post('/api/projects', json={'project_id': project}).status_code == 200
    store = server.get_engine(project).store

    def revision(artifact, content, deps=()):
        return store.add_revision(artifact_id=artifact, artifact_type='doc',
                                  content=content, produced_by='test', deps=deps)

    up1 = revision('up', {'value': 1})
    down1 = revision('down', {'value': 1}, [up1['revision_id']])
    initial = store.create_changeset(None, 'baseline', store.current_baseline())
    for name, item in (('up', up1), ('down', down1)):
        store.add_changeset_item(initial, item['revision_id'], name)
    assert client.post(base + '/changesets/' + initial + '/accept').json()['status'] == 'accepted'

    up2 = revision('up', {'value': 2})
    down2 = revision('down', {'value': 2}, [up2['revision_id']])
    up3 = revision('up', {'value': 3})
    candidate = store.create_changeset(None, 'mixed versions', store.current_baseline())
    for name, item in (('up', up2), ('down', down2), ('up', up3)):
        store.add_changeset_item(candidate, item['revision_id'], name)
    result = client.post(base + '/changesets/' + candidate + '/accept').json()
    assert result['status'] == 'accepted'
    assert store.accepted_rev_id('up') == up3['revision_id']
    assert store.accepted_rev_id('down') == down2['revision_id']
    assert store.is_stale('down')
    assert 'down' in result['stale_artifacts']


def test_candidate_with_unaccepted_dependency_is_not_current(client):
    project = 'unaccepted-dependency'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    store = server.get_engine(project).store
    source = store.add_revision(artifact_id='source', artifact_type='doc',
                                content={'value': 1}, produced_by='test')
    output = store.add_revision(artifact_id='output', artifact_type='doc',
                                content={'value': 1}, produced_by='test',
                                deps=[source['revision_id']])
    candidate = store.create_changeset(None, 'missing input', store.current_baseline())
    store.add_changeset_item(candidate, output['revision_id'], 'output')
    result = client.post(base + '/changesets/' + candidate + '/accept').json()
    assert result['status'] == 'accepted'
    assert store.is_stale('output')
    assert 'output' in result['stale_artifacts']


def test_frozen_psychology_unit_is_valid_without_a_current_pointer(client):
    from conftest import FakeLLM, FakeResearch, run_build

    project = 'frozen-unit-input'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    pinned = client.post(base + '/psychology/units/research-methods').json()
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    assert engine.store.accepted_rev_id(pinned['artifact_id']) is None
    _, changeset = run_build(engine, '生成学习单，不要PPT，不要动画。 学科修订=' + pinned['revision_id'],
                             environment='test_fixture')
    result = client.post(base + '/changesets/' + changeset + '/accept').json()
    assert result['status'] == 'accepted'
    assert not engine.store.is_stale('materials')


def test_unaccepted_published_rule_is_valid_only_while_it_is_the_latest_version(client):
    project = 'pinned-published-rule'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    store = server.get_engine(project).store
    rule = store.add_revision(artifact_id='psychology_rule:example', artifact_type='psychology_rule',
                              content={'status': 'PUBLISHED'}, produced_by='test')
    first = store.add_revision(artifact_id='first', artifact_type='doc', content={},
                               produced_by='test', deps=[rule['revision_id']])
    candidate = store.create_changeset(None, 'current published rule', store.current_baseline())
    store.add_changeset_item(candidate, first['revision_id'], 'first')
    assert client.post(base + '/changesets/' + candidate + '/accept').json()['status'] == 'accepted'
    assert not store.is_stale('first')
    store.add_revision(artifact_id='psychology_rule:example', artifact_type='psychology_rule',
                       content={'status': 'WITHDRAWN'}, produced_by='test')
    second = store.add_revision(artifact_id='second', artifact_type='doc', content={},
                                produced_by='test', deps=[rule['revision_id']])
    candidate = store.create_changeset(None, 'withdrawn rule', store.current_baseline())
    store.add_changeset_item(candidate, second['revision_id'], 'second')
    assert client.post(base + '/changesets/' + candidate + '/accept').json()['status'] == 'accepted'
    assert store.is_stale('second')


def test_stale_formal_manifest_is_not_published_on_accept(client):
    project = 'mixed-revision-formal'
    base = '/api/projects/' + project
    assert client.post('/api/projects', json={'project_id': project}).status_code == 200
    engine = server.get_engine(project)
    store = engine.store
    candidate = store.create_changeset(None, 'formal with superseded input', store.current_baseline())
    staging = engine._staging_dir(candidate)
    staging.mkdir(parents=True)
    source = staging / 'course.md'
    source.write_text('candidate', encoding='utf8')
    first = store.add_revision(artifact_id='script:sec1', artifact_type='script',
                               content={'version': 1}, produced_by='test')
    manifest = store.add_revision(artifact_id='export_manifest', artifact_type='export_manifest',
                                  content={'mode': 'formal', 'files': [{'path': str(source)}]},
                                  produced_by='test', deps=[first['revision_id']])
    latest = store.add_revision(artifact_id='script:sec1', artifact_type='script',
                                content={'version': 2}, produced_by='test')
    gate_id = 'gate:G8:export_manifest'
    gate = store.add_revision(artifact_id=gate_id, artifact_type='gate_result',
                              content={'status': 'PASS', 'target': {'revision_id': manifest['revision_id']}},
                              produced_by='test', deps=[manifest['revision_id']])
    for name, item in (('script:sec1', first), ('export_manifest', manifest),
                       ('script:sec1', latest), (gate_id, gate)):
        store.add_changeset_item(candidate, item['revision_id'], name)
    result = client.post(base + '/changesets/' + candidate + '/accept').json()
    assert result['status'] == 'accepted'
    assert store.is_stale('export_manifest')
    assert store.is_stale(gate_id)
    assert result['published'] == []


def test_formal_export_rejects_stale_gate_even_when_target_is_unchanged(client, no_pptx):
    from conftest import FakeLLM, FakeResearch, REQUEST_1, run_build
    from pebs import gates

    project = 'stale-gate-export'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, changeset = run_build(engine, REQUEST_1)
    assert client.post(base + '/changesets/' + changeset + '/accept').json()['status'] == 'accepted'
    gate = 'gate:G1:script:sec1'
    assert engine.store.accepted_content(gate)['status'] == 'PASS'
    assert gates.export_readiness(engine.store)['ready']
    engine.store.set_stale(gate, True)
    response = client.post(base + '/export', json={'mode': 'formal'}).json()
    assert response['ok'] is False


def test_formal_publish_rejects_path_outside_staging(client):
    from pebs import gates

    project = 'formal-staging-boundary'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    store = engine.store
    candidate = store.create_changeset(None, 'invalid source', store.current_baseline())
    staging = engine._staging_dir(candidate)
    staging.mkdir(parents=True)
    outside = staging.parent / 'outside.md'
    outside.write_text('outside', encoding='utf8')
    escaped = staging / '..' / outside.name
    manifest = store.add_revision(artifact_id='export_manifest', artifact_type='export_manifest',
                                  content={'mode': 'formal', 'files': [{'path': str(escaped)}]},
                                  produced_by='test')
    gate_id = gates.gate_artifact_id('G8', 'export_manifest')
    gate = store.add_revision(artifact_id=gate_id, artifact_type='gate_result',
                              content={'status': 'PASS', 'target': {'revision_id': manifest['revision_id']}},
                              produced_by='test', deps=[manifest['revision_id']])
    for name, item in (('export_manifest', manifest), (gate_id, gate)):
        store.add_changeset_item(candidate, item['revision_id'], name)
    result = client.post(base + '/changesets/' + candidate + '/accept').json()
    assert result['status'] == 'accepted'
    assert result['published'] == []


def test_formal_publish_rechecks_gates_after_candidate_creation(client, no_pptx):
    from conftest import FakeLLM, FakeResearch, REQUEST_1, run_build

    project = 'gate-stale-before-publish'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, initial = run_build(engine, REQUEST_1)
    assert client.post(base + '/changesets/' + initial + '/accept').json()['status'] == 'accepted'
    candidate = client.post(base + '/export', json={'mode': 'formal'}).json()
    assert candidate['ok'] and candidate['mode'] == 'formal'
    engine.store.set_stale('gate:G1:script:sec1', True)
    result = client.post(base + '/changesets/' + candidate['changeset_id'] + '/accept').json()
    assert result['status'] == 'accepted'
    assert result['published'] == []


def test_formal_publish_rejects_files_changed_after_validation(client, no_pptx):
    from conftest import FakeLLM, FakeResearch, REQUEST_1, run_build
    from pathlib import Path

    project = 'file-changed-before-publish'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, initial = run_build(engine, REQUEST_1)
    assert client.post(base + '/changesets/' + initial + '/accept').json()['status'] == 'accepted'
    candidate = client.post(base + '/export', json={'mode': 'formal'}).json()
    assert candidate['ok'] and candidate['mode'] == 'formal'
    Path(candidate['manifest']['files'][0]['path']).write_text('changed', encoding='utf8')
    result = client.post(base + '/changesets/' + candidate['changeset_id'] + '/accept').json()
    assert result['status'] == 'accepted'
    assert result['published'] == []


def test_formal_publish_rejects_g8_from_old_rules(client, no_pptx):
    from conftest import FakeLLM, FakeResearch, REQUEST_1, run_build
    from pebs import gates

    project = 'old-g8-before-publish'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, initial = run_build(engine, REQUEST_1)
    assert client.post(base + '/changesets/' + initial + '/accept').json()['status'] == 'accepted'
    candidate = client.post(base + '/export', json={'mode': 'formal'}).json()
    assert candidate['ok'] and candidate['mode'] == 'formal'
    changeset = engine.store.get_changeset(candidate['changeset_id'])
    manifest = next(i['revision'] for i in changeset['items'] if i['artifact_id'] == 'export_manifest')
    gate_id = gates.gate_artifact_id('G8', 'export_manifest')
    gate = engine.store.add_revision(artifact_id=gate_id, artifact_type='gate_result',
                                     content={'status': 'PASS', 'rules_version': 'obsolete-rules',
                                              'target': {'revision_id': manifest['revision_id']}},
                                     produced_by='test', deps=[manifest['revision_id']])
    engine.store.add_changeset_item(candidate['changeset_id'], gate['revision_id'], gate_id)
    result = client.post(base + '/changesets/' + candidate['changeset_id'] + '/accept').json()
    assert result['status'] == 'accepted'
    assert result['published'] == []


def test_formal_publish_rejects_manifest_without_file_hash(client, no_pptx):
    from conftest import FakeLLM, FakeResearch, REQUEST_1, run_build
    from pebs import config, gates

    project = 'missing-hash-before-publish'
    base = '/api/projects/' + project
    client.post('/api/projects', json={'project_id': project})
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    _, initial = run_build(engine, REQUEST_1)
    assert client.post(base + '/changesets/' + initial + '/accept').json()['status'] == 'accepted'
    candidate = client.post(base + '/export', json={'mode': 'formal'}).json()
    assert candidate['ok'] and candidate['mode'] == 'formal'
    changeset = engine.store.get_changeset(candidate['changeset_id'])
    manifest = next(i['revision'] for i in changeset['items'] if i['artifact_id'] == 'export_manifest')
    altered = dict(manifest['content'])
    altered['files'] = [dict(item) for item in altered['files']]
    altered['files'][0].pop('sha256')
    new_manifest = engine.store.add_revision(artifact_id='export_manifest', artifact_type='export_manifest',
                                             content=altered, produced_by='test')
    gate_id = gates.gate_artifact_id('G8', 'export_manifest')
    gate = engine.store.add_revision(artifact_id=gate_id, artifact_type='gate_result',
                                     content={'status': 'PASS', 'rules_version': config.RULES_VERSION,
                                              'target': {'revision_id': new_manifest['revision_id']}},
                                     produced_by='test', deps=[new_manifest['revision_id']])
    engine.store.add_changeset_item(candidate['changeset_id'], new_manifest['revision_id'], 'export_manifest')
    engine.store.add_changeset_item(candidate['changeset_id'], gate['revision_id'], gate_id)
    result = client.post(base + '/changesets/' + candidate['changeset_id'] + '/accept').json()
    assert result['status'] == 'accepted'
    assert result['published'] == []
