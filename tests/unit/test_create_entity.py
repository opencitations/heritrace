import json
from unittest.mock import MagicMock, patch

import pytest
from flask import url_for
from rdflib import XSD, URIRef


@pytest.fixture
def mock_form_fields():
    return {
        "http://example.org/Person": {
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
        "http://example.org/Address": {
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
        "http://example.org/Person": {
            "http://example.org/hasAddress": [{
                "nodeShape": "http://example.org/AddressShape",
                "subjectShape": "http://example.org/PersonShape",
                "orderedBy": "http://example.org/nextAddress"
            }]
        },
        "http://example.org/Address": {
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
        "http://example.org/Person": {
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
        "http://example.org/Address": {
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
        "http://example.org/Person": {
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
    assert any("has name" in error.lower() for error in response.json["errors"])

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
        "http://example.org/Person": {
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
    
    # Test data with direct URI references
    data = {
        "entity_type": "http://example.org/Person",
        "properties": {
            "http://example.org/hasAddress": [
                "http://example.org/addresses/existing-address-1",
                "http://example.org/addresses/existing-address-2"
            ],
            "http://example.org/hasContact": [
                "http://example.org/contacts/existing-contact"
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
        "http://example.org/Person": {
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
            "http://example.org/hasBestFriend": "http://example.org/persons/existing-friend"  # Single URI reference
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