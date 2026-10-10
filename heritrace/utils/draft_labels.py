# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from uuid import uuid4

from rdflib import RDF, Graph, Literal, URIRef

from heritrace.extensions import get_form_fields
from heritrace.sparql import select_results
from heritrace.utils.datatypes import determine_datatype
from heritrace.utils.display_rules_utils import find_matching_rule
from heritrace.utils.shacl_utils import find_matching_form_field
from heritrace.utils.uri_utils import is_valid_url


def add_draft_entity(graph: Graph, entity: dict) -> URIRef:
    if entity.get("is_existing_entity"):
        uri = URIRef(entity["entity_uri"])
        if "properties" not in entity:
            return uri
    else:
        uri = URIRef(f"urn:heritrace:draft:{uuid4()}")
    graph.add((uri, RDF.type, URIRef(entity["entity_type"])))
    form_fields = get_form_fields()
    key = find_matching_form_field(
        entity["entity_type"], entity["entity_shape"], form_fields
    )
    for predicate, raw_values in entity["properties"].items():
        values = raw_values if isinstance(raw_values, list) else [raw_values]
        for value in values:
            if isinstance(value, dict):
                node = add_draft_entity(graph, value)
            elif is_valid_url(str(value)):
                node = URIRef(value)
            else:
                datatypes = []
                if key and predicate in form_fields[key]:
                    fields = form_fields[key][predicate]
                    if fields and "datatypes" in fields[0]:
                        datatypes = fields[0]["datatypes"]
                node = Literal(
                    value, datatype=determine_datatype(str(value), datatypes)
                )
            graph.add((uri, URIRef(predicate), node))
    return uri


def relation_display_query(entry: dict) -> str | None:
    parent_rule = find_matching_rule(entry["parent_class"], entry["parent_shape"])
    if not parent_rule or "displayProperties" not in parent_rule:
        return None
    for prop in parent_rule["displayProperties"]:
        if prop.get("property") != entry["predicate"]:
            continue
        candidates = [prop]
        if "displayRules" in prop:
            candidates = prop["displayRules"]
        for rule in candidates:
            if "shape" in rule and rule["shape"] != entry["entity"]["entity_shape"]:
                continue
            if "fetchValueFromQuery" in rule:
                return rule["fetchValueFromQuery"]
    return None


def draft_label(entry: dict) -> str | None:
    graph = Graph()
    entity = entry["entity"]
    uri = add_draft_entity(graph, entity)
    parent = URIRef(f"urn:heritrace:draft:{uuid4()}")
    graph.add((parent, RDF.type, URIRef(entry["parent_class"])))
    graph.add((parent, URIRef(entry["predicate"]), uri))
    query = relation_display_query(entry)
    if query is None:
        rule = find_matching_rule(entity["entity_type"], entity["entity_shape"])
        if rule and "fetchUriDisplay" in rule:
            query = rule["fetchUriDisplay"]
    if query is None:
        return None
    query = (
        query.replace("[[subject]]", parent.n3())
        .replace("[[value]]", uri.n3())
        .replace("[[uri]]", uri.n3())
    )
    for row in select_results(graph.query(query)):
        if row[0] is not None:
            label = str(row[0]).strip()
            if label and "urn:heritrace:draft:" not in label:
                return label
    return None
