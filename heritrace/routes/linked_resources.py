import traceback

from flask import Blueprint, current_app, jsonify, request
from flask_babel import gettext
from flask_login import login_required
from heritrace.extensions import get_custom_filter, get_sparql
from heritrace.utils.display_rules_utils import get_highest_priority_class
from heritrace.utils.shacl_utils import determine_shape_for_classes
from heritrace.utils.sparql_utils import get_entity_types
from heritrace.utils.virtuoso_utils import (VIRTUOSO_EXCLUDED_GRAPHS,
                                            is_virtuoso)
from SPARQLWrapper import JSON

linked_resources_bp = Blueprint("linked_resources", __name__, url_prefix="/api/linked-resources")

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
    # Fetch limit + 1 to check if there are more results
    query_limit = limit + 1

    try:
        # Main Query with pagination (limit + 1)
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
            label = custom_filter.human_readable_entity(subject, (highest_priority_type, shape))
            type_label = custom_filter.human_readable_class((highest_priority_type, shape)) if highest_priority_type else None

            references.append({
                "subject": subject,
                "predicate": predicate,
                "predicate_label": custom_filter.human_readable_predicate(predicate, (highest_priority_type, shape)),
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