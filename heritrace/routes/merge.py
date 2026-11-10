# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

from collections import defaultdict

import validators
from flask import Blueprint, Response, current_app, jsonify, request
from flask_login import current_user, login_required
from rdflib import RDF, Literal, URIRef
from SPARQLWrapper import JSON

from heritrace.apis.orcid import get_responsible_agent_uri
from heritrace.extensions import (
    get_custom_filter,
    get_presentation,
    get_primary_source,
    get_sparql,
    new_editor,
    record_dataset_change,
)
from heritrace.routes.entity import build_entity_view
from heritrace.sparql import get_sparql_bindings
from heritrace.utils.display_rules_utils import get_highest_priority_class
from heritrace.utils.primary_source_utils import (
    save_user_default_primary_source,
)
from heritrace.utils.shacl_utils import determine_shape_for_classes
from heritrace.utils.sparql_utils import get_entity_types, import_entity_graph
from heritrace.utils.virtuoso_utils import is_virtuoso

merge_bp = Blueprint("merge", __name__)

DRAFT_SIMILAR_LIMIT = 5


def _entity_summary(entity_uri: URIRef, entity_types: list[str]) -> dict:
    custom_filter = get_custom_filter()
    entity_type = get_highest_priority_class(entity_types)
    entity_shape = determine_shape_for_classes(entity_types)
    label = (
        custom_filter.human_readable_entity(entity_uri, (entity_type, entity_shape))
        if entity_type
        else str(entity_uri)
    )
    return {
        "uri": str(entity_uri),
        "label": label,
        "type": entity_type,
        "type_label": custom_filter.human_readable_class((entity_type, entity_shape)),
        "shape": entity_shape,
    }


def _comparison_entity(entity_uri: str) -> dict:
    view = build_entity_view(entity_uri)
    predicates_with_options = {
        predicate for predicate, options in view["optional_values"].items() if options
    }
    return {
        "uri": view["uri"],
        "label": view["label"],
        "type_label": view["type_label"],
        "properties": [
            {
                "predicate": group["property"],
                "label": group["display_name"],
                "values": [
                    {
                        "readable_label": triple["label"]
                        if group["property"] in predicates_with_options
                        else triple["value"]
                    }
                    for triple in group["triples"]
                ],
            }
            for group in view["groups"]
            if group["triples"] and group["property"] != str(RDF.type)
        ],
    }


@merge_bp.route("", methods=["POST"])
@login_required
def execute_merge() -> Response | tuple[Response, int]:
    """Merge two entities: entity 1 (keep) absorbs entity 2 (delete)."""
    data = request.get_json()
    entity1_uri_str = data.get("entity1_uri")
    entity2_uri_str = data.get("entity2_uri")
    primary_source = data.get("primary_source") or None
    save_default_source = bool(data.get("save_default_source"))

    if not entity1_uri_str or not entity2_uri_str:
        return jsonify(
            {"status": "error", "message": "Missing entity URIs for merge."}
        ), 400

    entity1_uri = URIRef(entity1_uri_str)
    entity2_uri = URIRef(entity2_uri_str)

    if primary_source and not validators.url(primary_source):  # type: ignore[arg-type]
        return jsonify(
            {"status": "error", "message": "Invalid primary source URL provided."}
        ), 400

    if save_default_source and primary_source:
        save_user_default_primary_source(current_user.orcid, primary_source)

    try:
        entity1_types = get_entity_types(entity1_uri)
        entity2_types = get_entity_types(entity2_uri)
        kept = _entity_summary(entity1_uri, entity1_types)
        deleted = _entity_summary(entity2_uri, entity2_types)

        editor = new_editor(
            get_responsible_agent_uri(current_user.orcid), get_primary_source()
        )

        editor = import_entity_graph(editor, entity1_uri)
        editor = import_entity_graph(editor, entity2_uri)
        editor.merge(
            keep_entity_uri=entity1_uri,
            delete_entity_uri=entity2_uri,
            primary_source=URIRef(primary_source) if primary_source else None,
        )
    except ValueError as ve:
        current_app.logger.warning("Merge attempt failed: %s", ve)
        return jsonify({"status": "error", "message": str(ve)}), 400
    except Exception:
        current_app.logger.exception(
            "Error executing Editor merge for <%s> and <%s>",
            entity1_uri,
            entity2_uri,
        )
        return jsonify(
            {
                "status": "error",
                "message": (
                    "An error occurred during the merge operation."
                    " Please check the logs. No changes were made."
                ),
            }
        ), 500

    record_dataset_change()
    return jsonify({"status": "success", "kept": kept, "deleted": deleted})


@merge_bp.route("/compare")
@login_required
def compare_and_merge() -> Response | tuple[Response, int]:
    """Details of two entities side by side for merge confirmation."""
    entity1_uri_str = request.args.get("subject")
    entity2_uri_str = request.args.get("other_subject")

    if not entity1_uri_str or not entity2_uri_str:
        return jsonify(
            {
                "status": "error",
                "message": "Two entities must be selected for merging/comparison.",
            }
        ), 400

    return jsonify(
        {
            "entity1": _comparison_entity(entity1_uri_str),
            "entity2": _comparison_entity(entity2_uri_str),
        }
    )


def _format_rdf_term(node: dict[str, str]) -> str | None:
    value = node["value"]
    value_type = node["type"]
    if value_type == "uri":
        return f"<{value}>"
    if value_type in {"literal", "typed-literal"}:
        datatype = node.get("datatype")
        lang = node.get("xml:lang")
        escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
        if datatype:
            return f'"{escaped_value}"^^<{datatype}>'
        if lang:
            return f'"{escaped_value}"@{lang}'
        return f'"{escaped_value}"'
    return None


def _duplicate_keys(entity_type: str, shape_uri: str | None) -> list[list[str]]:
    shape = shape_uri or determine_shape_for_classes([entity_type])
    return get_presentation().shape_duplicate_keys(shape)


def _key_properties(duplicate_keys: list[list[str]]) -> set[str]:
    return {prop for key in duplicate_keys for prop in key}


def _fetch_subject_values(
    subject_uri: str,
    duplicate_keys: list[list[str]],
) -> defaultdict[str, list[str]]:
    sparql = get_sparql()
    property_list = ", ".join(f"<{p}>" for p in _key_properties(duplicate_keys))
    sparql.setQuery(f"""
    SELECT DISTINCT ?p ?o WHERE {{
        <{subject_uri}> ?p ?o .
        FILTER(?p IN ({property_list}))
    }}
    """)
    sparql.setReturnFormat(JSON)
    subject_bindings = get_sparql_bindings(sparql.query().convert())

    subject_values_by_prop: defaultdict[str, list[str]] = defaultdict(list)
    for binding in subject_bindings:
        formatted_value = _format_rdf_term(binding["o"])
        if formatted_value:
            subject_values_by_prop[binding["p"]["value"]].append(formatted_value)

    return subject_values_by_prop


def _build_similarity_pattern(prop_uri: str, values: list[str], index: int) -> str:
    variable = f"?o_{index}"
    if not is_virtuoso():
        return (
            f"VALUES {variable} {{ {' '.join(values)} }} "
            f"?similar <{prop_uri}> {variable} ."
        )
    return (
        f"?similar <{prop_uri}> {variable} . "
        f"FILTER({variable} IN ({', '.join(values)}))"
    )


def _build_union_blocks(
    duplicate_keys: list[list[str]],
    values_by_prop: defaultdict[str, list[str]],
) -> list[str]:
    union_blocks: list[str] = []
    var_counter = 0
    for key in duplicate_keys:
        if not all(prop in values_by_prop for prop in key):
            continue
        patterns = []
        for prop_uri in key:
            var_counter += 1
            pattern = _build_similarity_pattern(
                prop_uri, values_by_prop[prop_uri], var_counter
            )
            patterns.append(f"    {pattern}")
        union_blocks.append("  {\n" + "\n".join(patterns) + "\n  }")
    return union_blocks


def _execute_similarity_query(
    union_blocks: list[str],
    entity_type: str,
    subject_uri: str | None,
    limit: int,
    offset: int,
) -> tuple[list[str], bool]:
    sparql = get_sparql()
    similarity_query_body = " UNION ".join(union_blocks)
    subject_filter = f"FILTER(?similar != <{subject_uri}>)" if subject_uri else ""

    query_limit = limit + 1
    final_query = f"""
    SELECT DISTINCT ?similar WHERE {{
      ?similar a <{entity_type}> .
      {subject_filter}
      {{
        {similarity_query_body}
      }}
    }} ORDER BY ?similar OFFSET {offset} LIMIT {query_limit}
    """

    sparql.setQuery(final_query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    bindings = get_sparql_bindings(results)
    candidate_uris = [item["similar"]["value"] for item in bindings]

    has_more = len(candidate_uris) > limit
    return candidate_uris[:limit], has_more


def _transform_results(
    uris: list[str],
    entity_type: str,
    shape_uri: str | None,
) -> list[dict[str, str]]:
    custom_filter = get_custom_filter()
    transformed: list[dict[str, str]] = []
    for uri in uris:
        readable_label = (
            custom_filter.human_readable_entity(uri, (entity_type, shape_uri))
            if entity_type
            else uri
        )
        transformed.append({"uri": uri, "label": readable_label or uri})
    return transformed


@merge_bp.route("/similar", methods=["GET"])
@login_required
def find_similar_resources() -> Response | tuple[Response, int]:  # noqa: PLR0911
    subject_uri = request.args.get("subject_uri")
    entity_type = request.args.get("entity_type")
    shape_uri = request.args.get("shape_uri")
    try:
        limit = int(request.args.get("limit", 5))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify(
            {"status": "error", "message": "Invalid limit or offset parameter"}
        ), 400

    if not subject_uri or not entity_type:
        return jsonify(
            {
                "status": "error",
                "message": "Missing required parameters (subject_uri, entity_type)",
            }
        ), 400

    if limit <= 0 or offset < 0:
        return jsonify(
            {
                "status": "error",
                "message": "Limit must be positive and offset non-negative",
            }
        ), 400

    try:
        duplicate_keys = _duplicate_keys(entity_type, shape_uri)
        if not duplicate_keys:
            return jsonify({"status": "success", "results": [], "has_more": False})

        union_blocks = _build_union_blocks(
            duplicate_keys, _fetch_subject_values(subject_uri, duplicate_keys)
        )
        if not union_blocks:
            return jsonify({"status": "success", "results": [], "has_more": False})

        result_uris, has_more = _execute_similarity_query(
            union_blocks, entity_type, subject_uri, limit, offset
        )
        transformed_results = _transform_results(result_uris, entity_type, shape_uri)

        return jsonify(
            {
                "status": "success",
                "results": transformed_results,
                "has_more": has_more,
            }
        )

    except Exception:
        current_app.logger.exception(
            "Error finding similar resources for %s", subject_uri
        )
        return jsonify(
            {
                "status": "error",
                "message": "An error occurred while finding similar resources",
            }
        ), 500


def _draft_term(value: dict[str, str]) -> str:
    if "uri" in value:
        return URIRef(value["uri"]).n3()
    datatype = URIRef(value["datatype"]) if "datatype" in value else None
    return Literal(value["value"], datatype=datatype).n3()


def _existing_nested_entities(fields: list[dict[str, str]]) -> list[str]:
    patterns = " ".join(
        f"?nested {URIRef(field['predicate']).n3()} {_draft_term(field)} ."
        for field in fields
    )
    sparql = get_sparql()
    sparql.setQuery(f"SELECT DISTINCT ?nested WHERE {{ {patterns} }}")
    sparql.setReturnFormat(JSON)
    return [
        URIRef(binding["nested"]["value"]).n3()
        for binding in get_sparql_bindings(sparql.query().convert())
    ]


def _draft_values(
    duplicate_keys: list[list[str]], values: dict[str, list[dict]]
) -> defaultdict[str, list[str]]:
    draft_values: defaultdict[str, list[str]] = defaultdict(list)
    for predicate in _key_properties(duplicate_keys) & values.keys():
        for value in values[predicate]:
            if "fields" in value:
                draft_values[predicate].extend(
                    _existing_nested_entities(value["fields"])
                )
            else:
                draft_values[predicate].append(_draft_term(value))
    return draft_values


@merge_bp.route("/similar/draft", methods=["POST"])
@login_required
def find_resources_similar_to_draft() -> Response:
    data = request.get_json()
    duplicate_keys = _duplicate_keys(data["entity_type"], data["shape_uri"])
    if not duplicate_keys:
        return jsonify({"status": "success", "results": [], "has_more": False})
    union_blocks = _build_union_blocks(
        duplicate_keys, _draft_values(duplicate_keys, data["values"])
    )
    if not union_blocks:
        return jsonify({"status": "success", "results": [], "has_more": False})
    result_uris, has_more = _execute_similarity_query(
        union_blocks, data["entity_type"], None, DRAFT_SIMILAR_LIMIT, 0
    )
    return jsonify(
        {
            "status": "success",
            "results": _transform_results(
                result_uris, data["entity_type"], data["shape_uri"]
            ),
            "has_more": has_more,
        }
    )
