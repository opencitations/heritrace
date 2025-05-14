from collections import OrderedDict, defaultdict
from typing import List

from rdflib import Graph, URIRef
from rdflib.plugins.sparql import prepareQuery


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


def get_display_name_for_shape(entity_type: str, property_uri: str, shape_uri: str, display_rules: List[dict]) -> str|None:
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
            rule_class = None
            rule_shape = None
            if "target" in rule:
                if "class" in rule["target"]:
                    rule_class = rule["target"]["class"]
                if "shape" in rule["target"]:
                    rule_shape = rule["target"]["shape"]
                
            # Match only when both class and shape are specified
            if rule_class == entity_type and rule_shape == shape_uri:
                for prop in rule.get("displayProperties", []):
                    if prop.get("property") == property_uri:
                        return prop.get("displayName")


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
        
        entity_key = (entity_type, subject_shape)

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

        if predicate not in form_fields[entity_key]:
            form_fields[entity_key][predicate] = []

        nodeShapes = []
        if nodeShape:
            nodeShapes.append(nodeShape)
        nodeShapes.extend(orNodes)

        existing_field = None
        for field in form_fields[entity_key][predicate]:
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
                "entityKey": entity_key,
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

            form_fields[entity_key][predicate].append(field_info)

    return form_fields


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

    if shape_uri in processed_shapes:
        return []

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
    if not display_rules:
        return []
        
    for rule in display_rules:
        if rule.get("class") == entity_type and "propertyOrder" in rule:
            return rule["propertyOrder"]
        elif rule.get("class") == entity_type:
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
        key=lambda f: order_dict.get(f.get("predicate", f.get("uri", "")), float("inf")),
    )


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
            target = rule.get("target", {})
            entity_class = target.get("class")
            entity_shape = target.get("shape")
            
            # Case 1: Both class and shape are specified (exact match)
            if entity_class and entity_shape:
                entity_key = (entity_class, entity_shape)
                if entity_key in form_fields:
                    ordered_properties = [
                        prop_rule["property"]
                        for prop_rule in rule.get("displayProperties", [])
                    ]
                    ordered_form_fields[entity_key] = OrderedDict()
                    for prop in ordered_properties:
                        if prop in form_fields[entity_key]:
                            ordered_form_fields[entity_key][prop] = form_fields[entity_key][prop]
                    # Aggiungi le proprietà rimanenti non specificate nell'ordine
                    for prop in form_fields[entity_key]:
                        if prop not in ordered_properties:
                            ordered_form_fields[entity_key][prop] = form_fields[entity_key][prop]
            
            # Case 2: Only class is specified (apply to all matching classes)
            elif entity_class:
                for key in form_fields:
                    if key[0] == entity_class:  # Check if class part of tuple matches
                        entity_key = key
                        ordered_properties = [
                            prop_rule["property"]
                            for prop_rule in rule.get("displayProperties", [])
                        ]
                        ordered_form_fields[entity_key] = OrderedDict()
                        for prop in ordered_properties:
                            if prop in form_fields[entity_key]:
                                ordered_form_fields[entity_key][prop] = form_fields[entity_key][prop]
                        # Aggiungi le proprietà rimanenti non specificate nell'ordine
                        for prop in form_fields[entity_key]:
                            if prop not in ordered_properties:
                                ordered_form_fields[entity_key][prop] = form_fields[entity_key][prop]
            
            # Case 3: Only shape is specified (apply to all matching shapes)
            elif entity_shape:
                for key in form_fields:
                    if key[1] == entity_shape:  # Check if shape part of tuple matches
                        entity_key = key
                        ordered_properties = [
                            prop_rule["property"]
                            for prop_rule in rule.get("displayProperties", [])
                        ]
                        ordered_form_fields[entity_key] = OrderedDict()
                        for prop in ordered_properties:
                            if prop in form_fields[entity_key]:
                                ordered_form_fields[entity_key][prop] = form_fields[entity_key][prop]
                        # Aggiungi le proprietà rimanenti non specificate nell'ordine
                        for prop in form_fields[entity_key]:
                            if prop not in ordered_properties:
                                ordered_form_fields[entity_key][prop] = form_fields[entity_key][prop]
    else:
        ordered_form_fields = form_fields
    return ordered_form_fields


def apply_display_rules(shacl, form_fields, display_rules):
    """
    Applica le regole di visualizzazione ai campi del form.

    Argomenti:
        form_fields (dict): I campi del form iniziali estratti dalle shape SHACL.

    Restituisce:
        dict: I campi del form dopo aver applicato le regole di visualizzazione.
    """
    for rule in display_rules:
        target = rule.get("target", {})
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


def apply_rule_to_entity(shacl, form_fields, entity_key, rule):
    """
    Apply a display rule to a specific entity key.
    
    Args:
        shacl: The SHACL graph
        form_fields: The form fields dictionary
        entity_key: The entity key tuple (class, shape)
        rule: The display rule to apply
    """
    for prop in rule.get("displayProperties", []):
        prop_uri = prop["property"]
        if prop_uri in form_fields[entity_key]:
            for field_info in form_fields[entity_key][prop_uri]:
                add_display_information(field_info, prop)
                # Chiamata ricorsiva per le nestedShape
                if "nestedShape" in field_info:
                    apply_display_rules_to_nested_shapes(
                        field_info["nestedShape"], prop, rule.get("target", {}).get("shape")
                    )
                if "or" in field_info:
                    for or_field in field_info["or"]:
                        apply_display_rules_to_nested_shapes(
                            [or_field], field_info, rule.get("target", {}).get("shape")
                        )
                if "intermediateRelation" in prop:
                    handle_intermediate_relation(shacl, field_info, prop)
            if "displayRules" in prop:
                handle_sub_display_rules(
                    shacl,
                    form_fields,
                    entity_key,
                    form_fields[entity_key][prop_uri],
                    prop,
                )


def apply_display_rules_to_nested_shapes(nested_fields, parent_prop, shape_uri):
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

    # Find the matching shape in the parent property's display rules
    found_matching_shape = False
    for rule in parent_prop.get("displayRules", []):
        if rule.get("shape") == shape_uri and "nestedDisplayRules" in rule:
            found_matching_shape = True
            # Apply nested display rules to each field
            for field in result_fields:
                for nested_rule in rule["nestedDisplayRules"]:
                    # Check both predicate and uri keys to be more flexible
                    field_key = field.get("predicate", field.get("uri"))
                    if field_key == nested_rule["property"]:
                        # Apply display properties from the rule to the field
                        for key, value in nested_rule.items():
                            if key != "property":
                                field[key] = value
            break

    return result_fields


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
    if "supportsSearch" in prop:
        field_info["supportsSearch"] = prop["supportsSearch"]
    if "minCharsForSearch" in prop:
        field_info["minCharsForSearch"] = prop["minCharsForSearch"]
    if "searchTarget" in prop:
        field_info["searchTarget"] = prop["searchTarget"]


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


def handle_sub_display_rules(shacl, form_fields, entity_key, field_info_list, prop):
    """
    Gestisce 'displayRules' nelle display_rules, applicando la regola corretta in base allo shape.

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
                shape_uri = matching_rule["shape"]
                additional_properties = extract_additional_properties(shacl, shape_uri)
                if additional_properties:
                    new_field["additionalProperties"] = additional_properties

            new_field_info_list.append(new_field)
        else:
            # Se non c'è una regola corrispondente, mantieni il campo originale
            new_field_info_list.append(original_field)

    form_fields[entity_key][prop["property"]] = new_field_info_list


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