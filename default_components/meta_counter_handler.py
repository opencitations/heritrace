# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import urllib.parse

import redis
from rdflib_ocdm.counter_handler.counter_handler import SupplierAwareCounterHandler

from default_components.meta_entities import META_DATA_ENTITY_TYPE_ABBR


class MetaCounterHandler(SupplierAwareCounterHandler):
    def __init__(self) -> None:
        """
        Constructor of the ``MetaCounterHandler`` class.
        Configure these values directly in this script.
        """
        host = "redis"
        port = 6379
        db = 0
        password = None
        supplier_prefix = "09110"

        if host is None or host == "redis":
            host = "localhost"

        # Store connection parameters for lazy initialization
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._redis_client = None

        self.base_iri = "https://w3id.org/oc/meta"
        self.short_names = ["ar", "br", "id", "ra", "re"]
        self.supplier_prefix = supplier_prefix
        self.entity_type_abbr = META_DATA_ENTITY_TYPE_ABBR

    @property
    def redis_client(self) -> redis.Redis:
        """Lazy initialization of Redis client."""
        if self._redis_client is None:
            self._redis_client = redis.Redis(
                host=self.host, port=self.port, db=self.db, password=self.password
            )
        return self._redis_client

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
            msg = "new_value must be a non negative integer!"
            raise ValueError(msg)

        namespace, processed_entity_name = self._process_entity_name(entity_name)
        key = f"{namespace}:{self.supplier_prefix}:{processed_entity_name}"
        self.redis_client.set(key, new_value)

    def read_counter(self, entity_name: str) -> int:
        """
        It allows to read the counter value of provenance entities.

        :param entity_name: The entity name
        :type entity_name: str
        :return: The requested counter value.
        """
        namespace, processed_entity_name = self._process_entity_name(entity_name)
        key = f"{namespace}:{self.supplier_prefix}:{processed_entity_name}"
        result = self.redis_client.get(key)

        if result:
            return int(result)  # type: ignore[arg-type]
        return 0

    def increment_counter(self, entity_name: str) -> int:
        """
        It allows to increment the counter value of graph
        and provenance entities by one unit.

        :param entity_name: The entity name
        :type entity_name: str
        :return: The newly-updated (already incremented) counter value.
        """
        namespace, processed_entity_name = self._process_entity_name(entity_name)
        key = f"{namespace}:{self.supplier_prefix}:{processed_entity_name}"
        return self.redis_client.incr(key)  # type: ignore[return-value]

    def close(self) -> None:
        """
        Closes the Redis connection.
        """
        if self.redis_client:
            self.redis_client.close()
