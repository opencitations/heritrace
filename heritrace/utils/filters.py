# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, cast
from urllib.parse import urlparse

from rdflib import RDF
from SPARQLWrapper import JSON

from heritrace.apis.orcid import is_orcid_url, orcid_agent
from heritrace.apis.zenodo import is_zenodo_url, zenodo_source
from heritrace.sparql import get_sparql_bindings, select_results
from heritrace.utils.references import (
    AgentRef,
    SourceRef,
    text_agent,
    text_source,
    unknown_agent,
    unknown_source,
    url_agent,
    url_source,
)
from heritrace.utils.uri_utils import is_valid_url

if TYPE_CHECKING:
    from collections.abc import Callable

    from rdflib import Dataset, Graph, URIRef

    from heritrace.sparql import SparqlEndpoint
    from heritrace.utils.shacl_presentation import ShapesPresentation

VERSION_SOURCE_MARKER = "/prov/se/"


class Filter:
    def __init__(
        self,
        context: dict,
        presentation: ShapesPresentation,
        new_sparql: Callable[[], SparqlEndpoint],
    ) -> None:
        self.context = context
        self.presentation = presentation
        self.new_sparql = new_sparql
        self._thread_local = threading.local()
        self._query_lock = threading.Lock()

    def _get_sparql(self) -> SparqlEndpoint:
        if not hasattr(self._thread_local, "sparql"):
            sparql = self.new_sparql()
            sparql.setReturnFormat(JSON)
            self._thread_local.sparql = sparql
        return self._thread_local.sparql

    @staticmethod
    def _shape_for(entity_key: tuple[str | None, str | None]) -> str | None:
        from heritrace.utils.shacl_utils import (  # noqa: PLC0415
            determine_shape_for_classes,
        )

        class_uri, shape_uri = entity_key
        if shape_uri is None and class_uri is not None:
            return determine_shape_for_classes([class_uri])
        return shape_uri

    def human_readable_predicate(
        self,
        predicate_uri: str,
        entity_key: tuple[str | None, str | None],
        *,
        object_shape_uri: str | None = None,
    ) -> str:
        display_name = self.presentation.property_name(
            self._shape_for(entity_key), str(predicate_uri), object_shape_uri
        )
        if display_name is not None:
            return display_name

        first_part, _ = split_namespace(predicate_uri)
        if first_part in self.context:
            return format_uri_as_readable(predicate_uri)
        return str(predicate_uri)

    def human_readable_class(
        self, entity_key: tuple[str | None, str | None] | None
    ) -> str:
        if entity_key is None:
            return "Unknown"

        class_uri, shape_uri = entity_key

        if class_uri is None and shape_uri is None:
            return "Unknown"

        display_name = self.presentation.shape_name(self._shape_for(entity_key))
        if display_name is not None:
            return display_name

        if class_uri is None:
            return "Unknown"
        return format_uri_as_readable(class_uri)

    def has_label(self, shape: str | None) -> bool:
        return shape in self.presentation.label_queries

    def entity_label(
        self,
        uri: str | URIRef,
        shape: str | None,
        graph: Graph | Dataset | None = None,
    ) -> str | None:
        query = cast("str", self.presentation.label_query(shape, str(uri)))
        if graph is not None:
            with self._query_lock:
                results = graph.query(query)
            for row in select_results(results):
                if row[0] is not None:
                    return str(row[0])
            return None
        sparql = self._get_sparql()
        sparql.setQuery(query)
        result = sparql.query().convert()
        bindings = get_sparql_bindings(result)
        if not bindings:
            return None
        label_variable = cast("dict", result)["head"]["vars"][0]
        if label_variable not in bindings[0]:
            return None
        return bindings[0][label_variable]["value"]

    def human_readable_entity(
        self,
        uri: str | URIRef,
        entity_key: tuple[str | None, str | None],
        graph: Graph | Dataset | None = None,
    ) -> str:
        uri_string = str(uri)
        shape = self._shape_for(entity_key)
        if not self.has_label(shape):
            return uri_string
        label = self.entity_label(uri_string, shape, graph)
        if label is None:
            msg = f"The label query returned no result for {uri_string}"
            raise ValueError(msg)
        return label

    # The catalogue lists every instance of a type, also incomplete ones.
    def catalogue_label(
        self,
        uri: str | URIRef,
        entity_key: tuple[str | None, str | None],
    ) -> str:
        shape = self._shape_for(entity_key)
        label = self.entity_label(uri, shape) if self.has_label(shape) else None
        return str(uri) if label is None else label

    # An entity with a type but no label is named after its type.
    def entity_title(
        self,
        uri: str | URIRef,
        entity_key: tuple[str | None, str | None],
        graph: Graph | Dataset | None = None,
    ) -> str:
        class_uri, _ = entity_key
        if class_uri is not None and not self.has_label(self._shape_for(entity_key)):
            return self.human_readable_class(entity_key)
        return self.human_readable_entity(uri, entity_key, graph)

    def format_source_reference(self, url: str | None) -> SourceRef:
        if not url:
            return unknown_source()
        if is_zenodo_url(url):
            return zenodo_source(url)
        if VERSION_SOURCE_MARKER in url:
            entity_uri, timestamp = url.split(VERSION_SOURCE_MARKER, 1)
            return {
                "kind": "version",
                "url": url,
                "label": f"Version {timestamp}",
                "extra": None,
                "entity_uri": entity_uri,
                "timestamp": timestamp,
            }
        if is_valid_url(url):
            return url_source(url)
        return text_source(url)

    def format_agent_reference(self, url: str | None) -> AgentRef:
        if not url:
            return unknown_agent()
        if is_orcid_url(url):
            return orcid_agent(url)
        if is_valid_url(url):
            return url_agent(url)
        return text_agent(url)


def split_namespace(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.fragment:
        first_part = parsed.scheme + "://" + parsed.netloc + parsed.path + "#"
        last_part = parsed.fragment
    else:
        first_part = (
            parsed.scheme
            + "://"
            + parsed.netloc
            + "/".join(parsed.path.split("/")[:-1])
            + "/"
        )
        last_part = parsed.path.split("/")[-1]
    return first_part, last_part


def format_uri_as_readable(uri: str) -> str:
    _, last_part = split_namespace(uri)

    if last_part.islower():
        return last_part
    words = []
    word = ""
    for char in last_part:
        if char.isupper() and word:
            words.append(word)
            word = char
        else:
            word += char
    words.append(word)
    return " ".join(words).lower()


def field_with_labels(details: dict, custom_filter: Filter) -> dict:
    """Copy a form field adding the labels the client shows for fixed values."""
    field = dict(details)
    entity_key = (field.get("subjectClass"), field.get("subjectShape"))
    has_value = field.get("hasValue")
    if has_value:
        field["hasValueLabel"] = (
            custom_filter.human_readable_class((has_value, None))
            if field.get("uri") == str(RDF.type)
            else custom_filter.human_readable_predicate(has_value, entity_key)
        )
    if field.get("optionalValues"):
        field["optionalValueLabels"] = {
            value: custom_filter.human_readable_predicate(value, entity_key)
            for value in field["optionalValues"]
        }
    if field.get("nestedShape"):
        field["nestedShape"] = [
            field_with_labels(nested, custom_filter) for nested in field["nestedShape"]
        ]
    if field.get("or"):
        field["or"] = [
            {
                "displayName": custom_filter.human_readable_class(
                    (option.get("entityType"), option.get("nodeShape"))
                ),
                **field_with_labels(option, custom_filter),
            }
            for option in field["or"]
        ]
    return field
