import json
from unittest.mock import MagicMock, patch

import pytest
from flask import url_for
from rdflib import XSD, URIRef


@pytest.fixture
def mock_form_fields():
    return {
        ("http://example.org/Person", None): {
            "http://example.org/hasName": [{
                "datatypes": [str(XSD.string)],
                "min": 1,
                "max": 1
            }],
            "http://example.org/hasAddress": [{
                "nodeShape": "http://example.org/AddressShape",
                "subjectShape": "http://example.org/PersonShape",
                "orderedBy": "http://example.org/nextAddress"
            }],
            "http://example.org/hasContact": [{
                "objectClass": "http://example.org/Contact"
            }]
        },
        ("http://example.org/Address", None): {
            "http://example.org/street": [{
                "datatypes": [str(XSD.string)],
                "min": 1
            }]
        }
    }

@pytest.fixture
def mock_editor():
    return MagicMock()

@patch('heritrace.routes.entity.Editor')
@patch('heritrace.routes.entity.get_form_fields')
@patch('heritrace.routes.entity.get_dataset_endpoint')
@patch('heritrace.routes.entity.get_provenance_endpoint')
def test_create_entity_with_shacl(mock_get_prov, mock_get_dataset, mock_get_form_fields, mock_editor, logged_in_client, app, mock_form_fields):
    """Test creating an entity with SHACL validation"""
    # Setup mocks
    mock_get_form_fields.return_value = mock_form_fields
    mock_editor_instance = mock_editor.return_value
    app.config["URI_GENERATOR"] = MagicMock()
    app.config["URI_GENERATOR"].generate_uri.return_value = "http://example.org/test/123"
    
    data = {
        "entity_type": "http://example.org/Person",
        "properties": {
            "http://example.org/hasName": ["John Doe"],
            "http://example.org/hasAddress": [
                {
                    "entity_type": "http://example.org/Address",
                    "shape": "http://example.org/AddressShape",
                    "properties": {
                        "http://example.org/street": ["123 Main St"]
                    }
                }
            ]
        }
    }

    response = logged_in_client.post(
        url_for('entity.create_entity'),
        data={"structured_data": json.dumps(data)}
    )

    assert response.status_code == 200
    assert response.json["status"] == "success"
    
    # Verify editor calls
    mock_editor_instance.preexisting_finished.assert_called_once()
    assert mock_editor_instance.create.call_count >= 3  # At least 3 create calls expected

@patch('heritrace.routes.entity.Editor')
@patch('heritrace.routes.entity.get_form_fields')
def test_create_entity_without_shacl(mock_get_form_fields, mock_editor, logged_in_client, app):
    """Test creating an entity without SHACL validation"""
    # Setup mocks
    mock_get_form_fields.return_value = {}
    mock_editor_instance = mock_editor.return_value
    app.config["URI_GENERATOR"] = MagicMock()
    app.config["URI_GENERATOR"].generate_uri.return_value = "http://example.org/test/123"
    
    data = {
        "entity_type": "http://example.org/Thing",  # Add entity_type since it's required
        "properties": {
            "http://example.org/hasName": [
                {"type": "literal", "value": "John Doe", "datatype": str(XSD.string)},
                {"type": "uri", "value": "http://example.org/names/john"}
            ]
        }
    }

    response = logged_in_client.post(
        url_for('entity.create_entity'),
        data={"structured_data": json.dumps(data)}
    )

    assert response.status_code == 200
    assert response.json["status"] == "success"
    
    # Verify editor calls
    mock_editor_instance.import_entity.assert_called_once()
    mock_editor_instance.preexisting_finished.assert_called_once()
    assert mock_editor_instance.create.call_count >= 2  # At least 2 create calls expected

@patch('heritrace.routes.entity.Editor')
@patch('heritrace.routes.entity.get_form_fields')
def test_create_entity_with_ordered_properties(mock_get_form_fields, mock_editor, logged_in_client, app, mock_form_fields):
    """Test creating an entity with ordered properties"""
    mock_get_form_fields.return_value = {
        ("http://example.org/Person", None): {
            "http://example.org/hasAddress": [{
                "nodeShape": "http://example.org/AddressShape",
                "subjectShape": "http://example.org/PersonShape",
                "orderedBy": "http://example.org/nextAddress"
            }]
        },
        ("http://example.org/Address", None): {
            "http://example.org/street": [{
                "datatypes": [str(XSD.string)],
                "min": 1
            }]
        }
    }
    mock_editor_instance = mock_editor.return_value
    app.config["URI_GENERATOR"] = MagicMock()
    app.config["URI_GENERATOR"].generate_uri.return_value = "http://example.org/test/123"
    
    data = {
        "entity_type": "http://example.org/Person",
        "properties": {
            "http://example.org/hasAddress": [
                {
                    "entity_type": "http://example.org/Address",
                    "shape": "http://example.org/AddressShape",
                    "properties": {
                        "http://example.org/street": ["First St"]
                    }
                },
                {
                    "entity_type": "http://example.org/Address",
                    "shape": "http://example.org/AddressShape",
                    "properties": {
                        "http://example.org/street": ["Second St"]
                    }
                }
            ]
        }
    }

    response = logged_in_client.post(
        url_for('entity.create_entity'),
        data={"structured_data": json.dumps(data)}
    )

    assert response.status_code == 200
    assert response.json["status"] == "success"
    
    # Verify ordered property handling
    create_calls = mock_editor_instance.create.call_args_list
    assert len(create_calls) >= 5  # At least 5 create calls expected (2 addresses + ordering + properties)

@patch('heritrace.routes.entity.Editor')
@patch('heritrace.routes.entity.get_form_fields')
def test_create_entity_with_shape_matching(mock_get_form_fields, mock_editor, logged_in_client, app):
    """Test creating an entity with shape matching validation"""
    # Setup form fields with multiple shapes for the same property
    form_fields = {
        ("http://example.org/Person", None): {
            "http://example.org/hasAddress": [
                {
                    "nodeShape": "http://example.org/HomeAddressShape",
                    "subjectShape": "http://example.org/PersonShape",
                    "min": 1
                },
                {
                    "nodeShape": "http://example.org/WorkAddressShape",
                    "subjectShape": "http://example.org/EmployeeShape",
                    "min": 0
                }
            ]
        },
        ("http://example.org/Address", None): {
            "http://example.org/street": [{
                "datatypes": [str(XSD.string)],
                "min": 1
            }]
        }
    }
    mock_get_form_fields.return_value = form_fields
    mock_editor_instance = mock_editor.return_value
    app.config["URI_GENERATOR"] = MagicMock()
    app.config["URI_GENERATOR"].generate_uri.return_value = "http://example.org/test/123"
    
    # Test with matching shape
    data = {
        "entity_type": "http://example.org/Person",
        "properties": {
            "http://example.org/hasAddress": [
                {
                    "entity_type": "http://example.org/Address",
                    "shape": "http://example.org/PersonShape",  # This should match the first field definition
                    "properties": {
                        "http://example.org/street": ["123 Home St"]
                    }
                }
            ]
        }
    }

    response = logged_in_client.post(
        url_for('entity.create_entity'),
        data={"structured_data": json.dumps(data)}
    )

    assert response.status_code == 200
    assert response.json["status"] == "success"

    # Test with non-matching shape
    data["properties"]["http://example.org/hasAddress"][0]["shape"] = "http://example.org/UnknownShape"
    
    response = logged_in_client.post(
        url_for('entity.create_entity'),
        data={"structured_data": json.dumps(data)}
    )

    assert response.status_code == 200  # Should still succeed as it falls back to first definition
    assert response.json["status"] == "success"

@patch('heritrace.routes.entity.Editor')
@patch('heritrace.routes.entity.get_form_fields')
def test_create_entity_validation_error(mock_get_form_fields, mock_editor, logged_in_client, app, mock_form_fields):
    """Test entity creation with validation errors"""
    # Setup mocks
    mock_get_form_fields.return_value = {
        ("http://example.org/Person", None): {
            "http://example.org/hasName": [{
                "datatypes": [str(XSD.string)],
                "min": 1,
                "max": 1
            }]
        }
    }
    app.config["URI_GENERATOR"] = MagicMock()
    app.config["URI_GENERATOR"].generate_uri.return_value = "http://example.org/test/123"
    
    # Missing required hasName property
    data = {
        "entity_type": "http://example.org/Person",
        "properties": {}
    }

    response = logged_in_client.post(
        url_for('entity.create_entity'),
        data={"structured_data": json.dumps(data)}
    )

    assert response.status_code == 400
    assert response.json["status"] == "error"
    assert len(response.json["errors"]) > 0
        
    assert len(response.json["errors"]) > 0

@patch('heritrace.routes.entity.Editor')
@patch('heritrace.routes.entity.get_form_fields')
def test_create_entity_editor_exception(mock_get_form_fields, mock_editor, logged_in_client, app, mock_form_fields):
    """Test handling of editor exceptions during entity creation"""
    mock_get_form_fields.return_value = mock_form_fields
    mock_editor_instance = mock_editor.return_value
    mock_editor_instance.save.side_effect = Exception("Test error")
    app.config["URI_GENERATOR"] = MagicMock()
    app.config["URI_GENERATOR"].generate_uri.return_value = "http://example.org/test/123"
    
    data = {
        "entity_type": "http://example.org/Person",
        "properties": {
            "http://example.org/hasName": ["John Doe"]
        }
    }

    response = logged_in_client.post(
        url_for('entity.create_entity'),
        data={"structured_data": json.dumps(data)}
    )

    assert response.status_code == 500
    assert response.json["status"] == "error"
    assert "Test error" in response.json["errors"][0]

@patch('heritrace.routes.entity.Editor')
@patch('heritrace.routes.entity.get_form_fields')
def test_create_entity_with_direct_uri_reference(mock_get_form_fields, mock_editor, logged_in_client, app):
    """Test creating an entity with direct URI references to existing entities"""
    # Setup form fields
    form_fields = {
        ("http://example.org/Person", None): {
            "http://example.org/hasAddress": [{
                "nodeShape": "http://example.org/AddressShape",
                "min": 0
            }],
            "http://example.org/hasContact": [{
                "objectClass": "http://example.org/Contact",
                "min": 0
            }]
        }
    }
    mock_get_form_fields.return_value = form_fields
    mock_editor_instance = mock_editor.return_value
    app.config["URI_GENERATOR"] = MagicMock()
    app.config["URI_GENERATOR"].generate_uri.return_value = "http://example.org/test/123"
    
    # Test data with explicit metadata for existing entity references
    data = {
        "entity_type": "http://example.org/Person",
        "properties": {
            "http://example.org/hasAddress": [
                {
                    "is_existing_entity": True,
                    "entity_uri": "http://example.org/addresses/existing-address-1"
                },
                {
                    "is_existing_entity": True,
                    "entity_uri": "http://example.org/addresses/existing-address-2"
                }
            ],
            "http://example.org/hasContact": [
                {
                    "is_existing_entity": True,
                    "entity_uri": "http://example.org/contacts/existing-contact"
                }
            ]
        }
    }

    response = logged_in_client.post(
        url_for('entity.create_entity'),
        data={"structured_data": json.dumps(data)}
    )

    assert response.status_code == 200
    assert response.json["status"] == "success"

    # Verify that editor.create was called with URIRef for direct references
    create_calls = mock_editor_instance.create.call_args_list
    
    # Check for address references
    assert any(
        call[0][0] == URIRef("http://example.org/test/123") and
        call[0][1] == URIRef("http://example.org/hasAddress") and
        call[0][2] == URIRef("http://example.org/addresses/existing-address-1")
        for call in create_calls
    )
    assert any(
        call[0][0] == URIRef("http://example.org/test/123") and
        call[0][1] == URIRef("http://example.org/hasAddress") and
        call[0][2] == URIRef("http://example.org/addresses/existing-address-2")
        for call in create_calls
    )
    
    # Check for contact reference
    assert any(
        call[0][0] == URIRef("http://example.org/test/123") and
        call[0][1] == URIRef("http://example.org/hasContact") and
        call[0][2] == URIRef("http://example.org/contacts/existing-contact")
        for call in create_calls
    )

@patch('heritrace.routes.entity.Editor')
@patch('heritrace.routes.entity.get_form_fields')
def test_create_entity_with_single_value_properties(mock_get_form_fields, mock_editor, logged_in_client, app):
    """Test creating an entity with single value properties (non-list values)"""
    # Setup form fields
    form_fields = {
        ("http://example.org/Person", None): {
            "http://example.org/hasName": [{
                "datatypes": [str(XSD.string)],
                "min": 1,
                "max": 1
            }],
            "http://example.org/hasAge": [{
                "datatypes": [str(XSD.integer)],
                "min": 0,
                "max": 1
            }],
            "http://example.org/hasBestFriend": [{
                "objectClass": "http://example.org/Person",
                "min": 0,
                "max": 1
            }]
        }
    }
    mock_get_form_fields.return_value = form_fields
    mock_editor_instance = mock_editor.return_value
    app.config["URI_GENERATOR"] = MagicMock()
    app.config["URI_GENERATOR"].generate_uri.return_value = "http://example.org/test/123"
    
    # Test data with single values (not in lists)
    data = {
        "entity_type": "http://example.org/Person",
        "properties": {
            "http://example.org/hasName": "John Doe",  # Single string value
            "http://example.org/hasAge": 30,  # Single integer value
            "http://example.org/hasBestFriend": {  # Existing entity reference with explicit metadata
                "is_existing_entity": True,
                "entity_uri": "http://example.org/persons/existing-friend"
            }
        }
    }

    response = logged_in_client.post(
        url_for('entity.create_entity'),
        data={"structured_data": json.dumps(data)}
    )

    assert response.status_code == 200
    assert response.json["status"] == "success"

    # Verify that editor.create was called correctly for each property
    create_calls = mock_editor_instance.create.call_args_list
    
    # Check string value
    assert any(
        call[0][0] == URIRef("http://example.org/test/123") and
        call[0][1] == URIRef("http://example.org/hasName") and
        str(call[0][2]) == "John Doe"
        for call in create_calls
    )
    
    # Check integer value
    assert any(
        call[0][0] == URIRef("http://example.org/test/123") and
        call[0][1] == URIRef("http://example.org/hasAge") and
        str(call[0][2]) == "30"
        for call in create_calls
    )
    
    # Check URI reference
    assert any(
        call[0][0] == URIRef("http://example.org/test/123") and
        call[0][1] == URIRef("http://example.org/hasBestFriend") and
        call[0][2] == URIRef("http://example.org/persons/existing-friend")
        for call in create_calls
    )

@patch('heritrace.routes.entity.gettext')
@patch('heritrace.routes.entity.Editor')
@patch('heritrace.routes.entity.get_form_fields')
def test_create_entity_invalid_primary_source(mock_get_form_fields, mock_editor, mock_gettext, logged_in_client, app):
    """Test entity creation with an invalid primary source URL"""
    mock_get_form_fields.return_value = {}  # No SHACL validation needed for this test
    app.config["URI_GENERATOR"] = MagicMock()
    app.config["URI_GENERATOR"].generate_uri.return_value = "http://example.org/test/123"
    mock_gettext.return_value = "Invalid primary source URL provided" # Mock translation

    data = {
        "properties": {
            "http://example.org/hasName": [{"type": "literal", "value": "Invalid Source Test"}]
        }
    }

    response = logged_in_client.post(
        url_for('entity.create_entity'),
        data={
            "structured_data": json.dumps(data),
            "primary_source": "not-a-valid-url", # Invalid URL
            "save_default_source": "false"
        }
    )

    assert response.status_code == 400
    assert response.json["status"] == "error"
    assert "Invalid primary source URL provided" in response.json["errors"]
    mock_editor.assert_not_called() # Editor should not be instantiated


@patch('heritrace.routes.entity.save_user_default_primary_source')
@patch('heritrace.routes.entity.Editor')
@patch('heritrace.routes.entity.get_form_fields')
@patch('heritrace.routes.entity.get_dataset_endpoint')
@patch('heritrace.routes.entity.get_provenance_endpoint')
def test_create_entity_save_default_primary_source(mock_get_prov, mock_get_dataset, mock_get_form_fields, mock_editor, mock_save_default, logged_in_client, app, mock_form_fields):
    """Test saving the primary source as default when creating an entity"""
    mock_get_form_fields.return_value = mock_form_fields
    mock_editor_instance = mock_editor.return_value
    app.config["URI_GENERATOR"] = MagicMock()
    app.config["URI_GENERATOR"].generate_uri.return_value = "http://example.org/test/123"
    
    primary_source_url = "http://valid.source.org/data"
    
    data = {
        "entity_type": "http://example.org/Person",
        "properties": {
            "http://example.org/hasName": ["Test Person"]
        }
    }

    # Mock current_user which is used inside the route
    with patch('heritrace.routes.entity.current_user') as mock_current_user:
        mock_current_user.orcid = "0000-0000-0000-0001" # Example ORCID

        response = logged_in_client.post(
            url_for('entity.create_entity'),
            data={
                "structured_data": json.dumps(data),
                "primary_source": primary_source_url,
                "save_default_source": 'true' # Set to save as default
            }
        )

    assert response.status_code == 200
    assert response.json["status"] == "success"
    
    # Verify save_user_default_primary_source was called correctly
    mock_save_default.assert_called_once_with("0000-0000-0000-0001", primary_source_url)
    
    # Verify editor was instantiated with the primary source
    mock_editor.assert_called_once()
    call_args, call_kwargs = mock_editor.call_args
    # Editor arguments are positional: (dataset_endpoint, prov_endpoint, counter_handler, user_uri, primary_source, ...)
    assert len(call_args) >= 5  # Ensure enough positional arguments were passed
    assert call_args[4] == primary_source_url # Check the 5th positional argument (index 4)