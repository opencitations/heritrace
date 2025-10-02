import re
from collections import defaultdict

from heritrace.uri_generator.uri_generator import URIGenerator
from rdflib import URIRef
from SPARQLWrapper import JSON, SPARQLWrapper


class InvalidURIFormatError(Exception):
    """Exception raised when an URI has an invalid format."""
    pass


class MetaURIGenerator(URIGenerator):
    def __init__(self, counter_handler):
        """
        Initialize MetaURIGenerator with hardcoded configuration.
        Configure these values directly in this script.

        :param counter_handler: Counter handler instance for URI generation
        """
        # Configuration - modify these values directly
        self.base_iri = 'https://w3id.org/oc/meta'
        self.supplier_prefix_regex = '0[6|9][1-9]+0'
        self.new_supplier_prefix = '09110'
        
        self.counter_handler = counter_handler
        self.counter_handler.supplier_prefix = self.new_supplier_prefix
        
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
            "http://purl.org/spar/cito/Citation": "ci",
            "http://www.w3.org/2002/07/owl#Thing": "en",
        }

    def generate_uri(self, entity_type: str, context_data: dict = None) -> str:
        """
        Generate a URI for the given entity type.

        For Citation entities, generates URIs in the format:
        https://w3id.org/oc/meta/ci/{citing_omid}-{cited_omid}

        :param entity_type: The RDF type of the entity
        :param context_data: Entity data containing properties. For Citations, expects:
            {
                "entity_type": "http://purl.org/spar/cito/Citation",
                "properties": {
                    "http://purl.org/spar/cito/hasCitingEntity": [
                        {
                            "is_existing_entity": True,
                            "entity_uri": "https://w3id.org/oc/meta/br/061503302037"
                        }
                    ],
                    "http://purl.org/spar/cito/hasCitedEntity": [
                        {
                            "is_existing_entity": True,
                            "entity_uri": "https://w3id.org/oc/meta/br/061503302004"
                        }
                    ]
                }
            }
        :return: Generated URI as URIRef
        """
        if entity_type == "http://purl.org/spar/cito/Citation" and context_data:
            citing_entity = None
            cited_entity = None

            properties = context_data.get("properties", {})
            for prop_key, prop_value in properties.items():
                if prop_key == "http://purl.org/spar/cito/hasCitingEntity":
                    if isinstance(prop_value, list) and len(prop_value) > 0:
                        first_value = prop_value[0]
                        if isinstance(first_value, dict) and first_value.get("is_existing_entity"):
                            citing_entity = first_value.get("entity_uri")
                        else:
                            citing_entity = first_value
                elif prop_key == "http://purl.org/spar/cito/hasCitedEntity":
                    if isinstance(prop_value, list) and len(prop_value) > 0:
                        first_value = prop_value[0]
                        if isinstance(first_value, dict) and first_value.get("is_existing_entity"):
                            cited_entity = first_value.get("entity_uri")
                        else:
                            cited_entity = first_value

            if citing_entity and cited_entity:
                citing_omid = self._extract_omid_from_uri(str(citing_entity))
                cited_omid = self._extract_omid_from_uri(str(cited_entity))

                if citing_omid and cited_omid:
                    uri = f"{self.base_iri}/ci/{citing_omid}-{cited_omid}"
                    return URIRef(uri)

        last_used = self.counter_handler.read_counter(entity_type)
        next_number = last_used + 1
        self.counter_handler.set_counter(next_number, entity_type)
        return URIRef(
            f"{self.base_iri}/{self.entity_type_abbr[entity_type]}/{self.new_supplier_prefix}{next_number}"
        )

    def _extract_omid_from_uri(self, uri_string: str) -> str:
        """Extract the OMID (numerical part) from a URI using regex pattern."""
        if not uri_string:
            return None

        escaped_base = re.escape(self.base_iri)
        abbr_pattern = '|'.join(re.escape(abbr) for abbr in self.entity_type_abbr.values())

        pattern = f'^{escaped_base}/({abbr_pattern})/(.+)$'
        match = re.match(pattern, uri_string)

        if match:
            return match.group(2)

        return None

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
                if entity_type == "http://purl.org/spar/cito/Citation":
                    # Citations use special URI generation and are counted only in provenance
                    continue

                try:
                    numeric_part = entity_uri.rsplit('/', 1)[-1]
                    match = re.search(self.supplier_prefix_regex, numeric_part)
                    if match:
                        supplier_prefix = match.group()
                        number_str = numeric_part[match.end():]
                        if number_str:
                            number = int(number_str)
                            abbr = self.entity_type_abbr[entity_type]
                            old_max = max_numbers_by_prefix[supplier_prefix][abbr]
                            max_numbers_by_prefix[supplier_prefix][abbr] = max(old_max, number)
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

            if "/ci/" in entity_uri:
                continue

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
                if entity_type == "http://purl.org/spar/cito/Citation":
                    continue
                counter_value = max_numbers[abbr]
                self.counter_handler.set_counter(counter_value, entity_type)

            # Restore original prefix
            self.counter_handler.supplier_prefix = original_prefix