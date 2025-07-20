import re
from collections import defaultdict

from heritrace.uri_generator.uri_generator import URIGenerator
from rdflib import URIRef
from heritrace.meta_counter_handler import MetaCounterHandler
from SPARQLWrapper import JSON, SPARQLWrapper


class InvalidURIFormatError(Exception):
    """Exception raised when an URI has an invalid format."""
    pass


class MetaURIGenerator(URIGenerator):
    def __init__(
        self, base_iri: str, supplier_prefix_regex: str, new_supplier_prefix: str, counter_handler: MetaCounterHandler
    ):
        self.base_iri = base_iri
        self.supplier_prefix_regex = supplier_prefix_regex
        self.new_supplier_prefix = new_supplier_prefix
        self.counter_handler = counter_handler
        self.counter_handler.supplier_prefix = new_supplier_prefix
        self.entity_type_abbr = {
            "http://purl.org/spar/fabio/Expression": "br",
            "http://purl.org/spar/fabio/Article": "br",
            "http://purl.org/spar/fabio/JournalArticle": "br",
            "http://purl.org/spar/fabio/Book": "br",
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
            "http://www.w3.org/2002/07/owl#Thing": "en",
        }

    def generate_uri(self, entity_type: str) -> str:
        last_used = self.counter_handler.read_counter(entity_type)
        next_number = last_used + 1
        self.counter_handler.set_counter(next_number, entity_type)
        return URIRef(
            f"{self.base_iri}/{self.entity_type_abbr[entity_type]}/{self.new_supplier_prefix}{next_number}"
        )

    def initialize_counters(self, sparql: SPARQLWrapper):
        """
        Initialize counters for entity types supported by this URI generator.
        Extracts sequential numbers from both data and provenance for each abbreviation,
        grouping by supplier prefix to maintain separate counters.
        
        :param sparql: SPARQLWrapper instance to execute queries on the dataset
        :raises InvalidURIFormatError: If an URI with invalid format is found
        """
        max_numbers_by_prefix = defaultdict(lambda: defaultdict(int))

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
                    numeric_part = entity_uri.rsplit('/', 1)[-1]
                    match = re.search(self.supplier_prefix_regex, numeric_part)
                    if match:
                        supplier_prefix = match.group()
                        number_str = numeric_part[match.end():]
                        if number_str:
                            number = int(number_str)
                            abbr = self.entity_type_abbr[entity_type]
                            max_numbers_by_prefix[supplier_prefix][abbr] = max(max_numbers_by_prefix[supplier_prefix][abbr], number)
                    else:
                        pass
                except (ValueError, IndexError):
                    raise InvalidURIFormatError(f"Invalid URI format found for entity: {entity_uri}")

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
            
            # For provenance, we directly search for the abbreviation in the URI
            numeric_part = entity_uri.rsplit('/', 1)[-1]
            match = re.search(self.supplier_prefix_regex, numeric_part)
            if match:
                supplier_prefix = match.group()
                # For provenance, we need to find the abbreviation in the URI to associate the counter correctly.
                for abbr in set(self.entity_type_abbr.values()):
                    if f"/{abbr}/" in entity_uri:
                        try:
                            number_str = numeric_part[match.end():]
                            if number_str:
                                number = int(number_str)
                                max_numbers_by_prefix[supplier_prefix][abbr] = max(max_numbers_by_prefix[supplier_prefix][abbr], number)
                        except (ValueError, IndexError):
                            raise InvalidURIFormatError(f"Invalid URI format found in provenance for entity: {entity_uri}")
                        break

        # Set counters for all found prefixes
        for supplier_prefix, max_numbers in max_numbers_by_prefix.items():
            # Temporarily set the supplier prefix for the counter handler
            original_prefix = self.counter_handler.supplier_prefix
            self.counter_handler.supplier_prefix = supplier_prefix
            
            for entity_type, abbr in self.entity_type_abbr.items():
                self.counter_handler.set_counter(max_numbers[abbr], entity_type)
            
            # Restore original prefix
            self.counter_handler.supplier_prefix = original_prefix
