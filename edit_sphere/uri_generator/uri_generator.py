from abc import ABC, abstractmethod

class URIGenerator(ABC):
    @abstractmethod
    def generate_uri(self, entity_type: str|None = None) -> str:
        pass