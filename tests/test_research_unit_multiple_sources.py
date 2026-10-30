import pytest

from test_benchmark_evaluation import client  # noqa: F401


def test_research_unit_pins_mediation_terminology_with_its_own_source(client, monkeypatch, tmp_path):
    from pebs import psychology

    unit = client.get('/api/psychology/units/research-methods').json()
    terms = {entry['term_id']: entry for entry in unit['terminology']}
    mediator = terms['mediator']
    confounder = terms['confounding-variable']
    assert '因果' in mediator['definition'] and '路径' in mediator['definition']
    assert '共同原因' in confounder['definition']
    assert mediator['evidence_anchor']['source_ref'] in mediator['source_refs']
    assert mediator['evidence_anchor']['source_ref'] != confounder['evidence_anchor']['source_ref']
    assert all(mediator['terms'][lang]['full'] for lang in ('zh-CN', 'en', 'ja', 'ko'))
    assert client.post('/api/projects', json={'project_id': 'research-multiple-sources'}).status_code == 200
    base = '/api/projects/research-multiple-sources/psychology/units/research-methods'
    pinned = client.post(base)
    assert pinned.status_code == 200, pinned.text
    monkeypatch.setattr(psychology, 'SOURCE_DIRECTORY', tmp_path / 'missing-sources')
    materials = client.get(base + '/materials', params={'revision_id': pinned.json()['revision_id'], 'audience': 'teacher'})
    assert materials.status_code == 200, materials.text
    assert materials.json()['target']['content_hash'] == pinned.json()['content_hash']
    assert materials.json()['teacher_review']['status'] == 'PENDING'


def test_build_reads_both_frozen_sources_after_catalog_disappears(client, monkeypatch, tmp_path):
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import psychology, server

    project = 'research-multiple-sources-build'
    client.post('/api/projects', json={'project_id': project})
    base = '/api/projects/' + project
    pinned = client.post(base + '/psychology/units/research-methods').json()
    monkeypatch.setattr(psychology, 'SOURCE_DIRECTORY', tmp_path / 'missing-sources')
    engine = server.get_engine(project)
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    run_build(engine, f"学科修订={pinned['revision_id']} 不要PPT，不要动画。", environment='test_fixture')
    rev = engine.store.revisions_of('materials')[-1]
    materials = client.get(base + '/artifacts/materials', params={'rev': rev}).json()['content']
    titles = {source['title'] for source in engine.evidence.sources()}
    assert 'A Systematic Literature Review of Causal Mediation Analysis in Social Psychology' in titles
    assert len(materials['psychology_sources']) == 2
    sources = {source['catalog_source_id']: source for source in materials['psychology_sources']}
    second = sources['kim-thoemmes-2026-mediation']
    assert {entry['term_id'] for entry in second['terminology_anchors']} == {'mediator'}
    assert all(anchor['source_ref'] == source_id for source_id, source in sources.items()
               for anchor in source['terminology_anchors'] + source['concept_anchors'])


@pytest.mark.parametrize('tamper', ['text', 'title'])
def test_altered_extra_snapshot_is_rejected_by_public_materials_and_build(client, tamper):
    from copy import deepcopy
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'research-multiple-sources-tampered-' + tamper
    client.post('/api/projects', json={'project_id': project})
    base = '/api/projects/' + project
    pinned = client.post(base + '/psychology/units/research-methods').json()
    engine = server.get_engine(project)
    content = deepcopy(engine.store.get_revision(pinned['revision_id'])['content'])
    extra = content['frozen_extra_sources']['kim-thoemmes-2026-mediation']
    if tamper == 'text':
        extra['text'] += 'tampered'
    else:
        extra['metadata']['title'] = 'A different paper'
    revision = engine.store.add_revision(artifact_id='psychology_unit:research-methods',
                                         artifact_type='psychology_unit', content=content,
                                         produced_by='test')
    materials = client.get(base + '/psychology/units/research-methods/materials',
                           params={'revision_id': revision['revision_id'], 'audience': 'teacher'})
    assert materials.status_code == 409
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    run_id, _ = run_build(engine, f"学科修订={revision['revision_id']} 不要PPT，不要动画。", environment='test_fixture')
    steps = client.get(base + f'/runs/{run_id}').json()['steps']
    assert next(step for step in steps if step['step_id'] == 'parse_inputs')['status'] == 'FAILED'


def test_build_rejects_unit_artifact_and_content_identity_mismatch(client):
    from copy import deepcopy
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'research-unit-identity-mismatch'
    client.post('/api/projects', json={'project_id': project})
    base = '/api/projects/' + project
    pinned = client.post(base + '/psychology/units/research-methods').json()
    engine = server.get_engine(project)
    content = deepcopy(engine.store.get_revision(pinned['revision_id'])['content'])
    revision = engine.store.add_revision(artifact_id='psychology_unit:operant-conditioning',
                                         artifact_type='psychology_unit', content=content,
                                         produced_by='test')
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    run_id, _ = run_build(engine, f"学科修订={revision['revision_id']} 不要PPT，不要动画。", environment='test_fixture')
    steps = client.get(base + f'/runs/{run_id}').json()['steps']
    assert next(step for step in steps if step['step_id'] == 'parse_inputs')['status'] == 'FAILED'


def test_frozen_primary_source_identity_must_match_the_unit(client):
    from copy import deepcopy
    from pebs import server

    project = 'research-primary-source-identity'
    client.post('/api/projects', json={'project_id': project})
    base = '/api/projects/' + project
    pinned = client.post(base + '/psychology/units/research-methods').json()
    engine = server.get_engine(project)
    content = deepcopy(engine.store.get_revision(pinned['revision_id'])['content'])
    content['frozen_source']['metadata']['url'] = 'https://example.org/different-source'
    revision = engine.store.add_revision(artifact_id='psychology_unit:research-methods',
                                         artifact_type='psychology_unit', content=content,
                                         produced_by='test')
    response = client.get(base + '/psychology/units/research-methods/materials',
                          params={'revision_id': revision['revision_id'], 'audience': 'teacher'})
    assert response.status_code == 409


def test_empty_frozen_primary_does_not_fall_back_to_live_catalog(client):
    from copy import deepcopy
    from pebs import server

    project = 'research-empty-frozen-source'
    client.post('/api/projects', json={'project_id': project})
    base = '/api/projects/' + project
    pinned = client.post(base + '/psychology/units/research-methods').json()
    engine = server.get_engine(project)
    content = deepcopy(engine.store.get_revision(pinned['revision_id'])['content'])
    content['frozen_source'] = {}
    revision = engine.store.add_revision(artifact_id='psychology_unit:research-methods',
                                         artifact_type='psychology_unit', content=content,
                                         produced_by='test')
    response = client.get(base + '/psychology/units/research-methods/materials',
                          params={'revision_id': revision['revision_id'], 'audience': 'teacher'})
    assert response.status_code == 409


def test_multiple_source_unit_requires_primary_source_identity(client):
    from copy import deepcopy
    from pebs import server

    project = 'research-missing-primary-identity'
    client.post('/api/projects', json={'project_id': project})
    base = '/api/projects/' + project
    pinned = client.post(base + '/psychology/units/research-methods').json()
    engine = server.get_engine(project)
    content = deepcopy(engine.store.get_revision(pinned['revision_id'])['content'])
    del content['sources'][0]['version_url']
    revision = engine.store.add_revision(artifact_id='psychology_unit:research-methods',
                                         artifact_type='psychology_unit', content=content,
                                         produced_by='test')
    response = client.get(base + '/psychology/units/research-methods/materials',
                          params={'revision_id': revision['revision_id'], 'audience': 'teacher'})
    assert response.status_code == 409


def test_anchor_cannot_override_term_identity_in_build(client):
    from copy import deepcopy
    from conftest import FakeLLM, FakeResearch, run_build
    from pebs import server

    project = 'research-anchor-identity'
    client.post('/api/projects', json={'project_id': project})
    base = '/api/projects/' + project
    pinned = client.post(base + '/psychology/units/research-methods').json()
    engine = server.get_engine(project)
    content = deepcopy(engine.store.get_revision(pinned['revision_id'])['content'])
    mediator = next(term for term in content['terminology'] if term['term_id'] == 'mediator')
    mediator['evidence_anchor']['term_id'] = 'wrong-term'
    revision = engine.store.add_revision(artifact_id='psychology_unit:research-methods',
                                         artifact_type='psychology_unit', content=content,
                                         produced_by='test')
    engine.llm, engine.research = FakeLLM(), FakeResearch()
    run_id, _ = run_build(engine, f"学科修订={revision['revision_id']} 不要PPT，不要动画。", environment='test_fixture')
    run = client.get(base + f'/runs/{run_id}').json()
    parse = next(step for step in run['steps'] if step['step_id'] == 'parse_inputs')
    if parse['status'] == 'SUCCEEDED':
        rev = engine.store.revisions_of('materials')[-1]
        materials = client.get(base + '/artifacts/materials', params={'rev': rev}).json()['content']
        secondary = next(s for s in materials['psychology_sources'] if s['catalog_source_id'] == 'kim-thoemmes-2026-mediation')
        assert {anchor['term_id'] for anchor in secondary['terminology_anchors']} == {'mediator'}
    else:
        assert parse['status'] == 'FAILED'
