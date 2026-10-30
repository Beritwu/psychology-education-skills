from pebs.providers import CompositeResearch


def test_merged_richer_abstract_reports_its_actual_provider():
    class Adapter:
        def __init__(self, item):
            self.item = item

        def search(self, query, rows=5):
            return [self.item]

    research = CompositeResearch({'enabled': True, 'allowed_sources': []})
    research.adapters = [
        ('openalex', Adapter({'title': 'A paper', 'doi': None, 'database': 'openalex',
                             'content_level': 'metadata', 'abstract': ''})),
        ('crossref', Adapter({'title': 'A paper', 'doi': None, 'database': 'crossref',
                             'content_level': 'abstract', 'abstract': 'An abstract.'})),
    ]
    result = research.search('topic').items
    assert len(result) == 1
    assert result[0]['abstract'] == 'An abstract.'
    assert result[0]['database'] == 'crossref'
    assert result[0]['source'] == 'crossref'
    assert set(result[0]['sources']) == {'openalex', 'crossref'}
