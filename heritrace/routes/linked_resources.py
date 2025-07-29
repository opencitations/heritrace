import traceback

from flask import Blueprint, current_app, jsonify, request
from flask_babel import gettext
from flask_login import login_required
from heritrace.extensions import (get_custom_filter, get_display_rules,
                                  get_sparql)
from heritrace.utils.display_rules_utils import get_highest_priority_class
from heritrace.utils.shacl_utils import determine_shape_for_classes
from heritrace.utils.sparql_utils import get_entity_types
from heritrace.utils.virtuoso_utils import (VIRTUOSO_EXCLUDED_GRAPHS,
                                            is_virtuoso)
from SPARQLWrapper import JSON

linked_resources_bp = Blueprint("linked_resources", __name__, url_prefix="/api/linked-resources")


def _is_proxy_entity(entity_types: list) -> tuple[bool, str]:
    """
    Check if an entity is a proxy (intermediate relation) entity based on display rules.
    
    Args:
        entity_types: List of entity types
        
    Returns:
        Tuple of (is_proxy, connecting_predicate)
    """
    if not entity_types:
        return False, ""
    
    display_rules = get_display_rules()
    if not display_rules:
        return False, ""
    
    for entity_type in entity_types:
        for rule in display_rules:
            for prop in rule.get("displayProperties", []):
                intermediate_config = prop.get("intermediateRelation")
                if intermediate_config and intermediate_config.get("class") == entity_type:
                    return True, prop["property"]
                    
                for display_rule in prop.get("displayRules", []):
                    nested_intermediate_config = display_rule.get("intermediateRelation")
                    if nested_intermediate_config and nested_intermediate_config.get("class") == entity_type:
                        return True, prop["property"]
    
    return False, ""


def _resolve_proxy_entity(subject_uri: str, predicate: str, connecting_predicate: str) -> tuple[str, str]:
    """
    Resolve proxy entities to their source entities.
    
    Args:
        subject_uri: URI of the proxy entity
        predicate: Original predicate
        connecting_predicate: The predicate that connects source to proxy
        
    Returns:
        Tuple of (final_subject_uri, final_predicate)
    """
    # Query to find the source entity that points to this proxy
    sparql = get_sparql()
    proxy_query_parts = [
        "SELECT DISTINCT ?source WHERE {",
    ]
    
    if is_virtuoso:
        proxy_query_parts.extend([
            "    GRAPH ?g {",
            f"        ?source <{connecting_predicate}> <{subject_uri}> .",
            "    }",
            f"    FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))"
        ])
    else:
        proxy_query_parts.extend([
            f"    ?source <{connecting_predicate}> <{subject_uri}> ."
        ])
    
    proxy_query_parts.append("} LIMIT 1")
    proxy_query = "\n".join(proxy_query_parts)
    
    try:
        sparql.setQuery(proxy_query)
        sparql.setReturnFormat(JSON)
        proxy_results = sparql.query().convert()
        
        proxy_bindings = proxy_results.get("results", {}).get("bindings", [])
        if proxy_bindings:
            source_uri = proxy_bindings[0]["source"]["value"]
            
            return source_uri, connecting_predicate
            
    except Exception as e:
        current_app.logger.error(f"Error resolving proxy entity {subject_uri}: {e}")
    
    return subject_uri, predicate

def get_paginated_inverse_references(subject_uri: str, limit: int, offset: int) -> tuple[list[dict], bool]:
    """
    Get paginated entities that reference this entity using the limit+1 strategy.

    Args:
        subject_uri: URI of the entity to find references to.
        limit: Maximum number of references to return per page.
        offset: Number of references to skip.

    Returns:
        A tuple containing:
            - List of dictionaries containing reference information (max 'limit' items).
            - Boolean indicating if there are more references.
    """
    sparql = get_sparql()
    custom_filter = get_custom_filter()
    references = []
    query_limit = limit + 1

    try:
        query_parts = [
            "SELECT DISTINCT ?s ?p WHERE {",
        ]
        if is_virtuoso:
            query_parts.append("    GRAPH ?g { ?s ?p ?o . }")
            query_parts.append(f"    FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))")
        else:
            query_parts.append("    ?s ?p ?o .")

        query_parts.extend([
            f"    FILTER(?o = <{subject_uri}>)",
            "    FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)",
            f"}} ORDER BY ?s OFFSET {offset} LIMIT {query_limit}" # Use query_limit
        ])
        main_query = "\n".join(query_parts)

        sparql.setQuery(main_query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        bindings = results.get("results", {}).get("bindings", [])

        # Determine if there are more results
        has_more = len(bindings) > limit

        # Process only up to 'limit' results
        results_to_process = bindings[:limit]

        for result in results_to_process:
            subject = result["s"]["value"]
            predicate = result["p"]["value"]

            types = get_entity_types(subject)
            highest_priority_type = get_highest_priority_class(types)
            shape = determine_shape_for_classes(types)
            
            is_proxy, connecting_predicate = _is_proxy_entity(types)
            if is_proxy:
                final_subject, final_predicate = _resolve_proxy_entity(subject, predicate, connecting_predicate)
            else:
                final_subject, final_predicate = subject, predicate

            if final_subject != subject:
                final_types = get_entity_types(final_subject)
                final_highest_priority_type = get_highest_priority_class(final_types)
                final_shape = determine_shape_for_classes(final_types)
            else:
                final_types = types
                final_highest_priority_type = highest_priority_type
                final_shape = shape
            
            label = custom_filter.human_readable_entity(final_subject, (final_highest_priority_type, final_shape))
            type_label = custom_filter.human_readable_class((final_highest_priority_type, final_shape)) if final_highest_priority_type else None

            references.append({
                "subject": final_subject,
                "predicate": final_predicate,
                "predicate_label": custom_filter.human_readable_predicate(final_predicate, (final_highest_priority_type, final_shape)),
                "type_label": type_label,
                "label": label
            })

        return references, has_more

    except Exception as e:
        tb_str = traceback.format_exc()
        current_app.logger.error(f"Error fetching inverse references for {subject_uri}: {e}\n{tb_str}")
        return [], False

@linked_resources_bp.route("/", methods=["GET"])
@login_required
def get_linked_resources_api():
    """API endpoint to fetch paginated linked resources (inverse references)."""
    subject_uri = request.args.get("subject_uri")
    try:
        limit = int(request.args.get("limit", 5))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"status": "error", "message": gettext("Invalid limit or offset parameter")}), 400

    if not subject_uri:
        return jsonify({"status": "error", "message": gettext("Missing subject_uri parameter")}), 400

    if limit <= 0 or offset < 0:
         return jsonify({"status": "error", "message": gettext("Limit must be positive and offset non-negative")}), 400

    references, has_more = get_paginated_inverse_references(subject_uri, limit, offset)

    return jsonify({
        "status": "success",
        "results": references,
        "has_more": has_more
    })