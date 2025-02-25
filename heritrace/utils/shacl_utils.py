from collections import OrderedDict, defaultdict
from typing import List

import validators
from flask_babel import gettext
from heritrace.extensions import get_custom_filter, get_shacl_graph
from heritrace.utils.display_rules_utils import get_highest_priority_class
from heritrace.utils.sparql_utils import fetch_data_graph_for_subject
from rdflib import RDF, XSD, Graph, Literal, URIRef
from rdflib.plugins.sparql import prepareQuery
from resources.datatypes import DATATYPE_MAPPING

COMMON_SPARQL_QUERY = prepareQuery(
    """
    SELECT ?shape ?type ?predicate ?nodeShape ?datatype ?maxCount ?minCount ?hasValue ?objectClass 
           ?conditionPath ?conditionValue ?pattern ?message
           (GROUP_CONCAT(?optionalValue; separator=",") AS ?optionalValues)
           (GROUP_CONCAT(?orNode; separator=",") AS ?orNodes)
    WHERE {
        ?shape sh:targetClass ?type ;
               sh:property ?property .
        ?property sh:path ?predicate .
        OPTIONAL {
            ?property sh:node ?nodeShape .
            OPTIONAL {?nodeShape sh:targetClass ?objectClass .}
        }
        OPTIONAL {
            ?property sh:or ?orList .
            {
                ?orList rdf:rest*/rdf:first ?orConstraint .
                ?orConstraint sh:datatype ?datatype .
            } UNION {
                ?orList rdf:rest*/rdf:first ?orNodeShape .
                ?orNodeShape sh:node ?orNode .
            }
        }
        OPTIONAL { ?property sh:datatype ?datatype . }
        OPTIONAL { ?property sh:maxCount ?maxCount . }
        OPTIONAL { ?property sh:minCount ?minCount . }
        OPTIONAL { ?property sh:hasValue ?hasValue . }
        OPTIONAL {
            ?property sh:in ?list .
            ?list rdf:rest*/rdf:first ?optionalValue .
        }
        OPTIONAL {
            ?property sh:condition ?conditionNode .
            ?conditionNode sh:path ?conditionPath ;
                           sh:hasValue ?conditionValue .
        }
        OPTIONAL { ?property sh:pattern ?pattern . }
        OPTIONAL { ?property sh:message ?message . }
        FILTER (isURI(?predicate))
    }
    GROUP BY ?shape ?type ?predicate ?nodeShape ?datatype ?maxCount ?minCount ?hasValue 
            ?objectClass ?conditionPath ?conditionValue ?pattern ?message
""",
    initNs={
        "sh": "http://www.w3.org/ns/shacl#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    },
)


def get_form_fields_from_shacl(shacl: Graph, display_rules: List[dict]):
    """
    Analizza le shape SHACL per estrarre i campi del form per ogni tipo di entità.

    Restituisce:
        OrderedDict: Un dizionario dove le chiavi sono i tipi di entità e i valori sono dizionari
                     dei campi del form con le loro proprietà.
    """
    if not shacl:
        return dict()

    # Step 1: Ottieni i campi iniziali dalle shape SHACL
    form_fields = extract_shacl_form_fields(shacl, display_rules)

    # Step 2: Processa le shape annidate per ogni campo
    processed_shapes = set()
    for entity_type in form_fields:
        for predicate in form_fields[entity_type]:
            for field_info in form_fields[entity_type][predicate]:
                if field_info.get("nodeShape"):
                    field_info["nestedShape"] = process_nested_shapes(
                        shacl,
                        display_rules,
                        field_info["nodeShape"],
                        processed_shapes=processed_shapes,
                    )

    # Step 3: Applica le regole di visualizzazione ai campi del form
    if display_rules:
        form_fields = apply_display_rules(shacl, form_fields, display_rules)

    # Step 4: Ordina i campi del form secondo le regole di visualizzazione
    ordered_form_fields = order_form_fields(form_fields, display_rules)

    return ordered_form_fields


def extract_shacl_form_fields(shacl, display_rules):
    """
    Estrae i campi del form dalle shape SHACL.

    Restituisce:
        defaultdict: Un dizionario dove le chiavi sono i tipi di entità e i valori sono dizionari
                     dei campi del form con le loro proprietà.
    """
    if not shacl:
        return dict()

    processed_shapes = set()
    results = execute_shacl_query(shacl, COMMON_SPARQL_QUERY)
    form_fields = process_query_results(
        shacl, results, display_rules, processed_shapes, depth=0
    )
    return form_fields


def execute_shacl_query(shacl: Graph, query, init_bindings=None):
    """
    Esegue una query SPARQL sul grafo SHACL con eventuali binding iniziali.

    Argomenti:
        shacl (Graph): Il grafo SHACL su cui eseguire la query.
        query (PreparedQuery): La query SPARQL preparata.
        init_bindings (dict): I binding iniziali per la query.

    Restituisce:
        Result: I risultati della query.
    """
    if init_bindings:
        return shacl.query(query, initBindings=init_bindings)
    else:
        return shacl.query(query)


def get_display_name_for_shape(entity_type, property_uri, shape_uri, display_rules):
    """
    Helper function to get displayName from display_rules by matching entity class,
    property, and shape URI.

    Args:
        entity_type (str): The type of the current entity
        property_uri (str): The URI of the property being processed
        shape_uri (str): The URI of the shape to match
        display_rules (list): The display rules configuration

    Returns:
        str: The display name if found, None otherwise
    """
    if display_rules:
        for rule in display_rules:
            # Match the entity class first
            if rule.get("class") == entity_type:
                # Then find the matching property
                for prop in rule.get("displayProperties", []):
                    if prop.get("property") == property_uri:
                        # Finally match the shape in displayRules
                        for shape_rule in prop.get("displayRules", []):
                            if shape_rule.get("shape") == shape_uri:
                                return shape_rule.get("displayName")
    return None


def process_query_results(shacl, results, display_rules, processed_shapes, depth=0):
    form_fields = defaultdict(dict)
    for row in results:
        subject_shape = str(row.shape)
        entity_type = str(row.type)
        predicate = str(row.predicate)
        nodeShape = str(row.nodeShape) if row.nodeShape else None
        hasValue = str(row.hasValue) if row.hasValue else None
        objectClass = str(row.objectClass) if row.objectClass else None
        minCount = 0 if row.minCount is None else int(row.minCount)
        maxCount = None if row.maxCount is None else int(row.maxCount)
        datatype = str(row.datatype) if row.datatype else None
        optionalValues = [v for v in (row.optionalValues or "").split(",") if v]
        orNodes = [v for v in (row.orNodes or "").split(",") if v]

        condition_entry = {}
        if row.conditionPath and row.conditionValue:
            condition_entry["condition"] = {
                "path": str(row.conditionPath),
                "value": str(row.conditionValue),
            }
        if row.pattern:
            condition_entry["pattern"] = str(row.pattern)
        if row.message:
            condition_entry["message"] = str(row.message)

        if predicate not in form_fields[entity_type]:
            form_fields[entity_type][predicate] = []

        nodeShapes = []
        if nodeShape:
            nodeShapes.append(nodeShape)
        nodeShapes.extend(orNodes)

        existing_field = None
        for field in form_fields[entity_type][predicate]:
            if (
                field.get("nodeShape") == nodeShape
                and field.get("nodeShapes") == nodeShapes
                and field.get("subjectShape") == subject_shape
                and field.get("hasValue") == hasValue
                and field.get("objectClass") == objectClass
                and field.get("min") == minCount
                and field.get("max") == maxCount
                and field.get("optionalValues") == optionalValues
            ):
                existing_field = field
                break

        if existing_field:
            if datatype and str(datatype) not in existing_field.get("datatypes", []):
                existing_field.setdefault("datatypes", []).append(str(datatype))
            if condition_entry:
                existing_field.setdefault("conditions", []).append(condition_entry)
            if orNodes:
                existing_field.setdefault("or", [])
                for node in orNodes:
                    entity_type_or_node = get_shape_target_class(shacl, node)
                    object_class = get_object_class(shacl, node, predicate)
                    shape_display_name = get_display_name_for_shape(
                        entity_type, predicate, node, display_rules
                    )
                    # Process orNode as a field_info
                    or_field_info = {
                        "entityType": entity_type_or_node,
                        "uri": predicate,
                        "displayName": shape_display_name,
                        "subjectShape": subject_shape,
                        "nodeShape": node,
                        "min": minCount,
                        "max": maxCount,
                        "hasValue": hasValue,
                        "objectClass": object_class,
                        "optionalValues": optionalValues,
                        "conditions": [condition_entry] if condition_entry else [],
                    }
                    if node not in processed_shapes:
                        or_field_info["nestedShape"] = process_nested_shapes(
                            shacl,
                            display_rules,
                            node,
                            depth=depth + 1,
                            processed_shapes=processed_shapes,
                        )
                    existing_field["or"].append(or_field_info)
        else:
            field_info = {
                "entityType": entity_type,
                "uri": predicate,
                "nodeShape": nodeShape,
                "nodeShapes": nodeShapes,
                "subjectShape": subject_shape,
                "datatypes": [datatype] if datatype else [],
                "min": minCount,
                "max": maxCount,
                "hasValue": hasValue,
                "objectClass": objectClass,
                "optionalValues": optionalValues,
                "conditions": [condition_entry] if condition_entry else [],
                "inputType": determine_input_type(datatype),
            }

            if nodeShape and nodeShape not in processed_shapes:
                field_info["nestedShape"] = process_nested_shapes(
                    shacl,
                    display_rules,
                    nodeShape,
                    depth=depth + 1,
                    processed_shapes=processed_shapes,
                )

            if orNodes:
                field_info["or"] = []
                for node in orNodes:
                    # Process orNode as a field_info
                    entity_type_or_node = get_shape_target_class(shacl, node)
                    object_class = get_object_class(shacl, node, predicate)
                    shape_display_name = get_display_name_for_shape(
                        entity_type, predicate, node, display_rules
                    )
                    or_field_info = {
                        "entityType": entity_type_or_node,
                        "uri": predicate,
                        "displayName": shape_display_name,
                        "subjectShape": subject_shape,
                        "nodeShape": node,
                        "min": minCount,
                        "max": maxCount,
                        "hasValue": hasValue,
                        "objectClass": objectClass,
                        "optionalValues": optionalValues,
                        "conditions": [condition_entry] if condition_entry else [],
                    }
                    if node not in processed_shapes:
                        or_field_info["nestedShape"] = process_nested_shapes(
                            shacl,
                            display_rules,
                            node,
                            depth=depth + 1,
                            processed_shapes=processed_shapes,
                        )
                    field_info["or"].append(or_field_info)

            form_fields[entity_type][predicate].append(field_info)

    return form_fields


def get_shape_target_class(shacl, shape_uri):
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
    for row in results:
        return str(row.targetClass)
    return None


def get_object_class(shacl, shape_uri, predicate_uri):
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
    for row in results:
        if row.targetClass:
            return str(row.targetClass)
    return None


def process_nested_shapes(
    shacl, display_rules, shape_uri, depth=0, processed_shapes=None
):
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

    if depth > 5 or shape_uri in processed_shapes:
        return [{"_reference": shape_uri}]

    processed_shapes.add(shape_uri)
    init_bindings = {"shape": URIRef(shape_uri)}
    nested_results = execute_shacl_query(shacl, COMMON_SPARQL_QUERY, init_bindings)
    nested_fields = []

    temp_form_fields = process_query_results(
        shacl, nested_results, display_rules, processed_shapes, depth
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


def get_property_order(entity_type, display_rules):
    """
    Recupera l'ordine delle proprietà per un tipo di entità dalle regole di visualizzazione.

    Argomenti:
        entity_type (str): L'URI del tipo di entità.

    Restituisce:
        list: Una lista di URI di proprietà nell'ordine desiderato.
    """
    if display_rules:
        for rule in display_rules:
            if rule["class"] == entity_type:
                return [prop["property"] for prop in rule.get("displayProperties", [])]
    return []


def order_fields(fields, property_order):
    """
    Ordina i campi secondo l'ordine specificato delle proprietà.

    Argomenti:
        fields (list): Una lista di dizionari dei campi da ordinare.
        property_order (list): Una lista di URI di proprietà nell'ordine desiderato.

    Restituisce:
        list: Una lista ordinata di dizionari dei campi.
    """
    ordered_fields = []
    field_dict = {field["uri"]: field for field in fields}

    for prop in property_order:
        if prop in field_dict:
            ordered_fields.append(field_dict[prop])
            del field_dict[prop]

    # Aggiungi eventuali campi rimanenti non specificati nell'ordine
    ordered_fields.extend(field_dict.values())

    return ordered_fields


def apply_display_rules(shacl, form_fields, display_rules):
    """
    Applica le regole di visualizzazione ai campi del form.

    Argomenti:
        form_fields (dict): I campi del form iniziali estratti dalle shape SHACL.

    Restituisce:
        dict: I campi del form dopo aver applicato le regole di visualizzazione.
    """
    for rule in display_rules:
        entity_class = rule.get("class")
        if entity_class and entity_class in form_fields:
            for prop in rule.get("displayProperties", []):
                prop_uri = prop["property"]
                if prop_uri in form_fields[entity_class]:
                    for field_info in form_fields[entity_class][prop_uri]:
                        add_display_information(field_info, prop)
                        # Chiamata ricorsiva per le nestedShape
                        if "nestedShape" in field_info:
                            apply_display_rules_to_nested_shapes(
                                field_info["nestedShape"], prop, display_rules
                            )
                        if "or" in field_info:
                            for or_field in field_info["or"]:
                                apply_display_rules_to_nested_shapes(
                                    [or_field], field_info, display_rules
                                )
                        if "intermediateRelation" in prop:
                            handle_intermediate_relation(shacl, field_info, prop)
                    if "displayRules" in prop:
                        handle_sub_display_rules(
                            shacl,
                            form_fields,
                            entity_class,
                            form_fields[entity_class][prop_uri],
                            prop,
                        )
    return form_fields


def apply_display_rules_to_nested_shapes(nested_fields, parent_prop, display_rules):
    for field_info in nested_fields:
        # Trova la regola di visualizzazione corrispondente
        matching_rule = None
        for rule in display_rules:
            if rule.get("class") == field_info.get("entityType"):
                for prop in rule.get("displayProperties", []):
                    if prop["property"] == field_info["uri"]:
                        matching_rule = prop
                        break
        if matching_rule:
            add_display_information(field_info, matching_rule)
        else:
            # Usa il displayName del parent se non c'è una regola specifica
            if "displayName" in parent_prop and "displayName" not in field_info:
                field_info["displayName"] = parent_prop["displayName"]
        # Chiamata ricorsiva se ci sono altre nestedShape
        if "nestedShape" in field_info:
            apply_display_rules_to_nested_shapes(
                field_info["nestedShape"], field_info, display_rules
            )
        if "or" in field_info:
            for or_field in field_info["or"]:
                apply_display_rules_to_nested_shapes(
                    [or_field], field_info, display_rules
                )


def determine_input_type(datatype):
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


def add_display_information(field_info, prop):
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


def handle_intermediate_relation(shacl, field_info, prop):
    """
    Processa 'intermediateRelation' nelle display_rules e aggiorna il campo.

    Argomenti:
        field_info (dict): Le informazioni del campo da aggiornare.
        prop (dict): Le informazioni della proprietà dalle display_rules.
    """
    intermediate_relation = prop["intermediateRelation"]
    target_entity_type = intermediate_relation.get("targetEntityType")
    intermediate_class = intermediate_relation.get("class")

    # Query SPARQL per trovare la proprietà collegante
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
        (str(row.property) for row in connecting_property_results), None
    )

    # Cerca il campo con il connecting_property nella nestedShape
    intermediate_properties = {}
    if "nestedShape" in field_info:
        for nested_field in field_info["nestedShape"]:
            if nested_field.get("uri") == connecting_property:
                # Usa le proprietà dalla nestedShape del connecting_property
                if "nestedShape" in nested_field:
                    for target_field in nested_field["nestedShape"]:
                        uri = target_field.get("uri")
                        if uri:
                            if uri not in intermediate_properties:
                                intermediate_properties[uri] = []
                            intermediate_properties[uri].append(target_field)

    field_info["intermediateRelation"] = {
        "class": intermediate_class,
        "targetEntityType": target_entity_type,
        "connectingProperty": connecting_property,
        "properties": intermediate_properties,
    }


def handle_sub_display_rules(shacl, form_fields, entity_class, field_info_list, prop):
    """
    Gestisce 'displayRules' nelle display_rules, applicando la regola corretta in base allo shape.

    Argomenti:
        form_fields (dict): I campi del form da aggiornare.
        entity_class (str): La classe dell'entità.
        field_info_list (list): Le informazioni del campo originale.
        prop (dict): Le informazioni della proprietà dalle display_rules.
    """
    new_field_info_list = []

    for original_field in field_info_list:
        # Trova la display rule corrispondente allo shape del campo
        matching_rule = next(
            (
                rule
                for rule in prop["displayRules"]
                if rule["shape"] == original_field["nodeShape"]
            ),
            None,
        )

        if matching_rule:
            new_field = {
                "entityType": entity_class,
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
                shape_uri = matching_rule["shape"]
                additional_properties = extract_additional_properties(shacl, shape_uri)
                if additional_properties:
                    new_field["additionalProperties"] = additional_properties

            new_field_info_list.append(new_field)
        else:
            # Se non c'è una regola corrispondente, mantieni il campo originale
            new_field_info_list.append(original_field)

    form_fields[entity_class][prop["property"]] = new_field_info_list


def extract_additional_properties(shacl, shape_uri):
    """
    Estrae proprietà aggiuntive da una shape SHACL.

    Argomenti:
        shape_uri (str): L'URI della shape SHACL.

    Restituisce:
        dict: Un dizionario delle proprietà aggiuntive.
    """
    additional_properties_query = prepareQuery(
        """
        SELECT ?predicate ?hasValue
        WHERE {
            ?shape a sh:NodeShape ;
                   sh:property ?property .
            ?property sh:path ?predicate ;
                     sh:hasValue ?hasValue .
        }
    """,
        initNs={"sh": "http://www.w3.org/ns/shacl#"},
    )

    additional_properties_results = shacl.query(
        additional_properties_query, initBindings={"shape": URIRef(shape_uri)}
    )

    additional_properties = {}
    for row in additional_properties_results:
        predicate = str(row.predicate)
        has_value = str(row.hasValue)
        additional_properties[predicate] = has_value

    return additional_properties


def order_form_fields(form_fields, display_rules):
    """
    Ordina i campi del form secondo le regole di visualizzazione.

    Argomenti:
        form_fields (dict): I campi del form con possibili modifiche dalle regole di visualizzazione.

    Restituisce:
        OrderedDict: I campi del form ordinati.
    """
    ordered_form_fields = OrderedDict()
    if display_rules:
        for rule in display_rules:
            entity_class = rule.get("class")
            if entity_class and entity_class in form_fields:
                ordered_properties = [
                    prop_rule["property"]
                    for prop_rule in rule.get("displayProperties", [])
                ]
                ordered_form_fields[entity_class] = OrderedDict()
                for prop in ordered_properties:
                    if prop in form_fields[entity_class]:
                        ordered_form_fields[entity_class][prop] = form_fields[
                            entity_class
                        ][prop]
                # Aggiungi le proprietà rimanenti non specificate nell'ordine
                for prop in form_fields[entity_class]:
                    if prop not in ordered_properties:
                        ordered_form_fields[entity_class][prop] = form_fields[
                            entity_class
                        ][prop]
    else:
        ordered_form_fields = form_fields
    return ordered_form_fields


def get_valid_predicates(triples):
    shacl = get_shacl_graph()

    existing_predicates = [triple[1] for triple in triples]
    predicate_counts = {
        str(predicate): existing_predicates.count(predicate)
        for predicate in set(existing_predicates)
    }
    default_datatypes = {
        str(predicate): XSD.string for predicate in existing_predicates
    }
    s_types = [triple[2] for triple in triples if triple[1] == RDF.type]

    valid_predicates = [
        {
            str(predicate): {
                "min": None,
                "max": None,
                "hasValue": None,
                "optionalValues": [],
            }
        }
        for predicate in set(existing_predicates)
    ]
    if not s_types:
        return (
            existing_predicates,
            existing_predicates,
            default_datatypes,
            dict(),
            dict(),
            [],
            [str(predicate) for predicate in existing_predicates],
        )
    if not shacl:
        return (
            existing_predicates,
            existing_predicates,
            default_datatypes,
            dict(),
            dict(),
            s_types,
            [str(predicate) for predicate in existing_predicates],
        )

    highest_priority_class = get_highest_priority_class(s_types)
    s_types = [highest_priority_class] if highest_priority_class else s_types

    query = prepareQuery(
        f"""
        SELECT ?predicate ?datatype ?maxCount ?minCount ?hasValue (GROUP_CONCAT(?optionalValue; separator=",") AS ?optionalValues) WHERE {{
            ?shape sh:targetClass ?type ;
                   sh:property ?property .
            VALUES ?type {{<{'> <'.join(s_types)}>}}
            ?property sh:path ?predicate .
            OPTIONAL {{?property sh:datatype ?datatype .}}
            OPTIONAL {{?property sh:maxCount ?maxCount .}}
            OPTIONAL {{?property sh:minCount ?minCount .}}
            OPTIONAL {{?property sh:hasValue ?hasValue .}}
            OPTIONAL {{
                ?property sh:in ?list .
                ?list rdf:rest*/rdf:first ?optionalValue .
            }}
            OPTIONAL {{
                ?property sh:or ?orList .
                ?orList rdf:rest*/rdf:first ?orConstraint .
                ?orConstraint sh:datatype ?datatype .
            }}
            FILTER (isURI(?predicate))
        }}
        GROUP BY ?predicate ?datatype ?maxCount ?minCount ?hasValue
    """,
        initNs={
            "sh": "http://www.w3.org/ns/shacl#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        },
    )
    results = shacl.query(query)
    valid_predicates = [
        {
            str(row.predicate): {
                "min": 0 if row.minCount is None else int(row.minCount),
                "max": None if row.maxCount is None else str(row.maxCount),
                "hasValue": row.hasValue,
                "optionalValues": (
                    row.optionalValues.split(",") if row.optionalValues else []
                ),
            }
        }
        for row in results
    ]

    can_be_added = set()
    can_be_deleted = set()
    mandatory_values = defaultdict(list)
    for valid_predicate in valid_predicates:
        for predicate, ranges in valid_predicate.items():
            if ranges["hasValue"]:
                mandatory_value_present = any(
                    triple[2] == ranges["hasValue"] for triple in triples
                )
                mandatory_values[str(predicate)].append(str(ranges["hasValue"]))
            else:
                max_reached = ranges["max"] is not None and int(
                    ranges["max"]
                ) <= predicate_counts.get(predicate, 0)

                if not max_reached:
                    can_be_added.add(predicate)
                if not (
                    ranges["min"] is not None
                    and int(ranges["min"]) == predicate_counts.get(predicate, 0)
                ):
                    can_be_deleted.add(predicate)

    datatypes = defaultdict(list)
    for row in results:
        if row.datatype:
            datatypes[str(row.predicate)].append(str(row.datatype))
        else:
            datatypes[str(row.predicate)].append(str(XSD.string))

    optional_values = dict()
    for valid_predicate in valid_predicates:
        for predicate, ranges in valid_predicate.items():
            if "optionalValues" in ranges:
                optional_values.setdefault(str(predicate), list()).extend(
                    ranges["optionalValues"]
                )
    return (
        list(can_be_added),
        list(can_be_deleted),
        dict(datatypes),
        mandatory_values,
        optional_values,
        s_types,
        {list(predicate_data.keys())[0] for predicate_data in valid_predicates},
    )


def validate_new_triple(subject, predicate, new_value, action: str, old_value=None):
    data_graph = fetch_data_graph_for_subject(subject)
    if old_value is not None:
        old_value = [
            triple[2]
            for triple in data_graph.triples((URIRef(subject), URIRef(predicate), None))
            if str(triple[2]) == str(old_value)
        ][0]
    if len(get_shacl_graph()):
        # Se non c'è SHACL, accettiamo qualsiasi valore
        if validators.url(new_value):
            return URIRef(new_value), old_value, ""
        else:
            return Literal(new_value), old_value, ""

    s_types = [
        triple[2] for triple in data_graph.triples((URIRef(subject), RDF.type, None))
    ]
    query = f"""
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT DISTINCT ?path ?datatype ?a_class ?classIn ?maxCount ?minCount (GROUP_CONCAT(DISTINCT COALESCE(?optionalValue, ""); separator=",") AS ?optionalValues)
        WHERE {{
            ?shape sh:targetClass ?type ;
                sh:property ?propertyShape .
            ?propertyShape sh:path ?path .
            FILTER(?path = <{predicate}>)
            VALUES ?type {{<{'> <'.join(s_types)}>}}
            OPTIONAL {{?propertyShape sh:datatype ?datatype .}}
            OPTIONAL {{?propertyShape sh:maxCount ?maxCount .}}
            OPTIONAL {{?propertyShape sh:minCount ?minCount .}}
            OPTIONAL {{?propertyShape sh:class ?a_class .}}
            OPTIONAL {{
                ?propertyShape sh:or ?orList .
                ?orList rdf:rest*/rdf:first ?orConstraint .
                ?orConstraint sh:datatype ?datatype .
                OPTIONAL {{?orConstraint sh:class ?class .}}
            }}
            OPTIONAL {{
                ?propertyShape  sh:classIn ?classInList .
                ?classInList rdf:rest*/rdf:first ?classIn .
            }}
            OPTIONAL {{
                ?propertyShape sh:in ?list .
                ?list rdf:rest*/rdf:first ?optionalValue .
            }}
        }}
        GROUP BY ?path ?datatype ?a_class ?classIn ?maxCount ?minCount
    """
    shacl = get_shacl_graph()
    custom_filter = get_custom_filter()

    results = shacl.query(query)
    property_exists = [row.path for row in results]
    if not property_exists:
        return (
            None,
            old_value,
            gettext(
                "The property %(predicate)s is not allowed for resources of type %(s_type)s",
                predicate=custom_filter.human_readable_predicate(predicate, s_types),
                s_type=custom_filter.human_readable_predicate(s_types[0], s_types),
            ),
        )
    datatypes = [row.datatype for row in results if row.datatype is not None]
    classes = [row.a_class for row in results if row.a_class]
    classes.extend([row.classIn for row in results if row.classIn])
    optional_values_str = [row.optionalValues for row in results if row.optionalValues]
    optional_values_str = optional_values_str[0] if optional_values_str else ""
    optional_values = [value for value in optional_values_str.split(",") if value]

    max_count = [row.maxCount for row in results if row.maxCount]
    min_count = [row.minCount for row in results if row.minCount]
    max_count = int(max_count[0]) if max_count else None
    min_count = int(min_count[0]) if min_count else None

    current_values = list(
        data_graph.triples((URIRef(subject), URIRef(predicate), None))
    )
    current_count = len(current_values)

    if action == "create":
        new_count = current_count + 1
    elif action == "delete":
        new_count = current_count - 1
    else:  # update
        new_count = current_count

    if max_count is not None and new_count > max_count:
        value = gettext("value") if max_count == 1 else gettext("values")
        return (
            None,
            old_value,
            gettext(
                "The property %(predicate)s allows at most %(max_count)s %(value)s",
                predicate=custom_filter.human_readable_predicate(predicate, s_types),
                max_count=max_count,
                value=value,
            ),
        )
    if min_count is not None and new_count < min_count:
        value = gettext("value") if min_count == 1 else gettext("values")
        return (
            None,
            old_value,
            gettext(
                "The property %(predicate)s requires at least %(min_count)s %(value)s",
                predicate=custom_filter.human_readable_predicate(predicate, s_types),
                min_count=min_count,
                value=value,
            ),
        )

    if optional_values and new_value not in optional_values:
        optional_value_labels = [
            custom_filter.human_readable_predicate(value, s_types)
            for value in optional_values
        ]
        return (
            None,
            old_value,
            gettext(
                "<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires one of the following values: %(o_values)s",
                new_value=custom_filter.human_readable_predicate(new_value, s_types),
                property=custom_filter.human_readable_predicate(predicate, s_types),
                o_values=", ".join(
                    [f"<code>{label}</code>" for label in optional_value_labels]
                ),
            ),
        )
    if classes:
        if not validators.url(new_value):
            return (
                None,
                old_value,
                gettext(
                    "<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires values of type %(o_types)s",
                    new_value=custom_filter.human_readable_predicate(
                        new_value, s_types
                    ),
                    property=custom_filter.human_readable_predicate(predicate, s_types),
                    o_types=", ".join(
                        [
                            f"<code>{custom_filter.human_readable_predicate(o_class, s_types)}</code>"
                            for o_class in classes
                        ]
                    ),
                ),
            )
        valid_value = convert_to_matching_class(new_value, classes)
        if valid_value is None:
            return (
                None,
                old_value,
                gettext(
                    "<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires values of type %(o_types)s",
                    new_value=custom_filter.human_readable_predicate(
                        new_value, s_types
                    ),
                    property=custom_filter.human_readable_predicate(predicate, s_types),
                    o_types=", ".join(
                        [
                            f"<code>{custom_filter.human_readable_predicate(o_class, s_types)}</code>"
                            for o_class in classes
                        ]
                    ),
                ),
            )
        return valid_value, old_value, ""
    elif datatypes:
        valid_value = convert_to_matching_literal(new_value, datatypes)
        if valid_value is None:
            datatype_labels = [get_datatype_label(datatype) for datatype in datatypes]
            return (
                None,
                old_value,
                gettext(
                    "<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires values of type %(o_types)s",
                    new_value=custom_filter.human_readable_predicate(
                        new_value, s_types
                    ),
                    property=custom_filter.human_readable_predicate(predicate, s_types),
                    o_types=", ".join(
                        [f"<code>{label}</code>" for label in datatype_labels]
                    ),
                ),
            )
        return valid_value, old_value, ""
    # Se non ci sono datatypes o classes specificati, determiniamo il tipo in base a old_value e new_value
    if isinstance(old_value, Literal):
        if old_value.datatype:
            valid_value = Literal(new_value, datatype=old_value.datatype)
        else:
            valid_value = Literal(new_value, datatype=XSD.string)
    elif isinstance(old_value, URIRef) or validators.url(new_value):
        valid_value = URIRef(new_value)
    else:
        valid_value = Literal(new_value, datatype=XSD.string)
    return valid_value, old_value, ""


def convert_to_matching_class(object_value, classes):
    data_graph = fetch_data_graph_for_subject(object_value)
    o_types = {c[2] for c in data_graph.triples((URIRef(object_value), RDF.type, None))}
    if o_types.intersection(classes):
        return URIRef(object_value)


def convert_to_matching_literal(object_value, datatypes):
    for datatype in datatypes:
        validation_func = next(
            (d[1] for d in DATATYPE_MAPPING if d[0] == datatype), None
        )
        if validation_func is None:
            return Literal(object_value, datatype=XSD.string)
        is_valid_datatype = validation_func(object_value)
        if is_valid_datatype:
            return Literal(object_value, datatype=datatype)


def get_datatype_label(datatype_uri):
    custom_filter = get_custom_filter()

    for dt_uri, _, dt_label in DATATYPE_MAPPING:
        if str(dt_uri) == str(datatype_uri):
            return dt_label
    return custom_filter.human_readable_predicate(datatype_uri, [])
