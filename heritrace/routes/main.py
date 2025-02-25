import json

import requests
from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import login_required
from heritrace.extensions import (
    get_dataset_endpoint,
    get_display_rules,
    get_form_fields,
)
from heritrace.utils.sparql_utils import (
    get_available_classes,
    get_catalog_data,
    get_deleted_entities_with_filtering,
    get_sortable_properties,
)

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

    available_classes = get_available_classes()

    if not selected_class and available_classes:
        selected_class = available_classes[0]["uri"]

    catalog_data = get_catalog_data(
        selected_class, page, per_page, sort_property, sort_direction
    )

    return render_template(
        "catalogue.jinja",
        available_classes=available_classes,
        selected_class=selected_class,
        page=page,
        total_entity_pages=catalog_data["total_pages"],
        per_page=per_page,
        allowed_per_page=[50, 100, 200, 500],
        sortable_properties=json.dumps(catalog_data["sortable_properties"]),
        current_sort_property=None,
        current_sort_direction="ASC",
        initial_entities=catalog_data["entities"],
    )


@main_bp.route("/time-vault")
@login_required
def time_vault():
    """
    Render the Time Vault page, which displays a list of deleted entities.
    """
    display_rules = get_display_rules()
    form_fields = get_form_fields()
    initial_page = request.args.get("page", 1, type=int)
    initial_per_page = request.args.get("per_page", 50, type=int)
    sort_property = request.args.get("sort_property", "deletionTime")
    sort_direction = request.args.get("sort_direction", "DESC")
    selected_class = request.args.get("class")

    allowed_per_page = [50, 100, 200, 500]

    initial_entities, available_classes, selected_class, _ = (
        get_deleted_entities_with_filtering(
            initial_page,
            initial_per_page,
            sort_property,
            sort_direction,
            selected_class,
        )
    )

    sortable_properties = [
        {"property": "deletionTime", "displayName": "Deletion Time", "sortType": "date"}
    ]
    sortable_properties.extend(
        get_sortable_properties(selected_class, display_rules, form_fields)
    )
    sortable_properties = json.dumps(sortable_properties)

    return render_template(
        "time_vault.jinja",
        available_classes=available_classes,
        selected_class=selected_class,
        page=initial_page,
        total_entity_pages=0,
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
    dataset_endpoint = get_dataset_endpoint()
    query = request.form.get("query")
    response = requests.post(
        dataset_endpoint,
        data={"query": query},
        headers={"Accept": "application/sparql-results+json"},
    )
    return (
        response.content,
        response.status_code,
        {"Content-Type": "application/sparql-results+json"},
    )


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
