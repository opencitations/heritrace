# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask import Blueprint, Response, current_app, jsonify, request
from flask_login import login_required
from SPARQLWrapper import JSON

from heritrace.extensions import get_custom_filter, get_sparql
from heritrace.sparql import get_sparql_bindings
from heritrace.utils.search import ContextConstraint, SearchRequest, build_search_query
from heritrace.utils.shacl_utils import determine_shape_for_classes
from heritrace.utils.uri_utils import is_valid_url

search_bp = Blueprint("search", __name__)


def _parse_request(data: dict) -> SearchRequest:
    return SearchRequest(
        term=data["term"],
        entity_class=data.get("entity_class"),
        predicate=data.get("predicate"),
        search_target=data.get("search_target", "self"),
        connecting_predicate=data.get("connecting_predicate"),
        context=[
            ContextConstraint(
                predicate=item["predicate"],
                value=item["value"],
                datatype=item.get("datatype"),
            )
            for item in data.get("context", [])
        ],
        offset=int(data.get("offset", 0)),
        limit=int(data.get("limit", 5)),
    )


@search_bp.route("/search", methods=["POST"])
@login_required
def search_entities() -> Response | tuple[Response, int]:
    data = request.get_json()
    if not isinstance(data, dict) or not data.get("term"):
        return jsonify({"status": "error", "message": "A search term is required"}), 400

    search_request = _parse_request(data)
    iris = [
        search_request.entity_class,
        search_request.predicate,
        search_request.connecting_predicate,
    ]
    for constraint in search_request.context:
        iris.append(constraint.predicate)
        iris.append(constraint.datatype or constraint.value)
    if not all(is_valid_url(iri) for iri in iris if iri is not None):
        return jsonify({"status": "error", "message": "Invalid IRI in request"}), 400
    if search_request.search_target == "parent" and not (
        search_request.entity_class
        and search_request.predicate
        and search_request.connecting_predicate
    ):
        return jsonify(
            {
                "status": "error",
                "message": (
                    "Parent searches require entity_class, predicate"
                    " and connecting_predicate"
                ),
            }
        ), 400

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
    has_more = len(uris) > search_request.limit
    uris = uris[: search_request.limit]

    custom_filter = get_custom_filter()
    entity_class = search_request.entity_class
    entity_key = (
        entity_class,
        determine_shape_for_classes([entity_class]) if entity_class else None,
    )
    results = [
        {"uri": uri, "label": custom_filter.human_readable_entity(uri, entity_key)}
        for uri in uris
    ]
    return jsonify({"status": "success", "results": results, "has_more": has_more})
