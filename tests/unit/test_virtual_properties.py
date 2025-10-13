"""
Tests for virtual_properties.py
"""

from unittest.mock import patch

from heritrace.utils.virtual_properties import (
    _validate_entity_data,
    _get_virtual_property_configs,
    get_virtual_properties_for_entity,
    apply_field_overrides,
    transform_changes_with_virtual_properties,
    process_virtual_properties_in_create_data,
    transform_entity_creation_with_virtual_properties,
    remove_virtual_properties_from_creation_data,
    transform_virtual_property_deletion,
    process_virtual_property_values,
)


class TestValidateEntityData:
    """Tests for _validate_entity_data function."""

    def test_validate_entity_data_valid(self):
        """Test with valid entity data."""
        data = {
            'properties': {'prop1': 'value1'},
            'entity_type': 'http://example.org/Person'
        }
        result = _validate_entity_data(data)
        assert result == 'http://example.org/Person'

    def test_validate_entity_data_no_properties(self):
        """Test with no properties."""
        data = {'entity_type': 'http://example.org/Person'}
        result = _validate_entity_data(data)
        assert result is None

    def test_validate_entity_data_empty_properties(self):
        """Test with empty properties."""
        data = {
            'properties': {},
            'entity_type': 'http://example.org/Person'
        }
        result = _validate_entity_data(data)
        assert result is None

    def test_validate_entity_data_no_entity_type(self):
        """Test with no entity_type."""
        data = {'properties': {'prop1': 'value1'}}
        result = _validate_entity_data(data)
        assert result is None

    def test_validate_entity_data_empty_entity_type(self):
        """Test with empty entity_type."""
        data = {
            'properties': {'prop1': 'value1'},
            'entity_type': ''
        }
        result = _validate_entity_data(data)
        assert result is None


class TestGetVirtualPropertyConfigs:
    """Tests for _get_virtual_property_configs function."""

    @patch('heritrace.utils.virtual_properties.get_display_rules')
    @patch('heritrace.utils.virtual_properties.find_matching_rule')
    def test_get_virtual_property_configs_with_virtual_properties(
        self, mock_find_matching_rule, mock_get_display_rules
    ):
        """Test getting virtual property configs when virtual properties exist."""
        mock_get_display_rules.return_value = [
            {
                'target': {'class': 'http://example.org/Person'},
                'displayProperties': [
                    {
                        'displayName': 'Virtual Prop',
                        'isVirtual': True,
                        'implementedVia': {}
                    }
                ]
            }
        ]
        mock_find_matching_rule.return_value = {
            'displayProperties': [
                {
                    'displayName': 'Virtual Prop',
                    'isVirtual': True,
                    'implementedVia': {}
                }
            ]
        }

        result = _get_virtual_property_configs('http://example.org/Person', None)

        assert 'Virtual Prop' in result
        assert result['Virtual Prop']['isVirtual'] is True

    @patch('heritrace.utils.virtual_properties.get_display_rules')
    def test_get_virtual_property_configs_no_display_rules(
        self, mock_get_display_rules
    ):
        """Test when there are no display rules."""
        mock_get_display_rules.return_value = None

        result = _get_virtual_property_configs('http://example.org/Person', None)

        assert result == {}

    @patch('heritrace.utils.virtual_properties.get_display_rules')
    @patch('heritrace.utils.virtual_properties.find_matching_rule')
    def test_get_virtual_property_configs_no_matching_rule(
        self, mock_find_matching_rule, mock_get_display_rules
    ):
        """Test when there is no matching rule."""
        mock_get_display_rules.return_value = [{'target': {'class': 'http://example.org/Other'}}]
        mock_find_matching_rule.return_value = None

        result = _get_virtual_property_configs('http://example.org/Person', None)

        assert result == {}

    @patch('heritrace.utils.virtual_properties.get_display_rules')
    @patch('heritrace.utils.virtual_properties.find_matching_rule')
    def test_get_virtual_property_configs_without_virtual_flag(
        self, mock_find_matching_rule, mock_get_display_rules
    ):
        """Test when properties don't have isVirtual flag."""
        mock_get_display_rules.return_value = [{'target': {'class': 'http://example.org/Person'}}]
        mock_find_matching_rule.return_value = {
            'displayProperties': [
                {
                    'displayName': 'Regular Prop',
                    'isVirtual': False
                }
            ]
        }

        result = _get_virtual_property_configs('http://example.org/Person', None)

        assert result == {}

    @patch('heritrace.utils.virtual_properties.get_display_rules')
    @patch('heritrace.utils.virtual_properties.find_matching_rule')
    def test_get_virtual_property_configs_without_display_name(
        self, mock_find_matching_rule, mock_get_display_rules
    ):
        """Test when virtual property has no displayName."""
        mock_get_display_rules.return_value = [{'target': {'class': 'http://example.org/Person'}}]
        mock_find_matching_rule.return_value = {
            'displayProperties': [
                {
                    'isVirtual': True,
                    'implementedVia': {}
                }
            ]
        }

        result = _get_virtual_property_configs('http://example.org/Person', None)

        assert result == {}


class TestGetVirtualPropertiesForEntity:
    """Tests for get_virtual_properties_for_entity function."""

    @patch('heritrace.utils.virtual_properties._get_virtual_property_configs')
    def test_get_virtual_properties_for_entity(self, mock_get_configs):
        """Test getting virtual properties for entity."""
        mock_get_configs.return_value = {
            'Virtual Prop 1': {'isVirtual': True},
            'Virtual Prop 2': {'isVirtual': True}
        }

        result = get_virtual_properties_for_entity('http://example.org/Person', None)

        assert len(result) == 2
        assert ('Virtual Prop 1', {'isVirtual': True}) in result
        assert ('Virtual Prop 2', {'isVirtual': True}) in result

    @patch('heritrace.utils.virtual_properties._get_virtual_property_configs')
    def test_get_virtual_properties_for_entity_no_configs(self, mock_get_configs):
        """Test when there are no virtual property configs."""
        mock_get_configs.return_value = {}

        result = get_virtual_properties_for_entity('http://example.org/Person', None)

        assert result == []


class TestApplyFieldOverrides:
    """Tests for apply_field_overrides function."""

    def test_apply_field_overrides_should_be_displayed(self):
        """Test applying shouldBeDisplayed override."""
        form_field_data = {
            'http://example.org/prop1': [
                {'displayName': 'Prop 1', 'shouldBeDisplayed': True}
            ]
        }
        field_overrides = {
            'http://example.org/prop1': {'shouldBeDisplayed': False}
        }

        result = apply_field_overrides(form_field_data, field_overrides)

        assert 'http://example.org/prop1' not in result

    def test_apply_field_overrides_display_name(self):
        """Test applying displayName override."""
        form_field_data = {
            'http://example.org/prop1': [
                {'displayName': 'Old Name'}
            ]
        }
        field_overrides = {
            'http://example.org/prop1': {'displayName': 'New Name'}
        }

        result = apply_field_overrides(form_field_data, field_overrides)

        assert result['http://example.org/prop1'][0]['displayName'] == 'New Name'

    def test_apply_field_overrides_value(self):
        """Test applying value override."""
        form_field_data = {
            'http://example.org/prop1': [
                {'hasValue': 'old_value', 'nestedShape': ['some_shape']}
            ]
        }
        field_overrides = {
            'http://example.org/prop1': {'value': 'new_value'}
        }

        result = apply_field_overrides(form_field_data, field_overrides)

        assert result['http://example.org/prop1'][0]['hasValue'] == 'new_value'
        assert result['http://example.org/prop1'][0]['nestedShape'] == []

    def test_apply_field_overrides_current_entity_placeholder(self):
        """Test applying ${currentEntity} placeholder."""
        form_field_data = {
            'http://example.org/prop1': [
                {'hasValue': 'old_value'}
            ]
        }
        field_overrides = {
            'http://example.org/prop1': {'value': '${currentEntity}'}
        }
        current_entity_uri = 'http://example.org/entity123'

        result = apply_field_overrides(
            form_field_data,
            field_overrides,
            current_entity_uri
        )

        assert result['http://example.org/prop1'][0]['hasValue'] == current_entity_uri

    def test_apply_field_overrides_no_overrides(self):
        """Test when property has no overrides."""
        form_field_data = {
            'http://example.org/prop1': [
                {'displayName': 'Prop 1'}
            ]
        }
        field_overrides = {}

        result = apply_field_overrides(form_field_data, field_overrides)

        assert result == form_field_data

    def test_apply_field_overrides_multiple_details(self):
        """Test applying overrides to multiple detail entries."""
        form_field_data = {
            'http://example.org/prop1': [
                {'displayName': 'Prop 1A'},
                {'displayName': 'Prop 1B'}
            ]
        }
        field_overrides = {
            'http://example.org/prop1': {'displayName': 'New Name'}
        }

        result = apply_field_overrides(form_field_data, field_overrides)

        assert len(result['http://example.org/prop1']) == 2
        assert all(
            d['displayName'] == 'New Name'
            for d in result['http://example.org/prop1']
        )

    def test_apply_field_overrides_filters_invisible_fields(self):
        """Test that invisible fields are filtered out."""
        form_field_data = {
            'http://example.org/prop1': [
                {'displayName': 'Prop 1', 'shouldBeDisplayed': True}
            ],
            'http://example.org/prop2': [
                {'displayName': 'Prop 2', 'shouldBeDisplayed': True}
            ]
        }
        field_overrides = {
            'http://example.org/prop1': {'shouldBeDisplayed': False},
            'http://example.org/prop2': {'shouldBeDisplayed': True}
        }

        result = apply_field_overrides(form_field_data, field_overrides)

        assert 'http://example.org/prop1' not in result
        assert 'http://example.org/prop2' in result


class TestTransformChangesWithVirtualProperties:
    """Tests for transform_changes_with_virtual_properties function."""

    @patch('heritrace.utils.virtual_properties.process_virtual_properties_in_create_data')
    def test_transform_changes_create_action(self, mock_process):
        """Test transforming create action with virtual properties."""
        mock_process.return_value = (
            {'entity_type': 'Person', 'properties': {'name': 'John'}},
            [{'entity_type': 'VirtualEntity', 'properties': {}}]
        )

        changes = [
            {
                'action': 'create',
                'subject': None,
                'data': {
                    'entity_type': 'Person',
                    'properties': {'name': 'John', 'virtual_prop': 'value'}
                }
            }
        ]

        result = transform_changes_with_virtual_properties(changes)

        assert len(result) == 2
        assert result[0]['action'] == 'create'
        assert result[0]['data']['properties'] == {'name': 'John'}
        assert result[1]['action'] == 'create'
        assert result[1]['subject'] is None

    @patch('heritrace.utils.virtual_properties.process_virtual_properties_in_create_data')
    def test_transform_changes_create_action_no_properties_remaining(self, mock_process):
        """Test transforming create action when no regular properties remain."""
        mock_process.return_value = (
            {'entity_type': 'Person', 'properties': {}},
            [{'entity_type': 'VirtualEntity', 'properties': {}}]
        )

        changes = [
            {
                'action': 'create',
                'subject': None,
                'data': {
                    'entity_type': 'Person',
                    'properties': {'virtual_prop': 'value'}
                }
            }
        ]

        result = transform_changes_with_virtual_properties(changes)

        assert len(result) == 1
        assert result[0]['action'] == 'create'
        assert result[0]['data']['entity_type'] == 'VirtualEntity'

    @patch('heritrace.utils.virtual_properties.transform_virtual_property_deletion')
    def test_transform_changes_delete_virtual_property(self, mock_transform):
        """Test transforming delete action for virtual property."""
        mock_transform.return_value = {
            'action': 'delete',
            'subject': 'http://example.org/intermediate123'
        }

        changes = [
            {
                'action': 'delete',
                'is_virtual': True,
                'object': 'http://example.org/intermediate123'
            }
        ]

        result = transform_changes_with_virtual_properties(changes)

        assert len(result) == 1
        assert result[0]['action'] == 'delete'
        assert result[0]['subject'] == 'http://example.org/intermediate123'

    @patch('heritrace.utils.virtual_properties.transform_virtual_property_deletion')
    def test_transform_changes_delete_virtual_property_returns_none(self, mock_transform):
        """Test when transform_virtual_property_deletion returns None."""
        mock_transform.return_value = None

        changes = [
            {
                'action': 'delete',
                'is_virtual': True,
                'object': 'http://example.org/intermediate123'
            }
        ]

        result = transform_changes_with_virtual_properties(changes)

        assert len(result) == 1
        assert result[0]['is_virtual'] is True

    def test_transform_changes_other_actions(self):
        """Test that other actions pass through unchanged."""
        changes = [
            {'action': 'update', 'subject': 'http://example.org/entity1'},
            {'action': 'delete', 'subject': 'http://example.org/entity2'}
        ]

        result = transform_changes_with_virtual_properties(changes)

        assert result == changes


class TestProcessVirtualPropertiesInCreateData:
    """Tests for process_virtual_properties_in_create_data function."""

    @patch('heritrace.utils.virtual_properties._validate_entity_data')
    @patch('heritrace.utils.virtual_properties._get_virtual_property_configs')
    @patch('heritrace.utils.virtual_properties.process_virtual_property_values')
    def test_process_virtual_properties_in_create_data(
        self, mock_process_values, mock_get_configs, mock_validate
    ):
        """Test processing virtual properties in create data."""
        mock_validate.return_value = 'http://example.org/Person'
        mock_get_configs.return_value = {
            'Virtual Prop': {
                'isVirtual': True,
                'implementedVia': {}
            }
        }
        mock_process_values.return_value = [
            {'entity_type': 'VirtualEntity', 'properties': {}}
        ]

        data = {
            'entity_type': 'http://example.org/Person',
            'properties': {
                'name': 'John',
                'Virtual Prop': [{'value': 'test'}]
            }
        }

        modified_data, virtual_entities = process_virtual_properties_in_create_data(data)

        assert 'name' in modified_data['properties']
        assert 'Virtual Prop' not in modified_data['properties']
        assert len(virtual_entities) == 1

    @patch('heritrace.utils.virtual_properties._validate_entity_data')
    def test_process_virtual_properties_invalid_data(self, mock_validate):
        """Test processing when data is invalid."""
        mock_validate.return_value = None

        data = {'properties': {}}

        modified_data, virtual_entities = process_virtual_properties_in_create_data(data)

        assert modified_data == data
        assert virtual_entities == []

    @patch('heritrace.utils.virtual_properties._validate_entity_data')
    @patch('heritrace.utils.virtual_properties._get_virtual_property_configs')
    def test_process_virtual_properties_no_configs(self, mock_get_configs, mock_validate):
        """Test processing when there are no virtual property configs."""
        mock_validate.return_value = 'http://example.org/Person'
        mock_get_configs.return_value = {}

        data = {
            'entity_type': 'http://example.org/Person',
            'properties': {'name': 'John'}
        }

        modified_data, virtual_entities = process_virtual_properties_in_create_data(data)

        assert modified_data == data
        assert virtual_entities == []


class TestTransformEntityCreationWithVirtualProperties:
    """Tests for transform_entity_creation_with_virtual_properties function."""

    @patch('heritrace.utils.virtual_properties._validate_entity_data')
    @patch('heritrace.utils.virtual_properties._get_virtual_property_configs')
    @patch('heritrace.utils.virtual_properties.process_virtual_property_values')
    def test_transform_entity_creation(
        self, mock_process_values, mock_get_configs, mock_validate
    ):
        """Test transforming entity creation with virtual properties."""
        mock_validate.return_value = 'http://example.org/Person'
        mock_get_configs.return_value = {
            'Virtual Prop': {'isVirtual': True}
        }
        mock_process_values.return_value = [
            {'entity_type': 'VirtualEntity', 'properties': {}}
        ]

        structured_data = {
            'entity_type': 'http://example.org/Person',
            'properties': {
                'Virtual Prop': [{'value': 'test'}]
            }
        }
        created_entity_uri = 'http://example.org/entity123'

        result = transform_entity_creation_with_virtual_properties(
            structured_data,
            created_entity_uri
        )

        assert len(result) == 1

    @patch('heritrace.utils.virtual_properties._validate_entity_data')
    def test_transform_entity_creation_invalid_data(self, mock_validate):
        """Test when structured data is invalid."""
        mock_validate.return_value = None

        result = transform_entity_creation_with_virtual_properties({}, 'uri')

        assert result == []

    @patch('heritrace.utils.virtual_properties._validate_entity_data')
    @patch('heritrace.utils.virtual_properties._get_virtual_property_configs')
    def test_transform_entity_creation_no_configs(self, mock_get_configs, mock_validate):
        """Test when there are no virtual property configs."""
        mock_validate.return_value = 'http://example.org/Person'
        mock_get_configs.return_value = {}

        structured_data = {
            'entity_type': 'http://example.org/Person',
            'properties': {'name': 'John'}
        }
        created_entity_uri = 'http://example.org/entity123'

        result = transform_entity_creation_with_virtual_properties(
            structured_data,
            created_entity_uri
        )

        assert result == []


class TestRemoveVirtualPropertiesFromCreationData:
    """Tests for remove_virtual_properties_from_creation_data function."""

    @patch('heritrace.utils.virtual_properties._validate_entity_data')
    @patch('heritrace.utils.virtual_properties._get_virtual_property_configs')
    def test_remove_virtual_properties(self, mock_get_configs, mock_validate):
        """Test removing virtual properties from creation data."""
        mock_validate.return_value = 'http://example.org/Person'
        mock_get_configs.return_value = {
            'Virtual Prop': {'isVirtual': True}
        }

        structured_data = {
            'entity_type': 'http://example.org/Person',
            'properties': {
                'name': 'John',
                'Virtual Prop': [{'value': 'test'}]
            }
        }

        result = remove_virtual_properties_from_creation_data(structured_data)

        assert 'name' in result['properties']
        assert 'Virtual Prop' not in result['properties']

    @patch('heritrace.utils.virtual_properties._validate_entity_data')
    def test_remove_virtual_properties_invalid_data(self, mock_validate):
        """Test when data is invalid."""
        mock_validate.return_value = None

        data = {'properties': {}}
        result = remove_virtual_properties_from_creation_data(data)

        assert result == data

    @patch('heritrace.utils.virtual_properties._validate_entity_data')
    @patch('heritrace.utils.virtual_properties._get_virtual_property_configs')
    def test_remove_virtual_properties_no_configs(self, mock_get_configs, mock_validate):
        """Test when there are no virtual property configs."""
        mock_validate.return_value = 'http://example.org/Person'
        mock_get_configs.return_value = {}

        data = {
            'entity_type': 'http://example.org/Person',
            'properties': {'name': 'John'}
        }
        result = remove_virtual_properties_from_creation_data(data)

        assert result == data


class TestTransformVirtualPropertyDeletion:
    """Tests for transform_virtual_property_deletion function."""

    def test_transform_virtual_property_deletion(self):
        """Test transforming virtual property deletion."""
        change = {
            'action': 'delete',
            'is_virtual': True,
            'object': 'http://example.org/intermediate123'
        }

        result = transform_virtual_property_deletion(change)

        assert result['action'] == 'delete'
        assert result['subject'] == 'http://example.org/intermediate123'

    def test_transform_virtual_property_deletion_not_virtual(self):
        """Test when change is not virtual."""
        change = {
            'action': 'delete',
            'is_virtual': False,
            'object': 'http://example.org/entity123'
        }

        result = transform_virtual_property_deletion(change)

        assert result is None

    def test_transform_virtual_property_deletion_no_flag(self):
        """Test when is_virtual flag is missing."""
        change = {
            'action': 'delete',
            'object': 'http://example.org/entity123'
        }

        result = transform_virtual_property_deletion(change)

        assert result is None

    def test_transform_virtual_property_deletion_no_object(self):
        """Test when object is missing."""
        change = {
            'action': 'delete',
            'is_virtual': True
        }

        result = transform_virtual_property_deletion(change)

        assert result is None


class TestProcessVirtualPropertyValues:
    """Tests for process_virtual_property_values function."""

    def test_process_virtual_property_values(self):
        """Test processing virtual property values."""
        values = [
            {
                'properties': {
                    'name': 'Test'
                },
                'entity_shape': 'http://example.org/Shape'
            }
        ]
        config = {
            'implementedVia': {
                'target': {
                    'class': 'http://example.org/IntermediateEntity',
                    'shape': 'http://example.org/IntermediateShape'
                },
                'fieldOverrides': {}
            }
        }
        subject_uri = 'http://example.org/entity123'

        result = process_virtual_property_values(values, config, subject_uri)

        assert len(result) == 1
        assert result[0]['entity_type'] == 'http://example.org/IntermediateEntity'
        assert result[0]['entity_shape'] == 'http://example.org/Shape'
        assert 'name' in result[0]['properties']

    def test_process_virtual_property_values_with_field_overrides(self):
        """Test processing with field overrides."""
        values = [{'properties': {}}]
        config = {
            'implementedVia': {
                'target': {
                    'class': 'http://example.org/IntermediateEntity'
                },
                'fieldOverrides': {
                    'http://example.org/linkProp': {
                        'shouldBeDisplayed': False,
                        'value': '${currentEntity}'
                    }
                }
            }
        }
        subject_uri = 'http://example.org/entity123'

        result = process_virtual_property_values(values, config, subject_uri)

        assert len(result) == 1
        assert 'http://example.org/linkProp' in result[0]['properties']
        prop_value = result[0]['properties']['http://example.org/linkProp'][0]
        assert prop_value['is_existing_entity'] is True
        assert prop_value['entity_uri'] == subject_uri

    def test_process_virtual_property_values_override_without_current_entity(self):
        """Test field override with static value."""
        values = [{'properties': {}}]
        config = {
            'implementedVia': {
                'target': {
                    'class': 'http://example.org/IntermediateEntity'
                },
                'fieldOverrides': {
                    'http://example.org/prop': {
                        'shouldBeDisplayed': False,
                        'value': 'static_value'
                    }
                }
            }
        }

        result = process_virtual_property_values(values, config)

        assert len(result) == 1
        assert result[0]['properties']['http://example.org/prop'] == ['static_value']

    def test_process_virtual_property_values_no_target_class(self):
        """Test when target has no class or shape."""
        values = [{'properties': {}}]
        config = {
            'implementedVia': {
                'target': {}
            }
        }

        result = process_virtual_property_values(values, config)

        assert result == []

    def test_process_virtual_property_values_non_dict_value(self):
        """Test when value is not a dictionary."""
        values = ['string_value', 123, None]
        config = {
            'implementedVia': {
                'target': {
                    'class': 'http://example.org/IntermediateEntity'
                }
            }
        }

        result = process_virtual_property_values(values, config)

        assert result == []

    def test_process_virtual_property_values_override_displayed_true(self):
        """Test when shouldBeDisplayed is True in override."""
        values = [{'properties': {}}]
        config = {
            'implementedVia': {
                'target': {
                    'class': 'http://example.org/IntermediateEntity'
                },
                'fieldOverrides': {
                    'http://example.org/prop': {
                        'shouldBeDisplayed': True,
                        'value': 'test_value'
                    }
                }
            }
        }

        result = process_virtual_property_values(values, config)

        assert len(result) == 1
        assert 'http://example.org/prop' not in result[0]['properties']
