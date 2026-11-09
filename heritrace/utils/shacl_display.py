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

from heritrace.sparql import select_results
from heritrace.utils.filters import Filter
from heritrace.utils.shacl_patterns import (
    PatternAlternative,
    read_pattern_alternatives,
)
from heritrace.utils.shacl_presentation import SHUI, ShapesPresentation


@dataclass(slots=True)
class ShaclProcessingContext:
    shacl: Graph
    display_rules: list[dict[str, object]] | None
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
    entity_key: tuple[str, str]
    node_shapes: list[str]
    name: str | None
    editor: str | None


COMMON_SPARQL_QUERY = prepareQuery(
    """
    SELECT ?shape ?type ?predicate ?node_shape ?datatype
           ?max_count ?min_count ?has_value ?object_class
           ?name ?editor
           (GROUP_CONCAT(?optional_value; separator=",")
            AS ?optional_values)
           (GROUP_CONCAT(?or_node; separator=",") AS ?or_nodes)
    WHERE {
        ?shape sh:targetClass ?type ;
               sh:property ?property .
        ?property sh:path ?predicate .
        OPTIONAL {
            ?property sh:node ?node_shape .
            OPTIONAL {
                ?node_shape sh:targetClass ?object_class .
            }
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
        FILTER (isURI(?predicate))
        FILTER NOT EXISTS { ?property sh:values ?computed . }
    }
    GROUP BY ?shape ?type ?predicate ?node_shape ?datatype
             ?max_count ?min_count ?has_value ?object_class
             ?name ?editor
""",
    initNs={
        "sh": "http://www.w3.org/ns/shacl#",
        "shui": str(SHUI),
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    },
)


def _parse_row(row: ResultRow) -> _ParsedRow:
    subject_shape = str(row.shape)
    entity_type = str(row.type)
    predicate = str(row.predicate)
    node_shape = str(row.node_shape) if row.node_shape else None
    has_value = str(row.has_value) if row.has_value else None
    object_class = str(row.object_class) if row.object_class else None
    min_count = 0 if row.min_count is None else int(row.min_count)
    max_count = None if row.max_count is None else int(row.max_count)
    datatype = str(row.datatype) if row.datatype else None
    optional_values = [v for v in (row.optional_values or "").split(",") if v]
    or_nodes = [v for v in (row.or_nodes or "").split(",") if v]

    node_shapes = []
    if node_shape:
        node_shapes.append(node_shape)
    node_shapes.extend(or_nodes)

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
        entity_key=(entity_type, subject_shape),
        node_shapes=node_shapes,
        name=str(row.name) if row.name else None,
        editor=str(row.editor) if row.editor else None,
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


def _process_or_nodes(
    ctx: ShaclProcessingContext,
    parsed: _ParsedRow,
    custom_filter: Filter,
    field_info: dict[str, object],
    depth: int,
) -> None:
    field_info["or"] = []
    for node in parsed.or_nodes:
        entity_type_or_node = get_shape_target_class(ctx.shacl, node)
        object_class = get_object_class(ctx.shacl, node, parsed.predicate)
        shape_display_name = custom_filter.human_readable_class(
            (entity_type_or_node, node)
        )
        or_field_info: dict[str, object] = {
            "entityType": entity_type_or_node,
            "uri": parsed.predicate,
            "displayName": shape_display_name,
            "subjectShape": parsed.subject_shape,
            "nodeShape": node,
            "min": parsed.min_count,
            "max": parsed.max_count,
            "hasValue": parsed.has_value,
            "objectClass": object_class,
            "optionalValues": parsed.optional_values,
            "conditions": _field_conditions(ctx, parsed),
            "autocomplete": parsed.editor == str(SHUI.AutoCompleteEditor),
            "shouldBeDisplayed": True,
        }
        if node not in ctx.processed_shapes:
            or_field_info["nestedShape"] = process_nested_shapes(
                ctx,
                node,
                depth=depth + 1,
            )
        field_info["or"].append(or_field_info)


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
        "shouldBeDisplayed": True,
    }
    if parsed.name is not None:
        field_info["displayName"] = parsed.name

    if parsed.node_shape and parsed.node_shape not in ctx.processed_shapes:
        field_info["nestedShape"] = process_nested_shapes(
            ctx,
            parsed.node_shape,
            depth=depth + 1,
        )

    if parsed.or_nodes:
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

    for fields in form_fields.values():
        for predicate_fields in fields.values():
            _add_distinguishing_properties(ctx.shacl, predicate_fields)

    return form_fields


# When several property shapes share a path and differ by sh:node, a new value
# needs the fixed values of its node shape to tell which property shape it
# belongs to.
def _add_distinguishing_properties(
    shacl: Graph, predicate_fields: list[dict[str, object]]
) -> None:
    node_shapes = {field.get("nodeShape") for field in predicate_fields}
    if len(node_shapes) == 1:
        return
    for field in predicate_fields:
        if field.get("nodeShape"):
            additional_properties = extract_additional_properties(
                shacl, str(field["nodeShape"])
            )
            if additional_properties:
                field["additionalProperties"] = additional_properties


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

    if ctx.display_rules:
        temp_form_fields = apply_display_rules(
            ctx.shacl, temp_form_fields, ctx.display_rules
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


def apply_display_rules(
    shacl: Graph,
    form_fields: dict[
        tuple[str, str],
        dict[str, list[dict[str, object]]],
    ],
    display_rules: list[dict[str, object]],
) -> dict[
    tuple[str, str],
    dict[str, list[dict[str, object]]],
]:
    """
    Applica le regole di visualizzazione ai campi del form.

    Argomenti:
        form_fields (dict): I campi del form iniziali estratti dalle shape SHACL.

    Restituisce:
        dict: I campi del form dopo aver applicato le regole di visualizzazione.
    """
    for rule in display_rules:
        target = cast("dict[str, str]", rule.get("target", {}))
        entity_class = target.get("class")
        entity_shape = target.get("shape")

        # Handle different cases based on available target information
        # Case 1: Both class and shape are specified (exact match)
        if entity_class and entity_shape:
            entity_key = (entity_class, entity_shape)
            if entity_key in form_fields:
                apply_rule_to_entity(shacl, form_fields, entity_key, rule)
        # Case 2: Only class is specified (apply to all matching classes)
        elif entity_class:
            for key in list(form_fields.keys()):
                if key[0] == entity_class:  # Check if class part of tuple matches
                    apply_rule_to_entity(shacl, form_fields, key, rule)
        # Case 3: Only shape is specified (apply to all matching shapes)
        elif entity_shape:
            for key in list(form_fields.keys()):
                if key[1] == entity_shape:  # Check if shape part of tuple matches
                    apply_rule_to_entity(shacl, form_fields, key, rule)
    return form_fields


def apply_rule_to_entity(
    shacl: Graph,
    form_fields: dict[
        tuple[str, str],
        dict[str, list[dict[str, object]]],
    ],
    entity_key: tuple[str, str],
    rule: dict[str, object],
) -> None:
    display_props = cast("list[dict[str, object]]", rule.get("displayProperties", []))
    for prop in display_props:
        prop_uri = prop.get("property")
        if prop_uri and prop_uri in form_fields[entity_key]:
            for field_info in form_fields[entity_key][str(prop_uri)]:
                add_display_information(field_info, prop)
                if "intermediateRelation" in prop:
                    handle_intermediate_relation(shacl, field_info, prop)


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


def add_display_information(
    field_info: dict[str, object],
    prop: dict[str, object],
) -> None:
    """
    Aggiunge informazioni di visualizzazione dal display_rules ad un campo.

    Argomenti:
        field_info (dict): Le informazioni del campo da aggiornare.
        prop (dict): Le informazioni della proprietà dalle display_rules.
    """
    if "shouldBeDisplayed" in prop:
        field_info["shouldBeDisplayed"] = prop.get("shouldBeDisplayed", True)
    if "orderedBy" in prop:
        field_info["orderedBy"] = prop["orderedBy"]


def handle_intermediate_relation(
    shacl: Graph,
    field_info: dict[str, object],
    prop: dict[str, object],
) -> None:
    """
    Processa 'intermediateRelation' nelle display_rules e aggiorna il campo.

    Argomenti:
        field_info (dict): Le informazioni del campo da aggiornare.
        prop (dict): Le informazioni della proprietà dalle display_rules.
    """
    intermediate_relation = cast("dict[str, str]", prop["intermediateRelation"])
    target_entity_type = intermediate_relation["targetEntityType"]
    intermediate_class = intermediate_relation["class"]

    connecting_property_query = prepareQuery(
        """
        SELECT ?property
        WHERE {
            ?shape sh:targetClass ?intermediateClass ;
                   sh:property ?propertyShape .
            ?propertyShape sh:path ?property ;
                           sh:node ?targetNode .
            ?targetNode sh:targetClass ?targetClass.
        }
    """,
        initNs={"sh": "http://www.w3.org/ns/shacl#"},
    )

    connecting_property_results = shacl.query(
        connecting_property_query,
        initBindings={
            "intermediateClass": URIRef(intermediate_class),
            "targetClass": URIRef(target_entity_type),
        },
    )

    connecting_property = next(
        (str(row.property) for row in select_results(connecting_property_results)), None
    )

    intermediate_properties = {}
    target_shape = None
    if "nestedShape" in field_info:
        for nested_field in cast("list[dict[str, object]]", field_info["nestedShape"]):
            if (
                nested_field.get("uri") == connecting_property
                and "nestedShape" in nested_field
            ):
                field_info["autocomplete"] = nested_field["autocomplete"]
                for target_field in cast(
                    "list[dict[str, object]]", nested_field["nestedShape"]
                ):
                    uri = target_field.get("uri")
                    if uri:
                        if uri not in intermediate_properties:
                            intermediate_properties[uri] = []
                        intermediate_properties[uri].append(target_field)
                    if target_field.get("subjectShape"):
                        target_shape = target_field["subjectShape"]

    field_info["intermediateRelation"] = {
        "class": intermediate_class,
        "targetEntityType": target_entity_type,
        "targetShape": target_shape,
        "connectingProperty": connecting_property,
        "properties": intermediate_properties,
    }


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
    display_rules: list[dict[str, object]] | None,
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
        display_rules: The display rules configuration
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
        display_rules=display_rules,
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


def extract_additional_properties(shacl: Graph, shape_uri: str) -> dict[str, str]:
    """
    Estrae proprietà aggiuntive da una shape SHACL.

    Argomenti:
        shape_uri (str): L'URI della shape SHACL.

    Restituisce:
        dict: Un dizionario delle proprietà aggiuntive.
    """
    additional_properties_query = prepareQuery(
        """
        SELECT ?predicate ?has_value
        WHERE {
            ?shape a sh:NodeShape ;
                   sh:property ?property .
            ?property sh:path ?predicate .
            { ?property sh:hasValue ?has_value . }
            UNION
            { ?property sh:qualifiedValueShape/sh:hasValue ?has_value . }
        }
    """,
        initNs={"sh": "http://www.w3.org/ns/shacl#"},
    )

    additional_properties_results = shacl.query(
        additional_properties_query,
        initBindings={"shape": URIRef(shape_uri)},
    )

    additional_properties = {}
    for row in select_results(additional_properties_results):
        predicate = str(row.predicate)
        has_value = str(row.has_value)
        additional_properties[predicate] = has_value

    return additional_properties
