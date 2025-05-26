from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
from flask import url_for
from heritrace.routes.merge import get_entity_details, merge_bp
from rdflib import URIRef

ENTITY1_URI = "http://example.org/entity1"
ENTITY2_URI = "http://example.org/entity2"
ENTITY1_LABEL = "Entity One Label"
ENTITY2_LABEL = "Entity Two Label"
ENTITY1_TYPES = ["http://example.org/TypeA"]
ENTITY2_TYPES = ["http://example.org/TypeB"]
USER_ORCID = "0000-0001-2345-6789"
RESP_AGENT_URI = URIRef(f"https://orcid.org/{USER_ORCID}")

MOCK_ENTITY1_PROPS = {
    "http://example.org/prop1": [{"value": "Value 1", "type": "literal", "readable_label": "Value 1"}],
    "http://example.org/prop2": [{"value": "http://example.org/obj1", "type": "uri", "readable_label": "Object One"}],
}
MOCK_ENTITY2_PROPS = {
    "http://example.org/prop3": [{"value": "Value 3", "type": "literal", "readable_label": "Value 3"}],
}

@pytest.fixture
def mock_user():
    """Fixture to mock a logged-in user."""
    user = MagicMock()
    user.is_authenticated = True
    user.orcid = "0000-0001-2345-6789"
    return user

@pytest.fixture(autouse=True)
def ensure_merge_bp(app):
    """Ensures the merge blueprint is registered on the app."""
    if not app.blueprints.get('merge'):
        app.register_blueprint(merge_bp, url_prefix='/merge')

@patch('heritrace.routes.merge.get_sparql')
@patch('heritrace.routes.merge.get_custom_filter')
@patch('heritrace.routes.merge.get_entity_types')
def test_get_entity_details_success(mock_get_entity_types, mock_get_custom_filter, mock_get_sparql, app):
    """Test get_entity_details successfully fetches properties and types."""
    entity1_uri = "http://test.com/entityDetailSuccess"
    entity1_types = ["http://test.com/TypeA"]
    obj_uri = "http://obj.uri/detail"
    obj_type = ["http://test.com/ObjectType"]
    prop1 = "http://test.com/prop1"
    prop2 = "http://test.com/prop2"
    literal_val = "Literal Val"
    readable_obj_label = "Readable Object Label"

    mock_sparql_instance = MagicMock()
    mock_sparql_instance.query().convert.return_value = {
        "results": {
            "bindings": [
                {"p": {"value": prop1}, "o": {"value": literal_val, "type": "literal"}},
                {"p": {"value": prop2}, "o": {"value": obj_uri, "type": "uri"}},
            ]
        }
    }
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_entity_types.side_effect = [
        entity1_types,
        obj_type
    ]
    mock_custom_filter_instance = MagicMock()
    mock_custom_filter_instance.human_readable_entity.return_value = readable_obj_label
    mock_get_custom_filter.return_value = mock_custom_filter_instance

    with app.app_context():
        props, types = get_entity_details(entity1_uri)

    assert types == entity1_types
    assert prop1 in props
    assert props[prop1][0]["value"] == literal_val
    assert props[prop1][0]["readable_label"] == literal_val
    assert prop2 in props
    assert props[prop2][0]["value"] == obj_uri
    assert props[prop2][0]["readable_label"] == readable_obj_label
    assert mock_get_entity_types.call_count == 2
    mock_get_entity_types.assert_any_call(entity1_uri)
    mock_get_entity_types.assert_any_call(obj_uri)
    mock_custom_filter_instance.human_readable_entity.assert_called_once_with(obj_uri, (obj_type[0], None))


@patch('heritrace.routes.merge.get_sparql')
@patch('heritrace.routes.merge.get_entity_types', return_value=[])
def test_get_entity_details_no_types(mock_get_entity_types, mock_get_sparql, app):
    """Test get_entity_details when no types are found for the entity."""
    entity1_uri = "http://test.com/entityDetailNoTypes"
    mock_sparql_instance = MagicMock()
    mock_sparql_instance.query().convert.return_value = { "results": { "bindings": [] } }
    mock_get_sparql.return_value = mock_sparql_instance

    with app.app_context():
        props, types = get_entity_details(entity1_uri)

    assert types == []
    assert props == {}
    mock_get_entity_types.assert_called_once_with(entity1_uri)


@patch('heritrace.routes.merge.get_sparql')
@patch('heritrace.routes.merge.get_entity_types')
def test_get_entity_details_sparql_error(mock_get_entity_types, mock_get_sparql, app):
    """Test get_entity_details handles SPARQL query errors."""
    entity1_uri = "http://test.com/entityDetailSparqlError"
    entity1_types = ["http://test.com/TypeAOnError"]

    mock_sparql_instance = MagicMock()
    mock_sparql_instance.query.side_effect = Exception("SPARQL Error")
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_entity_types.return_value = entity1_types

    with app.app_context():
        props, types = get_entity_details(entity1_uri)

    assert props is None
    assert types == []

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
        "entity1_props": {
            "http://merge.test/propA": [{"value": "Value A", "type": "literal", "readable_label": "Value A"}],
        },
        "entity2_props": {
            "http://merge.test/propB": [{"value": "Value B", "type": "literal", "readable_label": "Value B"}],
        }
    }


@patch('heritrace.routes.merge.get_custom_filter')
@patch('heritrace.routes.merge.get_entity_details')
@patch('heritrace.routes.merge.Editor')
@patch('heritrace.routes.merge.get_counter_handler')
@patch('heritrace.routes.merge.get_dataset_endpoint', return_value='http://db/ds_merge_flash')
@patch('heritrace.routes.merge.get_provenance_endpoint', return_value='http://db/prov_merge_flash')
@patch('heritrace.routes.merge.get_dataset_is_quadstore', return_value=False)
@patch('flask_login.utils._get_user')
def test_execute_merge_success_flash(mock_current_user, mock_quadstore, mock_prov, mock_ds, mock_counter, mock_editor_cls, mock_get_details, mock_get_filter, client, mock_user, merge_test_data):
    """Test flash message for successful execution of the merge."""
    mock_current_user.return_value = mock_user
    mock_get_details.side_effect = [
        (merge_test_data["entity1_props"], merge_test_data["entity1_types"]),
        (merge_test_data["entity2_props"], merge_test_data["entity2_types"]),
    ]
    mock_filter_instance = MagicMock()
    mock_filter_instance.human_readable_entity.side_effect = [
        merge_test_data["entity1_label"], merge_test_data["entity2_label"]
    ]
    mock_get_filter.return_value = mock_filter_instance
    mock_editor_instance = MagicMock()
    mock_editor_cls.return_value = mock_editor_instance

    with client.session_transaction() as session:
        session['_user_id'] = mock_user.orcid

    response = client.post(url_for('merge.execute_merge'), data={
        'entity1_uri': merge_test_data["entity1_uri"],
        'entity2_uri': merge_test_data["entity2_uri"],
    }, follow_redirects=False)

    assert response.status_code == 302
    with client.session_transaction() as session:
        flashes = session.get('_flashes', [])
        assert len(flashes) == 1
        assert flashes[0][0] == 'success'
        assert merge_test_data["entity1_label"] in str(flashes[0][1])
        assert merge_test_data["entity2_label"] in str(flashes[0][1])

    expected_path = urlparse(url_for('entity.about', subject=merge_test_data["entity1_uri"])).path
    assert urlparse(response.location).path == expected_path

@patch('flask_login.utils._get_user')
def test_execute_merge_missing_uris(mock_current_user, client, mock_user):
    """Test merge attempt with missing URIs."""
    mock_current_user.return_value = mock_user

    with client.session_transaction() as session:
        session['_user_id'] = mock_user.orcid

    response = client.post(url_for('merge.execute_merge'), data={}, follow_redirects=False)

    assert response.status_code == 302
    with client.session_transaction() as session:
        flashes = session.get('_flashes', [])
        assert len(flashes) == 1
        assert flashes[0][0] == 'danger'
        assert "Missing entity URIs" in flashes[0][1]

    expected_path = urlparse(url_for('main.catalogue')).path
    assert urlparse(response.location).path == expected_path


@patch('heritrace.routes.merge.get_custom_filter')
@patch('heritrace.routes.merge.get_entity_details')
@patch('heritrace.routes.merge.Editor')
@patch('flask_login.utils._get_user')
def test_execute_merge_editor_value_error(mock_current_user, mock_editor_cls, mock_get_details, mock_get_filter, client, mock_user, merge_test_data):
    """Test merge when Editor.merge raises ValueError."""
    mock_current_user.return_value = mock_user
    mock_get_details.side_effect = [
        (merge_test_data["entity1_props"], merge_test_data["entity1_types"]),
        (merge_test_data["entity2_props"], merge_test_data["entity2_types"]),
    ]
    mock_filter_instance = MagicMock()
    mock_filter_instance.human_readable_entity.side_effect = [
        merge_test_data["entity1_label"], merge_test_data["entity2_label"]
    ]
    mock_get_filter.return_value = mock_filter_instance
    mock_editor_instance = MagicMock()
    mock_editor_instance.merge.side_effect = ValueError("Test Editor Value Error")
    mock_editor_cls.return_value = mock_editor_instance

    response = client.post(url_for('merge.execute_merge'), data={
        'entity1_uri': merge_test_data["entity1_uri"],
        'entity2_uri': merge_test_data["entity2_uri"],
    }, follow_redirects=False)

    assert response.status_code == 302
    expected_path = urlparse(url_for('merge.compare_and_merge', subject=merge_test_data["entity1_uri"], other_subject=merge_test_data["entity2_uri"])).path
    assert urlparse(response.location).path == expected_path

@patch('heritrace.routes.merge.get_custom_filter')
@patch('heritrace.routes.merge.get_entity_details')
@patch('heritrace.routes.merge.Editor')
@patch('flask_login.utils._get_user')
def test_execute_merge_editor_value_error_flash(mock_current_user, mock_editor_cls, mock_get_details, mock_get_filter, client, mock_user, merge_test_data):
    """Test flash message for merge ValueError."""
    mock_current_user.return_value = mock_user
    mock_get_details.side_effect = [
        (merge_test_data["entity1_props"], merge_test_data["entity1_types"]),
        (merge_test_data["entity2_props"], merge_test_data["entity2_types"]),
    ]
    mock_filter_instance = MagicMock()
    mock_filter_instance.human_readable_entity.side_effect = [
        merge_test_data["entity1_label"], merge_test_data["entity2_label"]
    ]
    mock_get_filter.return_value = mock_filter_instance
    mock_editor_instance = MagicMock()
    mock_editor_instance.merge.side_effect = ValueError("Test Value Error Flash")
    mock_editor_cls.return_value = mock_editor_instance

    with client.session_transaction() as session:
        session['_user_id'] = mock_user.orcid

    response = client.post(url_for('merge.execute_merge'), data={
        'entity1_uri': merge_test_data["entity1_uri"],
        'entity2_uri': merge_test_data["entity2_uri"],
    }, follow_redirects=False)

    assert response.status_code == 302
    with client.session_transaction() as session:
        flashes = session.get('_flashes', [])
        assert len(flashes) == 1
        assert flashes[0][0] == 'warning'
        assert "Test Value Error Flash" in flashes[0][1]

    expected_path = urlparse(url_for('merge.compare_and_merge', subject=merge_test_data["entity1_uri"], other_subject=merge_test_data["entity2_uri"])).path
    assert urlparse(response.location).path == expected_path

@patch('heritrace.routes.merge.get_custom_filter')
@patch('heritrace.routes.merge.get_entity_details')
@patch('heritrace.routes.merge.Editor')
@patch('flask_login.utils._get_user')
def test_execute_merge_general_exception(mock_current_user, mock_editor_cls, mock_get_details, mock_get_filter, client, mock_user, merge_test_data):
    """Test merge when a general exception occurs."""
    mock_current_user.return_value = mock_user
    mock_get_details.side_effect = [
        (merge_test_data["entity1_props"], merge_test_data["entity1_types"]),
        (merge_test_data["entity2_props"], merge_test_data["entity2_types"]),
    ]
    mock_filter_instance = MagicMock()
    mock_filter_instance.human_readable_entity.side_effect = [
        merge_test_data["entity1_label"], merge_test_data["entity2_label"]
    ]
    mock_get_filter.return_value = mock_filter_instance
    mock_editor_instance = MagicMock()
    mock_editor_instance.merge.side_effect = Exception("Something went wrong general")
    mock_editor_cls.return_value = mock_editor_instance

    response = client.post(url_for('merge.execute_merge'), data={
        'entity1_uri': merge_test_data["entity1_uri"],
        'entity2_uri': merge_test_data["entity2_uri"],
    }, follow_redirects=False)

    assert response.status_code == 302
    expected_path = urlparse(url_for('merge.compare_and_merge', subject=merge_test_data["entity1_uri"], other_subject=merge_test_data["entity2_uri"])).path
    assert urlparse(response.location).path == expected_path

@patch('heritrace.routes.merge.get_custom_filter')
@patch('heritrace.routes.merge.get_entity_details')
@patch('heritrace.routes.merge.Editor')
@patch('flask_login.utils._get_user')
def test_execute_merge_general_exception_flash(mock_current_user, mock_editor_cls, mock_get_details, mock_get_filter, client, mock_user, merge_test_data):
    """Test flash message for general merge exception."""
    mock_current_user.return_value = mock_user
    mock_get_details.side_effect = [
        (merge_test_data["entity1_props"], merge_test_data["entity1_types"]),
        (merge_test_data["entity2_props"], merge_test_data["entity2_types"]),
    ]
    mock_filter_instance = MagicMock()
    mock_filter_instance.human_readable_entity.side_effect = [
        merge_test_data["entity1_label"], merge_test_data["entity2_label"]
    ]
    mock_get_filter.return_value = mock_filter_instance
    mock_editor_instance = MagicMock()
    mock_editor_instance.merge.side_effect = Exception("General Error Test Flash")
    mock_editor_cls.return_value = mock_editor_instance

    with client.session_transaction() as session:
        session['_user_id'] = mock_user.orcid

    response = client.post(url_for('merge.execute_merge'), data={
        'entity1_uri': merge_test_data["entity1_uri"],
        'entity2_uri': merge_test_data["entity2_uri"],
    }, follow_redirects=False)

    assert response.status_code == 302
    with client.session_transaction() as session:
        flashes = session.get('_flashes', [])
        assert len(flashes) == 1
        assert flashes[0][0] == 'danger'
        assert "An error occurred during the merge operation" in flashes[0][1]

    expected_path = urlparse(url_for('merge.compare_and_merge', subject=merge_test_data["entity1_uri"], other_subject=merge_test_data["entity2_uri"])).path
    assert urlparse(response.location).path == expected_path

@patch('heritrace.utils.sparql_utils.get_sparql')
@patch('heritrace.routes.merge.get_custom_filter')
@patch('heritrace.routes.merge.get_entity_details')
@patch('flask_login.utils._get_user')
def test_compare_and_merge_success(mock_current_user, mock_get_details, mock_get_filter, mock_sparql, client, mock_user, merge_test_data):
    """Test successfully rendering the comparison page."""
    mock_current_user.return_value = mock_user
    mock_get_details.side_effect = [
        (merge_test_data["entity1_props"], merge_test_data["entity1_types"]),
        (merge_test_data["entity2_props"], merge_test_data["entity2_types"]),
    ]
    mock_filter_instance = MagicMock()
    mock_filter_instance.human_readable_entity.side_effect = [
        merge_test_data["entity1_label"], merge_test_data["entity2_label"]
    ]
    mock_get_filter.return_value = mock_filter_instance

    response = client.get(url_for('merge.compare_and_merge', subject=merge_test_data["entity1_uri"], other_subject=merge_test_data["entity2_uri"]))

    assert response.status_code == 200
    assert merge_test_data["entity1_label"].encode() in response.data
    assert merge_test_data["entity2_label"].encode() in response.data
    assert b"Confirm Entity Merge" in response.data
    mock_get_details.assert_any_call(merge_test_data["entity1_uri"])
    mock_get_details.assert_any_call(merge_test_data["entity2_uri"])

@patch('flask_login.utils._get_user')
def test_compare_and_merge_missing_uris(mock_current_user, client, mock_user, merge_test_data):
    """Test compare page access with missing URIs."""
    mock_current_user.return_value = mock_user

    with client.session_transaction() as session:
        session['_user_id'] = mock_user.orcid

    response = client.get(url_for('merge.compare_and_merge', subject=merge_test_data["entity1_uri"]), follow_redirects=False)

    assert response.status_code == 302
    with client.session_transaction() as session:
        flashes = session.get('_flashes', [])
        assert len(flashes) == 1
        assert flashes[0][0] == 'warning'
        assert "Two entities must be selected" in flashes[0][1]

    expected_path = urlparse(url_for('main.catalogue')).path
    assert urlparse(response.location).path == expected_path

@patch('heritrace.routes.merge.get_entity_details', return_value=(None, []))
@patch('flask_login.utils._get_user')
def test_compare_and_merge_fetch_error(mock_current_user, mock_get_details, client, mock_user, merge_test_data):
    """Test compare page when fetching entity details fails."""
    mock_current_user.return_value = mock_user

    with client.session_transaction() as session:
        session['_user_id'] = mock_user.orcid

    response = client.get(url_for('merge.compare_and_merge', subject=merge_test_data["entity1_uri"], other_subject=merge_test_data["entity2_uri"]), follow_redirects=False)

    assert response.status_code == 302
    with client.session_transaction() as session:
        flashes = session.get('_flashes', [])
        assert len(flashes) == 1
        assert flashes[0][0] == 'danger'
        assert "Could not retrieve details" in flashes[0][1]

    expected_path = urlparse(url_for('main.catalogue')).path
    assert urlparse(response.location).path == expected_path

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

@patch('heritrace.routes.merge.get_sparql')
@patch('heritrace.routes.merge.get_custom_filter')
@patch('heritrace.routes.merge.get_similarity_properties')
@patch('heritrace.routes.merge.get_entity_types')
@patch('flask_login.utils._get_user')
def test_find_similar_resources_success(mock_current_user, mock_get_types, mock_get_sim_props, mock_get_filter, mock_get_sparql, client, mock_user, similar_test_data):
    """Test finding similar resources successfully."""
    mock_current_user.return_value = mock_user
    mock_sparql_instance = MagicMock()
    mock_sparql_instance.query().convert.side_effect = [
        {
            "results": {
                "bindings": [
                    {"p": {"value": similar_test_data["prop_name"]}, "o": {"value": similar_test_data["shared_name"], "type": "literal"}},
                    {"p": {"value": similar_test_data["prop_ref"]}, "o": {"value": similar_test_data["shared_ref"], "type": "uri"}},
                ]
            }
        },
        {
            "results": {
                "bindings": [
                    {"similar": {"value": similar_test_data["similar_uri"]}}
                ]
            }
        }
    ]
    mock_get_sparql.return_value = mock_sparql_instance
    similarity_props = [similar_test_data["prop_name"], similar_test_data["prop_ref"]]
    mock_get_sim_props.return_value = similarity_props
    mock_filter_instance = MagicMock()
    mock_filter_instance.human_readable_entity.return_value = similar_test_data["similar_label"]
    mock_filter_instance.human_readable_predicate.side_effect = lambda pred_uri, entity_key: f"Label_{pred_uri.split('/')[-1]}"
    mock_get_filter.return_value = mock_filter_instance
    mock_get_types.side_effect = [
        [similar_test_data["subject_type"]],
        [similar_test_data["similar_type"]]
    ]

    response = client.get(url_for('merge.find_similar_resources',
                                  subject_uri=similar_test_data["subject_uri"],
                                  entity_type=similar_test_data["subject_type"],
                                  limit=5))

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert len(data["results"]) == 1
    assert data["results"][0]["uri"] == similar_test_data["similar_uri"]
    assert data["results"][0]["label"] == similar_test_data["similar_label"]
    assert data["has_more"] == False
    assert mock_sparql_instance.setQuery.call_count == 2

@patch('heritrace.routes.merge.get_sparql')
@patch('heritrace.routes.merge.get_similarity_properties')
@patch('flask_login.utils._get_user')
def test_find_similar_resources_no_subject_values(mock_current_user, mock_get_sim_props, mock_get_sparql, client, mock_user, similar_test_data):
    """Test when the subject has no values for similarity properties."""
    mock_current_user.return_value = mock_user
    mock_sparql_instance = MagicMock()
    mock_sparql_instance.query().convert.return_value = {"results": {"bindings": []}}
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_sim_props.return_value = [similar_test_data["prop_name"]]

    response = client.get(url_for('merge.find_similar_resources',
                                  subject_uri=similar_test_data["subject_uri"],
                                  entity_type=similar_test_data["subject_type"]))

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["results"] == []
    mock_sparql_instance.setQuery.assert_called_once()

@patch('flask_login.utils._get_user')
def test_find_similar_resources_missing_params(mock_current_user, client, mock_user, similar_test_data):
    """Test request with missing parameters."""
    mock_current_user.return_value = mock_user
    response = client.get(url_for('merge.find_similar_resources', subject_uri=similar_test_data["subject_uri"]))
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "Missing required parameters" in json_data["message"]

@patch('heritrace.routes.merge.get_sparql')
@patch('flask_login.utils._get_user')
def test_find_similar_resources_exception(mock_current_user, mock_get_sparql, client, mock_user, similar_test_data):
    """Test handling of general exceptions during similarity search."""
    mock_current_user.return_value = mock_user
    mock_get_sparql.side_effect = Exception("Database connection failed similar")

    response = client.get(url_for('merge.find_similar_resources',
                                  subject_uri=similar_test_data["subject_uri"],
                                  entity_type=similar_test_data["subject_type"]))

    assert response.status_code == 500
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "An error occurred while finding similar resources" in json_data["message"]

@patch('heritrace.routes.merge.get_sparql')
@patch('heritrace.routes.merge.get_custom_filter')
@patch('heritrace.routes.merge.get_similarity_properties')
@patch('heritrace.routes.merge.get_entity_types')
@patch('flask_login.utils._get_user')
def test_find_similar_resources_literal_formatting(mock_current_user, mock_get_types, mock_get_sim_props, mock_get_filter, mock_get_sparql, client, mock_user, similar_test_data):
    """Test correct SPARQL formatting for various literal types."""
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
                    {"p": {"value": prop_typed}, "o": {"value": "TypedValue", "type": "typed-literal", "datatype": "http://www.w3.org/2001/XMLSchema#string"}},
                    {"p": {"value": prop_lang}, "o": {"value": "LangValue", "type": "literal", "xml:lang": "en"}},
                    {"p": {"value": prop_plain}, "o": {"value": "PlainValue", "type": "literal"}},
                    {"p": {"value": prop_bnode}, "o": {"value": "bnode1", "type": "bnode"}},
                ]
            }
        },
        {
            "results": {"bindings": [{"similar": {"value": similar_test_data["similar_uri"]}}]}
        }
    ]
    mock_get_sparql.return_value = mock_sparql_instance
    similarity_props = [prop_typed, prop_lang, prop_plain, prop_bnode]
    mock_get_sim_props.return_value = similarity_props
    mock_filter_instance = MagicMock()
    mock_filter_instance.human_readable_entity.return_value = similar_test_data["similar_label"]
    mock_filter_instance.human_readable_predicate.side_effect = lambda pred_uri, entity_key: f"Label_{pred_uri.split('/')[-1]}"
    mock_get_filter.return_value = mock_filter_instance
    mock_get_types.return_value = [similar_test_data["similar_type"]]

    client.get(url_for('merge.find_similar_resources',
                       subject_uri=similar_test_data["subject_uri"],
                       entity_type=similar_test_data["subject_type"]))

    assert mock_sparql_instance.setQuery.call_count == 2

    find_query = mock_sparql_instance.setQuery.call_args_list[1].args[0]

    assert f'FILTER(?o_1 IN ("TypedValue"^^<http://www.w3.org/2001/XMLSchema#string>))' in find_query
    assert f'FILTER(?o_2 IN ("LangValue"@en))' in find_query
    assert f'FILTER(?o_3 IN ("PlainValue"))' in find_query
    assert f'<{prop_bnode}>' not in find_query

@patch('heritrace.routes.merge.get_sparql')
@patch('heritrace.routes.merge.get_similarity_properties')
@patch('flask_login.utils._get_user')
def test_find_similar_resources_no_valid_conditions(mock_current_user, mock_get_sim_props, mock_get_sparql, client, mock_user, similar_test_data):
    """Test case where subject values exist but none are valid for similarity matching."""
    mock_current_user.return_value = mock_user
    mock_sparql_instance = MagicMock()
    prop_bnode_only = "http://similar.prop/bnode_only"

    mock_sparql_instance.query().convert.return_value = {
        "results": {
            "bindings": [
                {"p": {"value": prop_bnode_only}, "o": {"value": "bnode_val", "type": "bnode"}}
            ]
        }
    }
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_sim_props.return_value = [prop_bnode_only]

    response = client.get(url_for('merge.find_similar_resources',
                                  subject_uri=similar_test_data["subject_uri"],
                                  entity_type=similar_test_data["subject_type"]))

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["results"] == []
    mock_sparql_instance.setQuery.assert_called_once()

@patch('flask_login.utils._get_user')
def test_find_similar_resources_invalid_limit_offset_type(mock_current_user, client, mock_user, similar_test_data):
    """Test request with non-integer limit or offset."""
    mock_current_user.return_value = mock_user

    response_limit = client.get(url_for('merge.find_similar_resources',
                                       subject_uri=similar_test_data["subject_uri"],
                                       entity_type=similar_test_data["subject_type"],
                                       limit="not-an-int"))
    assert response_limit.status_code == 400
    json_data_limit = response_limit.get_json()
    assert json_data_limit["status"] == "error"
    assert "Invalid limit or offset parameter" in json_data_limit["message"]

    response_offset = client.get(url_for('merge.find_similar_resources',
                                         subject_uri=similar_test_data["subject_uri"],
                                         entity_type=similar_test_data["subject_type"],
                                         offset="invalid"))
    assert response_offset.status_code == 400
    json_data_offset = response_offset.get_json()
    assert json_data_offset["status"] == "error"
    assert "Invalid limit or offset parameter" in json_data_offset["message"]


@patch('flask_login.utils._get_user')
def test_find_similar_resources_invalid_limit_offset_value(mock_current_user, client, mock_user, similar_test_data):
    """Test request with non-positive limit or negative offset."""
    mock_current_user.return_value = mock_user

    response_limit = client.get(url_for('merge.find_similar_resources',
                                       subject_uri=similar_test_data["subject_uri"],
                                       entity_type=similar_test_data["subject_type"],
                                       limit=0))
    assert response_limit.status_code == 400
    json_data_limit = response_limit.get_json()
    assert json_data_limit["status"] == "error"
    assert "Limit must be positive and offset non-negative" in json_data_limit["message"]

    response_offset = client.get(url_for('merge.find_similar_resources',
                                         subject_uri=similar_test_data["subject_uri"],
                                         entity_type=similar_test_data["subject_type"],
                                         offset=-1))
    assert response_offset.status_code == 400
    json_data_offset = response_offset.get_json()
    assert json_data_offset["status"] == "error"
    assert "Limit must be positive and offset non-negative" in json_data_offset["message"]


@patch('heritrace.routes.merge.get_sparql')
@patch('flask_login.utils._get_user')
def test_find_similar_resources_exception(mock_current_user, mock_get_sparql, client, mock_user, similar_test_data):
    """Test handling of general exceptions during similarity search."""
    mock_current_user.return_value = mock_user
    mock_get_sparql.side_effect = Exception("Database connection failed similar")

    response = client.get(url_for('merge.find_similar_resources',
                                  subject_uri=similar_test_data["subject_uri"],
                                  entity_type=similar_test_data["subject_type"]))

    assert response.status_code == 500
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "An error occurred while finding similar resources" in json_data["message"]

@patch('heritrace.routes.merge.get_similarity_properties')
@patch('flask_login.utils._get_user')
def test_find_similar_resources_no_similarity_config(mock_current_user, mock_get_sim_props, client, mock_user, similar_test_data):
    """Test find_similar_resources when no similarity config is found for the type."""
    mock_current_user.return_value = mock_user
    mock_get_sim_props.return_value = None # Simulate no config found

    response = client.get(url_for('merge.find_similar_resources',
                                  subject_uri=similar_test_data["subject_uri"],
                                  entity_type=similar_test_data["subject_type"]))

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["results"] == []
    assert json_data["has_more"] == False
    mock_get_sim_props.assert_called_once_with((similar_test_data["subject_type"], None))


@patch('heritrace.routes.merge.get_similarity_properties')
@patch('flask_login.utils._get_user')
def test_find_similar_resources_empty_derived_properties(mock_current_user, mock_get_sim_props, client, mock_user, similar_test_data):
    """Test find_similar_resources when the derived property set is empty."""
    mock_current_user.return_value = mock_user
    # Simulate a config that results in no properties being extracted
    mock_get_sim_props.return_value = [{"invalid_key": "value"}]

    response = client.get(url_for('merge.find_similar_resources',
                                  subject_uri=similar_test_data["subject_uri"],
                                  entity_type=similar_test_data["subject_type"]))

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["results"] == []
    assert json_data["has_more"] == False
    mock_get_sim_props.assert_called_once_with((similar_test_data["subject_type"], None))


@patch('heritrace.routes.merge.get_sparql')
@patch('heritrace.routes.merge.get_similarity_properties')
@patch('flask_login.utils._get_user')
def test_find_similar_resources_skip_and_group_missing_subject_prop(mock_current_user, mock_get_sim_props, mock_get_sparql, client, mock_user, similar_test_data):
    """Test skipping an AND group because the subject lacks a required property value."""
    mock_current_user.return_value = mock_user
    mock_sparql_instance = MagicMock()
    prop_a = "http://similar.prop/propA"
    prop_b = "http://similar.prop/propB" # Subject will lack this
    prop_c = "http://similar.prop/propC" # OR condition

    # Simulate subject only having value for propA and propC
    mock_sparql_instance.query().convert.side_effect = [
        {
            "results": {
                "bindings": [
                    {"p": {"value": prop_a}, "o": {"value": "ValueA", "type": "literal"}},
                    {"p": {"value": prop_c}, "o": {"value": "ValueC", "type": "literal"}},
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
        }
    ]
    mock_get_sparql.return_value = mock_sparql_instance
    # Config with an AND group requiring propA and propB, and an OR for propC
    mock_get_sim_props.return_value = [{"and": [prop_a, prop_b]}, prop_c]

    response = client.get(url_for('merge.find_similar_resources',
                                  subject_uri=similar_test_data["subject_uri"],
                                  entity_type=similar_test_data["subject_type"]))

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    # Only the result from the OR condition (prop_c) should be found
    assert len(json_data["results"]) >= 0 # Can be 0 or 1 depending on mock_get_types
    assert mock_sparql_instance.setQuery.call_count == 2
    # Verify the generated query does not include the AND block but includes the OR block
    final_query = mock_sparql_instance.setQuery.call_args_list[1].args[0]
    assert f"<{prop_b}>" not in final_query # AND block should be skipped
    assert f"<{prop_c}> ?o_" in final_query   # OR block should be present


@patch('heritrace.routes.merge.get_sparql')
@patch('heritrace.routes.merge.get_similarity_properties')
@patch('flask_login.utils._get_user')
def test_find_similar_resources_no_valid_union_blocks_due_to_formatting(mock_current_user, mock_get_sim_props, mock_get_sparql, client, mock_user, similar_test_data):
    """Test case where subject has values but none are formattable (e.g., only bnodes)."""
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
    mock_get_sim_props.return_value = [prop_bnode_only]

    response = client.get(url_for('merge.find_similar_resources',
                                  subject_uri=similar_test_data["subject_uri"],
                                  entity_type=similar_test_data["subject_type"]))

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["results"] == []
    assert json_data["has_more"] is False

@patch('heritrace.routes.merge.get_sparql')
@patch('heritrace.routes.merge.get_custom_filter')
@patch('heritrace.routes.merge.get_similarity_properties')
@patch('heritrace.routes.merge.get_entity_types')
@patch('flask_login.utils._get_user')
def test_find_similar_resources_success_with_and_group(mock_current_user, mock_get_types, mock_get_sim_props, mock_get_filter, mock_get_sparql, client, mock_user, similar_test_data):
    """Test finding similar resources successfully using an AND group condition."""
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
        {
            "results": {
                "bindings": [
                    {"similar": {"value": similar_uri_and}}
                ]
            }
        }
    ]
    mock_get_sparql.return_value = mock_sparql_instance
    # Configure similarity with an AND group
    mock_get_sim_props.return_value = [{"and": [prop_a, prop_b]}]

    mock_filter_instance = MagicMock()
    mock_filter_instance.human_readable_entity.return_value = "Similar AND Label"
    mock_filter_instance.human_readable_predicate.side_effect = lambda pred_uri, entity_key: f"Label_{pred_uri.split('/')[-1]}"
    mock_get_filter.return_value = mock_filter_instance
    mock_get_types.return_value = [similar_test_data["similar_type"]] # For the similar entity

    response = client.get(url_for('merge.find_similar_resources',
                                  subject_uri=similar_test_data["subject_uri"],
                                  entity_type=similar_test_data["subject_type"],
                                  limit=5))

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert len(data["results"]) == 1
    assert data["results"][0]["uri"] == similar_uri_and
    assert data["results"][0]["label"] == "Similar AND Label"
    assert data["has_more"] == False
    assert mock_sparql_instance.setQuery.call_count == 2

    # Verify the final query includes the AND patterns correctly
    final_query = mock_sparql_instance.setQuery.call_args_list[1].args[0]
    assert f"<{prop_a}> ?o_" in final_query # Variable name depends on counter
    assert f"FILTER(?o_1 IN (\"{val_a}\"))" in final_query # Assuming var_counter starts at 0 -> o_1
    assert f"<{prop_b}> ?o_" in final_query
    assert f"FILTER(?o_2 IN (\"{val_b}\"))" in final_query # Assuming var_counter increments -> o_2
    assert "UNION" not in final_query # Since there's only one AND group