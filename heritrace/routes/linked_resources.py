import traceback

from flask import Blueprint, current_app, jsonify, request
from flask_babel import gettext
from flask_login import login_required
from heritrace.extensions import get_custom_filter, get_sparql
from heritrace.utils.display_rules_utils import get_highest_priority_class
from heritrace.utils.sparql_utils import get_entity_types
from heritrace.utils.virtuoso_utils import (VIRTUOSO_EXCLUDED_GRAPHS,
                                            is_virtuoso)
from SPARQLWrapper import JSON

linked_resources_bp = Blueprint("linked_resources", __name__, url_prefix="/api/linked-resources")

def get_paginated_inverse_references(subject_uri: str, limit: int, offset: int) -> tuple[list[dict], int, bool]:
    """
    Get paginated entities that reference this entity.

    Args:
        subject_uri: URI of the entity to find references to.
        limit: Maximum number of references to return.
        offset: Number of references to skip.

    Returns:
        A tuple containing:
            - List of dictionaries containing reference information.
            - Total count of references.
            - Boolean indicating if there are more references.
    """
    sparql = get_sparql()
    custom_filter = get_custom_filter()
    total_count = 0
    references = []

    try:
        # Count Query
        count_query_parts = [
            "SELECT (COUNT(DISTINCT ?s) as ?count) WHERE {",
        ]
        if is_virtuoso:
            count_query_parts.append("    GRAPH ?g { ?s ?p ?o . }")
            count_query_parts.append(f"    FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))")
        else:
            count_query_parts.append("    ?s ?p ?o .")

        count_query_parts.extend([
            f"    FILTER(?o = <{subject_uri}>)",
            "    FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)",
            "}"
        ])
        count_query = "\n".join(count_query_parts)

        sparql.setQuery(count_query)
        sparql.setReturnFormat(JSON)
        count_results = sparql.query().convert()
        if count_results.get("results", {}).get("bindings", []):
            count_binding = count_results["results"]["bindings"][0]
            if "count" in count_binding:
                total_count = int(count_binding["count"]["value"])

        # Main Query with pagination
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
            f"}} ORDER BY ?s OFFSET {offset} LIMIT {limit}"
        ])
        main_query = "\n".join(query_parts)

        sparql.setQuery(main_query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        bindings = results.get("results", {}).get("bindings", [])
        for result in bindings:
            subject = result["s"]["value"]
            predicate = result["p"]["value"]

            # Get the type of the referring entity
            types = get_entity_types(subject)
            highest_priority_type = get_highest_priority_class(types) if types else None
            display_types = [highest_priority_type] if highest_priority_type else []
            type_labels = [custom_filter.human_readable_predicate(t, display_types) for t in display_types] if display_types else []
            label = custom_filter.human_readable_entity(subject, display_types)

            references.append({
                "subject": subject,
                "predicate": predicate,
                "predicate_label": custom_filter.human_readable_predicate(predicate, display_types),
                "types": display_types,
                "type_labels": type_labels,
                "label": label
            })

        has_more = offset + limit < total_count
        return references, total_count, has_more

    except Exception as e:
        tb_str = traceback.format_exc()
        current_app.logger.error(f"Error fetching inverse references for {subject_uri}: {e}\n{tb_str}")
        return [], 0, False

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

    references, total_count, has_more = get_paginated_inverse_references(subject_uri, limit, offset)

    return jsonify({
        "status": "success",
        "results": references,
        "total_count": total_count,
        "has_more": has_more
    })