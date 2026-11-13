# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, cast
from urllib.parse import urlparse

from rdflib import RDF, RDFS, Literal, URIRef
from SPARQLWrapper import JSON

from heritrace.apis.orcid import is_orcid_url, orcid_agent
from heritrace.apis.zenodo import is_zenodo_url, zenodo_source
from heritrace.language import NEUTRAL, LocalizedText, localize
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
    from collections.abc import Callable, Mapping

    from rdflib import Dataset, Graph

    from heritrace.sparql import SparqlEndpoint
    from heritrace.utils.shacl_presentation import ShapesPresentation

VERSION_SOURCE_MARKER = "/prov/se/"


class Filter:
    def __init__(
        self,
        presentation: ShapesPresentation,
        new_sparql: Callable[[], SparqlEndpoint],
    ) -> None:
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
        return readable_local_name(predicate_uri)

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

    def _data_labels(
        self, values: list[str], graph: Graph | Dataset | None
    ) -> dict[str, LocalizedText]:
        if not values:
            return {}
        query = (
            "SELECT ?value ?label WHERE { VALUES ?value { "
            + " ".join(URIRef(value).n3() for value in values)
            + f" }} ?value {RDFS.label.n3()} ?label }}"
        )
        labels: dict[str, LocalizedText] = {}
        if graph is not None:
            with self._query_lock:
                results = graph.query(query)
            for value, label in select_results(results):
                if isinstance(label, Literal):
                    labels.setdefault(str(value), {})[label.language or NEUTRAL] = str(
                        label
                    )
            return labels
        sparql = self._get_sparql()
        sparql.setQuery(query)
        for binding in get_sparql_bindings(sparql.query().convert()):
            label = binding["label"]
            labels.setdefault(binding["value"]["value"], {})[
                label.get("xml:lang", NEUTRAL)
            ] = label["value"]
        return labels

    # SHACL UI Label Resolution for value nodes: the label role of the value's
    # shape, then rdfs:label in the data and in the shapes, then the local name.
    def value_labels(
        self,
        shapes: Mapping[URIRef | Literal, str | None],
        graph: Graph | Dataset | None = None,
    ) -> dict[URIRef | Literal, str]:
        labels: dict[URIRef | Literal, str] = {}
        unlabelled = []
        for value, shape in shapes.items():
            if isinstance(value, Literal):
                labels[value] = str(value)
                continue
            if self.has_label(shape):
                label = self.entity_label(str(value), shape, graph)
                if label is not None:
                    labels[value] = label
                    continue
            unlabelled.append(value)
        data_labels = self._data_labels(
            [str(value) for value in unlabelled if isinstance(value, URIRef)], graph
        )
        for value in unlabelled:
            labels[value] = (
                localize(data_labels.get(str(value), {}))
                or self.presentation.value_name(str(value))
                or readable_local_name(str(value))
            )
        return labels

    def value_label(
        self,
        value: URIRef | Literal | str,
        entity_key: tuple[str | None, str | None] = (None, None),
        graph: Graph | Dataset | None = None,
    ) -> str:
        node = value if isinstance(value, URIRef | Literal) else URIRef(value)
        return self.value_labels({node: self._shape_for(entity_key)}, graph)[node]

    def value_description(self, value: str) -> str | None:
        return self.presentation.value_description(value)

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


# A capital starts a word after a lowercase letter or a digit, or when it
# closes an acronym and a lowercase letter follows: NCName gives NC and Name.
def _starts_word(name: str, i: int) -> bool:
    if i == 0 or not name[i].isupper():
        return False
    previous = name[i - 1]
    if previous.islower() or previous.isdigit():
        return True
    return previous.isupper() and i + 1 < len(name) and name[i + 1].islower()


# Values that reach the server as text, such as the members of sh:in, are
# literals unless they read as IRIs.
def value_node(value: str) -> URIRef | Literal:
    return URIRef(value) if is_valid_url(value) else Literal(value)


def readable_local_name(uri: str) -> str:
    return format_uri_as_readable(uri) or uri


def format_uri_as_readable(uri: str) -> str:
    _, name = split_namespace(uri)
    words = [""]
    for i, char in enumerate(name):
        if _starts_word(name, i):
            words.append("")
        words[-1] += char
    text = " ".join(
        word if len(word) > 1 and word.isupper() else word.lower() for word in words
    )
    return text[:1].upper() + text[1:]


def field_with_labels(details: dict, custom_filter: Filter) -> dict:
    """Copy a form field adding the labels the client shows for fixed values."""
    field = dict(details)
    for key in ("displayName", "description"):
        if key in field:
            field[key] = localize(field[key])
    if "conditions" in field:
        field["conditions"] = [
            alternative.as_condition() for alternative in field["conditions"]
        ]
    has_value = field.get("hasValue")
    if has_value:
        field["hasValueLabel"] = (
            custom_filter.human_readable_class((has_value, None))
            if field.get("uri") == str(RDF.type)
            else custom_filter.value_label(has_value)
        )
    if field.get("optionalValues"):
        labels = custom_filter.value_labels(
            {value_node(value): None for value in field["optionalValues"]}
        )
        field["optionalValueLabels"] = {
            str(value): label for value, label in labels.items()
        }
        field["optionalValueDescriptions"] = {
            value: description
            for value in field["optionalValues"]
            if (description := custom_filter.value_description(value))
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
