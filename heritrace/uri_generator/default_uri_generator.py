import uuid

from rdflib import URIRef

from heritrace.uri_generator.uri_generator import URIGenerator


class DefaultURIGenerator(URIGenerator):
    def __init__(self, base_iri: str):
        self.base_iri = base_iri

    def generate_uri(self, entity_type: str | None = None) -> str:
        return URIRef(f"{self.base_iri}/{uuid.uuid4().hex}")
