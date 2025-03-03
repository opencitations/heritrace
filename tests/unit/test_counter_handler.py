"""
Tests for the counter handler functionality.
"""

from tests.test_config import TestConfig


def test_counter_handler_basic_operations():
    """Test basic operations of the counter handler."""
    # Get the counter handler from TestConfig
    counter_handler = TestConfig.COUNTER_HANDLER
    assert counter_handler is not None

    # Create a subject URI
    subject_uri = "https://w3id.org/oc/meta/br/123456"

    # The entity name is the subject URI string
    entity_name = subject_uri

    # Set an initial value for the counter
    initial_value = 42
    counter_handler.set_counter(initial_value, entity_name)

    # Read the counter value
    counter_value = counter_handler.read_counter(entity_name)

    # Verify the counter value was set correctly
    assert counter_value == initial_value, "Counter value should match the value we set"

    # Increment the counter
    new_value = initial_value + 1
    counter_handler.set_counter(new_value, entity_name)

    # Read the counter value again
    updated_counter_value = counter_handler.read_counter(entity_name)

    # Verify the counter was incremented
    assert (
        updated_counter_value == new_value
    ), "Counter should be incremented to the new value"


def test_counter_handler_with_different_entities():
    """Test counter handler with different entity names."""
    # Get the counter handler from TestConfig
    counter_handler = TestConfig.COUNTER_HANDLER
    assert counter_handler is not None

    # Test with multiple different entity names
    entity_names = [
        "https://w3id.org/oc/meta/br/1",
        "https://w3id.org/oc/meta/ra/2",
        "https://w3id.org/oc/meta/id/3",
    ]

    # Set and verify counters for each entity
    for i, entity_name in enumerate(entity_names):
        value = 100 + i
        counter_handler.set_counter(value, entity_name)
        assert (
            counter_handler.read_counter(entity_name) == value
        ), f"Counter for {entity_name} should be {value}"

    # Verify each counter maintained its own value
    for i, entity_name in enumerate(entity_names):
        expected_value = 100 + i
        assert (
            counter_handler.read_counter(entity_name) == expected_value
        ), f"Counter for {entity_name} should still be {expected_value}"


def test_counter_handler_negative_value():
    """Test that set_counter raises ValueError when a negative value is passed."""
    # Get the counter handler from TestConfig
    counter_handler = TestConfig.COUNTER_HANDLER
    assert counter_handler is not None

    # Create a test entity name
    entity_name = "https://w3id.org/oc/meta/br/test_negative"

    # Try to set a negative value and verify it raises ValueError
    import pytest

    with pytest.raises(ValueError, match="new_value must be a non negative integer!"):
        counter_handler.set_counter(-1, entity_name)

    # Verify that a zero value is accepted (edge case)
    counter_handler.set_counter(0, entity_name)
    assert (
        counter_handler.read_counter(entity_name) == 0
    ), "Counter should accept zero as a valid value"
