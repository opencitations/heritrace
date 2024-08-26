from rdflib import URIRef
from edit_sphere.uri_generator.uri_generator import URIGenerator

class MetaURIGenerator(URIGenerator):
    def __init__(self, base_iri: str, supplier_prefix: str, counter_handler: str):
        self.base_iri = base_iri
        self.supplier_prefix = supplier_prefix
        self.counter_handler = counter_handler

    def generate_uri(self, entity_type: str) -> str:
        count = self.counter_handler.get_count(entity_type)
        entity_type_abbr = {
            'http://purl.org/spar/fabio/Expression': 'br',
            'http://purl.org/spar/pro/RoleInTime': 'ar',
            'http://purl.org/spar/fabio/Manifestation': 're',
            'http://xmlns.com/foaf/0.1/Agent': 'ra',
            'http://purl.org/spar/datacite/Identifier': 'id'
        }
        return URIRef(f"{self.base_iri}/{entity_type_abbr}/{self.supplier_prefix}{count}")