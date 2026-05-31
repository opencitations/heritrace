# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import json
from collections import OrderedDict, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import cast

from flask import Flask
from rdflib import Graph, URIRef
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.sparql import Query
from rdflib.query import Result, ResultRow

from heritrace.sparql import select_results
from heritrace.utils.filters import Filter

COMMON_SPARQL_QUERY = prepareQuery(
    """
    SELECT ?shape ?type ?predicate ?node_shape ?datatype
           ?max_count ?min_count ?has_value ?object_class
           ?condition_path ?condition_value ?pattern ?message
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
            ?property sh:or ?orList .
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
        OPTIONAL { ?property sh:maxCount ?max_count . }
        OPTIONAL { ?property sh:minCount ?min_count . }
        OPTIONAL { ?property sh:hasValue ?has_value . }
        OPTIONAL {
            ?property sh:in ?list .
            ?list rdf:rest*/rdf:first ?optional_value .
        }
        OPTIONAL {
            ?property sh:condition ?condition_node .
            ?condition_node sh:path ?condition_path ;
                            sh:hasValue ?condition_value .
        }
        OPTIONAL { ?property sh:pattern ?pattern . }
        OPTIONAL { ?property sh:message ?message . }
        FILTER (isURI(?predicate))
    }
    GROUP BY ?shape ?type ?predicate ?node_shape ?datatype
             ?max_count ?min_count ?has_value ?object_class
             ?condition_path ?condition_value ?pattern ?message
""",
    initNs={
        "sh": "http://www.w3.org/ns/shacl#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    },
)


def process_query_results(  # noqa: C901, PLR0912, PLR0913, PLR0915
    shacl: Graph,
    results: Iterable[ResultRow],
    display_rules: list[dict[str, object]] | None,
    processed_shapes: set[str],
    app: Flask,
    depth: int = 0,
) -> defaultdict[tuple[str, str], dict[str, list[dict[str, object]]]]:
    form_fields = defaultdict(dict)

    with (Path(__file__).parent / "context.json").open() as config_file:
        context = json.load(config_file)["@context"]

    custom_filter = Filter(context, display_rules, app.config["DATASET_DB_URL"])

    for row in results:
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

        entity_key = (entity_type, subject_shape)

        condition_entry = {}
        if row.condition_path and row.condition_value:
            condition_entry["condition"] = {
                "path": str(row.condition_path),
                "value": str(row.condition_value),
            }
        if row.pattern:
            condition_entry["pattern"] = str(row.pattern)
        if row.message:
            condition_entry["message"] = str(row.message)

        if predicate not in form_fields[entity_key]:
            form_fields[entity_key][predicate] = []

        node_shapes = []
        if node_shape:
            node_shapes.append(node_shape)
        node_shapes.extend(or_nodes)

        existing_field = None
        for field in form_fields[entity_key][predicate]:
            if (
                field.get("nodeShape") == node_shape
                and field.get("nodeShapes") == node_shapes
                and field.get("subjectShape") == subject_shape
                and field.get("hasValue") == has_value
                and field.get("objectClass") == object_class
                and field.get("min") == min_count
                and field.get("max") == max_count
                and field.get("optionalValues") == optional_values
            ):
                existing_field = field
                break

        if existing_field:
            if datatype and str(datatype) not in existing_field.get("datatypes", []):
                existing_field.setdefault("datatypes", []).append(str(datatype))
            if condition_entry:
                existing_field.setdefault("conditions", []).append(condition_entry)
        else:
            field_info = {
                "entityType": entity_type,
                "uri": predicate,
                "nodeShape": node_shape,
                "nodeShapes": node_shapes,
                "subjectShape": subject_shape,
                "entityKey": entity_key,
                "datatypes": [datatype] if datatype else [],
                "min": min_count,
                "max": max_count,
                "hasValue": has_value,
                "objectClass": object_class,
                "optionalValues": optional_values,
                "conditions": [condition_entry] if condition_entry else [],
                "inputType": determine_input_type(datatype),
                "shouldBeDisplayed": True,
            }

            if node_shape and node_shape not in processed_shapes:
                field_info["nestedShape"] = process_nested_shapes(
                    shacl,
                    display_rules,
                    node_shape,
                    app,
                    depth=depth + 1,
                    processed_shapes=processed_shapes,
                )

            if or_nodes:
                field_info["or"] = []
                for node in or_nodes:
                    entity_type_or_node = get_shape_target_class(shacl, node)
                    object_class = get_object_class(shacl, node, predicate)
                    shape_display_name = custom_filter.human_readable_class(
                        (entity_type_or_node, node)
                    )
                    or_field_info = {
                        "entityType": entity_type_or_node,
                        "uri": predicate,
                        "displayName": shape_display_name,
                        "subjectShape": subject_shape,
                        "nodeShape": node,
                        "min": min_count,
                        "max": max_count,
                        "hasValue": has_value,
                        "objectClass": object_class,
                        "optionalValues": optional_values,
                        "conditions": [condition_entry] if condition_entry else [],
                        "shouldBeDisplayed": True,
                    }
                    if node not in processed_shapes:
                        or_field_info["nestedShape"] = process_nested_shapes(
                            shacl,
                            display_rules,
                            node,
                            app,
                            depth=depth + 1,
                            processed_shapes=processed_shapes,
                        )
                    field_info["or"].append(or_field_info)

            form_fields[entity_key][predicate].append(field_info)

    return form_fields


def process_nested_shapes(  # noqa: PLR0913
    shacl: Graph,
    display_rules: list[dict[str, object]] | None,
    shape_uri: str,
    app: Flask,
    depth: int = 0,
    processed_shapes: set[str] | None = None,
) -> list[dict[str, object]]:
    """
    Processa ricorsivamente le shape annidate.

    Argomenti:
        shape_uri (str): L'URI della shape da processare.
        depth (int): La profondità corrente della ricorsione.
        processed_shapes (set): Un insieme delle shape già processate.

    Restituisce:
        list: Una lista di dizionari dei campi annidati.
    """
    if processed_shapes is None:
        processed_shapes = set()

    if shape_uri in processed_shapes:
        return []

    processed_shapes.add(shape_uri)
    init_bindings = {"shape": URIRef(shape_uri)}
    nested_results = execute_shacl_query(shacl, COMMON_SPARQL_QUERY, init_bindings)
    nested_fields = []

    temp_form_fields = process_query_results(
        shacl,
        select_results(nested_results),
        display_rules,
        processed_shapes,
        app=app,
        depth=depth,
    )

    # Applica le regole di visualizzazione ai campi annidati
    if display_rules:
        temp_form_fields = apply_display_rules(shacl, temp_form_fields, display_rules)
        temp_form_fields = order_form_fields(temp_form_fields, display_rules)

    # Estrai i campi per il tipo di entità
    for entity_type in temp_form_fields:
        for predicate in temp_form_fields[entity_type]:
            nested_fields.extend(temp_form_fields[entity_type][predicate])

    processed_shapes.remove(shape_uri)
    return nested_fields


def get_property_order(
    entity_type: str,
    display_rules: list[dict[str, object]] | None,
) -> list[str | None]:
    """
    Recupera l'ordine delle proprietà per un tipo di entità dalle regole di
    visualizzazione.

    Argomenti:
        entity_type (str): L'URI del tipo di entità.

    Restituisce:
        list: Una lista di URI di proprietà nell'ordine desiderato.
    """
    if not display_rules:
        return []

    for rule in display_rules:
        if rule.get("class") == entity_type and "propertyOrder" in rule:
            return cast("list[str | None]", rule["propertyOrder"])
        if rule.get("class") == entity_type:
            display_props = cast(
                "list[dict[str, object]]", rule.get("displayProperties", [])
            )
            return [
                cast("str | None", prop.get("property") or prop.get("virtual_property"))
                for prop in display_props
                if prop.get("property") or prop.get("virtual_property")
            ]
    return []


def order_fields(
    fields: list[dict[str, object]],
    property_order: list[str],
) -> list[dict[str, object]]:
    """
    Ordina i campi secondo l'ordine specificato delle proprietà.

    Argomenti:
        fields (list): Una lista di dizionari dei campi da ordinare.
        property_order (list): Una lista di URI di proprietà nell'ordine desiderato.

    Restituisce:
        list: Una lista ordinata di dizionari dei campi.
    """
    if not fields:
        return []
    if not property_order:
        return fields

    # Create a dictionary to map predicates to their position in property_order
    order_dict = {pred: i for i, pred in enumerate(property_order)}

    # Sort fields based on their position in property_order
    # Fields not in property_order will be placed at the end
    return sorted(
        fields,
        key=lambda f: order_dict.get(
            str(f.get("predicate", f.get("uri", ""))), float("inf")
        ),
    )


def _find_matching_entity_keys(
    form_fields: dict[
        tuple[str, str],
        dict[str, list[dict[str, object]]],
    ],
    entity_class: str | None,
    entity_shape: str | None,
) -> list[tuple[str, str]]:
    if entity_class and entity_shape:
        entity_key = (entity_class, entity_shape)
        return [entity_key] if entity_key in form_fields else []
    if entity_class:
        return [key for key in form_fields if key[0] == entity_class]
    if entity_shape:
        return [key for key in form_fields if key[1] == entity_shape]
    return []


def _get_ordered_properties_from_rule(
    rule: dict[str, object],
) -> list[str | None]:
    display_props = cast("list[dict[str, object]]", rule.get("displayProperties", []))
    return [
        cast(
            "str | None",
            prop_rule.get("property") or prop_rule.get("virtual_property"),
        )
        for prop_rule in display_props
        if prop_rule.get("property") or prop_rule.get("virtual_property")
    ]


def _order_entity_fields(
    form_fields: dict[
        tuple[str, str],
        dict[str, list[dict[str, object]]],
    ],
    entity_key: tuple[str, str],
    ordered_properties: list[str | None],
    ordered_form_fields: OrderedDict[
        tuple[str, str],
        OrderedDict[str, list[dict[str, object]]],
    ],
) -> None:
    ordered_form_fields[entity_key] = OrderedDict()
    for prop in ordered_properties:
        if prop in form_fields[entity_key]:
            ordered_form_fields[entity_key][prop] = form_fields[entity_key][prop]
    # Aggiungi le proprietà rimanenti non specificate nell'ordine
    for prop in form_fields[entity_key]:
        if prop not in ordered_properties:
            ordered_form_fields[entity_key][prop] = form_fields[entity_key][prop]


def order_form_fields(
    form_fields: dict[
        tuple[str, str],
        dict[str, list[dict[str, object]]],
    ],
    display_rules: list[dict[str, object]] | None,
) -> (
    OrderedDict[
        tuple[str, str],
        OrderedDict[str, list[dict[str, object]]],
    ]
    | dict[
        tuple[str, str],
        dict[str, list[dict[str, object]]],
    ]
):
    """
    Ordina i campi del form secondo le regole di visualizzazione.

    Argomenti:
        form_fields (dict): I campi del form con possibili modifiche dalle regole di
        visualizzazione.

    Restituisce:
        OrderedDict: I campi del form ordinati.
    """
    ordered_form_fields = OrderedDict()
    if not display_rules:
        return form_fields
    for rule in display_rules:
        target = cast("dict[str, str]", rule.get("target", {}))
        entity_class = target.get("class")
        entity_shape = target.get("shape")
        ordered_properties = _get_ordered_properties_from_rule(rule)
        matching_keys = _find_matching_entity_keys(
            form_fields, entity_class, entity_shape
        )
        for key in matching_keys:
            _order_entity_fields(
                form_fields, key, ordered_properties, ordered_form_fields
            )
    return ordered_form_fields


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
    """
    Apply a display rule to a specific entity key.

    Args:
        shacl: The SHACL graph
        form_fields: The form fields dictionary
        entity_key: The entity key tuple (class, shape)
        rule: The display rule to apply
    """
    display_props = cast("list[dict[str, object]]", rule.get("displayProperties", []))
    for prop in display_props:
        prop_uri = prop.get("property") or prop.get("virtual_property")
        if prop_uri and prop_uri in form_fields[entity_key]:
            for field_info in form_fields[entity_key][str(prop_uri)]:
                add_display_information(field_info, prop)
                if "nestedShape" in field_info:
                    target = cast("dict[str, str]", rule.get("target", {}))
                    apply_display_rules_to_nested_shapes(
                        cast("list[dict[str, object]]", field_info["nestedShape"]),
                        prop,
                        target.get("shape"),
                    )
                if "or" in field_info:
                    target = cast("dict[str, str]", rule.get("target", {}))
                    for or_field in cast("list[dict[str, object]]", field_info["or"]):
                        apply_display_rules_to_nested_shapes(
                            [or_field], field_info, target.get("shape")
                        )
                if "intermediateRelation" in prop:
                    handle_intermediate_relation(shacl, field_info, prop)
            if "displayRules" in prop:
                handle_sub_display_rules(
                    shacl,
                    form_fields,
                    entity_key,
                    form_fields[entity_key][str(prop_uri)],
                    prop,
                )


def apply_display_rules_to_nested_shapes(  # noqa: C901
    nested_fields: list[dict[str, object]],
    parent_prop: dict[str, object],
    shape_uri: str | None,
) -> list[dict[str, object]]:
    """Apply display rules to nested shapes."""
    if not nested_fields:
        return []

    # Handle case where parent_prop is not a dictionary
    if not isinstance(parent_prop, dict):
        return nested_fields

    # Create a new list to avoid modifying the original
    result_fields = []
    for field in nested_fields:
        # Create a copy of the field to avoid modifying the original
        new_field = field.copy()
        result_fields.append(new_field)

    display_rules = cast("list[dict[str, object]]", parent_prop.get("displayRules", []))
    for rule in display_rules:
        if rule.get("shape") == shape_uri and "nestedDisplayRules" in rule:
            nested_display_rules = cast(
                "list[dict[str, object]]", rule["nestedDisplayRules"]
            )
            for field in result_fields:
                for nested_rule in nested_display_rules:
                    field_key = field.get("predicate", field.get("uri"))
                    if field_key == nested_rule["property"]:
                        # Apply display properties from the rule to the field
                        for key, value in nested_rule.items():
                            if key != "property":
                                field[key] = value
            break

    return result_fields


def determine_input_type(datatype: str | None) -> str:
    """
    Determina il tipo di input appropriato basato sul datatype XSD.
    """
    if not datatype:
        return "text"

    datatype = str(datatype)
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
    return datatype_to_input.get(datatype, "text")


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
    if "displayName" in prop:
        field_info["displayName"] = prop["displayName"]
    if "shouldBeDisplayed" in prop:
        field_info["shouldBeDisplayed"] = prop.get("shouldBeDisplayed", True)
    if "orderedBy" in prop:
        field_info["orderedBy"] = prop["orderedBy"]
    if "inputType" in prop:
        field_info["inputType"] = prop["inputType"]
    if "supportsSearch" in prop:
        field_info["supportsSearch"] = prop["supportsSearch"]
    if "minCharsForSearch" in prop:
        field_info["minCharsForSearch"] = prop["minCharsForSearch"]
    if "searchTarget" in prop:
        field_info["searchTarget"] = prop["searchTarget"]


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
            ) and "nestedShape" in nested_field:
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


def handle_sub_display_rules(
    shacl: Graph,
    form_fields: dict[
        tuple[str, str],
        dict[str, list[dict[str, object]]],
    ],
    entity_key: tuple[str, str],
    field_info_list: list[dict[str, object]],
    prop: dict[str, object],
) -> None:
    """
    Gestisce 'displayRules' nelle display_rules, applicando la regola corretta in base
    allo shape.

    Argomenti:
        form_fields (dict): I campi del form da aggiornare.
        entity_key (tuple): La chiave dell'entità (class, shape).
        field_info_list (list): Le informazioni del campo originale.
        prop (dict): Le informazioni della proprietà dalle display_rules.
    """
    new_field_info_list = []
    entity_class = entity_key[0] if isinstance(entity_key, tuple) else entity_key

    for original_field in field_info_list:
        # Trova la display rule corrispondente allo shape del campo
        sub_display_rules = cast("list[dict[str, object]]", prop["displayRules"])
        matching_rule = next(
            (
                rule
                for rule in sub_display_rules
                if rule["shape"] == original_field["nodeShape"]
            ),
            None,
        )

        if matching_rule:
            new_field = {
                "entityType": entity_class,
                "entityKey": entity_key,  # Store the tuple key
                "objectClass": original_field.get("objectClass"),
                "uri": prop["property"],
                "datatype": original_field.get("datatype"),
                "min": original_field.get("min"),
                "max": original_field.get("max"),
                "hasValue": original_field.get("hasValue"),
                "nodeShape": original_field.get("nodeShape"),
                "nodeShapes": original_field.get("nodeShapes"),
                "subjectShape": original_field.get("subjectShape"),
                "nestedShape": original_field.get("nestedShape"),
                "displayName": matching_rule["displayName"],
                "optionalValues": original_field.get("optionalValues", []),
                "orderedBy": original_field.get("orderedBy"),
                "or": original_field.get("or", []),
            }

            if "intermediateRelation" in original_field:
                new_field["intermediateRelation"] = original_field[
                    "intermediateRelation"
                ]

            # Aggiungi proprietà aggiuntive dalla shape SHACL
            if "shape" in matching_rule:
                shape_uri = str(matching_rule["shape"])
                additional_properties = extract_additional_properties(shacl, shape_uri)
                if additional_properties:
                    new_field["additionalProperties"] = additional_properties

            new_field_info_list.append(new_field)
        else:
            # Se non c'è una regola corrispondente, mantieni il campo originale
            new_field_info_list.append(original_field)

    form_fields[entity_key][str(prop["property"])] = new_field_info_list


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

    processed_shapes = set()
    results = execute_shacl_query(shacl, COMMON_SPARQL_QUERY)
    return process_query_results(
        shacl,
        select_results(results),
        display_rules,
        processed_shapes,
        app=app,
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
            ?property sh:path ?predicate ;
                     sh:hasValue ?has_value .
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
