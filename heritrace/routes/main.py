import json
import time

from flask import (Blueprint, current_app, redirect, render_template, request,
                   url_for)
from flask_login import login_required
from heritrace.extensions import get_sparql
from heritrace.utils.shacl_utils import determine_shape_for_classes
from heritrace.utils.sparql_utils import (get_available_classes,
                                          get_catalog_data,
                                          get_deleted_entities_with_filtering,
                                          get_sortable_properties)
from SPARQLWrapper import JSON

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.jinja")


@main_bp.route("/catalogue")
@login_required
def catalogue():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    selected_class = request.args.get("class")
    sort_property = request.args.get("sort_property")
    sort_direction = request.args.get("sort_direction", "ASC")
    selected_shape = request.args.get("shape")

    available_classes = get_available_classes()

    if not selected_class and available_classes:
        selected_class = available_classes[0]["uri"]

    if not selected_shape and selected_class:
        selected_shape = determine_shape_for_classes([selected_class])

    catalog_data = get_catalog_data(
        selected_class, 
        page, 
        per_page, 
        sort_property, 
        sort_direction,
        selected_shape
    )

    return render_template(
        "catalogue.jinja",
        available_classes=available_classes,
        selected_class=selected_class,
        selected_shape=selected_shape,
        page=page,
        total_entity_pages=catalog_data["total_pages"],
        per_page=per_page,
        allowed_per_page=[50, 100, 200, 500],
        sortable_properties=json.dumps(catalog_data["sortable_properties"]),
        current_sort_property=catalog_data["sort_property"],
        current_sort_direction=catalog_data["sort_direction"],
        initial_entities=catalog_data["entities"],
    )


@main_bp.route("/time-vault")
@login_required
def time_vault():
    """
    Render the Time Vault page, which displays a list of deleted entities.
    """
    initial_page = request.args.get("page", 1, type=int)
    initial_per_page = request.args.get("per_page", 50, type=int)
    sort_property = request.args.get("sort_property", "deletionTime")
    sort_direction = request.args.get("sort_direction", "DESC")
    selected_class = request.args.get("class")
    selected_shape = request.args.get("shape")

    allowed_per_page = [50, 100, 200, 500]

    initial_entities, available_classes, selected_class, selected_shape, sortable_properties, total_count = (
        get_deleted_entities_with_filtering(
            initial_page,
            initial_per_page,
            sort_property,
            sort_direction,
            selected_class,
            selected_shape
        )
    )

    sortable_properties = [
        {"property": "deletionTime", "displayName": "Deletion Time", "sortType": "date"}
    ]
    
    if selected_class is not None:
        entity_key = (selected_class, selected_shape)
        sortable_properties.extend(
            get_sortable_properties(entity_key)
        )
    
    sortable_properties = json.dumps(sortable_properties)

    return render_template(
        "time_vault.jinja",
        available_classes=available_classes,
        selected_class=selected_class,
        selected_shape=selected_shape,
        page=initial_page,
        total_entity_pages=(total_count + initial_per_page - 1) // initial_per_page if total_count > 0 else 0,
        per_page=initial_per_page,
        allowed_per_page=allowed_per_page,
        sortable_properties=sortable_properties,
        current_sort_property=sort_property,
        current_sort_direction=sort_direction,
        initial_entities=initial_entities,
    )


@main_bp.route("/dataset-endpoint", methods=["POST"])
@login_required
def sparql_proxy():
    query = request.form.get("query")
    
    # Use SPARQLWrapper instead of direct requests
    sparql_wrapper = get_sparql()
    sparql_wrapper.setQuery(query)
    sparql_wrapper.setReturnFormat(JSON) 
    
    # Implement retry mechanism
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            results = sparql_wrapper.query().convert()
            return json.dumps(results), 200, {"Content-Type": "application/sparql-results+json"}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                current_app.logger.error(f"All SPARQL query attempts failed for query: {query}")
                return json.dumps({"error": str(e)}), 500, {"Content-Type": "application/json"}


@main_bp.route("/endpoint")
@login_required
def endpoint():
    from heritrace.extensions import dataset_endpoint

    return render_template("endpoint.jinja", dataset_endpoint=dataset_endpoint)


@main_bp.route("/search")
@login_required
def search():
    subject = request.args.get("q")
    return redirect(url_for("entity.about", subject=subject))
