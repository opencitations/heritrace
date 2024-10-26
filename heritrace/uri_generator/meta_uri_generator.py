from rdflib import URIRef
from rdflib_ocdm.counter_handler.sqlite_counter_handler import \
    SqliteCounterHandler

from heritrace.uri_generator.uri_generator import URIGenerator


class MetaURIGenerator(URIGenerator):
    def __init__(self, base_iri: str, supplier_prefix: str, counter_handler: SqliteCounterHandler):
        self.base_iri = base_iri
        self.supplier_prefix = supplier_prefix
        self.counter_handler = counter_handler

    def generate_uri(self, entity_type: str) -> str:
        count = self.counter_handler.read_counter(entity_type)
        entity_type_abbr = {
            'http://purl.org/spar/fabio/Expression': 'br',
            'http://purl.org/spar/fabio/JournalArticle': 'br',
            'http://purl.org/spar/fabio/Book': 'br',
            'http://purl.org/spar/fabio/BookChapter': 'br',
            'http://purl.org/spar/fabio/JournalIssue': 'br',
            'http://purl.org/spar/fabio/JournalVolume': 'br',
            'http://purl.org/spar/fabio/Journal': 'br',
            'http://purl.org/spar/pro/RoleInTime': 'ar',
            'http://purl.org/spar/fabio/Manifestation': 're',
            'http://xmlns.com/foaf/0.1/Agent': 'ra',
            'http://purl.org/spar/datacite/Identifier': 'id'
        }
        return URIRef(f"{self.base_iri}/{entity_type_abbr[entity_type]}/{self.supplier_prefix}{count}")