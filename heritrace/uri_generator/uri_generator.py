from abc import ABC, abstractmethod


class URIGenerator(ABC): # pragma: no cover
    """
    Abstract base class for URI generators.
    """

    @abstractmethod
    def generate_uri(self, entity_type: str | None = None, context_data: dict = None) -> str:
        """
        Generate a new URI for an entity of the given type.

        :param entity_type: The type of entity to generate a URI for
        :type entity_type: str
        :param context_data: Additional context data for special URI generation.
            Expected structure:
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
        :type context_data: dict
        :return: The generated URI
        :rtype: str
        """
        pass

    @abstractmethod
    def initialize_counters(self, sparql) -> None:
        """
        Initialize counters for entity types supported by this URI generator.

        :param sparql: SPARQLWrapper instance to execute queries on the dataset
        :return: None
        """
        pass
