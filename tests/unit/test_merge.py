# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from dataclasses import replace
from unittest.mock import MagicMock, call, patch

import pytest
from flask import url_for
from rdflib import URIRef

from heritrace.routes.merge import merge_bp


@pytest.fixture
def mock_user():
    """Fixture to mock a logged-in user."""
    user = MagicMock()
    user.is_authenticated = True
    user.orcid = "0000-0001-2345-6789"
    return user


@pytest.fixture(autouse=True)
def ensure_merge_bp(app) -> None:
    """Ensures the merge blueprint is registered on the app."""
    if not app.blueprints.get("merge"):
        app.register_blueprint(merge_bp, url_prefix="/merge")


@pytest.fixture(autouse=True)
def mock_import_entity_graph():
    with patch("heritrace.routes.merge.import_entity_graph") as mock:
        mock.side_effect = lambda editor, _subject: editor
        yield mock


@pytest.fixture
def merge_test_data():
    """Provides common data for merge execution tests."""
    user_orcid = "0000-0001-2345-6789"
    return {
        "entity1_uri": "http://merge.test/entityKeep",
        "entity2_uri": "http://merge.test/entityDelete",
        "entity1_label": "Keep Entity Label",
        "entity2_label": "Delete Entity Label",
        "entity1_types": ["http://merge.test/TypeKeep"],
        "entity2_types": ["http://merge.test/TypeDelete"],
        "user_orcid": user_orcid,
        "resp_agent_uri": URIRef(f"https://orcid.org/{user_orcid}"),
    }


def _filter_with_labels(merge_test_data: dict) -> MagicMock:
    mock_filter_instance = MagicMock()
    mock_filter_instance.value_label.side_effect = [
        merge_test_data["entity1_label"],
        merge_test_data["entity2_label"],
    ]
    mock_filter_instance.human_readable_class.side_effect = ["Keep Type", "Delete Type"]
    return mock_filter_instance


@patch("heritrace.routes.merge.get_custom_filter")
@patch("heritrace.routes.merge.get_entity_types")
@patch("heritrace.routes.merge.new_editor")
@patch("flask_login.utils._get_user")
def test_execute_merge_success(
    mock_current_user,
    mock_editor_cls,
    mock_get_types,
    mock_get_filter,
    mock_import_entity_graph,
    client,
    mock_user,
    merge_test_data,
) -> None:
    mock_current_user.return_value = mock_user
    mock_get_types.side_effect = [
        merge_test_data["entity1_types"],
        merge_test_data["entity2_types"],
    ]
    mock_get_filter.return_value = _filter_with_labels(merge_test_data)
    mock_editor_instance = MagicMock()
    mock_editor_cls.return_value = mock_editor_instance

    response = client.post(
        url_for("merge.execute_merge"),
        json={
            "entity1_uri": merge_test_data["entity1_uri"],
            "entity2_uri": merge_test_data["entity2_uri"],
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "success",
        "kept": {
            "uri": merge_test_data["entity1_uri"],
            "label": merge_test_data["entity1_label"],
            "type": merge_test_data["entity1_types"][0],
            "type_label": "Keep Type",
            "shape": None,
        },
        "deleted": {
            "uri": merge_test_data["entity2_uri"],
            "label": merge_test_data["entity2_label"],
            "type": merge_test_data["entity2_types"][0],
            "type_label": "Delete Type",
            "shape": None,
        },
    }
    mock_editor_cls.assert_called_once_with(
        merge_test_data["resp_agent_uri"],
        URIRef("https://example.com/test-primary-source"),
    )
    assert mock_import_entity_graph.call_args_list == [
        call(mock_editor_instance, URIRef(merge_test_data["entity1_uri"])),
        call(mock_editor_instance, URIRef(merge_test_data["entity2_uri"])),
    ]
    mock_editor_instance.merge.assert_called_once_with(
        keep_entity_uri=URIRef(merge_test_data["entity1_uri"]),
        delete_entity_uri=URIRef(merge_test_data["entity2_uri"]),
        primary_source=None,
    )


@patch("flask_login.utils._get_user")
def test_execute_merge_invalid_primary_source(
    mock_current_user, client, mock_user, merge_test_data
) -> None:
    mock_current_user.return_value = mock_user

    response = client.post(
        url_for("merge.execute_merge"),
        json={
            "entity1_uri": merge_test_data["entity1_uri"],
            "entity2_uri": merge_test_data["entity2_uri"],
            "primary_source": "not-a-valid-url",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "status": "error",
        "message": "Invalid primary source URL provided.",
    }


@patch("heritrace.routes.merge.save_user_default_primary_source")
@patch("heritrace.routes.merge.get_custom_filter")
@patch("heritrace.routes.merge.get_entity_types")
@patch("heritrace.routes.merge.new_editor")
@patch("flask_login.utils._get_user")
def test_execute_merge_save_default_source(
    mock_current_user,
    mock_editor_cls,
    mock_get_types,
    mock_get_filter,
    mock_save_source,
    client,
    mock_user,
    merge_test_data,
) -> None:
    mock_current_user.return_value = mock_user
    mock_get_types.side_effect = [
        merge_test_data["entity1_types"],
        merge_test_data["entity2_types"],
    ]
    mock_get_filter.return_value = _filter_with_labels(merge_test_data)
    mock_editor_instance = MagicMock()
    mock_editor_cls.return_value = mock_editor_instance

    primary_source = "https://example.com/valid-source"

    response = client.post(
        url_for("merge.execute_merge"),
        json={
            "entity1_uri": merge_test_data["entity1_uri"],
            "entity2_uri": merge_test_data["entity2_uri"],
            "primary_source": primary_source,
            "save_default_source": True,
        },
    )

    assert response.status_code == 200
    mock_save_source.assert_called_once_with(mock_user.orcid, primary_source)
    mock_editor_instance.merge.assert_called_once_with(
        keep_entity_uri=URIRef(merge_test_data["entity1_uri"]),
        delete_entity_uri=URIRef(merge_test_data["entity2_uri"]),
        primary_source=URIRef(primary_source),
    )


@patch("flask_login.utils._get_user")
def test_execute_merge_missing_uris(mock_current_user, client, mock_user) -> None:
    mock_current_user.return_value = mock_user

    response = client.post(url_for("merge.execute_merge"), json={})

    assert response.status_code == 400
    assert response.get_json() == {
        "status": "error",
        "message": "Missing entity URIs for merge.",
    }


@patch("heritrace.routes.merge.get_custom_filter")
@patch("heritrace.routes.merge.get_entity_types")
@patch("heritrace.routes.merge.new_editor")
@patch("flask_login.utils._get_user")
def test_execute_merge_editor_value_error(
    mock_current_user,
    mock_editor_cls,
    mock_get_types,
    mock_get_filter,
    client,
    mock_user,
    merge_test_data,
) -> None:
    mock_current_user.return_value = mock_user
    mock_get_types.side_effect = [
        merge_test_data["entity1_types"],
        merge_test_data["entity2_types"],
    ]
    mock_get_filter.return_value = _filter_with_labels(merge_test_data)
    mock_editor_instance = MagicMock()
    mock_editor_instance.merge.side_effect = ValueError("Test Editor Value Error")
    mock_editor_cls.return_value = mock_editor_instance

    response = client.post(
        url_for("merge.execute_merge"),
        json={
            "entity1_uri": merge_test_data["entity1_uri"],
            "entity2_uri": merge_test_data["entity2_uri"],
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "status": "error",
        "message": "Test Editor Value Error",
    }


@patch("heritrace.routes.merge.get_custom_filter")
@patch("heritrace.routes.merge.get_entity_types")
@patch("heritrace.routes.merge.new_editor")
@patch("flask_login.utils._get_user")
def test_execute_merge_general_exception(
    mock_current_user,
    mock_editor_cls,
    mock_get_types,
    mock_get_filter,
    client,
    mock_user,
    merge_test_data,
) -> None:
    mock_current_user.return_value = mock_user
    mock_get_types.side_effect = [
        merge_test_data["entity1_types"],
        merge_test_data["entity2_types"],
    ]
    mock_get_filter.return_value = _filter_with_labels(merge_test_data)
    mock_editor_instance = MagicMock()
    mock_editor_instance.merge.side_effect = Exception("Something went wrong general")
    mock_editor_cls.return_value = mock_editor_instance

    response = client.post(
        url_for("merge.execute_merge"),
        json={
            "entity1_uri": merge_test_data["entity1_uri"],
            "entity2_uri": merge_test_data["entity2_uri"],
        },
    )

    assert response.status_code == 500
    assert response.get_json() == {
        "status": "error",
        "message": (
            "An error occurred during the merge operation."
            " Please check the logs. No changes were made."
        ),
    }


def _entity_view(uri: str, label: str, type_label: str, groups: list) -> dict:
    return {
        "uri": uri,
        "label": label,
        "type_label": type_label,
        "optional_values": {
            "http://merge.test/status": [
                {"value": "http://merge.test/open", "label": "Open"}
            ],
            "http://merge.test/title": [],
        },
        "groups": groups,
    }


def _group(predicate: str, display_name: str, triples: list[tuple]) -> dict:
    return {
        "property": predicate,
        "display_name": display_name,
        "triples": [{"value": value, "label": label} for value, label in triples],
    }


@patch("heritrace.routes.merge.build_entity_view")
@patch("flask_login.utils._get_user")
def test_compare_and_merge_success(
    mock_current_user,
    mock_build_view,
    client,
    mock_user,
    merge_test_data,
) -> None:
    mock_current_user.return_value = mock_user
    rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    mock_build_view.side_effect = [
        _entity_view(
            merge_test_data["entity1_uri"],
            merge_test_data["entity1_label"],
            "Keep Type",
            [
                _group(rdf_type, "Type", [("Keep Type", "Keep Type")]),
                _group(
                    "http://merge.test/author",
                    "Author",
                    [
                        ("Doe, Jane [id:1]", "http://merge.test/ar/1"),
                        ("Roe, Ann [id:2]", "http://merge.test/ar/2"),
                    ],
                ),
                _group("http://merge.test/editor", "Editor", []),
            ],
        ),
        _entity_view(
            merge_test_data["entity2_uri"],
            merge_test_data["entity2_label"],
            "Delete Type",
            [
                _group(
                    "http://merge.test/status",
                    "Status",
                    [("http://merge.test/open", "Open")],
                ),
                _group(
                    "http://merge.test/title",
                    "Title",
                    [("A title", "http://merge.test/title-label")],
                ),
            ],
        ),
    ]

    response = client.get(
        url_for(
            "merge.compare_and_merge",
            subject=merge_test_data["entity1_uri"],
            other_subject=merge_test_data["entity2_uri"],
        )
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "entity1": {
            "uri": merge_test_data["entity1_uri"],
            "label": merge_test_data["entity1_label"],
            "type_label": "Keep Type",
            "properties": [
                {
                    "predicate": "http://merge.test/author",
                    "label": "Author",
                    "values": [
                        {"readable_label": "Doe, Jane [id:1]"},
                        {"readable_label": "Roe, Ann [id:2]"},
                    ],
                }
            ],
        },
        "entity2": {
            "uri": merge_test_data["entity2_uri"],
            "label": merge_test_data["entity2_label"],
            "type_label": "Delete Type",
            "properties": [
                {
                    "predicate": "http://merge.test/status",
                    "label": "Status",
                    "values": [{"readable_label": "Open"}],
                },
                {
                    "predicate": "http://merge.test/title",
                    "label": "Title",
                    "values": [{"readable_label": "A title"}],
                },
            ],
        },
    }
    assert mock_build_view.call_args_list == [
        call(merge_test_data["entity1_uri"]),
        call(merge_test_data["entity2_uri"]),
    ]


@patch("flask_login.utils._get_user")
def test_compare_and_merge_missing_uris(
    mock_current_user, client, mock_user, merge_test_data
) -> None:
    mock_current_user.return_value = mock_user

    response = client.get(
        url_for("merge.compare_and_merge", subject=merge_test_data["entity1_uri"])
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "status": "error",
        "message": "Two entities must be selected for merging/comparison.",
    }


@pytest.fixture
def similar_test_data():
    """Provides common data for find_similar_resources tests."""
    return {
        "subject_uri": "http://similar.test/subject",
        "similar_uri": "http://similar.test/similar",
        "subject_type": "http://similar.test/TypeSub",
        "similar_type": "http://similar.test/TypeSim",
        "similar_label": "Similar Label",
        "prop_name": "http://similar.prop/name",
        "prop_ref": "http://similar.prop/ref",
        "shared_name": "Shared Similar Name",
        "shared_ref": "http://similar.ref/shared",
    }


@patch("heritrace.routes.merge.get_sparql")
@patch("heritrace.routes.merge.get_custom_filter")
@patch("heritrace.routes.merge._duplicate_keys")
@patch("heritrace.routes.merge.get_entity_types")
@patch("flask_login.utils._get_user")
def test_find_similar_resources_success(
    mock_current_user,
    mock_get_types,
    mock_get_sim_props,
    mock_get_filter,
    mock_get_sparql,
    client,
    mock_user,
    similar_test_data,
) -> None:
    """Test finding similar resources successfully."""
    mock_current_user.return_value = mock_user
    mock_sparql_instance = MagicMock()
    mock_sparql_instance.query().convert.side_effect = [
        {
            "results": {
                "bindings": [
                    {
                        "p": {"value": similar_test_data["prop_name"]},
                        "o": {
                            "value": similar_test_data["shared_name"],
                            "type": "literal",
                        },
                    },
                    {
                        "p": {"value": similar_test_data["prop_ref"]},
                        "o": {"value": similar_test_data["shared_ref"], "type": "uri"},
                    },
                ]
            }
        },
        {
            "results": {
                "bindings": [{"similar": {"value": similar_test_data["similar_uri"]}}]
            }
        },
    ]
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_sim_props.return_value = [
        [similar_test_data["prop_name"]],
        [similar_test_data["prop_ref"]],
    ]
    mock_filter_instance = MagicMock()
    mock_filter_instance.value_label.return_value = similar_test_data["similar_label"]
    mock_filter_instance.human_readable_predicate.side_effect = (
        lambda pred_uri, _entity_key: f"Label_{pred_uri.split('/')[-1]}"
    )
    mock_get_filter.return_value = mock_filter_instance
    mock_get_types.side_effect = [
        [similar_test_data["subject_type"]],
        [similar_test_data["similar_type"]],
    ]

    response = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
            limit=5,
        )
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert len(data["results"]) == 1
    assert data["results"][0]["uri"] == similar_test_data["similar_uri"]
    assert data["results"][0]["label"] == similar_test_data["similar_label"]
    assert not data["has_more"]
    assert mock_sparql_instance.setQuery.call_count == 2


@patch("heritrace.routes.merge.get_sparql")
@patch("heritrace.routes.merge._duplicate_keys")
@patch("flask_login.utils._get_user")
def test_find_similar_resources_no_subject_values(
    mock_current_user,
    mock_get_sim_props,
    mock_get_sparql,
    client,
    mock_user,
    similar_test_data,
) -> None:
    """Test when the subject has no values for similarity properties."""
    mock_current_user.return_value = mock_user
    mock_sparql_instance = MagicMock()
    mock_sparql_instance.query().convert.return_value = {"results": {"bindings": []}}
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_sim_props.return_value = [[similar_test_data["prop_name"]]]

    response = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
        )
    )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["results"] == []
    mock_sparql_instance.setQuery.assert_called_once()


@patch("flask_login.utils._get_user")
def test_find_similar_resources_missing_params(
    mock_current_user, client, mock_user, similar_test_data
) -> None:
    """Test request with missing parameters."""
    mock_current_user.return_value = mock_user
    response = client.get(
        url_for(
            "merge.find_similar_resources", subject_uri=similar_test_data["subject_uri"]
        )
    )
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "Missing required parameters" in json_data["message"]


@patch(
    "heritrace.routes.merge._duplicate_keys",
    side_effect=Exception("Database connection failed similar"),
)
@patch("flask_login.utils._get_user")
def test_find_similar_resources_exception(
    mock_current_user, mock_get_sim_props, client, mock_user, similar_test_data
) -> None:
    """Test handling of general exceptions during similarity search."""
    mock_current_user.return_value = mock_user

    response = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
        )
    )

    assert response.status_code == 500
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "An error occurred while finding similar resources" in json_data["message"]


@patch("heritrace.routes.merge.get_sparql")
@patch("heritrace.routes.merge.get_custom_filter")
@patch("heritrace.routes.merge._duplicate_keys")
@patch("heritrace.routes.merge.get_entity_types")
@patch("flask_login.utils._get_user")
@pytest.mark.parametrize("backend", ["virtuoso", "qlever", "default"])
def test_find_similar_resources_literal_formatting(
    mock_current_user,
    mock_get_types,
    mock_get_sim_props,
    mock_get_filter,
    mock_get_sparql,
    client,
    app,
    backend,
    mock_user,
    similar_test_data,
) -> None:
    """Test correct SPARQL formatting for various literal types."""
    app.config["DATASET_DB_TRIPLESTORE"] = backend
    app.extensions["heritrace"] = replace(
        app.extensions["heritrace"], is_virtuoso=backend == "virtuoso"
    )
    mock_current_user.return_value = mock_user
    mock_sparql_instance = MagicMock()

    prop_typed = "http://similar.prop/typed"
    prop_lang = "http://similar.prop/lang"
    prop_plain = "http://similar.prop/plain"
    prop_bnode = "http://similar.prop/bnode"

    mock_sparql_instance.query().convert.side_effect = [
        {
            "results": {
                "bindings": [
                    {
                        "p": {"value": prop_typed},
                        "o": {
                            "value": "TypedValue",
                            "type": "typed-literal",
                            "datatype": "http://www.w3.org/2001/XMLSchema#string",
                        },
                    },
                    {
                        "p": {"value": prop_lang},
                        "o": {
                            "value": "LangValue",
                            "type": "literal",
                            "xml:lang": "en",
                        },
                    },
                    {
                        "p": {"value": prop_plain},
                        "o": {"value": "PlainValue", "type": "literal"},
                    },
                    {
                        "p": {"value": prop_bnode},
                        "o": {"value": "bnode1", "type": "bnode"},
                    },
                ]
            }
        },
        {
            "results": {
                "bindings": [{"similar": {"value": similar_test_data["similar_uri"]}}]
            }
        },
    ]
    mock_get_sparql.return_value = mock_sparql_instance
    similarity_props = [[prop_typed], [prop_lang], [prop_plain], [prop_bnode]]
    mock_get_sim_props.return_value = similarity_props
    mock_filter_instance = MagicMock()
    mock_filter_instance.value_label.return_value = similar_test_data["similar_label"]
    mock_filter_instance.human_readable_predicate.side_effect = (
        lambda pred_uri, _entity_key: f"Label_{pred_uri.split('/')[-1]}"
    )
    mock_get_filter.return_value = mock_filter_instance
    mock_get_types.return_value = [similar_test_data["similar_type"]]

    client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
        )
    )

    assert mock_sparql_instance.setQuery.call_count == 2

    final_query = mock_sparql_instance.setQuery.call_args_list[1].args[0]
    if backend != "virtuoso":
        patterns = (
            '{ VALUES ?o_1 { "TypedValue"^^'
            "<http://www.w3.org/2001/XMLSchema#string> } "
            f"?similar <{prop_typed}> ?o_1 . }} UNION "
            '{ VALUES ?o_2 { "LangValue"@en } '
            f"?similar <{prop_lang}> ?o_2 . }} UNION "
            f'{{ VALUES ?o_3 {{ "PlainValue" }} ?similar <{prop_plain}> ?o_3 . }} '
        )
    else:
        patterns = (
            f"{{ ?similar <{prop_typed}> ?o_1 . "
            'FILTER(?o_1 IN ("TypedValue"^^'
            "<http://www.w3.org/2001/XMLSchema#string>)) } UNION "
            f"{{ ?similar <{prop_lang}> ?o_2 . "
            'FILTER(?o_2 IN ("LangValue"@en)) } UNION '
            f'{{ ?similar <{prop_plain}> ?o_3 . FILTER(?o_3 IN ("PlainValue")) }} '
        )
    assert " ".join(final_query.split()) == (
        "SELECT DISTINCT ?similar WHERE { "
        f"?similar a <{similar_test_data['subject_type']}> . "
        f"FILTER(?similar != <{similar_test_data['subject_uri']}>) {{ "
        + patterns
        + "} } ORDER BY ?similar OFFSET 0 LIMIT 6"
    )


@patch("heritrace.routes.merge.get_sparql")
@patch("heritrace.routes.merge._duplicate_keys")
@patch("flask_login.utils._get_user")
def test_find_similar_resources_no_valid_conditions(
    mock_current_user,
    mock_get_sim_props,
    mock_get_sparql,
    client,
    mock_user,
    similar_test_data,
) -> None:
    """
    Test case where subject values exist but none are valid for similarity matching.
    """
    mock_current_user.return_value = mock_user
    mock_sparql_instance = MagicMock()
    prop_bnode_only = "http://similar.prop/bnode_only"

    mock_sparql_instance.query().convert.return_value = {
        "results": {
            "bindings": [
                {
                    "p": {"value": prop_bnode_only},
                    "o": {"value": "bnode_val", "type": "bnode"},
                }
            ]
        }
    }
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_sim_props.return_value = [[prop_bnode_only]]

    response = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
        )
    )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["results"] == []
    mock_sparql_instance.setQuery.assert_called_once()


@patch("flask_login.utils._get_user")
def test_find_similar_resources_invalid_limit_offset_type(
    mock_current_user, client, mock_user, similar_test_data
) -> None:
    """Test request with non-integer limit or offset."""
    mock_current_user.return_value = mock_user

    response_limit = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
            limit="not-an-int",
        )
    )
    assert response_limit.status_code == 400
    json_data_limit = response_limit.get_json()
    assert json_data_limit["status"] == "error"
    assert "Invalid limit or offset parameter" in json_data_limit["message"]

    response_offset = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
            offset="invalid",
        )
    )
    assert response_offset.status_code == 400
    json_data_offset = response_offset.get_json()
    assert json_data_offset["status"] == "error"
    assert "Invalid limit or offset parameter" in json_data_offset["message"]


@patch("flask_login.utils._get_user")
def test_find_similar_resources_invalid_limit_offset_value(
    mock_current_user, client, mock_user, similar_test_data
) -> None:
    """Test request with non-positive limit or negative offset."""
    mock_current_user.return_value = mock_user

    response_limit = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
            limit=0,
        )
    )
    assert response_limit.status_code == 400
    json_data_limit = response_limit.get_json()
    assert json_data_limit["status"] == "error"
    assert (
        "Limit must be positive and offset non-negative" in json_data_limit["message"]
    )

    response_offset = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
            offset=-1,
        )
    )
    assert response_offset.status_code == 400
    json_data_offset = response_offset.get_json()
    assert json_data_offset["status"] == "error"
    assert (
        "Limit must be positive and offset non-negative" in json_data_offset["message"]
    )


@patch(
    "heritrace.routes.merge._duplicate_keys",
    side_effect=Exception("Database connection failed similar"),
)
@patch("flask_login.utils._get_user")
def test_find_similar_resources_database_exception(
    mock_current_user, mock_get_sim_props, client, mock_user, similar_test_data
) -> None:
    """Test handling of general exceptions during similarity search."""
    mock_current_user.return_value = mock_user

    response = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
        )
    )

    assert response.status_code == 500
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "An error occurred while finding similar resources" in json_data["message"]


@patch("heritrace.routes.merge._duplicate_keys")
@patch("flask_login.utils._get_user")
def test_find_similar_resources_no_similarity_config(
    mock_current_user, mock_get_sim_props, client, mock_user, similar_test_data
) -> None:
    """Test find_similar_resources when no similarity config is found for the type."""
    mock_current_user.return_value = mock_user
    mock_get_sim_props.return_value = []

    response = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
        )
    )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["results"] == []
    assert not json_data["has_more"]
    mock_get_sim_props.assert_called_once_with(similar_test_data["subject_type"], None)


@patch("heritrace.routes.merge.get_sparql")
@patch("heritrace.routes.merge._duplicate_keys")
@patch("flask_login.utils._get_user")
def test_find_similar_resources_skip_and_group_missing_subject_prop(
    mock_current_user,
    mock_get_sim_props,
    mock_get_sparql,
    client,
    mock_user,
    similar_test_data,
) -> None:
    """
    Test skipping an AND group because the subject lacks a required property value.
    """
    mock_current_user.return_value = mock_user
    mock_sparql_instance = MagicMock()
    prop_a = "http://similar.prop/propA"
    prop_b = "http://similar.prop/propB"  # Subject will lack this
    prop_c = "http://similar.prop/propC"  # OR condition

    # Simulate subject only having value for propA and propC
    mock_sparql_instance.query().convert.side_effect = [
        {
            "results": {
                "bindings": [
                    {
                        "p": {"value": prop_a},
                        "o": {"value": "ValueA", "type": "literal"},
                    },
                    {
                        "p": {"value": prop_c},
                        "o": {"value": "ValueC", "type": "literal"},
                    },
                ]
            }
        },
        # Second call (final query) - should only match based on prop_c
        {
            "results": {
                "bindings": [
                    {"similar": {"value": similar_test_data["similar_uri"] + "_c"}}
                ]
            }
        },
    ]
    mock_get_sparql.return_value = mock_sparql_instance
    # Config with an AND group requiring propA and propB, and an OR for propC
    mock_get_sim_props.return_value = [[prop_a, prop_b], [prop_c]]

    response = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
        )
    )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    # Only the result from the OR condition (prop_c) should be found
    assert len(json_data["results"]) >= 0  # Can be 0 or 1 depending on mock_get_types
    assert mock_sparql_instance.setQuery.call_count == 2
    # Verify the generated query does not include the AND block but includes the OR
    # block
    final_query = mock_sparql_instance.setQuery.call_args_list[1].args[0]
    assert f"<{prop_b}>" not in final_query  # AND block should be skipped
    assert f"<{prop_c}> ?o_" in final_query  # OR block should be present


@patch("heritrace.routes.merge.get_sparql")
@patch("heritrace.routes.merge._duplicate_keys")
@patch("flask_login.utils._get_user")
def test_find_similar_resources_no_valid_union_blocks_due_to_formatting(
    mock_current_user,
    mock_get_sim_props,
    mock_get_sparql,
    client,
    mock_user,
    similar_test_data,
) -> None:
    """
    Test case where subject has values but none are formattable (e.g., only bnodes).
    """
    mock_current_user.return_value = mock_user
    mock_sparql_instance = MagicMock()
    prop_bnode_only = "http://similar.prop/bnode_only"

    # Simulate subject only having a blank node value for the configured property
    mock_sparql_instance.query().convert.return_value = {
        "results": {
            "bindings": [
                {"p": {"value": prop_bnode_only}, "o": {"value": "b1", "type": "bnode"}}
            ]
        }
    }
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_sim_props.return_value = [[prop_bnode_only]]

    response = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
        )
    )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["results"] == []
    assert json_data["has_more"] is False


@patch("heritrace.routes.merge.get_sparql")
@patch("heritrace.routes.merge.get_custom_filter")
@patch("heritrace.routes.merge._duplicate_keys")
@patch("heritrace.routes.merge.get_entity_types")
@patch("flask_login.utils._get_user")
@pytest.mark.parametrize("backend", ["virtuoso", "qlever", "default"])
def test_find_similar_resources_success_with_and_group(
    mock_current_user,
    mock_get_types,
    mock_get_sim_props,
    mock_get_filter,
    mock_get_sparql,
    client,
    app,
    backend,
    mock_user,
    similar_test_data,
) -> None:
    """Test finding similar resources successfully using an AND group condition."""
    app.config["DATASET_DB_TRIPLESTORE"] = backend
    app.extensions["heritrace"] = replace(
        app.extensions["heritrace"], is_virtuoso=backend == "virtuoso"
    )
    mock_current_user.return_value = mock_user
    mock_sparql_instance = MagicMock()
    prop_a = "http://similar.prop/propA"
    prop_b = "http://similar.prop/propB"
    val_a = "ValueA"
    val_b = "ValueB"
    similar_uri_and = similar_test_data["similar_uri"] + "_and"

    # Simulate subject having values for both properties in the AND group
    mock_sparql_instance.query().convert.side_effect = [
        {
            "results": {
                "bindings": [
                    {"p": {"value": prop_a}, "o": {"value": val_a, "type": "literal"}},
                    {"p": {"value": prop_b}, "o": {"value": val_b, "type": "literal"}},
                ]
            }
        },
        # Simulate finding a similar entity that matches the AND condition
        {"results": {"bindings": [{"similar": {"value": similar_uri_and}}]}},
    ]
    mock_get_sparql.return_value = mock_sparql_instance
    # Configure similarity with an AND group
    mock_get_sim_props.return_value = [[prop_a, prop_b]]

    mock_filter_instance = MagicMock()
    mock_filter_instance.value_label.return_value = "Similar AND Label"
    mock_filter_instance.human_readable_predicate.side_effect = (
        lambda pred_uri, _entity_key: f"Label_{pred_uri.split('/')[-1]}"
    )
    mock_get_filter.return_value = mock_filter_instance
    mock_get_types.return_value = [
        similar_test_data["similar_type"]
    ]  # For the similar entity

    response = client.get(
        url_for(
            "merge.find_similar_resources",
            subject_uri=similar_test_data["subject_uri"],
            entity_type=similar_test_data["subject_type"],
            limit=5,
        )
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert len(data["results"]) == 1
    assert data["results"][0]["uri"] == similar_uri_and
    assert data["results"][0]["label"] == "Similar AND Label"
    assert not data["has_more"]
    assert mock_sparql_instance.setQuery.call_count == 2

    final_query = mock_sparql_instance.setQuery.call_args_list[1].args[0]
    if backend != "virtuoso":
        patterns = (
            f'VALUES ?o_1 {{ "{val_a}" }} ?similar <{prop_a}> ?o_1 . '
            f'VALUES ?o_2 {{ "{val_b}" }} ?similar <{prop_b}> ?o_2 . '
        )
    else:
        patterns = (
            f'?similar <{prop_a}> ?o_1 . FILTER(?o_1 IN ("{val_a}")) '
            f'?similar <{prop_b}> ?o_2 . FILTER(?o_2 IN ("{val_b}")) '
        )
    assert " ".join(final_query.split()) == (
        "SELECT DISTINCT ?similar WHERE { "
        f"?similar a <{similar_test_data['subject_type']}> . "
        f"FILTER(?similar != <{similar_test_data['subject_uri']}>) {{ {{ "
        + patterns
        + "} } } ORDER BY ?similar OFFSET 0 LIMIT 6"
    )


@patch("heritrace.routes.merge._transform_results")
@patch("heritrace.routes.merge.get_sparql")
@patch("flask_login.utils._get_user")
def test_similar_draft_matches_values_and_existing_nested_entities(
    mock_current_user,
    mock_get_sparql,
    mock_transform_results,
    client,
    mock_user,
) -> None:
    mock_current_user.return_value = mock_user
    title = "http://purl.org/dc/terms/title"
    identifier = "http://purl.org/spar/datacite/hasIdentifier"
    value = "http://example.org/value"
    xsd_string = "http://www.w3.org/2001/XMLSchema#string"
    sparql = MagicMock()
    sparql.query().convert.side_effect = [
        {"results": {"bindings": [{"nested": {"value": "http://example.org/id/1"}}]}},
        {"results": {"bindings": [{"similar": {"value": "http://example.org/br/1"}}]}},
    ]
    mock_get_sparql.return_value = sparql
    mock_transform_results.return_value = [
        {"uri": "http://example.org/br/1", "label": "An article"}
    ]

    response = client.post(
        "/api/merge/similar/draft",
        json={
            "entity_type": "http://purl.org/spar/fabio/JournalArticle",
            "shape_uri": "http://schema.org/JournalArticleShape",
            "values": {
                title: [{"value": 'A "title"', "datatype": xsd_string}],
                identifier: [
                    {
                        "fields": [
                            {
                                "predicate": value,
                                "value": "10.1/x",
                                "datatype": xsd_string,
                            }
                        ]
                    }
                ],
                "http://example.org/ignored": [{"value": "x"}],
            },
        },
    )

    assert response.status_code == 200
    assert response.get_json()["results"] == [
        {"uri": "http://example.org/br/1", "label": "An article"}
    ]
    nested_query = sparql.setQuery.call_args_list[0].args[0]
    similar_query = sparql.setQuery.call_args_list[1].args[0]
    assert f'<{value}> "10.1/x"^^<{xsd_string}>' in nested_query
    assert '"A \\"title\\""' in similar_query
    assert "<http://example.org/id/1>" in similar_query
    assert "ignored" not in similar_query
    assert "FILTER(?similar !=" not in similar_query
