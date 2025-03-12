from abc import ABC, abstractmethod


class URIGenerator(ABC): # pragma: no cover
    """
    Abstract base class for URI generators.
    """

    @abstractmethod
    def generate_uri(self, entity_type: str | None = None) -> str:
        """
        Generate a new URI for an entity of the given type.

        :param entity_type: The type of entity to generate a URI for
        :type entity_type: str
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
