from abc import ABC, abstractmethod


class URIGenerator(ABC): # pragma: no cover
    @abstractmethod
    def generate_uri(self, entity_type: str | None = None) -> str:
        pass
