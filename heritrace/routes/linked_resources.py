# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask import Blueprint, Response, current_app, jsonify, request
from flask_login import login_required
from SPARQLWrapper import JSON
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

from heritrace.extensions import (
    get_custom_filter,
    get_form_fields,
    get_sparql,
    get_sparql_bindings,
)
from heritrace.utils.display_rules_utils import get_highest_priority_class
from heritrace.utils.shacl_presentation import is_inverse_path
from heritrace.utils.shacl_utils import determine_shape_for_classes
from heritrace.utils.sparql_utils import get_entity_types
from heritrace.utils.virtuoso_utils import VIRTUOSO_EXCLUDED_GRAPHS, is_virtuoso

linked_resources_bp = Blueprint(
    "linked_resources", __name__, url_prefix="/api/linked-resources"
)


def _composite_parent_paths() -> dict[str, str]:
    return {
        field["nodeShape"]: field["uri"]
        for fields in get_form_fields().values()
        for definitions in fields.values()
        for field in definitions
        if field["composite"] and field["nodeShape"]
    }


def _resolve_parent_entity(
    subject_uri: str, predicate: str, connecting_predicate: str
) -> tuple[str, str]:
    sparql = get_sparql()
    parent_query_parts = [
        "SELECT DISTINCT ?source WHERE {",
    ]

    if is_virtuoso():
        parent_query_parts.extend(
            [
                "    GRAPH ?g {",
                f"        ?source <{connecting_predicate}> <{subject_uri}> .",
                "    }",
                f"    FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))",
            ]
        )
    else:
        parent_query_parts.extend(
            [f"    ?source <{connecting_predicate}> <{subject_uri}> ."]
        )

    parent_query_parts.append("} LIMIT 1")
    parent_query = "\n".join(parent_query_parts)

    sparql.setQuery(parent_query)
    sparql.setReturnFormat(JSON)
    parent_results = sparql.query().convert()

    parent_bindings = get_sparql_bindings(parent_results)
    if parent_bindings:
        source_uri = parent_bindings[0]["source"]["value"]

        return source_uri, connecting_predicate

    return subject_uri, predicate


def get_paginated_inverse_references(
    subject_uri: str, limit: int, offset: int
) -> tuple[list[dict], bool]:
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
    composite_parent_paths = _composite_parent_paths()

    query_parts = [
        "SELECT DISTINCT ?s ?p WHERE {",
    ]
    if is_virtuoso():
        query_parts.append("    GRAPH ?g { ?s ?p ?o . }")
        query_parts.append(
            f"    FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))"
        )
        query_parts.append(f"    FILTER(?o = <{subject_uri}>)")
    else:
        query_parts.append(f"    ?s ?p <{subject_uri}> .")

    query_parts.extend(
        [
            "    FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)",
            f"}} ORDER BY ?s OFFSET {offset} LIMIT {query_limit}",
        ]
    )
    main_query = "\n".join(query_parts)

    sparql.setQuery(main_query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    bindings = get_sparql_bindings(results)

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
        parent_path = composite_parent_paths.get(str(shape))

        if parent_path is not None and is_inverse_path(parent_path):
            continue

        if parent_path is not None:
            final_subject, final_predicate = _resolve_parent_entity(
                subject, predicate, parent_path
            )
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

        label = custom_filter.value_label(
            final_subject, (final_highest_priority_type, final_shape)
        )
        type_label = (
            custom_filter.human_readable_class(
                (final_highest_priority_type, final_shape)
            )
            if final_highest_priority_type
            else None
        )

        references.append(
            {
                "subject": final_subject,
                "predicate": final_predicate,
                "predicate_label": custom_filter.human_readable_predicate(
                    final_predicate, (final_highest_priority_type, final_shape)
                ),
                "type_label": type_label,
                "label": label,
            }
        )

    return references, has_more


@linked_resources_bp.route("/", methods=["GET"])
@login_required
def get_linked_resources_api() -> Response | tuple[Response, int]:
    """API endpoint to fetch paginated linked resources (inverse references)."""
    subject_uri = request.args.get("subject_uri")
    try:
        limit = int(request.args.get("limit", 5))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify(
            {"status": "error", "message": "Invalid limit or offset parameter"}
        ), 400

    if not subject_uri:
        return jsonify(
            {"status": "error", "message": "Missing subject_uri parameter"}
        ), 400

    if limit <= 0 or offset < 0:
        return jsonify(
            {
                "status": "error",
                "message": "Limit must be positive and offset non-negative",
            }
        ), 400

    try:
        references, has_more = get_paginated_inverse_references(
            subject_uri, limit, offset
        )
    except (SPARQLWrapperException, OSError):
        current_app.logger.exception(
            "Error fetching inverse references for %s", subject_uri
        )
        return jsonify(
            {"status": "error", "message": "Error loading linked resources."}
        ), 502

    return jsonify({"status": "success", "results": references, "has_more": has_more})
