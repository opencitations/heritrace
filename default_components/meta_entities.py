# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from typing import Protocol

META_DATA_ENTITY_TYPE_ABBR = {
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
}

META_URI_ENTITY_TYPE_ABBR = {
    **META_DATA_ENTITY_TYPE_ABBR,
    "http://purl.org/spar/cito/Citation": "ci",
    "http://www.w3.org/2002/07/owl#Thing": "en",
}
META_SHORT_NAMES = frozenset(META_URI_ENTITY_TYPE_ABBR.values())


class MetaCounterHandlerProtocol(Protocol):
    base_iri: str
    supplier_prefix: str

    def set_counter(self, new_value: int, entity_name: str) -> None: ...

    def read_counter(self, entity_name: str) -> int: ...

    def increment_counter(self, entity_name: str) -> int: ...
