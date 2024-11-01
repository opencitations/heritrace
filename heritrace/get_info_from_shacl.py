from collections import OrderedDict, defaultdict
from typing import List

from rdflib import Graph, URIRef
from rdflib.plugins.sparql import prepareQuery


def get_form_fields_from_shacl(shacl: Graph, display_rules: List[dict] ):
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
                        processed_shapes=processed_shapes
                    )
    
    # Step 3: Applica le regole di visualizzazione ai campi del form
    if display_rules:
        form_fields = apply_display_rules(shacl, form_fields, display_rules)

    # Step 4: Ordina i campi del form secondo le regole di visualizzazione
    ordered_form_fields = order_form_fields(form_fields, display_rules)

    # Step 5: Arricchisci la struttura 'or' con le informazioni complete
    ordered_form_fields = enrich_or_shapes(ordered_form_fields)
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
    
    query = prepareQuery("""
        SELECT ?type ?predicate ?nodeShape ?datatype ?maxCount ?minCount ?hasValue ?objectClass 
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
        GROUP BY ?type ?predicate ?nodeShape ?datatype ?maxCount ?minCount ?hasValue 
                ?objectClass ?conditionPath ?conditionValue ?pattern ?message
    """, initNs={"sh": "http://www.w3.org/ns/shacl#", "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"})

    results = shacl.query(query)
    form_fields = defaultdict(dict)
    processed_shapes = set()  # Insieme per tracciare le shape già processate

    for row in results:        
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
            condition_entry['condition'] = {
                "path": str(row.conditionPath),
                "value": str(row.conditionValue)
            }
        if row.pattern:
            condition_entry['pattern'] = str(row.pattern)
        if row.message:
            condition_entry['message'] = str(row.message)

        if predicate not in form_fields[entity_type]:
            form_fields[entity_type][predicate] = []

        existing_field = None
        for field in form_fields[entity_type][predicate]:
            if (field.get('nodeShape') == nodeShape and
                field.get('hasValue') == hasValue and
                field.get('objectClass') == objectClass and
                field.get('min') == minCount and
                field.get('max') == maxCount and
                field.get('optionalValues') == optionalValues):
                existing_field = field
                break

        if existing_field:
            if datatype and str(datatype) not in existing_field.get("datatypes", []):
                existing_field.setdefault("datatypes", []).append(str(datatype))
            if condition_entry:
                existing_field.setdefault('conditions', []).append(condition_entry)
            if orNodes:
                # Salviamo solo l'informazione essenziale della shape per gli orNodes
                existing_field.setdefault("or", [])
                for node in orNodes:
                    if not any(s.get("shape") == node for s in existing_field["or"]):
                        existing_field["or"].append({
                            "shape": node,
                            "uri": predicate
                        })
        else:
            field_info = {
                "entityType": entity_type,
                "uri": predicate,
                "nodeShape": nodeShape,
                "datatypes": [datatype] if datatype else [],
                "min": minCount,
                "max": maxCount,
                "hasValue": hasValue,
                "objectClass": objectClass,
                "optionalValues": optionalValues,
                "conditions": [condition_entry] if condition_entry else [],
                "inputType": determine_input_type(datatype)
            }

            # Processa la nodeShape se presente
            if nodeShape:
                field_info["nestedShape"] = process_nested_shapes(
                    shacl,
                    display_rules=display_rules,
                    shape_uri=nodeShape,
                    depth=0,
                    processed_shapes=processed_shapes
                )

            # Se abbiamo orNodes, processiamo ogni shape
            if orNodes:
                # Aggiungiamo min e max per ogni shape nell'or
                field_info["or"] = [{
                    "shape": node,
                    "uri": predicate
                } for node in orNodes]
            
            form_fields[entity_type][predicate].append(field_info)

    return form_fields

def process_nested_shapes(shacl, display_rules, shape_uri, depth=0, processed_shapes=None):
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

    nested_query = prepareQuery("""
        SELECT ?type ?predicate ?nodeShape ?datatype ?maxCount ?minCount ?hasValue ?objectClass 
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
        GROUP BY ?type ?predicate ?nodeShape ?datatype ?maxCount ?minCount ?hasValue ?objectClass 
                ?conditionPath ?conditionValue ?pattern ?message
    """, initNs={"sh": "http://www.w3.org/ns/shacl#", "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"})

    nested_results = shacl.query(nested_query, initBindings={'shape': URIRef(shape_uri)})
    
    nested_fields = []
    entity_type = None
    temp_form_fields = defaultdict(dict)

    for row in nested_results:
        predicate = str(row.predicate)
        nodeShape = str(row.nodeShape) if row.nodeShape else None
        hasValue = str(row.hasValue) if row.hasValue else None
        objectClass = str(row.objectClass) if row.objectClass else None
        minCount = 0 if row.minCount is None else int(row.minCount)
        maxCount = None if row.maxCount is None else int(row.maxCount)
        datatype = str(row.datatype) if row.datatype else None
        optionalValues = [v for v in (row.optionalValues or "").split(",") if v]
        orNodes = [n for n in (row.orNodes or "").split(",") if n]

        condition_entry = {}
        if row.conditionPath and row.conditionValue:
            condition_entry['condition'] = {
                "path": str(row.conditionPath),
                "value": str(row.conditionValue)
            }
        if row.pattern:
            condition_entry['pattern'] = str(row.pattern)
        if row.message:
            condition_entry['message'] = str(row.message)

        if row.type:
            entity_type = str(row.type)

        if entity_type:
            if predicate not in temp_form_fields[entity_type]:
                temp_form_fields[entity_type][predicate] = []

            # Cerca un campo esistente con gli stessi attributi (eccetto datatype)
            existing_field = None
            for field in temp_form_fields[entity_type][predicate]:
                if (field.get('nodeShape') == nodeShape and
                    field.get('hasValue') == hasValue and
                    field.get('objectClass') == objectClass and
                    field.get('min') == minCount and
                    field.get('max') == maxCount and
                    field.get('optionalValues') == optionalValues):
                    existing_field = field
                    break

            if existing_field:
                # Aggiorna la lista dei datatypes
                if datatype and str(datatype) not in existing_field.get("datatypes", []):
                    existing_field.setdefault("datatypes", []).append(str(datatype))
                if condition_entry:
                    existing_field.setdefault('conditions', []).append(condition_entry)
                if orNodes:
                    # Aggiungiamo min e max per ogni shape nell'or
                    existing_field.setdefault("or", [])
                    for node in orNodes:
                        if not any(s.get("shape") == node and s.get("uri") == predicate for s in existing_field["or"]):
                            existing_field["or"].append({
                                "shape": node,
                                "uri": predicate
                            })
            else:
                field_info = {
                    "entityType": entity_type,
                    "uri": predicate,
                    "nodeShape": nodeShape,
                    "datatypes": [datatype] if datatype else [],
                    "min": minCount,
                    "max": maxCount,
                    "hasValue": hasValue,
                    "objectClass": objectClass,
                    "optionalValues": optionalValues,
                    "conditions": [condition_entry] if condition_entry else [],
                    "inputType": determine_input_type(datatype)
                }

                if nodeShape:
                    # Processa ricorsivamente le shape annidate
                    field_info["nestedShape"] = process_nested_shapes(
                        shacl, display_rules, nodeShape, depth + 1, processed_shapes
                    )

                if orNodes:
                    field_info["or"] = [{
                        "shape": node,
                        "uri": predicate
                    } for node in orNodes]

                temp_form_fields[entity_type][predicate].append(field_info)

    # Applichiamo le regole di visualizzazione al dizionario temporaneo
    if display_rules and entity_type:
        temp_form_fields = apply_display_rules(shacl, temp_form_fields, display_rules)

        # Applichiamo l'ordinamento ai campi
        temp_form_fields = order_form_fields(temp_form_fields, display_rules)

        # Estraiamo i campi processati per il tipo di entità
        if entity_type in temp_form_fields:
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
            if rule['class'] == entity_type:
                return [prop['property'] for prop in rule.get('displayProperties', [])]
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
    field_dict = {field['uri']: field for field in fields}
    
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
        entity_class = rule.get('class')
        if entity_class and entity_class in form_fields:
            for prop in rule.get('displayProperties', []):
                prop_uri = prop['property']
                if prop_uri in form_fields[entity_class]:
                    for field_info in form_fields[entity_class][prop_uri]:
                        add_display_information(field_info, prop)
                        # Chiamata ricorsiva per le nestedShape
                        if 'nestedShape' in field_info:
                            apply_display_rules_to_nested_shapes(field_info['nestedShape'], prop, display_rules)
                        if 'intermediateRelation' in prop:
                            handle_intermediate_relation(shacl, field_info, prop)
                    if 'displayRules' in prop:
                        handle_sub_display_rules(shacl, form_fields, entity_class, form_fields[entity_class][prop_uri], prop)
    return form_fields

def apply_display_rules_to_nested_shapes(nested_fields, parent_prop, display_rules):
    for field_info in nested_fields:
        # Trova la regola di visualizzazione corrispondente
        matching_rule = None
        for rule in display_rules:
            if rule.get('class') == field_info.get('entityType'):
                for prop in rule.get('displayProperties', []):
                    if prop['property'] == field_info['uri']:
                        matching_rule = prop
                        break
        if matching_rule:
            add_display_information(field_info, matching_rule)
        else:
            # Usa il displayName del parent se non c'è una regola specifica
            if 'displayName' in parent_prop and 'displayName' not in field_info:
                field_info['displayName'] = parent_prop['displayName']
        # Chiamata ricorsiva se ci sono altre nestedShape
        if 'nestedShape' in field_info:
            apply_display_rules_to_nested_shapes(field_info['nestedShape'], field_info, display_rules)

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
        "http://www.w3.org/2001/XMLSchema#email": "email"
    }
    return datatype_to_input.get(datatype, "text")

def add_display_information(field_info, prop):
    """
    Aggiunge informazioni di visualizzazione dal display_rules ad un campo.

    Argomenti:
        field_info (dict): Le informazioni del campo da aggiornare.
        prop (dict): Le informazioni della proprietà dalle display_rules.
    """
    if 'displayName' in prop:
        field_info['displayName'] = prop['displayName']
    if 'shouldBeDisplayed' in prop:
        field_info['shouldBeDisplayed'] = prop.get('shouldBeDisplayed', True)
    if 'orderedBy' in prop:
        field_info['orderedBy'] = prop['orderedBy']
    if 'inputType' in prop:
        field_info['inputType'] = prop['inputType']

def handle_intermediate_relation(shacl, field_info, prop):
    """
    Processa 'intermediateRelation' nelle display_rules e aggiorna il campo.

    Argomenti:
        field_info (dict): Le informazioni del campo da aggiornare.
        prop (dict): Le informazioni della proprietà dalle display_rules.
    """
    intermediate_relation = prop['intermediateRelation']
    target_entity_type = intermediate_relation.get('targetEntityType')
    intermediate_class = intermediate_relation.get('class')

    # Query SPARQL per trovare la proprietà collegante
    connecting_property_query = prepareQuery("""
        SELECT ?property
        WHERE {
            ?shape sh:targetClass ?intermediateClass ;
                   sh:property ?propertyShape .
            ?propertyShape sh:path ?property ;
                           sh:node ?targetNode .
            ?targetNode sh:targetClass ?targetClass.
        }
    """, initNs={"sh": "http://www.w3.org/ns/shacl#"})
    
    connecting_property_results = shacl.query(connecting_property_query, initBindings={
        'intermediateClass': URIRef(intermediate_class),
        'targetClass': URIRef(target_entity_type)
    })
    
    connecting_property = next((str(row.property) for row in connecting_property_results), None)

    # Cerca il campo con il connecting_property nella nestedShape
    intermediate_properties = {}
    if 'nestedShape' in field_info:
        for nested_field in field_info['nestedShape']:
            if nested_field.get('uri') == connecting_property:
                # Usa le proprietà dalla nestedShape del connecting_property
                if 'nestedShape' in nested_field:
                    for target_field in nested_field['nestedShape']:
                        uri = target_field.get('uri')
                        if uri:
                            if uri not in intermediate_properties:
                                intermediate_properties[uri] = []
                            intermediate_properties[uri].append(target_field)

    field_info['intermediateRelation'] = {
        "class": intermediate_class,
        "targetEntityType": target_entity_type,
        "connectingProperty": connecting_property,
        "properties": intermediate_properties
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
        matching_rule = next((rule for rule in prop['displayRules'] if rule['shape'] == original_field['nodeShape']), None)

        if matching_rule:
            new_field = {
                "entityType": entity_class,
                "objectClass": original_field.get("objectClass"),
                "uri": prop['property'],
                "datatype": original_field.get("datatype"),
                "min": original_field.get("min"),
                "max": original_field.get("max"),
                "hasValue": original_field.get("hasValue"),
                "nodeShape": original_field.get("nodeShape"),
                "nestedShape": original_field.get("nestedShape"),
                "displayName": matching_rule['displayName'],
                "optionalValues": original_field.get("optionalValues", []),
                "orderedBy": original_field.get('orderedBy')
            }

            if 'intermediateRelation' in original_field:
                new_field['intermediateRelation'] = original_field['intermediateRelation']

            # Aggiungi proprietà aggiuntive dalla shape SHACL
            if 'shape' in matching_rule:
                shape_uri = matching_rule['shape']
                additional_properties = extract_additional_properties(shacl, shape_uri)
                if additional_properties:
                    new_field['additionalProperties'] = additional_properties

            new_field_info_list.append(new_field)
        else:
            # Se non c'è una regola corrispondente, mantieni il campo originale
            new_field_info_list.append(original_field)

    form_fields[entity_class][prop['property']] = new_field_info_list

def extract_additional_properties(shacl, shape_uri):
    """
    Estrae proprietà aggiuntive da una shape SHACL.

    Argomenti:
        shape_uri (str): L'URI della shape SHACL.

    Restituisce:
        dict: Un dizionario delle proprietà aggiuntive.
    """
    additional_properties_query = prepareQuery("""
        SELECT ?predicate ?hasValue
        WHERE {
            ?shape a sh:NodeShape ;
                   sh:property ?property .
            ?property sh:path ?predicate ;
                     sh:hasValue ?hasValue .
        }
    """, initNs={"sh": "http://www.w3.org/ns/shacl#"})

    additional_properties_results = shacl.query(additional_properties_query, initBindings={
        'shape': URIRef(shape_uri)
    })

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
            entity_class = rule.get('class')
            if entity_class and entity_class in form_fields:
                ordered_properties = [prop_rule['property'] for prop_rule in rule.get('displayProperties', [])]
                ordered_form_fields[entity_class] = OrderedDict()
                for prop in ordered_properties:
                    if prop in form_fields[entity_class]:
                        ordered_form_fields[entity_class][prop] = form_fields[entity_class][prop]
                # Aggiungi le proprietà rimanenti non specificate nell'ordine
                for prop in form_fields[entity_class]:
                    if prop not in ordered_properties:
                        ordered_form_fields[entity_class][prop] = form_fields[entity_class][prop]
    else:
        ordered_form_fields = form_fields
    return ordered_form_fields

def enrich_or_shapes(form_fields):
    """
    Arricchisce la struttura 'or' nei form_fields con tutte le informazioni complete
    delle shape, mantenendo la stessa struttura usata per le altre parti del form.

    Args:
        form_fields (OrderedDict): La struttura dei form fields da arricchire

    Returns:
        OrderedDict: La struttura arricchita con le informazioni complete
    """
    # Costruiamo un mapping delle shape e del predicato e relative informazioni complete
    shape_predicate_to_info_map = {}
    for entity_type, properties in form_fields.items():
        for prop_uri, field_details_list in properties.items():
            for field_details in field_details_list:
                if field_details.get('nodeShape'):
                    key = (field_details['nodeShape'], field_details['uri'])
                    shape_predicate_to_info_map[key] = {
                        'uri': field_details.get('uri'),
                        'nodeShape': field_details.get('nodeShape'),
                        'datatypes': field_details.get('datatypes', []),
                        'min': field_details.get('min', 0),
                        'max': field_details.get('max'),
                        'hasValue': field_details.get('hasValue'),
                        'objectClass': field_details.get('objectClass'),
                        'optionalValues': field_details.get('optionalValues', []),
                        'conditions': field_details.get('conditions', []),
                        'inputType': field_details.get('inputType'),
                        'displayName': field_details.get('displayName'),
                        'shouldBeDisplayed': field_details.get('shouldBeDisplayed', True),
                        'orderedBy': field_details.get('orderedBy'),
                        'intermediateRelation': field_details.get('intermediateRelation'),
                        'nestedShape': field_details.get('nestedShape', []),
                        'additionalProperties': field_details.get('additionalProperties', {})
                    }

    # Ora arricchiamo la struttura 'or', mantenendo il tipo dell'entità padre
    for entity_type, properties in form_fields.items():
        for prop_uri, field_details_list in properties.items():
            for field_details in field_details_list:
                if 'or' in field_details:
                    enriched_or = []
                    for shape_info in field_details['or']:
                        shape_uri = shape_info.get('shape')
                        predicate_uri = shape_info.get('uri')
                        key = (shape_uri, predicate_uri)
                        if shape_uri and predicate_uri and key in shape_predicate_to_info_map:
                            base_info = shape_predicate_to_info_map[key].copy()

                            # Manteniamo l'entityType del contesto padre
                            enriched_shape = {
                                'shape': shape_uri,
                                'entityType': entity_type,  # Usiamo l'entityType del contesto padre
                                'uri': predicate_uri,
                                'nodeShape': shape_uri,
                                'datatypes': base_info.get('datatypes', []),
                                'min': base_info.get('min', 0),
                                'max': base_info.get('max', None),
                                'hasValue': base_info.get('hasValue'),
                                'objectClass': base_info.get('objectClass'),
                                'optionalValues': base_info.get('optionalValues', []),
                                'conditions': base_info.get('conditions', []),
                                'inputType': base_info.get('inputType'),
                                'displayName': base_info.get('displayName'),
                                'shouldBeDisplayed': base_info.get('shouldBeDisplayed', True),
                                'orderedBy': base_info.get('orderedBy'),
                                'intermediateRelation': base_info.get('intermediateRelation'),
                                'nestedShape': base_info.get('nestedShape', []),
                                'additionalProperties': base_info.get('additionalProperties', {})
                            }
                            enriched_or.append(enriched_shape)
                        else:
                            # Se non troviamo la combinazione, aggiungiamo un placeholder
                            enriched_or.append({
                                'shape': shape_uri,
                                'uri': predicate_uri,
                                'entityType': entity_type
                            })

                    # Sostituiamo la struttura 'or' originale con quella arricchita
                    field_details['or'] = enriched_or

    return form_fields