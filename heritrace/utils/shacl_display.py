# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import json
from collections import OrderedDict, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from flask import Flask
from rdflib import Graph, URIRef
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.sparql import Query
from rdflib.query import Result, ResultRow

from heritrace.configuration.vocabulary import DASH, HT, SHUI
from heritrace.sparql import select_results
from heritrace.utils.filters import Filter
from heritrace.utils.shacl_patterns import (
    PatternAlternative,
    read_pattern_alternatives,
)
from heritrace.utils.shacl_presentation import (
    ShapesPresentation,
    inverse_path_key,
    inverse_predicate,
)


@dataclass(slots=True)
class ShaclProcessingContext:
    shacl: Graph
    presentation: ShapesPresentation
    pattern_alternatives: list[PatternAlternative]
    app: Flask
    processed_shapes: set[str]


@dataclass(slots=True)
class _ParsedRow:
    subject_shape: str
    entity_type: str
    predicate: str
    node_shape: str | None
    has_value: str | None
    object_class: str | None
    min_count: int
    max_count: int | None
    datatype: str | None
    optional_values: list[str]
    or_nodes: list[str]
    or_link_shapes: list[str]
    detail_paths: list[str]
    link_only: bool
    entity_key: tuple[str, str]
    node_shapes: list[str]
    name: str | None
    editor: str | None
    viewer: str | None
    composite: bool
    hidden: bool
    ordered_by: str | None


COMMON_SPARQL_QUERY = prepareQuery(
    """
    SELECT ?shape ?type ?path ?inverse ?node_shape ?link_shape ?link_class ?datatype
           ?max_count ?min_count ?has_value ?object_class
           ?name ?editor ?viewer ?composite ?hidden ?ordered_by
           (GROUP_CONCAT(?optional_value; separator=",")
            AS ?optional_values)
           (GROUP_CONCAT(?or_node; separator=",") AS ?or_nodes)
           (GROUP_CONCAT(?or_link_shape; separator=",") AS ?or_link_shapes)
           (GROUP_CONCAT(?detail_path; separator=",") AS ?detail_paths)
    WHERE {
        ?shape sh:targetClass ?type ;
               sh:property ?property .
        ?property sh:path ?path .
        OPTIONAL { ?path sh:inversePath ?inverse . }
        OPTIONAL {
            ?property sh:node ?node_shape .
            OPTIONAL {
                ?node_shape sh:targetClass ?object_class .
            }
        }
        OPTIONAL {
            ?property shui:editor shui:AutoCompleteEditor ;
                      sh:class ?link_class .
            ?link_shape sh:targetClass ?link_class .
            FILTER NOT EXISTS { ?property sh:node ?declared_node . }
        }
        OPTIONAL {
            { ?property sh:or ?orList . }
            UNION
            { ?property sh:qualifiedValueShape/sh:or ?orList . }
            {
                ?orList rdf:rest*/rdf:first ?or_constraint .
                ?or_constraint sh:datatype ?datatype .
            } UNION {
                ?orList rdf:rest*/rdf:first ?or_node_shape .
                ?or_node_shape sh:node ?or_node .
            } UNION {
                ?property shui:editor shui:AutoCompleteEditor .
                ?orList rdf:rest*/rdf:first ?or_link .
                ?or_link sh:class ?or_link_class .
                ?or_link_shape sh:targetClass ?or_link_class .
                FILTER NOT EXISTS { ?or_link sh:node ?or_declared_node . }
            } UNION {
                ?orList rdf:rest*/rdf:first ?or_constraint .
                ?or_constraint sh:hasValue ?optional_value .
            }
        }
        OPTIONAL { ?property sh:datatype ?datatype . }
        OPTIONAL {
            { ?property sh:maxCount ?max_count . }
            UNION
            { ?property sh:qualifiedMaxCount ?max_count . }
        }
        OPTIONAL {
            { ?property sh:minCount ?min_count . }
            UNION
            { ?property sh:qualifiedMinCount ?min_count . }
        }
        OPTIONAL {
            { ?property sh:hasValue ?has_value . }
            UNION
            { ?property sh:qualifiedValueShape/sh:hasValue ?has_value . }
        }
        OPTIONAL {
            ?property sh:in ?list .
            ?list rdf:rest*/rdf:first ?optional_value .
        }
        OPTIONAL { ?property sh:name ?name . }
        OPTIONAL { ?property shui:editor ?editor . }
        OPTIONAL { ?property shui:viewer ?viewer . }
        OPTIONAL { ?property dash:composite ?composite . }
        OPTIONAL { ?property dash:hidden ?hidden . }
        OPTIONAL { ?property ht:orderedBy ?chained_by . }
        BIND(COALESCE(
            ?chained_by,
            IF(BOUND(?node_shape)
               && EXISTS { ?node_shape sh:property/sh:path sh:order },
               sh:order, ?no_order)
        ) AS ?ordered_by)
        OPTIONAL { ?property sh:property/sh:path ?detail_path . }
        FILTER (isURI(?path) || BOUND(?inverse))
        FILTER NOT EXISTS { ?property sh:values ?computed . }
    }
    GROUP BY ?shape ?type ?path ?inverse ?node_shape ?link_shape ?link_class ?datatype
             ?max_count ?min_count ?has_value ?object_class
             ?name ?editor ?viewer ?composite ?hidden ?ordered_by
""",
    initNs={
        "sh": "http://www.w3.org/ns/shacl#",
        "shui": str(SHUI),
        "dash": str(DASH),
        "ht": str(HT),
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    },
)


def _parse_row(row: ResultRow) -> _ParsedRow:
    subject_shape = str(row.shape)
    entity_type = str(row.type)
    predicate = inverse_path_key(row.inverse) if row.inverse else str(row.path)
    linked_shape = row.node_shape or row.link_shape
    node_shape = str(linked_shape) if linked_shape else None
    has_value = str(row.has_value) if row.has_value else None
    linked_class = row.object_class or row.link_class
    object_class = str(linked_class) if linked_class else None
    min_count = 0 if row.min_count is None else int(row.min_count)
    max_count = None if row.max_count is None else int(row.max_count)
    datatype = str(row.datatype) if row.datatype else None
    optional_values = [v for v in (row.optional_values or "").split(",") if v]
    or_nodes = [v for v in (row.or_nodes or "").split(",") if v]
    or_link_shapes = [v for v in (row.or_link_shapes or "").split(",") if v]
    detail_paths = sorted({v for v in (row.detail_paths or "").split(",") if v})

    node_shapes = []
    if node_shape:
        node_shapes.append(node_shape)
    node_shapes.extend(or_nodes)
    node_shapes.extend(or_link_shapes)

    return _ParsedRow(
        subject_shape=subject_shape,
        entity_type=entity_type,
        predicate=predicate,
        node_shape=node_shape,
        has_value=has_value,
        object_class=object_class,
        min_count=min_count,
        max_count=max_count,
        datatype=datatype,
        optional_values=optional_values,
        or_nodes=or_nodes,
        or_link_shapes=or_link_shapes,
        detail_paths=detail_paths,
        link_only=row.node_shape is None and row.link_shape is not None,
        entity_key=(entity_type, subject_shape),
        node_shapes=node_shapes,
        name=str(row.name) if row.name else None,
        editor=str(row.editor) if row.editor else None,
        viewer=str(row.viewer) if row.viewer else None,
        composite=bool(row.composite),
        hidden=bool(row.hidden),
        ordered_by=str(row.ordered_by) if row.ordered_by else None,
    )


def _field_conditions(
    ctx: ShaclProcessingContext, parsed: _ParsedRow
) -> list[dict[str, object]]:
    return [
        alternative.as_condition()
        for alternative in ctx.pattern_alternatives
        if alternative.shape == parsed.subject_shape
        and alternative.path == parsed.predicate
    ]


def _find_existing_field(
    fields: list[dict[str, object]],
    parsed: _ParsedRow,
) -> dict[str, object] | None:
    for field in fields:
        if (
            field.get("nodeShape") == parsed.node_shape
            and field.get("nodeShapes") == parsed.node_shapes
            and field.get("subjectShape") == parsed.subject_shape
            and field.get("hasValue") == parsed.has_value
            and field.get("objectClass") == parsed.object_class
            and field.get("min") == parsed.min_count
            and field.get("max") == parsed.max_count
            and field.get("optionalValues") == parsed.optional_values
        ):
            return field
    return None


def _or_option(
    ctx: ShaclProcessingContext,
    parsed: _ParsedRow,
    custom_filter: Filter,
    node: str,
) -> dict[str, object]:
    target_class = get_shape_target_class(ctx.shacl, node)
    return {
        "entityType": target_class,
        "uri": parsed.predicate,
        "displayName": custom_filter.human_readable_class((target_class, node)),
        "subjectShape": parsed.subject_shape,
        "nodeShape": node,
        "min": parsed.min_count,
        "max": parsed.max_count,
        "hasValue": parsed.has_value,
        "objectClass": get_object_class(ctx.shacl, node, parsed.predicate),
        "optionalValues": parsed.optional_values,
        "conditions": _field_conditions(ctx, parsed),
        "autocomplete": parsed.editor == str(SHUI.AutoCompleteEditor),
        "detailsEditor": parsed.editor == str(SHUI.DetailsEditor),
        "detailsViewer": parsed.viewer == str(SHUI.DetailsViewer),
        "composite": parsed.composite,
        "hidden": parsed.hidden,
    }


def _process_or_nodes(
    ctx: ShaclProcessingContext,
    parsed: _ParsedRow,
    custom_filter: Filter,
    field_info: dict[str, object],
    depth: int,
) -> None:
    options: list[dict[str, object]] = []
    for node in parsed.or_nodes:
        option = _or_option(ctx, parsed, custom_filter, node)
        if node not in ctx.processed_shapes:
            option["nestedShape"] = process_nested_shapes(ctx, node, depth=depth + 1)
        options.append(option)
    for node in parsed.or_link_shapes:
        option = _or_option(ctx, parsed, custom_filter, node)
        option["objectClass"] = option["entityType"]
        option["nestedShape"] = []
        options.append(option)
    field_info["or"] = options


def _process_single_row(
    ctx: ShaclProcessingContext,
    parsed: _ParsedRow,
    custom_filter: Filter,
    form_fields: defaultdict[tuple[str, str], dict[str, list[dict[str, object]]]],
    depth: int,
) -> None:
    if parsed.predicate not in form_fields[parsed.entity_key]:
        form_fields[parsed.entity_key][parsed.predicate] = []

    existing_field = _find_existing_field(
        form_fields[parsed.entity_key][parsed.predicate], parsed
    )

    if existing_field:
        if parsed.datatype and str(parsed.datatype) not in cast(
            "list", existing_field.get("datatypes", [])
        ):
            cast("list", existing_field.setdefault("datatypes", [])).append(
                str(parsed.datatype)
            )
        return

    field_info: dict[str, object] = {
        "entityType": parsed.entity_type,
        "uri": parsed.predicate,
        "nodeShape": parsed.node_shape,
        "nodeShapes": parsed.node_shapes,
        "subjectShape": parsed.subject_shape,
        "entityKey": parsed.entity_key,
        "datatypes": [parsed.datatype] if parsed.datatype else [],
        "min": parsed.min_count,
        "max": parsed.max_count,
        "hasValue": parsed.has_value,
        "objectClass": parsed.object_class,
        "optionalValues": parsed.optional_values,
        "conditions": _field_conditions(ctx, parsed),
        "inputType": determine_input_type(parsed.editor, parsed.datatype),
        "autocomplete": parsed.editor == str(SHUI.AutoCompleteEditor),
        "detailsEditor": parsed.editor == str(SHUI.DetailsEditor),
        "detailsViewer": parsed.viewer == str(SHUI.DetailsViewer),
        "composite": parsed.composite,
        "hidden": parsed.hidden,
    }
    if parsed.name is not None:
        field_info["displayName"] = parsed.name
    if parsed.detail_paths:
        field_info["detailPaths"] = parsed.detail_paths
    if parsed.ordered_by is not None:
        field_info["orderedBy"] = parsed.ordered_by

    if parsed.link_only:
        field_info["nestedShape"] = []
    elif parsed.node_shape and parsed.node_shape not in ctx.processed_shapes:
        field_info["nestedShape"] = process_nested_shapes(
            ctx,
            parsed.node_shape,
            depth=depth + 1,
        )

    if parsed.or_nodes or parsed.or_link_shapes:
        _process_or_nodes(ctx, parsed, custom_filter, field_info, depth)

    form_fields[parsed.entity_key][parsed.predicate].append(field_info)


def process_query_results(
    ctx: ShaclProcessingContext,
    results: Iterable[ResultRow],
    depth: int = 0,
) -> defaultdict[tuple[str, str], dict[str, list[dict[str, object]]]]:
    form_fields: defaultdict[tuple[str, str], dict[str, list[dict[str, object]]]] = (
        defaultdict(dict)
    )

    with (Path(__file__).parent / "context.json").open() as config_file:
        context = json.load(config_file)["@context"]

    from heritrace.extensions import new_store_sparql  # noqa: PLC0415

    custom_filter = Filter(context, ctx.presentation, new_store_sparql)

    for row in results:
        parsed = _parse_row(row)
        _process_single_row(ctx, parsed, custom_filter, form_fields, depth)

    return form_fields


def process_nested_shapes(
    ctx: ShaclProcessingContext,
    shape_uri: str,
    depth: int = 0,
) -> list[dict[str, object]]:
    if shape_uri in ctx.processed_shapes:
        return []

    ctx.processed_shapes.add(shape_uri)
    init_bindings = {"shape": URIRef(shape_uri)}
    nested_results = execute_shacl_query(ctx.shacl, COMMON_SPARQL_QUERY, init_bindings)
    nested_fields = []

    temp_form_fields = process_query_results(
        ctx,
        select_results(nested_results),
        depth=depth,
    )

    temp_form_fields = order_form_fields(temp_form_fields, ctx.presentation)

    for entity_type in temp_form_fields:
        for predicate in temp_form_fields[entity_type]:
            nested_fields.extend(temp_form_fields[entity_type][predicate])

    ctx.processed_shapes.remove(shape_uri)
    return nested_fields


def _ordered_fields(
    fields: dict[str, list[dict[str, object]]],
    shape: str,
    presentation: ShapesPresentation,
) -> OrderedDict[str, list[dict[str, object]]]:
    predicate_order = presentation.predicate_order(shape)
    ordered: OrderedDict[str, list[dict[str, object]]] = OrderedDict()
    for predicate in [
        *[p for p in predicate_order if p in fields],
        *[p for p in fields if p not in predicate_order],
    ]:
        node_order = presentation.node_order(shape, predicate)
        ordered[predicate] = sorted(
            fields[predicate],
            key=lambda field: (
                node_order.index(cast("str", field.get("nodeShape")))
                if field.get("nodeShape") in node_order
                else len(node_order)
            ),
        )
    return ordered


def order_form_fields(
    form_fields: dict[
        tuple[str, str],
        dict[str, list[dict[str, object]]],
    ],
    presentation: ShapesPresentation,
) -> OrderedDict[
    tuple[str, str],
    OrderedDict[str, list[dict[str, object]]],
]:
    return OrderedDict(
        (entity_key, _ordered_fields(fields, entity_key[1], presentation))
        for entity_key, fields in form_fields.items()
    )


def determine_input_type(editor: str | None, datatype: str | None) -> str:
    if editor == str(SHUI.TextAreaEditor):
        return "textarea"
    if editor == str(SHUI.TextFieldEditor) or not datatype:
        return "text"

    datatype_to_input = {
        "http://www.w3.org/2001/XMLSchema#string": "text",
        "http://www.w3.org/2001/XMLSchema#integer": "number",
        "http://www.w3.org/2001/XMLSchema#decimal": "number",
        "http://www.w3.org/2001/XMLSchema#float": "number",
        "http://www.w3.org/2001/XMLSchema#double": "number",
        "http://www.w3.org/2001/XMLSchema#boolean": "checkbox",
        "http://www.w3.org/2001/XMLSchema#date": "date",
        "http://www.w3.org/2001/XMLSchema#time": "time",
        "http://www.w3.org/2001/XMLSchema#dateTime": "datetime-local",
        "http://www.w3.org/2001/XMLSchema#anyURI": "url",
        "http://www.w3.org/2001/XMLSchema#email": "email",
    }
    return datatype_to_input.get(str(datatype), "text")


def get_shape_target_class(shacl: Graph, shape_uri: str) -> str | None:
    query = prepareQuery(
        """
        SELECT ?targetClass
        WHERE {
            ?shape sh:targetClass ?targetClass .
        }
    """,
        initNs={"sh": "http://www.w3.org/ns/shacl#"},
    )
    results = execute_shacl_query(shacl, query, {"shape": URIRef(shape_uri)})
    for row in select_results(results):
        return str(row.targetClass)
    return None


def get_object_class(shacl: Graph, shape_uri: str, predicate_uri: str) -> str | None:
    query = prepareQuery(
        """
        SELECT DISTINCT ?targetClass
        WHERE {
            ?shape sh:property ?propertyShape .
            ?propertyShape sh:path ?predicate .
            {
                # Caso 1: definizione diretta con sh:node
                ?propertyShape sh:node ?nodeShape .
                ?nodeShape sh:targetClass ?targetClass .
            } UNION {
                # Caso 2: definizione diretta con sh:class
                ?propertyShape sh:class ?targetClass .
            } UNION {
                # Caso 3: definizione con sh:or che include node shapes
                ?propertyShape sh:or ?orList .
                ?orList rdf:rest*/rdf:first ?choice .
                {
                    ?choice sh:node ?nodeShape .
                    ?nodeShape sh:targetClass ?targetClass .
                } UNION {
                    ?choice sh:class ?targetClass .
                }
            }
        }
    """,
        initNs={
            "sh": "http://www.w3.org/ns/shacl#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        },
    )

    results = execute_shacl_query(
        shacl, query, {"shape": URIRef(shape_uri), "predicate": URIRef(predicate_uri)}
    )

    # Prendiamo il primo risultato valido
    for row in select_results(results):
        if row.targetClass:
            return str(row.targetClass)
    return None


def extract_shacl_form_fields(
    shacl: Graph | None,
    presentation: ShapesPresentation,
    app: Flask,
) -> (
    dict[
        tuple[str, str],
        dict[str, list[dict[str, object]]],
    ]
    | defaultdict[
        tuple[str, str],
        dict[str, list[dict[str, object]]],
    ]
):
    """
    Estrae i campi del form dalle shape SHACL.

    Args:
        shacl: The SHACL graph
        app: Flask application instance

    Returns:
        defaultdict: A dictionary where the keys are tuples (class, shape) and the
        values are dictionaries
                     of form fields with their properties.
    """
    if not shacl:
        return {}

    ctx = ShaclProcessingContext(
        shacl=shacl,
        presentation=presentation,
        pattern_alternatives=read_pattern_alternatives(shacl),
        app=app,
        processed_shapes=set(),
    )
    results = execute_shacl_query(shacl, COMMON_SPARQL_QUERY)
    return process_query_results(
        ctx,
        select_results(results),
        depth=0,
    )


def execute_shacl_query(
    shacl: Graph,
    query: Query,
    init_bindings: dict[str, URIRef] | None = None,
) -> Result:
    """
    Esegue una query SPARQL sul grafo SHACL con eventuali binding iniziali.

    Args:
        shacl (Graph): The SHACL graph on which to execute the query.
        query (PreparedQuery): The prepared SPARQL query.
        init_bindings (dict): Initial bindings for the query.

    Returns:
        Result: The query results.
    """
    if init_bindings:
        return shacl.query(query, initBindings=init_bindings)
    return shacl.query(query)


def remove_inverse_back_links(fields: Iterable[dict[str, object]]) -> None:
    for field in fields:
        if "or" in field:
            remove_inverse_back_links(cast("list[dict[str, object]]", field["or"]))
        if "nestedShape" not in field:
            continue
        nested = cast("list[dict[str, object]]", field["nestedShape"])
        back_link = inverse_predicate(cast("str", field["uri"]))
        field["nestedShape"] = [item for item in nested if item["uri"] != back_link]
        remove_inverse_back_links(cast("list[dict[str, object]]", field["nestedShape"]))
