"""
Virtual properties utilities for display rules.

This module contains functions for processing virtual properties which allow
entities to display computed or derived relationships that don't exist directly
in the knowledge graph.
"""

from typing import Dict, List, Tuple, Any, Optional

from heritrace.extensions import get_display_rules
from heritrace.utils.display_rules_utils import find_matching_rule


def _validate_entity_data(data: Dict[str, Any]) -> Optional[str]:
    """
    Validate entity data for virtual property processing.

    Returns:
        entity_type if valid, None if invalid
    """
    if not data.get('properties'):
        return None

    entity_type = data.get('entity_type')
    if not entity_type:
        return None

    return entity_type


def _get_virtual_property_configs(entity_type: str, entity_shape: str) -> Dict[str, Dict]:
    """
    Get virtual property configurations for an entity type and shape.

    Returns:
        Dictionary mapping display names to property configs
    """
    display_rules = get_display_rules()
    if not display_rules:
        return {}

    matching_rule = find_matching_rule(entity_type, entity_shape, display_rules)
    if not matching_rule:
        return {}

    virtual_property_configs = {}
    for prop_config in matching_rule.get('displayProperties', []):
        if prop_config.get('isVirtual'):
            display_name = prop_config.get('displayName')
            if display_name:
                virtual_property_configs[display_name] = prop_config

    return virtual_property_configs


def get_virtual_properties_for_entity(highest_priority_class: str, entity_shape: str) -> List[Tuple[str, Dict]]:
    """
    Extract virtual properties configured for a specific entity class and shape.

    Args:
        highest_priority_class: The highest priority class for the entity
        entity_shape: The shape for the entity

    Returns:
        List of tuples (displayName, property_config)
    """
    virtual_property_configs = _get_virtual_property_configs(highest_priority_class, entity_shape)

    return [(display_name, config) for display_name, config in virtual_property_configs.items()]


def apply_field_overrides(form_field_data: Dict, field_overrides: Dict, current_entity_uri: str = None) -> Dict:
    """
    Apply field overrides to form field data.

    Args:
        form_field_data: Dictionary from form_fields with structure {property_uri: [details]}
        field_overrides: Dictionary with field override rules

    Returns:
        Modified form field data with overrides applied
    """
    modified_data = {}

    for property_uri, details_list in form_field_data.items():
        if property_uri in field_overrides:
            override = field_overrides[property_uri]
            modified_details_list = []

            for details in details_list:
                modified_details = details.copy()

                if "shouldBeDisplayed" in override:
                    modified_details["shouldBeDisplayed"] = override["shouldBeDisplayed"]

                if "displayName" in override:
                    modified_details["displayName"] = override["displayName"]

                if "value" in override:
                    value = override["value"]
                    if value == "${currentEntity}" and current_entity_uri:
                        value = current_entity_uri
                    modified_details["hasValue"] = value
                    if "nestedShape" in modified_details:
                        modified_details["nestedShape"] = []

                modified_details_list.append(modified_details)

            visible_details = [details for details in modified_details_list if details.get('shouldBeDisplayed', True)]
            if visible_details:
                modified_data[property_uri] = visible_details
        else:
            modified_data[property_uri] = details_list

    return modified_data

def transform_changes_with_virtual_properties(changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transform a list of changes, expanding virtual properties into actual entity creations.

    This is the main function to call from the API to handle virtual properties.
    It processes all changes and returns an expanded list where virtual properties
    have been converted to proper entity creation changes.

    Args:
        changes: List of change dictionaries from the API

    Returns:
        Expanded list of changes with virtual properties transformed
    """
    processed_changes = []

    for change in changes:
        if change["action"] == "create" and change.get("data"):
            data = change["data"]
            modified_data, virtual_entities = process_virtual_properties_in_create_data(
                data,
                change.get("subject")
            )

            # Only add the main change if there are non-virtual properties remaining
            if modified_data.get('properties'):
                main_change = change.copy()
                main_change["data"] = modified_data
                processed_changes.append(main_change)

            for virtual_entity in virtual_entities:
                virtual_change = {
                    "action": "create",
                    "subject": None,  # Will be generated
                    "data": virtual_entity
                }
                processed_changes.append(virtual_change)
        else:
            processed_changes.append(change)

    return processed_changes


def process_virtual_properties_in_create_data(data: Dict[str, Any], subject_uri: str = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Process virtual properties in entity creation data.

    Virtual properties need to be transformed into actual entity creations with proper relationships.

    Args:
        data: The entity creation data containing properties
        subject_uri: The URI of the subject entity being created/edited

    Returns:
        Tuple of:
        - Modified data with virtual properties removed
        - List of intermediate entities to create
    """
    entity_type = _validate_entity_data(data)
    if not entity_type:
        return data, []

    entity_shape = data.get('entity_shape')
    virtual_property_configs = _get_virtual_property_configs(entity_type, entity_shape)

    if not virtual_property_configs:
        return data, []

    regular_properties = {}
    virtual_entities = []

    for property_name, property_values in data['properties'].items():
        if property_name in virtual_property_configs:
            config = virtual_property_configs[property_name]
            entities = process_virtual_property_values(
                property_values,
                config,
                subject_uri
            )
            virtual_entities.extend(entities)
        else:
            regular_properties[property_name] = property_values

    modified_data = data.copy()
    modified_data['properties'] = regular_properties

    return modified_data, virtual_entities


def transform_entity_creation_with_virtual_properties(structured_data: Dict[str, Any], created_entity_uri: str) -> List[Dict[str, Any]]:
    """
    Transform virtual properties in entity creation data after the main entity has been created.

    This function is specifically for entity creation where we need to process virtual properties
    after the main entity URI is available.

    Args:
        structured_data: The original entity creation data
        created_entity_uri: The URI of the entity that was just created

    Returns:
        List of intermediate entities to create
    """
    entity_type = _validate_entity_data(structured_data)
    if not entity_type:
        return []

    entity_shape = structured_data.get('entity_shape')
    virtual_property_configs = _get_virtual_property_configs(entity_type, entity_shape)

    if not virtual_property_configs:
        return []

    virtual_entities = []

    for property_name, property_values in structured_data['properties'].items():
        if property_name in virtual_property_configs:
            config = virtual_property_configs[property_name]
            entities = process_virtual_property_values(
                property_values,
                config,
                created_entity_uri
            )
            virtual_entities.extend(entities)

    return virtual_entities


def remove_virtual_properties_from_creation_data(structured_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove virtual properties from entity creation data, leaving only regular properties.

    Args:
        structured_data: The original entity creation data

    Returns:
        Modified structured data with virtual properties removed
    """
    entity_type = _validate_entity_data(structured_data)
    if not entity_type:
        return structured_data

    entity_shape = structured_data.get('entity_shape')
    virtual_property_configs = _get_virtual_property_configs(entity_type, entity_shape)

    if not virtual_property_configs:
        return structured_data

    # Create modified structured data without virtual properties
    modified_data = structured_data.copy()
    modified_properties = {}

    for property_name, property_values in structured_data['properties'].items():
        if property_name not in virtual_property_configs:
            modified_properties[property_name] = property_values

    modified_data['properties'] = modified_properties
    return modified_data


def process_virtual_property_values(values: List[Any], config: Dict[str, Any], subject_uri: str = None) -> List[Dict[str, Any]]:
    """
    Process values of a virtual property to create intermediate entities.

    Args:
        values: List of values for the virtual property
        config: Virtual property configuration
        subject_uri: URI of the main entity

    Returns:
        List of intermediate entities to create
    """
    entities = []
    implementation = config.get('implementedVia', {})
    target = implementation.get('target', {})
    field_overrides = implementation.get('fieldOverrides', {})

    if not target.get('class') and not target.get('shape'):
        return entities

    for value in values:
        if isinstance(value, dict):
            entity = {
                'entity_type': target.get('class'),
                'entity_shape': target.get('shape'),
                'properties': {}
            }

            if 'properties' in value:
                entity['properties'] = value['properties'].copy()

            for field_uri, override in field_overrides.items():
                if not override.get('shouldBeDisplayed', True):
                    if 'value' in override:
                        override_value = override['value']
                        if override_value == '${currentEntity}' and subject_uri:
                            entity['properties'][field_uri] = [{
                                'is_existing_entity': True,
                                'entity_uri': subject_uri
                            }]
                        else:
                            entity['properties'][field_uri] = [override_value]

            if 'entity_shape' in value:
                entity['entity_shape'] = value['entity_shape']

            entities.append(entity)

    return entities
