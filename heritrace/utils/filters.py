# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

import threading
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from rdflib import RDF
from SPARQLWrapper import JSON

from heritrace.apis.orcid import is_orcid_url, orcid_agent
from heritrace.apis.zenodo import is_zenodo_url, zenodo_source
from heritrace.sparql import (
    SPARQLWrapperWithRetry,
    get_sparql_bindings,
    select_results,
)
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
    from rdflib import Dataset, Graph, URIRef

VERSION_SOURCE_MARKER = "/prov/se/"


class Filter:
    def __init__(
        self, context: dict, display_rules: list[dict] | None, sparql_endpoint: str
    ) -> None:
        self.context = context
        self.display_rules = display_rules
        self.sparql_endpoint = sparql_endpoint
        self._thread_local = threading.local()
        self._query_lock = threading.Lock()

    def _get_sparql(self) -> SPARQLWrapperWithRetry:
        if not hasattr(self._thread_local, "sparql"):
            sparql = SPARQLWrapperWithRetry(self.sparql_endpoint, timeout=30.0)
            sparql.setReturnFormat(JSON)
            self._thread_local.sparql = sparql
        return self._thread_local.sparql

    @staticmethod
    def _find_display_name_from_rule(
        rule: dict,
        predicate_uri: str,
        object_shape_uri: str | None,
    ) -> str | None:
        if "displayProperties" not in rule:
            return None
        for display_property in rule["displayProperties"]:
            prop_uri = display_property.get("property") or display_property.get(
                "virtual_property"
            )
            if prop_uri == str(predicate_uri):
                if "displayRules" in display_property:
                    if object_shape_uri:
                        for display_rule in display_property["displayRules"]:
                            if display_rule.get("shape") == object_shape_uri:
                                return display_rule["displayName"]
                    return display_property["displayRules"][0]["displayName"]
                if "displayName" in display_property:
                    return display_property["displayName"]
        return None

    def human_readable_predicate(
        self,
        predicate_uri: str,
        entity_key: tuple[str | None, str | None],
        *,
        object_shape_uri: str | None = None,
    ) -> str:
        from heritrace.utils.display_rules_utils import (  # noqa: PLC0415
            find_matching_rule,
        )

        class_uri, shape_uri = entity_key
        rule = find_matching_rule(class_uri, shape_uri, self.display_rules)

        if rule:
            display_name = self._find_display_name_from_rule(
                rule, predicate_uri, object_shape_uri
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
        from heritrace.utils.display_rules_utils import (  # noqa: PLC0415
            find_matching_rule,
        )
        from heritrace.utils.shacl_utils import (  # noqa: PLC0415
            determine_shape_for_classes,
        )

        if entity_key is None:
            return "Unknown"

        class_uri, shape_uri = entity_key

        if class_uri is None and shape_uri is None:
            return "Unknown"

        if shape_uri is None and class_uri is not None:
            shape_uri = determine_shape_for_classes([class_uri])
        rule = find_matching_rule(class_uri, shape_uri, self.display_rules)

        if rule and "displayName" in rule:
            return rule["displayName"]

        if class_uri is None:
            return "Unknown"
        return format_uri_as_readable(class_uri)

    def human_readable_entity(
        self,
        uri: str | URIRef,
        entity_key: tuple[str | None, str | None],
        graph: Graph | Dataset | None = None,
    ) -> str:
        from heritrace.utils.display_rules_utils import (  # noqa: PLC0415
            find_matching_rule,
        )

        uri_string = str(uri)
        rule = find_matching_rule(entity_key[0], entity_key[1], self.display_rules)
        if not rule:
            return uri_string

        if "fetchUriDisplay" in rule:
            return self.get_fetch_uri_display(uri_string, rule, graph)

        if "displayName" in rule:
            return rule["displayName"]

        return uri_string

    def get_fetch_uri_display(
        self,
        uri: str | URIRef,
        rule: dict,
        graph: Graph | Dataset | None = None,
    ) -> str:
        uri_string = str(uri)
        query = rule["fetchUriDisplay"].replace("[[uri]]", f"<{uri_string}>")

        if graph is not None:
            with self._query_lock:
                results = graph.query(query)
            for row in select_results(results):
                display = row["display"]
                if display is not None:
                    return str(display)
        else:
            sparql = self._get_sparql()
            sparql.setQuery(query)
            bindings = get_sparql_bindings(sparql.query().convert())
            if bindings:
                return bindings[0]["display"]["value"]

        msg = f"fetchUriDisplay returned no result for {uri_string}"
        raise ValueError(msg)

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
    relation = field.get("intermediateRelation")
    if relation and relation.get("properties"):
        field["intermediateRelation"] = {
            **relation,
            "properties": {
                prop: [
                    field_with_labels(nested, custom_filter) for nested in nested_list
                ]
                for prop, nested_list in relation["properties"].items()
            },
        }
    return field
