
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask_babel import gettext
from heritrace.editor import Editor
from heritrace.extensions import (display_rules, form_fields_cache,
                                  get_change_tracking_config,
                                  get_custom_filter, get_dataset_is_quadstore,
                                  get_provenance_sparql, get_sparql)
from heritrace.utils.converters import convert_to_datetime
from heritrace.utils.display_rules_utils import (get_highest_priority_class,
                                                 get_sortable_properties,
                                                 is_entity_type_visible)
from heritrace.utils.virtuoso_utils import (VIRTUOSO_EXCLUDED_GRAPHS,
                                            is_virtuoso)
from rdflib import RDF, XSD, ConjunctiveGraph, Graph, Literal, URIRef
from rdflib.plugins.sparql.algebra import translateUpdate
from rdflib.plugins.sparql.parser import parseUpdate
from SPARQLWrapper import JSON, XML, SPARQLWrapper
from time_agnostic_library.agnostic_entity import AgnosticEntity


def get_available_classes():
    """
    Fetch and format all available entity classes from the triplestore.
    
    Returns:
        list: List of dictionaries containing class information
    """
    sparql = get_sparql()
    custom_filter = get_custom_filter()

    if is_virtuoso():
        classes_query = f"""
            SELECT DISTINCT ?class (COUNT(DISTINCT ?subject) as ?count)
            WHERE {{
                GRAPH ?g {{
                    ?subject a ?class .
                }}
                FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
            }}
            GROUP BY ?class
            ORDER BY DESC(?count)
        """
    else:
        classes_query = """
            SELECT DISTINCT ?class (COUNT(DISTINCT ?subject) as ?count)
            WHERE {
                ?subject a ?class .
            }
            GROUP BY ?class
            ORDER BY DESC(?count)
        """
    
    sparql.setQuery(classes_query)
    sparql.setReturnFormat(JSON)
    classes_results = sparql.query().convert()

    available_classes = [
        {
            'uri': result['class']['value'],
            'label': custom_filter.human_readable_predicate(result['class']['value'], [result['class']['value']]),
            'count': int(result['count']['value'])
        }
        for result in classes_results["results"]["bindings"]
        if is_entity_type_visible(result['class']['value'])
    ]

    # Sort classes by label
    available_classes.sort(key=lambda x: x['label'].lower())
    return available_classes

def build_sort_clause(sort_property: str, entity_type: str, display_rules) -> str:
    """
    Costruisce la clausola di ordinamento SPARQL in base alla configurazione sortableBy.
    
    Args:
        sort_property: La proprietà su cui ordinare
        entity_type: Il tipo di entità
        
    Returns:
        Clausola SPARQL per l'ordinamento o stringa vuota
    """
    if not display_rules or not sort_property:
        return ""
        
    # Trova la configurazione di ordinamento
    sort_config = None
    for rule in display_rules:
        if rule['class'] == entity_type and 'sortableBy' in rule:
            sort_config = next(
                (s for s in rule['sortableBy'] if s['property'] == sort_property), 
                None
            )
            break
    
    if not sort_config:
        return ""
            
    return f"OPTIONAL {{ ?subject <{sort_property}> ?sortValue }}"

def get_entities_for_class(selected_class, page, per_page, sort_property=None, sort_direction='ASC'):
    """
    Retrieve entities for a specific class with pagination and sorting.
    
    Args:
        selected_class (str): URI of the class to fetch entities for
        page (int): Current page number
        per_page (int): Number of items per page
        sort_property (str, optional): Property to sort by
        sort_direction (str, optional): Sort direction ('ASC' or 'DESC')
        
    Returns:
        tuple: (list of entities, total count)
    """
    sparql = get_sparql()
    custom_filter = get_custom_filter()

    offset = (page - 1) * per_page

    # Build sort clause if sort property is provided
    sort_clause = ""
    order_clause = "ORDER BY ?subject"
    if sort_property:
        sort_clause = build_sort_clause(sort_property, selected_class, display_rules)
        order_clause = f"ORDER BY {sort_direction}(?sortValue)"

    # Build query based on database type
    if is_virtuoso():
        entities_query = f"""
        SELECT DISTINCT ?subject {f"?sortValue" if sort_property else ""}
        WHERE {{
            GRAPH ?g {{
                ?subject a <{selected_class}> .
                {sort_clause}
            }}
            FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
        }}
        {order_clause}
        LIMIT {per_page} 
        OFFSET {offset}
        """
        
        # Count query for total number of entities
        count_query = f"""
        SELECT (COUNT(DISTINCT ?subject) as ?count)
        WHERE {{
            GRAPH ?g {{
                ?subject a <{selected_class}> .
            }}
            FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
        }}
        """
    else:
        entities_query = f"""
        SELECT DISTINCT ?subject {f"?sortValue" if sort_property else ""}
        WHERE {{
            ?subject a <{selected_class}> .
            {sort_clause}
        }}
        {order_clause}
        LIMIT {per_page} 
        OFFSET {offset}
        """
        
        count_query = f"""
        SELECT (COUNT(DISTINCT ?subject) as ?count)
        WHERE {{
            ?subject a <{selected_class}> .
        }}
        """

    # Execute count query
    sparql.setQuery(count_query)
    sparql.setReturnFormat(JSON)
    count_results = sparql.query().convert()
    total_count = int(count_results["results"]["bindings"][0]["count"]["value"])

    # Execute entities query
    sparql.setQuery(entities_query)
    entities_results = sparql.query().convert()
    
    entities = []
    for result in entities_results["results"]["bindings"]:
        subject_uri = result['subject']['value']
        entity_label = custom_filter.human_readable_entity(subject_uri, [selected_class])
        
        entities.append({
            'uri': subject_uri,
            'label': entity_label
        })

    return entities, total_count

def get_catalog_data(selected_class, page, per_page, sort_property=None, sort_direction='ASC'):
    """
    Get catalog data with pagination and sorting.
    
    Args:
        selected_class (str): Selected class URI
        page (int): Current page number
        per_page (int): Items per page
        sort_property (str, optional): Property to sort by
        sort_direction (str, optional): Sort direction ('ASC' or 'DESC')
        
    Returns:
        dict: Catalog data including entities, pagination info, and sort settings
    """
    entities = []
    total_count = 0
    sortable_properties = []

    if selected_class:
        entities, total_count = get_entities_for_class(
            selected_class, 
            page, 
            per_page,
            sort_property,
            sort_direction
        )
        
        # Get sortable properties for the class
        sortable_properties = get_sortable_properties(selected_class, display_rules, form_fields_cache)

    if not sort_property and sortable_properties:
        sort_property = sortable_properties[0]['property']

    return {
        'entities': entities,
        'total_pages': (total_count + per_page - 1) // per_page if total_count > 0 else 0,
        'current_page': page,
        'per_page': per_page,
        'total_count': total_count,
        'sort_property': sort_property,
        'sort_direction': sort_direction,
        'sortable_properties': sortable_properties,
        'selected_class': selected_class
    }

def fetch_data_graph_for_subject(subject: str) -> Graph:
    g = Graph()
    sparql = get_sparql()

    if is_virtuoso():
        query = f"""
        SELECT ?predicate ?object WHERE {{
            GRAPH ?g {{
                <{subject}> ?predicate ?object.
            }}
            FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
        }}
        """
    else:
        query = f"""
        SELECT ?predicate ?object WHERE {{
            <{subject}> ?predicate ?object.
        }}
        """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    triples = sparql.query().convert().get("results", {}).get("bindings", [])
    
    for triple in triples:
        value = (Literal(triple['object']['value'], datatype=URIRef(triple['object']['datatype'])) 
                if triple['object']['type'] in {'literal', 'typed-literal'} and 'datatype' in triple['object'] 
                else Literal(triple['object']['value'], datatype=XSD.string) 
                if triple['object']['type'] in {'literal', 'typed-literal'} 
                else URIRef(triple['object']['value']))
        g.add((URIRef(subject), URIRef(triple['predicate']['value']), value))
    
    return g

def parse_sparql_update(query) -> dict:
    parsed = parseUpdate(query)
    translated = translateUpdate(parsed).algebra
    modifications = {}

    def extract_quads(quads):
        result = []
        if isinstance(quads, defaultdict):
            for graph, triples in quads.items():
                for triple in triples:
                    result.append((triple[0], triple[1], triple[2]))
        else:
            # Fallback for triples
            result.extend(quads)
        return result

    for operation in translated:
        if operation.name == "DeleteData":
            if hasattr(operation, 'quads'):
                deletions = extract_quads(operation.quads)
            else:
                deletions = operation.triples
            if deletions:
                modifications.setdefault(gettext('Deletions'), list()).extend(deletions)
        elif operation.name == "InsertData":
            if hasattr(operation, 'quads'):
                additions = extract_quads(operation.quads)
            else:
                additions = extract_quads(operation.quads)
            if additions:
                modifications.setdefault(gettext('Additions'), list()).extend(additions)

    return modifications

def fetch_data_graph_recursively(subject_uri, max_depth=5, current_depth=0, visited=None):
    """
    Recursively fetch all quads associated with a subject and its connected entities.

    Args:
        subject_uri (str): The URI of the subject to fetch.
        max_depth (int): Maximum depth of recursion.
        current_depth (int): Current depth in recursion.
        visited (set): Set of visited URIs to avoid cycles.

    Returns:
        ConjunctiveGraph: A graph containing all fetched quads.
    """
    dataset_is_quadstore = get_dataset_is_quadstore()
    sparql = get_sparql()

    if visited is None:
        visited = set()
    if current_depth > max_depth or subject_uri in visited:
        return ConjunctiveGraph()

    visited.add(subject_uri)
    g = ConjunctiveGraph()

    # Fetch all quads where the subject is involved
    if dataset_is_quadstore:
        query = f"""
        SELECT ?s ?p ?o ?g
        WHERE {{
            GRAPH ?g {{
                ?s ?p ?o .
                VALUES (?s) {{(<{subject_uri}>)}}
            }}
        }}
        """
    else:
        query = f"""
        CONSTRUCT {{
            <{subject_uri}> ?p ?o .
        }}
        WHERE {{
            <{subject_uri}> ?p ?o .
        }}
        """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON if dataset_is_quadstore else XML)
    results = sparql.query().convert()

    if dataset_is_quadstore:
        for result in results["results"]["bindings"]:
            s = URIRef(result["s"]["value"])
            p = URIRef(result["p"]["value"])
            o = result["o"]
            g_context = URIRef(result["g"]["value"])

            if o["type"] == "uri":
                o_node = URIRef(o["value"])
            else:
                value = o["value"]
                lang = result.get("lang", {}).get("value")
                datatype = o.get("datatype")
                
                if lang:
                    o_node = Literal(value, lang=lang)
                elif datatype:
                    o_node = Literal(value, datatype=URIRef(datatype))
                else:
                    o_node = Literal(value, datatype=XSD.string)
            g.add((s, p, o_node, g_context))
    else:
        for triple in results:
            g.add(triple)

    # Recursively fetch connected entities
    for triple in g.quads((URIRef(subject_uri), None, None, None)):
        o = triple[2]
        if isinstance(o, URIRef) and o not in visited:
            if dataset_is_quadstore:
                for quad in fetch_data_graph_recursively(str(o), max_depth, current_depth + 1, visited).quads():
                    g.add(quad)
            else:
                for triple in fetch_data_graph_recursively(str(o), max_depth, current_depth + 1, visited):
                    g.add(triple)
    return g

def get_deleted_entities_with_filtering(page=1, per_page=50, sort_property='deletionTime', sort_direction='DESC',
                                        selected_class=None):
    """
    Fetch and process deleted entities from the provenance graph, with filtering and sorting.
    """
    sortable_properties = [{'property': 'deletionTime', 'displayName': 'Deletion Time', 'sortType': 'date'}]
    provenance_sparql = get_provenance_sparql()
    custom_filter = get_custom_filter()

    if selected_class:
        sortable_properties.extend(get_sortable_properties(selected_class, display_rules, form_fields_cache))

    prov_query = """
    SELECT DISTINCT ?entity ?lastSnapshot ?deletionTime ?agent ?lastValidSnapshotTime
    WHERE {
        ?lastSnapshot a <http://www.w3.org/ns/prov#Entity> ;
                     <http://www.w3.org/ns/prov#specializationOf> ?entity ;
                     <http://www.w3.org/ns/prov#generatedAtTime> ?deletionTime ;
                     <http://www.w3.org/ns/prov#invalidatedAtTime> ?invalidationTime ;
                     <http://www.w3.org/ns/prov#wasDerivedFrom> ?lastValidSnapshot.

        ?lastValidSnapshot <http://www.w3.org/ns/prov#generatedAtTime> ?lastValidSnapshotTime .

        OPTIONAL { ?lastSnapshot <http://www.w3.org/ns/prov#wasAttributedTo> ?agent . }

        FILTER NOT EXISTS {
            ?laterSnapshot <http://www.w3.org/ns/prov#wasDerivedFrom> ?lastSnapshot .
        }
    }
    """
    provenance_sparql.setQuery(prov_query)
    provenance_sparql.setReturnFormat(JSON)
    prov_results = provenance_sparql.query().convert()

    results_bindings = prov_results["results"]["bindings"]
    if not results_bindings:
        return [], [], None, []

    # Process entities with parallel execution
    deleted_entities = []
    max_workers = max(1, min(32, len(results_bindings)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_entity = {
            executor.submit(process_deleted_entity, result, sortable_properties): result
            for result in results_bindings
        }
        for future in as_completed(future_to_entity):
            entity_info = future.result()
            if entity_info is not None:
                deleted_entities.append(entity_info)

    # Calculate class counts from filtered entities
    class_counts = {}
    for entity in deleted_entities:
        for type_uri in entity["entity_types"]:
            class_counts[type_uri] = class_counts.get(type_uri, 0) + 1

    available_classes = [
        {
            'uri': class_uri,
            'label': custom_filter.human_readable_predicate(class_uri, [class_uri]),
            'count': count
        }
        for class_uri, count in class_counts.items()
    ]

    # Determine the sort key based on sort_property
    reverse_sort = (sort_direction.upper() == 'DESC')
    if sort_property == 'deletionTime':
        deleted_entities.sort(key=lambda e: e["deletionTime"], reverse=reverse_sort)
    else:
        deleted_entities.sort(key=lambda e: e['sort_values'].get(sort_property, '').lower(), reverse=reverse_sort)

    # Paginate the results
    offset = (page - 1) * per_page
    paginated_entities = deleted_entities[offset:offset + per_page]

    available_classes.sort(key=lambda x: x['label'].lower())
    if not selected_class and available_classes:
        selected_class = available_classes[0]['uri']

    if selected_class:
        paginated_entities = [entity for entity in paginated_entities if selected_class in entity["entity_types"]]
    else:
        paginated_entities = []

    return paginated_entities, available_classes, selected_class, sortable_properties

def process_deleted_entity(result, sortable_properties):
    """
    Process a single deleted entity, filtering by visible classes.
    """
    change_tracking_config = get_change_tracking_config()
    custom_filter = get_custom_filter()

    entity_uri = result["entity"]["value"]
    last_valid_snapshot_time = result["lastValidSnapshotTime"]["value"]

    # Get entity state at its last valid time
    agnostic_entity = AgnosticEntity(res=entity_uri, config=change_tracking_config, related_entities_history=True)
    state, _, _ = agnostic_entity.get_state_at_time((last_valid_snapshot_time, last_valid_snapshot_time))

    if entity_uri not in state:
        return None

    last_valid_time = convert_to_datetime(last_valid_snapshot_time, stringify=True)
    last_valid_state: ConjunctiveGraph = state[entity_uri][last_valid_time]

    # Get entity types and filter for visible ones early
    entity_types = [str(o) for s, p, o in last_valid_state.triples((URIRef(entity_uri), RDF.type, None))]
    visible_types = [t for t in entity_types if is_entity_type_visible(t)]

    if not visible_types:
        return None

    # Get the highest priority class
    highest_priority_type = get_highest_priority_class(visible_types)
    if not highest_priority_type:
        return None

    # Extract sort values for sortable properties
    sort_values = {}
    for prop in sortable_properties:
        prop_uri = prop['property']
        values = [str(o) for s, p, o in last_valid_state.triples((URIRef(entity_uri), URIRef(prop_uri), None))]
        sort_values[prop_uri] = values[0] if values else ''

    return {
        "uri": entity_uri,
        "deletionTime": result["deletionTime"]["value"],
        "deletedBy": custom_filter.format_agent_reference(result.get("agent", {}).get("value", "")),
        "lastValidSnapshotTime": last_valid_snapshot_time,
        "type": custom_filter.human_readable_predicate(highest_priority_type, [highest_priority_type]),
        "label": custom_filter.human_readable_entity(entity_uri, [highest_priority_type], last_valid_state),
        "entity_types": visible_types,
        "sort_values": sort_values
    }

def find_orphaned_entities(subject, predicate=None, object_value=None):
    """
    Find entities that would become orphaned after deleting a triple or an entire entity.
    An entity is considered orphaned if:
    1. It has no incoming references from other entities (except from the entity being deleted)
    2. It does not reference any entities that are subjects of other triples
    
    Args:
        subject (str): The URI of the subject being deleted
        predicate (str, optional): The predicate being deleted. If None, entire entity is being deleted
        object_value (str, optional): The object value being deleted. If None, entire entity is being deleted
        
    Returns:
        list: A list of dictionaries containing URIs and types of orphaned entities
    """
    sparql = get_sparql()
    
    if predicate and object_value:
        query = f"""
        SELECT DISTINCT ?entity ?type
        WHERE {{
            # The entity we're checking
            <{subject}> <{predicate}> ?entity .
            FILTER(?entity = <{object_value}>)
            
            # Get entity type
            ?entity a ?type .
            
            # First condition: No incoming references from other entities
            FILTER NOT EXISTS {{
                ?other ?anyPredicate ?entity .
                FILTER(?other != <{subject}>)
            }}
            
            # Second condition: Does not reference any entities that are subjects
            FILTER NOT EXISTS {{
                # Find any outgoing connections from our entity
                ?entity ?outgoingPredicate ?connectedEntity .
                
                # Check if the connected entity is a subject in any triple
                ?connectedEntity ?furtherPredicate ?furtherObject .
            }}
        }}
        """
    else:
        query = f"""
        SELECT DISTINCT ?entity ?type
        WHERE {{
            # Find all entities referenced by the subject being deleted
            <{subject}> ?p ?entity .
            
            # Only consider URIs, not literal values
            FILTER(isIRI(?entity))
            
            # Get entity type
            ?entity a ?type .
            
            # First condition: No incoming references from other entities
            FILTER NOT EXISTS {{
                ?other ?anyPredicate ?entity .
                FILTER(?other != <{subject}>)
            }}
            
            # Second condition: Does not reference any entities that are subjects
            FILTER NOT EXISTS {{
                # Find any outgoing connections from our entity
                ?entity ?outgoingPredicate ?connectedEntity .
                
                # Check if the connected entity is a subject in any triple
                # (excluding the entity being deleted)
                ?connectedEntity ?furtherPredicate ?furtherObject .
                FILTER(?connectedEntity != <{subject}>)
            }}
        }}
        """
    
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    orphaned_entities = []
    for result in results["results"]["bindings"]:
        orphaned_entities.append({
            'uri': result["entity"]["value"],
            'type': result["type"]["value"]
        })
    
    return orphaned_entities

def import_entity_graph(editor: Editor, subject: str, max_depth: int = 5):
    """
    Recursively import the main subject and its connected entity graph up to a specified depth.

    This function imports the specified subject and all entities connected to it,
    directly or indirectly, up to the maximum depth specified. It traverses the
    graph of connected entities, importing each one into the editor.

    Args:
    editor (Editor): The Editor instance to use for importing.
    subject (str): The URI of the subject to start the import from.
    max_depth (int): The maximum depth of recursion (default is 5).

    Returns:
    Editor: The updated Editor instance with all imported entities.
    """
    imported_subjects = set()

    def recursive_import(current_subject: str, current_depth: int):
        if current_depth > max_depth or current_subject in imported_subjects:
            return

        imported_subjects.add(current_subject)
        editor.import_entity(URIRef(current_subject))

        query = f"""
            SELECT ?p ?o
            WHERE {{
                <{current_subject}> ?p ?o .
                FILTER(isIRI(?o))
            }}
        """
        
        sparql = SPARQLWrapper(editor.dataset_endpoint)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        for result in results["results"]["bindings"]:
            object_entity = result["o"]["value"]
            recursive_import(object_entity, current_depth + 1)

    recursive_import(subject, 1)
    return editor