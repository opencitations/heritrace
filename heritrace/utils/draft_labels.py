# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from uuid import uuid4

from rdflib import RDF, Graph, Literal, URIRef

from heritrace.extensions import get_custom_filter, get_form_fields
from heritrace.language import is_tagged, tagged_literal
from heritrace.utils.datatypes import determine_datatype
from heritrace.utils.shacl_presentation import inverse_predicate
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
            if is_tagged(value):
                node = tagged_literal(value)
            elif isinstance(value, dict):
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


def draft_label(entry: dict) -> str | None:
    graph = Graph()
    entity = entry["entity"]
    uri = add_draft_entity(graph, entity)
    parent = URIRef(f"urn:heritrace:draft:{uuid4()}")
    graph.add((parent, RDF.type, URIRef(entry["parent_class"])))
    inverse_of = inverse_predicate(entry["predicate"])
    if inverse_of is None:
        graph.add((parent, URIRef(entry["predicate"]), uri))
    else:
        graph.add((uri, URIRef(inverse_of), parent))
    custom_filter = get_custom_filter()
    if not custom_filter.has_label(entity["entity_shape"]):
        return None
    label = custom_filter.entity_label(uri, entity["entity_shape"], graph)
    if label is None:
        return None
    label = label.strip()
    if label and "urn:heritrace:draft:" not in label:
        return label
    return None
