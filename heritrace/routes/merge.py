# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

import validators
from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_babel import gettext
from flask_login import current_user, login_required
from markupsafe import Markup
from rdflib import URIRef
from SPARQLWrapper import JSON

from heritrace.apis.orcid import get_responsible_agent_uri
from heritrace.editor import Editor, EndpointConfig
from heritrace.extensions import (
    get_counter_handler,
    get_custom_filter,
    get_dataset_endpoint,
    get_dataset_is_quadstore,
    get_provenance_endpoint,
    get_sparql,
)
from heritrace.sparql import get_sparql_bindings
from heritrace.utils.display_rules_utils import (
    get_highest_priority_class,
    get_similarity_properties,
)
from heritrace.utils.primary_source_utils import (
    get_default_primary_source,
    save_user_default_primary_source,
)
from heritrace.utils.shacl_utils import determine_shape_for_classes
from heritrace.utils.sparql_utils import get_entity_types

if TYPE_CHECKING:
    from werkzeug.wrappers import Response as WerkzeugResponse

merge_bp = Blueprint("merge", __name__)


def get_entity_details(
    entity_uri: URIRef,
) -> tuple[dict[str, list[dict[str, Any]]] | None, list[str]]:
    """
    Fetches all properties (predicates and objects) for a given entity URI,
    grouped by predicate, along with its types.

    Args:
        entity_uri: The URI of the entity to fetch details for.

    Returns:
        A tuple containing:
        - A dictionary where keys are predicate URIs and values are lists of
          object dictionaries (containing 'value', 'type', 'lang', 'datatype').
          Returns None if an error occurs.
        - A list of entity type URIs. Returns an empty list if an error occurs
          or no types are found.
    """
    sparql = get_sparql()
    custom_filter = get_custom_filter()
    grouped_properties: dict[str, list[dict[str, Any]]] = {}
    entity_types: list[str] = []

    try:
        entity_types = get_entity_types(entity_uri)
        if not entity_types:
            current_app.logger.warning("No types found for entity: %s", entity_uri)

        query = f"""
        SELECT DISTINCT ?p ?o WHERE {{
            <{entity_uri}> ?p ?o .
        }}
        """
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        bindings = get_sparql_bindings(results)
        for binding in bindings:
            predicate = binding["p"]["value"]
            obj_node = binding["o"]
            obj_details = {
                "value": obj_node["value"],
                "type": obj_node["type"],
                "lang": obj_node.get("xml:lang"),
                "datatype": obj_node.get("datatype"),
                "readable_label": None,
            }
            if obj_details["type"] == "uri":
                obj_types = get_entity_types(URIRef(obj_details["value"]))
                obj_type = get_highest_priority_class(obj_types)
                if obj_type:
                    obj_details["readable_label"] = custom_filter.human_readable_entity(
                        obj_details["value"], (obj_type, None)
                    )
                else:
                    obj_details["readable_label"] = obj_details["value"]
            else:
                obj_details["readable_label"] = obj_details["value"]

            if predicate not in grouped_properties:
                grouped_properties[predicate] = []
            grouped_properties[predicate].append(obj_details)

    except Exception:
        current_app.logger.exception(
            "Error fetching details for %s",
            entity_uri,
        )
        return None, []
    else:
        return grouped_properties, entity_types


@merge_bp.route("/execute-merge", methods=["POST"])
@login_required
def execute_merge() -> WerkzeugResponse:
    """
    Handles the actual merging of two entities using the Editor class
    to ensure provenance and data model agnosticism.
    Entity 1 (keep) absorbs Entity 2 (delete).
    """
    entity1_uri_str = request.form.get("entity1_uri")
    entity2_uri_str = request.form.get("entity2_uri")
    primary_source = request.form.get("primary_source")
    save_default_source = request.form.get("save_default_source") == "true"

    # TODO(arcangelo): Implement CSRF validation
    # if using Flask-WTF

    if not entity1_uri_str or not entity2_uri_str:
        flash(gettext("Missing entity URIs for merge."), "danger")
        return redirect(url_for("main.catalogue"))

    entity1_uri = URIRef(entity1_uri_str)
    entity2_uri = URIRef(entity2_uri_str)

    if primary_source and not validators.url(primary_source):  # type: ignore[arg-type]
        flash(gettext("Invalid primary source URL provided."), "danger")
        return redirect(
            url_for(
                ".compare_and_merge", subject=entity1_uri, other_subject=entity2_uri
            )
        )

    if save_default_source and primary_source and validators.url(primary_source):  # type: ignore[arg-type]
        save_user_default_primary_source(current_user.orcid, primary_source)

    try:
        custom_filter = get_custom_filter()

        _, entity1_types = get_entity_details(entity1_uri)
        _, entity2_types = get_entity_details(entity2_uri)

        entity1_type = get_highest_priority_class(entity1_types)
        entity2_type = get_highest_priority_class(entity2_types)
        entity1_shape = determine_shape_for_classes(entity1_types)
        entity2_shape = determine_shape_for_classes(entity2_types)
        entity1_label = (
            custom_filter.human_readable_entity(
                entity1_uri, (entity1_type, entity1_shape)
            )
            if entity1_type
            else entity1_uri
        )
        entity2_label = (
            custom_filter.human_readable_entity(
                entity2_uri, (entity2_type, entity2_shape)
            )
            if entity2_type
            else entity2_uri
        )

        counter_handler = get_counter_handler()
        resp_agent = get_responsible_agent_uri(current_user.orcid)

        dataset_endpoint = get_dataset_endpoint()
        provenance_endpoint = get_provenance_endpoint()
        dataset_is_quadstore = get_dataset_is_quadstore()

        editor = Editor(
            EndpointConfig(
                dataset=dataset_endpoint,
                provenance=provenance_endpoint,
                is_quadstore=dataset_is_quadstore,
            ),
            counter_handler,
            resp_agent,
            save_plugin=current_app.config.get("SAVE_PLUGIN"),
        )

        if primary_source and validators.url(primary_source):  # type: ignore[arg-type]
            editor.set_primary_source(URIRef(primary_source))

        editor.merge(keep_entity_uri=entity1_uri, delete_entity_uri=entity2_uri)

        entity1_url = url_for("entity.about", subject=entity1_uri)
        entity2_url = url_for("entity.about", subject=entity2_uri)
        flash_message_html = gettext(
            "Entities merged successfully. "
            "<a href='%(entity2_url)s' target='_blank'>%(entity2)s</a> "
            "has been deleted and its references now point to "
            "<a href='%(entity1_url)s' target='_blank'>%(entity1)s</a>.",
            entity1=entity1_label,
            entity2=entity2_label,
            entity1_url=entity1_url,
            entity2_url=entity2_url,
        )

        flash(Markup(flash_message_html), "success")  # noqa: S704

        return redirect(url_for("entity.about", subject=entity1_uri))

    except ValueError as ve:
        current_app.logger.warning("Merge attempt failed: %s", ve)
        flash(str(ve), "warning")
        return redirect(
            url_for(
                ".compare_and_merge", subject=entity1_uri, other_subject=entity2_uri
            )
        )

    except Exception:
        current_app.logger.exception(
            "Error executing Editor merge for <%s> and <%s>",
            entity1_uri,
            entity2_uri,
        )
        flash(
            gettext(
                "An error occurred during the merge"
                " operation. Please check the logs."
                " No changes were made."
            ),
            "danger",
        )
        return redirect(
            url_for(
                ".compare_and_merge", subject=entity1_uri, other_subject=entity2_uri
            )
        )


@merge_bp.route("/compare-and-merge")
@login_required
def compare_and_merge() -> str | WerkzeugResponse:
    """
    Route to display details of two entities side-by-side for merge confirmation.
    """
    entity1_uri_str = request.args.get("subject")
    entity2_uri_str = request.args.get("other_subject")
    custom_filter = get_custom_filter()

    if not entity1_uri_str or not entity2_uri_str:
        flash(
            gettext("Two entities must be selected for merging/comparison."), "warning"
        )
        return redirect(url_for("main.catalogue"))

    entity1_uri = URIRef(entity1_uri_str)
    entity2_uri = URIRef(entity2_uri_str)

    entity1_props, entity1_types = get_entity_details(entity1_uri)
    entity2_props, entity2_types = get_entity_details(entity2_uri)

    if entity1_props is None or entity2_props is None:
        flash(
            gettext("Could not retrieve details for one or both entities. Check logs."),
            "danger",
        )
        return redirect(url_for("main.catalogue"))

    entity1_type = get_highest_priority_class(entity1_types)
    entity2_type = get_highest_priority_class(entity2_types)
    entity1_shape = determine_shape_for_classes(entity1_types)
    entity2_shape = determine_shape_for_classes(entity2_types)
    entity1_label = (
        custom_filter.human_readable_entity(entity1_uri, (entity1_type, entity1_shape))
        if entity1_type
        else entity1_uri
    )
    entity2_label = (
        custom_filter.human_readable_entity(entity2_uri, (entity2_type, entity2_shape))
        if entity2_type
        else entity2_uri
    )

    entity1_data = {
        "uri": entity1_uri,
        "label": entity1_label,
        "type_label": custom_filter.human_readable_class((entity1_type, entity1_shape)),
        "type": entity1_type,
        "shape": entity1_shape,
        "properties": entity1_props,
    }
    entity2_data = {
        "uri": entity2_uri,
        "label": entity2_label,
        "type_label": custom_filter.human_readable_class((entity2_type, entity2_shape)),
        "type": entity2_type,
        "shape": entity2_shape,
        "properties": entity2_props,
    }

    default_primary_source = get_default_primary_source(current_user.orcid)

    return render_template(
        "entity/merge_confirm.jinja",
        entity1=entity1_data,
        entity2=entity2_data,
        default_primary_source=default_primary_source,
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


def _fetch_subject_values(
    subject_uri: str,
    similarity_config: list,
) -> defaultdict[str, list[str]] | None:
    sparql = get_sparql()

    all_props_in_config: set[str] = set()
    for item in similarity_config:
        if isinstance(item, str):
            all_props_in_config.add(item)
        elif isinstance(item, dict) and "and" in item:
            all_props_in_config.update(item["and"])

    if not all_props_in_config:
        current_app.logger.warning(
            "Empty properties list derived from similarity config for type %s",
            subject_uri,
        )
        return None

    prop_uris_formatted_for_filter = [f"<{p}>" for p in all_props_in_config]
    property_filter_for_subject = (
        f"FILTER(?p IN ({', '.join(prop_uris_formatted_for_filter)}))"
    )

    fetch_comparison_values_query = f"""
    SELECT DISTINCT ?p ?o WHERE {{
        <{subject_uri}> ?p ?o .
        {property_filter_for_subject}
    }}
    """

    sparql.setQuery(fetch_comparison_values_query)
    sparql.setReturnFormat(JSON)
    subject_values_results = sparql.query().convert()
    subject_bindings = get_sparql_bindings(subject_values_results)

    if not subject_bindings:
        return None

    subject_values_by_prop: defaultdict[str, list[str]] = defaultdict(list)
    for binding in subject_bindings:
        formatted_value = _format_rdf_term(binding["o"])
        if formatted_value:
            subject_values_by_prop[binding["p"]["value"]].append(formatted_value)

    return subject_values_by_prop


def _build_union_blocks(
    similarity_config: list,
    subject_values_by_prop: defaultdict[str, list[str]],
    subject_uri: str,
) -> list[str]:
    union_blocks: list[str] = []
    var_counter = 0

    for condition in similarity_config:
        if isinstance(condition, str):
            prop_values = subject_values_by_prop.get(condition)
            if prop_values:
                var_counter += 1
                values_filter = ", ".join(prop_values)
                union_blocks.append(
                    f"  {{ ?similar <{condition}>"
                    f" ?o_{var_counter} ."
                    f" FILTER(?o_{var_counter}"
                    f" IN ({values_filter})) }}"
                )
        elif isinstance(condition, dict) and "and" in condition:
            block = _build_and_block(
                condition["and"], subject_values_by_prop, subject_uri, var_counter
            )
            if block is not None:
                text, var_counter = block
                union_blocks.append(text)
            else:
                var_counter += len(condition["and"])

    return union_blocks


def _build_and_block(
    and_props: list[str],
    subject_values_by_prop: defaultdict[str, list[str]],
    subject_uri: str,
    var_counter: int,
) -> tuple[str, int] | None:
    if not all(p in subject_values_by_prop for p in and_props):
        current_app.logger.debug(
            "Skipping AND group %s because"
            " subject %s lacks values for"
            " all its properties.",
            and_props,
            subject_uri,
        )
        return None

    and_patterns = []
    for prop_uri in and_props:
        prop_values = subject_values_by_prop[prop_uri]
        var_counter += 1
        values_filter = ", ".join(prop_values)
        and_patterns.append(
            f"    ?similar <{prop_uri}>"
            f" ?o_{var_counter} ."
            f" FILTER(?o_{var_counter}"
            f" IN ({values_filter})) ."
        )

    patterns_str = "\n".join(and_patterns)
    return f"  {{\n{patterns_str}\n  }}", var_counter


def _execute_similarity_query(
    union_blocks: list[str],
    entity_type: str,
    subject_uri: str,
    limit: int,
    offset: int,
) -> tuple[list[str], bool]:
    sparql = get_sparql()
    similarity_query_body = " UNION ".join(union_blocks)

    query_limit = limit + 1
    final_query = f"""
    SELECT DISTINCT ?similar WHERE {{
      ?similar a <{entity_type}> .
      FILTER(?similar != <{subject_uri}>)
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


@merge_bp.route("/find_similar", methods=["GET"])
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
            {"status": "error", "message": gettext("Invalid limit or offset parameter")}
        ), 400

    if not subject_uri or not entity_type:
        return jsonify(
            {
                "status": "error",
                "message": gettext(
                    "Missing required parameters (subject_uri, entity_type)"
                ),
            }
        ), 400

    if limit <= 0 or offset < 0:
        return jsonify(
            {
                "status": "error",
                "message": gettext("Limit must be positive and offset non-negative"),
            }
        ), 400

    try:
        entity_key = (entity_type, shape_uri)
        similarity_config = get_similarity_properties(entity_key)

        if not similarity_config or not isinstance(similarity_config, list):
            return jsonify({"status": "success", "results": [], "has_more": False})

        subject_values_by_prop = _fetch_subject_values(subject_uri, similarity_config)
        if subject_values_by_prop is None:
            return jsonify({"status": "success", "results": [], "has_more": False})

        union_blocks = _build_union_blocks(
            similarity_config, subject_values_by_prop, subject_uri
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
                "message": gettext("An error occurred while finding similar resources"),
            }
        ), 500
