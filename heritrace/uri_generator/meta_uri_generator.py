from collections import defaultdict

from heritrace.uri_generator.uri_generator import URIGenerator
from rdflib import URIRef
from rdflib_ocdm.counter_handler.redis_counter_handler import RedisCounterHandler
from SPARQLWrapper import JSON, SPARQLWrapper


class MetaURIGenerator(URIGenerator):
    def __init__(
        self, base_iri: str, supplier_prefix: str, counter_handler: RedisCounterHandler
    ):
        self.base_iri = base_iri
        self.supplier_prefix = supplier_prefix
        self.counter_handler = counter_handler
        self.entity_type_abbr = {
            "http://purl.org/spar/fabio/Expression": "br",
            "http://purl.org/spar/fabio/Article": "br",
            "http://purl.org/spar/fabio/JournalArticle": "br",
            "http://purl.org/spar/fabio/Book": "br",
            "http://purl.org/spar/fabio/BookChapter": "br",
            "http://purl.org/spar/fabio/JournalIssue": "br",
            "http://purl.org/spar/fabio/JournalVolume": "br",
            "http://purl.org/spar/fabio/Journal": "br",
            "http://purl.org/spar/fabio/AcademicProceedings": "br",
            "http://purl.org/spar/fabio/ProceedingsPaper": "br",
            "http://purl.org/spar/fabio/ReferenceBook": "br",
            "http://purl.org/spar/fabio/Review": "br",
            "http://purl.org/spar/fabio/ReviewArticle": "br",
            "http://purl.org/spar/fabio/Series": "br",
            "http://purl.org/spar/fabio/Thesis": "br",
            "http://purl.org/spar/pro/RoleInTime": "ar",
            "http://purl.org/spar/fabio/Manifestation": "re",
            "http://xmlns.com/foaf/0.1/Agent": "ra",
            "http://purl.org/spar/datacite/Identifier": "id",
        }

    def generate_uri(self, entity_type: str) -> str:
        last_used = self.counter_handler.read_counter(entity_type)
        next_number = last_used + 1
        self.counter_handler.set_counter(next_number, entity_type)
        return URIRef(
            f"{self.base_iri}/{self.entity_type_abbr[entity_type]}/{self.supplier_prefix}{next_number}"
        )

    def initialize_counters(self, sparql: SPARQLWrapper):
        """
        Inizializza i contatori per i tipi di entità supportati da questo URI generator.
        Estrae i numeri sequenziali sia dai dati che dalla provenance per ogni abbreviazione.
        
        :param sparql: SPARQLWrapper instance per eseguire le query sul dataset
        """
        max_numbers = defaultdict(int)

        data_query = f"""
            SELECT ?s ?type
            WHERE {{
                ?s a ?type .
                FILTER(STRSTARTS(str(?s), "{self.base_iri}/"))
            }}
        """

        sparql.setQuery(data_query)
        sparql.setReturnFormat(JSON)
        data_results = sparql.query().convert()

        for result in data_results["results"]["bindings"]:
            entity_type = result["type"]["value"]
            entity_uri = result["s"]["value"]
            
            if entity_type in self.entity_type_abbr:
                try:
                    uri_parts = entity_uri.split(self.supplier_prefix)
                    if len(uri_parts) == 2:
                        number_str = uri_parts[1].strip("/")
                        number = int(number_str)
                        abbr = self.entity_type_abbr[entity_type]
                        max_numbers[abbr] = max(max_numbers[abbr], number)
                except (ValueError, IndexError):
                    print(f"Invalid URI format found for entity: {entity_uri}")

        prov_query = f"""
            SELECT ?entity
            WHERE {{
                ?snapshot <http://www.w3.org/ns/prov#specializationOf> ?entity .
            }}
        """

        sparql.setQuery(prov_query)
        prov_results = sparql.query().convert()

        for result in prov_results["results"]["bindings"]:
            entity_uri = result["entity"]["value"]
            
            # Per la provenance, cerchiamo direttamente l'abbreviazione nell'URI
            for abbr in set(self.entity_type_abbr.values()):
                if f"/{abbr}/" in entity_uri:
                    try:
                        uri_parts = entity_uri.split(self.supplier_prefix)
                        if len(uri_parts) == 2:
                            number_str = uri_parts[1].strip("/")
                            number = int(number_str)
                            max_numbers[abbr] = max(max_numbers[abbr], number)
                    except (ValueError, IndexError):
                        print(f"Invalid URI format found in provenance for entity: {entity_uri}")
                    break

        for entity_type, abbr in self.entity_type_abbr.items():
            self.counter_handler.set_counter(max_numbers[abbr], entity_type)
