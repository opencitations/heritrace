import urllib.parse
import redis


class MetaCounterHandler:
    def __init__(self, host='localhost', port=6379, db=0, password=None) -> None:
        """
        Constructor of the ``MetaCounterHandler`` class.

        :param host: Redis host address
        :type host: str
        :param port: Redis port number
        :type port: int
        :param db: Redis database number
        :type db: int
        :param password: Redis password if required
        :type password: str
        """
        self.redis_client = redis.Redis(host=host, port=port, db=db, password=password)

        self.base_iri = "https://w3id.org/oc/meta/"
        self.short_names = ["ar", "br", "id", "ra", "re"]
        self.supplier_prefix = "060"

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

    def _process_entity_name(self, entity_name: str) -> tuple:
        """
        Process the entity name and format it for Redis storage.

        :param entity_name: The entity name
        :type entity_name: str
        :return: A tuple containing the namespace and the processed entity name
        :rtype: tuple
        """
        entity_name_str = str(entity_name)
        if entity_name_str in self.entity_type_abbr:
            return ("data", self.entity_type_abbr[entity_name_str])
        else:
            return ("prov", urllib.parse.quote(entity_name_str))

    def set_counter(self, new_value: int, entity_name: str) -> None:
        """
        It allows to set the counter value of provenance entities.

        :param new_value: The new counter value to be set
        :type new_value: int
        :param entity_name: The entity name
        :type entity_name: str
        :raises ValueError: if ``new_value`` is a negative integer.
        :return: None
        """
        if new_value < 0:
            raise ValueError("new_value must be a non negative integer!")

        namespace, processed_entity_name = self._process_entity_name(entity_name)
        key = f"{namespace}:{processed_entity_name}"
        self.redis_client.set(key, new_value)

    def read_counter(self, entity_name: str) -> int:
        """
        It allows to read the counter value of provenance entities.

        :param entity_name: The entity name
        :type entity_name: str
        :return: The requested counter value.
        """
        namespace, processed_entity_name = self._process_entity_name(entity_name)
        key = f"{namespace}:{processed_entity_name}"
        result = self.redis_client.get(key)

        if result:
            return int(result)
        else:
            return 0

    def increment_counter(self, entity_name: str) -> int:
        """
        It allows to increment the counter value of graph and provenance entities by one unit.

        :param entity_name: The entity name
        :type entity_name: str
        :return: The newly-updated (already incremented) counter value.
        """
        namespace, processed_entity_name = self._process_entity_name(entity_name)
        key = f"{namespace}:{processed_entity_name}"
        new_count = self.redis_client.incr(key)
        return new_count

    def close(self):
        """
        Closes the Redis connection.
        """
        if self.redis_client:
            self.redis_client.close()
