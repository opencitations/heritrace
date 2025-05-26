import traceback
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import validators
from flask import (Blueprint, current_app, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_babel import gettext
from flask_login import current_user, login_required
from heritrace.editor import Editor
from heritrace.extensions import (get_counter_handler, get_custom_filter,
                                  get_dataset_endpoint,
                                  get_dataset_is_quadstore,
                                  get_provenance_endpoint, get_sparql)
from heritrace.utils.display_rules_utils import (get_highest_priority_class,
                                                 get_similarity_properties)
from heritrace.utils.primary_source_utils import (
    get_default_primary_source, save_user_default_primary_source)
from heritrace.utils.shacl_utils import determine_shape_for_classes
from heritrace.utils.sparql_utils import get_entity_types
from markupsafe import Markup
from rdflib import URIRef
from SPARQLWrapper import JSON

merge_bp = Blueprint("merge", __name__)


def get_entity_details(entity_uri: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
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
    grouped_properties: Dict[str, List[Dict[str, Any]]] = {}
    entity_types: List[str] = []

    try:
        entity_types = get_entity_types(entity_uri)
        if not entity_types:
            current_app.logger.warning(f"No types found for entity: {entity_uri}")

        query = f"""
        SELECT DISTINCT ?p ?o WHERE {{
            <{entity_uri}> ?p ?o .
        }}
        """
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        bindings = results.get("results", {}).get("bindings", [])
        for binding in bindings:
            predicate = binding["p"]["value"]
            obj_node = binding["o"]
            obj_details = {
                "value": obj_node["value"],
                "type": obj_node["type"],
                "lang": obj_node.get("xml:lang"),
                "datatype": obj_node.get("datatype"),
                "readable_label": None
            }
            if obj_details["type"] == 'uri':
                obj_types = get_entity_types(obj_details["value"])
                obj_type = get_highest_priority_class(obj_types)
                obj_details["readable_label"] = custom_filter.human_readable_entity(obj_details["value"], (obj_type, None))
            else:
                 obj_details["readable_label"] = obj_details["value"]


            if predicate not in grouped_properties:
                grouped_properties[predicate] = []
            grouped_properties[predicate].append(obj_details)

        return grouped_properties, entity_types

    except Exception as e:
        tb_str = traceback.format_exc()
        current_app.logger.error(f"Error fetching details for {entity_uri}: {e}\n{tb_str}")
        return None, []


@merge_bp.route("/execute-merge", methods=["POST"])
@login_required
def execute_merge():
    """
    Handles the actual merging of two entities using the Editor class
    to ensure provenance and data model agnosticism.
    Entity 1 (keep) absorbs Entity 2 (delete).
    """
    entity1_uri = request.form.get("entity1_uri")
    entity2_uri = request.form.get("entity2_uri")
    primary_source = request.form.get("primary_source")
    save_default_source = request.form.get("save_default_source") == "true"

    # TODO: Implement CSRF validation if using Flask-WTF

    if not entity1_uri or not entity2_uri:
        flash(gettext("Missing entity URIs for merge."), "danger")
        return redirect(url_for("main.catalogue"))
        
    if primary_source and not validators.url(primary_source):
        flash(gettext("Invalid primary source URL provided."), "danger")
        return redirect(url_for('.compare_and_merge', subject=entity1_uri, other_subject=entity2_uri))
        
    if save_default_source and primary_source and validators.url(primary_source):
        save_user_default_primary_source(current_user.orcid, primary_source)

    try:
        custom_filter = get_custom_filter()

        _, entity1_types = get_entity_details(entity1_uri)
        _, entity2_types = get_entity_details(entity2_uri)

        entity1_type = get_highest_priority_class(entity1_types)
        entity2_type = get_highest_priority_class(entity2_types)
        entity1_shape = determine_shape_for_classes(entity1_types)
        entity2_shape = determine_shape_for_classes(entity2_types)
        entity1_label = custom_filter.human_readable_entity(entity1_uri, (entity1_type, entity1_shape)) or entity1_uri
        entity2_label = custom_filter.human_readable_entity(entity2_uri, (entity2_type, entity2_shape)) or entity2_uri

        counter_handler = get_counter_handler()
        resp_agent_uri = URIRef(f"https://orcid.org/{current_user.orcid}") if current_user.is_authenticated and hasattr(current_user, 'orcid') else None
        
        dataset_endpoint = get_dataset_endpoint()
        provenance_endpoint = get_provenance_endpoint()
        dataset_is_quadstore = get_dataset_is_quadstore()

        editor = Editor(
            dataset_endpoint=dataset_endpoint,
            provenance_endpoint=provenance_endpoint,
            counter_handler=counter_handler,
            resp_agent=resp_agent_uri,
            dataset_is_quadstore=dataset_is_quadstore
        )
        
        if primary_source and validators.url(primary_source):
            editor.set_primary_source(primary_source)

        editor.merge(keep_entity_uri=entity1_uri, delete_entity_uri=entity2_uri)

        entity1_url = url_for('entity.about', subject=entity1_uri)
        entity2_url = url_for('entity.about', subject=entity2_uri)
        flash_message_html = gettext(
            "Entities merged successfully. "
            "<a href='%(entity2_url)s' target='_blank'>%(entity2)s</a> "
            "has been deleted and its references now point to "
            "<a href='%(entity1_url)s' target='_blank'>%(entity1)s</a>.",
            entity1=entity1_label, 
            entity2=entity2_label, 
            entity1_url=entity1_url, 
            entity2_url=entity2_url
        )

        flash(Markup(flash_message_html), "success")

        return redirect(url_for("entity.about", subject=entity1_uri))

    except ValueError as ve:
        current_app.logger.warning(f"Merge attempt failed: {ve}")
        flash(str(ve), "warning")
        return redirect(url_for('.compare_and_merge', subject=entity1_uri, other_subject=entity2_uri))

    except Exception as e:
        tb_str = traceback.format_exc()
        current_app.logger.error(f"Error executing Editor merge for <{entity1_uri}> and <{entity2_uri}>: {e}\n{tb_str}")
        flash(gettext("An error occurred during the merge operation. Please check the logs. No changes were made."), "danger")
        return redirect(url_for('.compare_and_merge', subject=entity1_uri, other_subject=entity2_uri))


@merge_bp.route("/compare-and-merge")
@login_required
def compare_and_merge():
    """
    Route to display details of two entities side-by-side for merge confirmation.
    """
    entity1_uri = request.args.get("subject")
    entity2_uri = request.args.get("other_subject")
    custom_filter = get_custom_filter()


    if not entity1_uri or not entity2_uri:
        flash(gettext("Two entities must be selected for merging/comparison."), "warning")
        return redirect(url_for("main.catalogue"))

    entity1_props, entity1_types = get_entity_details(entity1_uri)
    entity2_props, entity2_types = get_entity_details(entity2_uri)

    if entity1_props is None or entity2_props is None:
        flash(gettext("Could not retrieve details for one or both entities. Check logs."), "danger")
        return redirect(url_for("main.catalogue"))

    entity1_type = get_highest_priority_class(entity1_types)
    entity2_type = get_highest_priority_class(entity2_types)
    entity1_shape = determine_shape_for_classes(entity1_types)
    entity2_shape = determine_shape_for_classes(entity2_types)
    entity1_label = custom_filter.human_readable_entity(entity1_uri, (entity1_type, entity1_shape)) or entity1_uri
    entity2_label = custom_filter.human_readable_entity(entity2_uri, (entity2_type, entity2_shape)) or entity2_uri


    entity1_data = {
        "uri": entity1_uri,
        "label": entity1_label,
        "type_label": custom_filter.human_readable_class((entity1_type, entity1_shape)),
        "type": entity1_type,
        "shape": entity1_shape,
        "properties": entity1_props
    }
    entity2_data = {
        "uri": entity2_uri,
        "label": entity2_label,
        "type_label": custom_filter.human_readable_class((entity2_type, entity2_shape)),
        "type": entity2_type,
        "shape": entity2_shape,
        "properties": entity2_props
    }

    default_primary_source = get_default_primary_source(current_user.orcid)

    return render_template(
        "entity/merge_confirm.jinja",
        entity1=entity1_data,
        entity2=entity2_data,
        default_primary_source=default_primary_source
    )


@merge_bp.route("/find_similar", methods=["GET"])
@login_required
def find_similar_resources():
    """Find resources potentially similar to a given subject based on shared properties,
    respecting AND/OR logic defined in display rules."""
    subject_uri = request.args.get("subject_uri")
    entity_type = request.args.get("entity_type") # Primary entity type
    shape_uri = request.args.get("shape_uri")
    try:
        limit = int(request.args.get("limit", 5))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"status": "error", "message": gettext("Invalid limit or offset parameter")}), 400

    if not subject_uri or not entity_type:
        return jsonify({"status": "error", "message": gettext("Missing required parameters (subject_uri, entity_type)")}), 400

    if limit <= 0 or offset < 0:
        return jsonify({"status": "error", "message": gettext("Limit must be positive and offset non-negative")}), 400

    try:
        sparql = get_sparql()
        custom_filter = get_custom_filter()

        entity_key = (entity_type, shape_uri)
        similarity_config = get_similarity_properties(entity_key)

        if not similarity_config or not isinstance(similarity_config, list):
            current_app.logger.warning(f"No valid similarity properties found or configured for type {entity_type}")
            return jsonify({"status": "success", "results": [], "has_more": False})

        def format_rdf_term(node):
            value = node["value"]
            value_type = node["type"]
            if value_type == 'uri':
                return f"<{value}>"
            elif value_type in {'literal', 'typed-literal'}:
                datatype = node.get("datatype")
                lang = node.get("xml:lang")
                escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
                if datatype:
                    return f'"{escaped_value}"^^<{datatype}>'
                elif lang:
                    return f'"{escaped_value}"@{lang}'
                else:
                    return f'"{escaped_value}"'
            return None

        all_props_in_config = set()
        for item in similarity_config:
            if isinstance(item, str):
                all_props_in_config.add(item)
            elif isinstance(item, dict) and "and" in item:
                all_props_in_config.update(item["and"])

        if not all_props_in_config:
            current_app.logger.warning(f"Empty properties list derived from similarity config for type {entity_type}")
            return jsonify({"status": "success", "results": [], "has_more": False})

        prop_uris_formatted_for_filter = [f"<{p}>" for p in all_props_in_config]
        property_filter_for_subject = f"FILTER(?p IN ({', '.join(prop_uris_formatted_for_filter)}))"

        fetch_comparison_values_query = f"""
        SELECT DISTINCT ?p ?o WHERE {{
            <{subject_uri}> ?p ?o .
            {property_filter_for_subject}
        }}
        """

        sparql.setQuery(fetch_comparison_values_query)
        sparql.setReturnFormat(JSON)
        subject_values_results = sparql.query().convert()
        subject_bindings = subject_values_results.get("results", {}).get("bindings", [])

        if not subject_bindings:
            return jsonify({"status": "success", "results": [], "has_more": False})

        subject_values_by_prop = defaultdict(list)
        for binding in subject_bindings:
            formatted_value = format_rdf_term(binding["o"])
            if formatted_value:
                subject_values_by_prop[binding["p"]["value"]].append(formatted_value)

        union_blocks = []
        var_counter = 0

        for condition in similarity_config:
            if isinstance(condition, str):
                prop_uri = condition
                prop_values = subject_values_by_prop.get(prop_uri)
                if prop_values:
                    var_counter += 1
                    values_filter = ", ".join(prop_values)
                    union_blocks.append(f"  {{ ?similar <{prop_uri}> ?o_{var_counter} . FILTER(?o_{var_counter} IN ({values_filter})) }}")

            elif isinstance(condition, dict) and "and" in condition:
                and_props = condition["and"]
                and_patterns = []
                can_match_and_group = True

                if not all(p in subject_values_by_prop for p in and_props):
                    can_match_and_group = False
                    current_app.logger.debug(f"Skipping AND group {and_props} because subject {subject_uri} lacks values for all its properties.")
                    continue

                for prop_uri in and_props:
                    prop_values = subject_values_by_prop.get(prop_uri)
                    var_counter += 1
                    values_filter = ", ".join(prop_values)
                    and_patterns.append(f"    ?similar <{prop_uri}> ?o_{var_counter} . FILTER(?o_{var_counter} IN ({values_filter})) .")

                if can_match_and_group and and_patterns:
                    # Construct the block with newlines outside the formatted expression
                    patterns_str = '\n'.join(and_patterns)
                    union_blocks.append(f"  {{\n{patterns_str}\n  }}")

        if not union_blocks:
            return jsonify({"status": "success", "results": [], "has_more": False})

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

        bindings = results.get("results", {}).get("bindings", [])
        candidate_uris = [item["similar"]["value"] for item in bindings]

        has_more = len(candidate_uris) > limit
        results_to_process = candidate_uris[:limit]

        transformed_results = []
        for uri in results_to_process:
            readable_label = custom_filter.human_readable_entity(uri, (entity_type, shape_uri)) if entity_type else uri
            transformed_results.append({
                "uri": uri,
                "label": readable_label or uri
            })

        return jsonify({
            "status": "success",
            "results": transformed_results,
            "has_more": has_more,
        })

    except Exception as e:
        tb_str = traceback.format_exc()
        current_app.logger.error(f"Error finding similar resources for {subject_uri}: {str(e)}\nTraceback: {tb_str}")
        return jsonify({"status": "error", "message": gettext("An error occurred while finding similar resources")}), 500 