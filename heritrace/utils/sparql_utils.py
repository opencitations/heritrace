import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List

from heritrace.editor import Editor
from heritrace.extensions import (display_rules, form_fields_cache,
                                  get_change_tracking_config,
                                  get_custom_filter, get_dataset_is_quadstore,
                                  get_display_rules, get_provenance_sparql,
                                  get_sparql)
from heritrace.utils.converters import convert_to_datetime
from heritrace.utils.display_rules_utils import (get_highest_priority_class,
                                                 get_sortable_properties,
                                                 is_entity_type_visible)
from heritrace.utils.virtuoso_utils import (VIRTUOSO_EXCLUDED_GRAPHS,
                                            is_virtuoso)
from rdflib import RDF, ConjunctiveGraph, Graph, Literal, URIRef
from rdflib.plugins.sparql.algebra import translateUpdate
from rdflib.plugins.sparql.parser import parseUpdate
from SPARQLWrapper import JSON, SPARQLWrapper
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
            "uri": result["class"]["value"],
            "label": custom_filter.human_readable_predicate(
                result["class"]["value"], [result["class"]["value"]]
            ),
            "count": int(result["count"]["value"]),
        }
        for result in classes_results["results"]["bindings"]
        if is_entity_type_visible(result["class"]["value"])
    ]

    # Sort classes by label
    available_classes.sort(key=lambda x: x["label"].lower())
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
        if rule["class"] == entity_type and "sortableBy" in rule:
            sort_config = next(
                (s for s in rule["sortableBy"] if s["property"] == sort_property), None
            )
            break

    if not sort_config:
        return ""

    return f"OPTIONAL {{ ?subject <{sort_property}> ?sortValue }}"


def get_entities_for_class(
    selected_class, page, per_page, sort_property=None, sort_direction="ASC"
):
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
        subject_uri = result["subject"]["value"]
        entity_label = custom_filter.human_readable_entity(
            subject_uri, [selected_class]
        )

        entities.append({"uri": subject_uri, "label": entity_label})

    return entities, total_count


def get_catalog_data(
    selected_class, page, per_page, sort_property=None, sort_direction="ASC"
):
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
            selected_class, page, per_page, sort_property, sort_direction
        )

        # Get sortable properties for the class
        sortable_properties = get_sortable_properties(
            selected_class, display_rules, form_fields_cache
        )

    if not sort_property and sortable_properties:
        sort_property = sortable_properties[0]["property"]

    return {
        "entities": entities,
        "total_pages": (
            (total_count + per_page - 1) // per_page if total_count > 0 else 0
        ),
        "current_page": page,
        "per_page": per_page,
        "total_count": total_count,
        "sort_property": sort_property,
        "sort_direction": sort_direction,
        "sortable_properties": sortable_properties,
        "selected_class": selected_class,
    }


def fetch_data_graph_for_subject(subject: str) -> Graph | ConjunctiveGraph:
    """
    Fetch all triples/quads associated with a subject from the dataset.
    Handles both triplestore and quadstore cases appropriately.

    Args:
        subject (str): The URI of the subject to fetch data for

    Returns:
        Graph|ConjunctiveGraph: A graph containing all triples/quads for the subject
    """
    g = ConjunctiveGraph() if get_dataset_is_quadstore() else Graph()
    sparql = get_sparql()

    if is_virtuoso():
        # For virtuoso we need to explicitly query the graph
        query = f"""
        SELECT ?predicate ?object ?g WHERE {{
            GRAPH ?g {{
                <{subject}> ?predicate ?object.
            }}
            FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
        }}
        """
    else:
        if get_dataset_is_quadstore():
            # For non-virtuoso quadstore, we need to query all graphs
            query = f"""
            SELECT ?predicate ?object ?g WHERE {{
                GRAPH ?g {{
                    <{subject}> ?predicate ?object.
                }}
            }}
            """
        else:
            # For regular triplestore
            query = f"""
            SELECT ?predicate ?object WHERE {{
                <{subject}> ?predicate ?object.
            }}
            """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert().get("results", {}).get("bindings", [])

    for result in results:
        # Create the appropriate value (Literal or URIRef)
        obj_data = result["object"]
        if obj_data["type"] in {"literal", "typed-literal"}:
            if "datatype" in obj_data:
                value = Literal(
                    obj_data["value"], datatype=URIRef(obj_data["datatype"])
                )
            else:
                value = Literal(obj_data["value"])
        else:
            value = URIRef(obj_data["value"])

        # Add triple/quad based on store type
        if get_dataset_is_quadstore():
            graph_uri = URIRef(result["g"]["value"])
            g.add(
                (
                    URIRef(subject),
                    URIRef(result["predicate"]["value"]),
                    value,
                    graph_uri,
                )
            )
        else:
            g.add((URIRef(subject), URIRef(result["predicate"]["value"]), value))

    return g


def parse_sparql_update(query) -> dict:
    parsed = parseUpdate(query)
    translated = translateUpdate(parsed).algebra
    modifications = {}

    def extract_quads(quads):
        result = []
        for graph, triples in quads.items():
            for triple in triples:
                result.append((triple[0], triple[1], triple[2]))
        return result

    for operation in translated:
        if operation.name == "DeleteData":
            if hasattr(operation, "quads") and operation.quads:
                deletions = extract_quads(operation.quads)
            else:
                deletions = operation.triples
            if deletions:
                modifications.setdefault("Deletions", list()).extend(deletions)
        elif operation.name == "InsertData":
            if hasattr(operation, "quads") and operation.quads:
                additions = extract_quads(operation.quads)
            else:
                additions = operation.triples
            if additions:
                modifications.setdefault("Additions", list()).extend(additions)

    return modifications


def fetch_current_state_with_related_entities(
    provenance: dict,
) -> Graph | ConjunctiveGraph:
    """
    Fetch the current state of an entity and all its related entities known from provenance.

    Args:
        provenance (dict): Dictionary containing provenance metadata for main entity and related entities

    Returns:
        ConjunctiveGraph: A graph containing the current state of all entities
    """
    combined_graph = ConjunctiveGraph() if get_dataset_is_quadstore() else Graph()

    # Fetch state for all entities mentioned in provenance
    for entity_uri in provenance.keys():
        current_graph = fetch_data_graph_for_subject(entity_uri)

        if get_dataset_is_quadstore():
            for quad in current_graph.quads():
                combined_graph.add(quad)
        else:
            for triple in current_graph:
                combined_graph.add(triple)

    return combined_graph


def get_deleted_entities_with_filtering(
    page=1,
    per_page=50,
    sort_property="deletionTime",
    sort_direction="DESC",
    selected_class=None,
):
    """
    Fetch and process deleted entities from the provenance graph, with filtering and sorting.
    """
    sortable_properties = [
        {"property": "deletionTime", "displayName": "Deletion Time", "sortType": "date"}
    ]
    provenance_sparql = get_provenance_sparql()
    custom_filter = get_custom_filter()

    if selected_class:
        sortable_properties.extend(
            get_sortable_properties(selected_class, display_rules, form_fields_cache)
        )

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
        return [], [], None, [], 0

    # Process entities with parallel execution
    deleted_entities = []
    max_workers = max(1, min(os.cpu_count() or 4, len(results_bindings)))
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
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
            "uri": class_uri,
            "label": custom_filter.human_readable_predicate(class_uri, [class_uri]),
            "count": count,
        }
        for class_uri, count in class_counts.items()
    ]

    # Determine the sort key based on sort_property
    reverse_sort = sort_direction.upper() == "DESC"
    if sort_property == "deletionTime":
        deleted_entities.sort(key=lambda e: e["deletionTime"], reverse=reverse_sort)
    else:
        deleted_entities.sort(
            key=lambda e: e["sort_values"].get(sort_property, "").lower(),
            reverse=reverse_sort,
        )

    available_classes.sort(key=lambda x: x["label"].lower())
    if not selected_class and available_classes:
        selected_class = available_classes[0]["uri"]

    # First filter by class
    if selected_class:
        filtered_entities = [
            entity
            for entity in deleted_entities
            if selected_class in entity["entity_types"]
        ]
    else:
        filtered_entities = deleted_entities

    # Calculate total count for pagination
    total_count = len(filtered_entities)

    # Then paginate the filtered results
    offset = (page - 1) * per_page
    paginated_entities = filtered_entities[offset : offset + per_page]

    return paginated_entities, available_classes, selected_class, sortable_properties, total_count


def process_deleted_entity(result, sortable_properties):
    """
    Process a single deleted entity, filtering by visible classes.
    """
    change_tracking_config = get_change_tracking_config()
    custom_filter = get_custom_filter()

    entity_uri = result["entity"]["value"]
    last_valid_snapshot_time = result["lastValidSnapshotTime"]["value"]

    # Get entity state at its last valid time
    agnostic_entity = AgnosticEntity(
        res=entity_uri, config=change_tracking_config, related_entities_history=True
    )
    state, _, _ = agnostic_entity.get_state_at_time(
        (last_valid_snapshot_time, last_valid_snapshot_time)
    )

    if entity_uri not in state:
        return None

    last_valid_time = convert_to_datetime(last_valid_snapshot_time, stringify=True)
    last_valid_state: ConjunctiveGraph = state[entity_uri][last_valid_time]

    # Get entity types and filter for visible ones early
    entity_types = [
        str(o)
        for s, p, o in last_valid_state.triples((URIRef(entity_uri), RDF.type, None))
    ]
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
        prop_uri = prop["property"]
        values = [
            str(o)
            for s, p, o in last_valid_state.triples(
                (URIRef(entity_uri), URIRef(prop_uri), None)
            )
        ]
        sort_values[prop_uri] = values[0] if values else ""

    return {
        "uri": entity_uri,
        "deletionTime": result["deletionTime"]["value"],
        "deletedBy": custom_filter.format_agent_reference(
            result.get("agent", {}).get("value", "")
        ),
        "lastValidSnapshotTime": last_valid_snapshot_time,
        "type": custom_filter.human_readable_predicate(
            highest_priority_type, [highest_priority_type]
        ),
        "label": custom_filter.human_readable_entity(
            entity_uri, [highest_priority_type], last_valid_state
        ),
        "entity_types": visible_types,
        "sort_values": sort_values,
    }


def find_orphaned_entities(subject, entity_type, predicate=None, object_value=None):
    """
    Find entities that would become orphaned after deleting a triple or an entire entity,
    including intermediate relation entities.

    An entity is considered orphaned if:
    1. It has no incoming references from other entities (except from the entity being deleted)
    2. It does not reference any entities that are subjects of other triples

    For intermediate relations, an entity is also considered orphaned if:
    1. It connects to the entity being deleted
    2. It has no other valid connections after the deletion
    3. It is directly involved in the deletion operation (if predicate and object_value are specified)

    Args:
        subject (str): The URI of the subject being deleted
        entity_type (str): The type of the entity being deleted
        predicate (str, optional): The predicate being deleted
        object_value (str, optional): The object value being deleted

    Returns:
        tuple: Lists of (orphaned_entities, intermediate_orphans)
    """
    sparql = get_sparql()
    display_rules = get_display_rules()

    # Extract intermediate relation classes from display rules
    intermediate_classes = set()

    for rule in display_rules:
        if rule["class"] == entity_type:
            for prop in rule.get("displayProperties", []):
                if "intermediateRelation" in prop:
                    intermediate_classes.add(prop["intermediateRelation"]["class"])

    # Query to find regular orphans
    orphan_query = f"""
    SELECT DISTINCT ?entity ?type
    WHERE {{
        {f"<{subject}> <{predicate}> ?entity ." if predicate and object_value else ""}
        {f"FILTER(?entity = <{object_value}>)" if predicate and object_value else ""}
        
        # If no specific predicate, get all connected entities
        {f"<{subject}> ?p ?entity ." if not predicate else ""}
        
        FILTER(isIRI(?entity))
        ?entity a ?type .
        
        # No incoming references from other entities
        FILTER NOT EXISTS {{
            ?other ?anyPredicate ?entity .
            FILTER(?other != <{subject}>)
        }}
        
        # No outgoing references to active entities
        FILTER NOT EXISTS {{
            ?entity ?outgoingPredicate ?connectedEntity .
            ?connectedEntity ?furtherPredicate ?furtherObject .
            {f"FILTER(?connectedEntity != <{subject}>)" if not predicate else ""}
        }}
        
        # Exclude intermediate relation entities
        FILTER(?type NOT IN (<{f">, <".join(intermediate_classes)}>))
    }}
    """

    # Query to find orphaned intermediate relations
    # Se stiamo cancellando una tripla specifica (predicate e object_value specificati)
    if predicate and object_value:
        # Verifica se l'object_value è un'entità intermedia
        intermediate_query = f"""
        SELECT DISTINCT ?entity ?type
        WHERE {{
            <{object_value}> a ?type .
            FILTER(?type IN (<{f">, <".join(intermediate_classes)}>))            
            BIND(<{object_value}> AS ?entity)
        }}
        """
    else:
        # Se stiamo cancellando l'intera entità, trova tutte le entità intermedie collegate
        intermediate_query = f"""
        SELECT DISTINCT ?entity ?type
        WHERE {{
            # Find intermediate relations connected to the entity being deleted
            {{
                <{subject}> ?p ?entity .
                ?entity a ?type .
                FILTER(?type IN (<{f">, <".join(intermediate_classes)}>))
            }} UNION {{
                ?entity ?p <{subject}> .
                ?entity a ?type .
                FILTER(?type IN (<{f">, <".join(intermediate_classes)}>))
            }}        
        }}
        """

    orphaned = []
    intermediate_orphans = []

    # Execute queries and process results
    for query, result_list in [
        (orphan_query, orphaned),
        (intermediate_query, intermediate_orphans),
    ]:
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        for result in results["results"]["bindings"]:
            result_list.append(
                {"uri": result["entity"]["value"], "type": result["type"]["value"]}
            )

    return orphaned, intermediate_orphans


def import_entity_graph(editor: Editor, subject: str, max_depth: int = 5, include_referencing_entities: bool = False):
    """
    Recursively import the main subject and its connected entity graph up to a specified depth.

    This function imports the specified subject and all entities connected to it,
    directly or indirectly, up to the maximum depth specified. It traverses the
    graph of connected entities, importing each one into the editor.

    Args:
    editor (Editor): The Editor instance to use for importing.
    subject (str): The URI of the subject to start the import from.
    max_depth (int): The maximum depth of recursion (default is 5).
    include_referencing_entities (bool): Whether to include entities that have the subject as their object (default False).
                                         Useful when deleting an entity to ensure all references are properly removed.

    Returns:
    Editor: The updated Editor instance with all imported entities.
    """
    imported_subjects = set()

    # First import referencing entities if needed
    if include_referencing_entities:
        sparql = SPARQLWrapper(editor.dataset_endpoint)
        
        # Build query based on database type
        if editor.dataset_is_quadstore:
            query = f"""
            SELECT DISTINCT ?s
            WHERE {{
                GRAPH ?g {{
                    ?s ?p <{subject}> .
                }}
                FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
            }}
            """
        else:
            query = f"""
            SELECT DISTINCT ?s
            WHERE {{
                ?s ?p <{subject}> .
                FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
            }}
            """
        
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        
        # Import each referencing entity
        for result in results["results"]["bindings"]:
            referencing_subject = result["s"]["value"]
            if referencing_subject != subject and referencing_subject not in imported_subjects:
                imported_subjects.add(referencing_subject)
                editor.import_entity(URIRef(referencing_subject))

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


def get_entity_types(subject_uri: str) -> List[str]:
    """
    Get all RDF types for an entity.

    Args:
        subject_uri: URI of the entity

    Returns:
        List of type URIs
    """
    sparql = get_sparql()

    query = f"""
    SELECT ?type WHERE {{
        <{subject_uri}> a ?type .
    }}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    return [result["type"]["value"] for result in results["results"]["bindings"]]
