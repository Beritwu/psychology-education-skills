from pebs.providers import CompositeResearch


def test_composite_exposes_provider_for_doi_free_results():
    class Adapter:
        def search(self, query, rows=5):
            return [{'title': 'Record without a DOI', 'doi': None, 'database': 'openalex'}]

    research = CompositeResearch({'enabled': True, 'allowed_sources': []})
    research.adapters = [('openalex', Adapter())]
    item = research.search('topic').items[0]
    assert item.get('source') == 'openalex'
