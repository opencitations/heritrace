# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask import Blueprint, Response, current_app, jsonify, request
from flask_login import login_required
from SPARQLWrapper import JSON

from heritrace.extensions import get_custom_filter, get_form_fields, get_sparql
from heritrace.sparql import get_sparql_bindings
from heritrace.utils.search import SearchRequest, build_search_query, text_paths

search_bp = Blueprint("search", __name__)


@search_bp.route("/search", methods=["POST"])
@login_required
def search_entities() -> Response | tuple[Response, int]:
    data = request.get_json()
    if not isinstance(data, dict) or not data.get("term"):
        return jsonify({"status": "error", "message": "A search term is required"}), 400
    entity_key = (str(data["entity_class"]), str(data["shape"]))
    form_fields = get_form_fields()
    if entity_key not in form_fields:
        return jsonify({"status": "error", "message": "Unknown entity type"}), 400

    paths = text_paths(form_fields[entity_key])
    if not paths:
        return jsonify({"status": "success", "results": [], "has_more": False})
    search_request = SearchRequest(
        term=data["term"],
        entity_class=entity_key[0],
        paths=paths,
        offset=int(data["offset"]),
        limit=int(data["limit"]),
    )
    query = build_search_query(
        search_request,
        current_app.config["DATASET_DB_TRIPLESTORE"],
        text_index_enabled=current_app.config["DATASET_DB_TEXT_INDEX_ENABLED"],
    )
    sparql = get_sparql()
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    bindings = get_sparql_bindings(sparql.query().convert())
    uris = [binding["entity"]["value"] for binding in bindings]
    custom_filter = get_custom_filter()
    results = [
        {"uri": uri, "label": custom_filter.human_readable_entity(uri, entity_key)}
        for uri in uris[: search_request.limit]
    ]
    return jsonify(
        {
            "status": "success",
            "results": results,
            "has_more": len(uris) > search_request.limit,
        }
    )
