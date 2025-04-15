import traceback
from typing import Dict, List, Optional, Any, Tuple

from flask import (Blueprint, current_app, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_babel import gettext
from flask_login import login_required, current_user
from heritrace.extensions import (
    get_custom_filter, get_sparql, get_counter_handler, 
    get_dataset_endpoint, get_provenance_endpoint, get_dataset_is_quadstore
)
from heritrace.utils.display_rules_utils import get_similarity_properties
from heritrace.utils.sparql_utils import get_entity_types
from SPARQLWrapper import JSON, POST

# Import the Editor class and URIRef
from heritrace.editor import Editor
from rdflib import URIRef
from markupsafe import Markup

merge_bp = Blueprint("merge", __name__)


# New helper function to fetch detailed properties
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
        # Fetch entity types first
        entity_types = get_entity_types(entity_uri)
        if not entity_types:
            current_app.logger.warning(f"No types found for entity: {entity_uri}")
            # Proceed anyway, might be an entity without explicit type

        # Fetch all direct properties
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
                # Attempt to get a readable label for URI objects
                "readable_label": None
            }
            if obj_details["type"] == 'uri':
                 # Fetch types for the object URI to help human_readable_entity
                 try:
                     obj_types = get_entity_types(obj_details["value"])
                     obj_details["readable_label"] = custom_filter.human_readable_entity(obj_details["value"], obj_types)
                 except Exception as inner_e:
                     current_app.logger.warning(f"Could not fetch types/label for object URI {obj_details['value']}: {inner_e}")
                     obj_details["readable_label"] = obj_details["value"] # Fallback
            else:
                # For literals, use the value itself or apply specific formatting if needed
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

    # TODO: Implement CSRF validation if using Flask-WTF

    if not entity1_uri or not entity2_uri:
        flash(gettext("Missing entity URIs for merge."), "danger")
        return redirect(url_for("main.catalogue"))

    if entity1_uri == entity2_uri:
        flash(gettext("Cannot merge an entity with itself."), "warning")
        referer = request.headers.get("Referer")
        if referer and url_for('.compare_and_merge') in referer:
            return redirect(url_for('entity.about', subject=entity1_uri))
        return redirect(url_for("main.catalogue"))

    try:
        # Get custom filter for readable labels later
        custom_filter = get_custom_filter()

        # Fetch labels BEFORE the merge, as entity2 will be deleted
        _, entity1_types = get_entity_details(entity1_uri)
        _, entity2_types = get_entity_details(entity2_uri)
        # Fallback to URI if label cannot be generated
        entity1_label = custom_filter.human_readable_entity(entity1_uri, entity1_types) or entity1_uri
        entity2_label = custom_filter.human_readable_entity(entity2_uri, entity2_types) or entity2_uri

        # Instantiate the Editor
        counter_handler = get_counter_handler()
        # Construct responsible agent URI from current_user's ORCID
        resp_agent_uri = URIRef(f"https://orcid.org/{current_user.orcid}") if current_user.is_authenticated and hasattr(current_user, 'orcid') else None
        if not resp_agent_uri:
            # Fallback or error handling if user URI is not available
            current_app.logger.error("Responsible agent URI not found for current user.")
            flash(gettext("Could not identify the responsible agent. Merge aborted."), "danger")
            return redirect(url_for('.compare_and_merge', subject=entity1_uri, other_subject=entity2_uri))
        
        # Get configurations using getter functions
        dataset_endpoint = get_dataset_endpoint()
        provenance_endpoint = get_provenance_endpoint()
        dataset_is_quadstore = get_dataset_is_quadstore()

        if not dataset_endpoint or not provenance_endpoint:
            current_app.logger.error("Dataset or Provenance endpoint configuration missing.")
            flash(gettext("Server configuration error. Merge aborted."), "danger")
            return redirect(url_for('.compare_and_merge', subject=entity1_uri, other_subject=entity2_uri))

        editor = Editor(
            dataset_endpoint=dataset_endpoint,
            provenance_endpoint=provenance_endpoint,
            counter_handler=counter_handler,
            resp_agent=resp_agent_uri,
            dataset_is_quadstore=dataset_is_quadstore
            # source and c_time can be added if needed for merge context
        )

        current_app.logger.info(f"Executing merge via Editor: Keep <{entity1_uri}>, Delete <{entity2_uri}>")

        # Call the Editor's merge method
        editor.merge(keep_entity_uri=entity1_uri, delete_entity_uri=entity2_uri)

        current_app.logger.info(f"Successfully merged <{entity2_uri}> into <{entity1_uri}> via Editor.")
        # Use human-readable labels in the flash message
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

        # Use Markup to render HTML safely
        flash(Markup(flash_message_html), "success")

        # Redirect to the page of the entity that was kept
        return redirect(url_for("entity.about", subject=entity1_uri))

    except ValueError as ve:
        # Specific handling for merge with self
        current_app.logger.warning(f"Merge attempt failed: {ve}")
        flash(str(ve), "warning")
        return redirect(url_for('.compare_and_merge', subject=entity1_uri, other_subject=entity2_uri))

    except Exception as e:
        tb_str = traceback.format_exc()
        current_app.logger.error(f"Error executing Editor merge for <{entity1_uri}> and <{entity2_uri}>: {e}\n{tb_str}")
        flash(gettext("An error occurred during the merge operation. Please check the logs. No changes were made."), "danger")
        # Redirect back to the confirmation page or catalogue
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

    if entity1_uri == entity2_uri:
         flash(gettext("Cannot compare or merge an entity with itself."), "warning")
         # Try to redirect back sensibly
         referer = request.headers.get("Referer")
         if referer and f"/about/{entity1_uri}" in referer:
             return redirect(url_for('entity.about', subject=entity1_uri))
         else:
             return redirect(url_for("main.catalogue"))

    # Fetch detailed information for both entities
    entity1_props, entity1_types = get_entity_details(entity1_uri)
    entity2_props, entity2_types = get_entity_details(entity2_uri)

    if entity1_props is None or entity2_props is None:
        flash(gettext("Could not retrieve details for one or both entities. Check logs."), "danger")
        return redirect(url_for("main.catalogue"))

    # Get human-readable labels
    entity1_label = custom_filter.human_readable_entity(entity1_uri, entity1_types) or entity1_uri
    entity2_label = custom_filter.human_readable_entity(entity2_uri, entity2_types) or entity2_uri


    # Prepare data for the template
    entity1_data = {
        "uri": entity1_uri,
        "label": entity1_label,
        "types": entity1_types,
        "properties": entity1_props
    }
    entity2_data = {
        "uri": entity2_uri,
        "label": entity2_label,
        "types": entity2_types,
        "properties": entity2_props
    }

    return render_template(
        "entity/merge_confirm.jinja",
        entity1=entity1_data,
        entity2=entity2_data
    )


@merge_bp.route("/find_similar", methods=["GET"])
@login_required
def find_similar_resources():
    """Find resources potentially similar to a given subject based on shared literal properties."""
    subject_uri = request.args.get("subject_uri")
    entity_type = request.args.get("entity_type") # Primary entity type
    limit = int(request.args.get("limit", 5))

    if not subject_uri or not entity_type:
        return jsonify({"status": "error", "message": gettext("Missing required parameters (subject_uri, entity_type)")}), 400

    try:
        sparql = get_sparql()
        custom_filter = get_custom_filter()

        similarity_properties = get_similarity_properties(entity_type)
        
        property_filter = ""
        if similarity_properties:
            prop_uris = [f"<{p}>" for p in similarity_properties]
            property_filter = f"FILTER(?p IN ({', '.join(prop_uris)}))"

        fetch_comparison_values_query = f"""
        SELECT DISTINCT ?p ?o WHERE {{
            <{subject_uri}> ?p ?o .
            {property_filter}
        }}
        """
        sparql.setQuery(fetch_comparison_values_query)
        sparql.setReturnFormat(JSON)
        subject_values_results = sparql.query().convert()
        subject_values = subject_values_results.get("results", {}).get("bindings", [])

        if not subject_values:
            return jsonify({"status": "success", "results": []}) 

        similarity_conditions = []
        for binding in subject_values:
            prop = binding["p"]["value"]
            val_node = binding["o"] 
            value = val_node["value"]
            value_type = val_node["type"]
            
            formatted_value = ""
            if value_type == 'uri':
                formatted_value = f"<{value}>"
            elif value_type in {'literal', 'typed-literal'}:
                datatype = val_node.get("datatype")
                lang = val_node.get("xml:lang")
                escaped_value_literal = value.replace('\\', '\\\\').replace('"', '\\"')
                if datatype:
                    formatted_value = f'"{escaped_value_literal}"^^<{datatype}>'
                elif lang:
                    formatted_value = f'"{escaped_value_literal}"@{lang}'
                else:
                    formatted_value = f'"{escaped_value_literal}"'
            else: 
                continue
                
            similarity_conditions.append(f"{{ ?similar <{prop}> {formatted_value} . }}")

        if not similarity_conditions:
            return jsonify({"status": "success", "results": []})

        query_parts = [
            "SELECT DISTINCT ?similar WHERE {",
            f"  ?similar a <{entity_type}> .",
            f"  FILTER(?similar != <{subject_uri}>)",
            "  {",
            "    " + " \n    UNION\n    ".join(similarity_conditions),
            "  }",
            f"}} LIMIT {limit}"
        ]
        final_query = "\n".join(query_parts)

        sparql.setQuery(final_query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        candidate_uris = [item["similar"]["value"] for item in results.get("results", {}).get("bindings", [])]
        transformed_results = []
        for uri in candidate_uris:
            readable_label = custom_filter.human_readable_entity(uri, [entity_type]) 
            sim_types = get_entity_types(uri)
            type_labels = [custom_filter.human_readable_predicate(type_uri, sim_types) for type_uri in sim_types]
            transformed_results.append({
                "uri": uri,
                "label": readable_label,
                "types": sim_types,
                "type_labels": type_labels
            })

        return jsonify({"status": "success", "results": transformed_results})

    except Exception as e:
        tb_str = traceback.format_exc()
        current_app.logger.error(f"Error finding similar resources: {str(e)}\nTraceback: {tb_str}")
        return jsonify({"status": "error", "message": gettext("An error occurred while finding similar resources")}), 500 