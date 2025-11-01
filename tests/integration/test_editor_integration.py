"""
Tests for the editor module.
"""

from unittest.mock import MagicMock
from SPARQLWrapper import JSON, SPARQLWrapper

import pytest
from rdflib_ocdm.ocdm_graph import OCDMGraph
from unittest.mock import patch
from datetime import datetime

# Import the editor module
from heritrace.editor import Editor
from rdflib import RDF, XSD, Literal, URIRef
from rdflib_ocdm.ocdm_graph import OCDMDataset, OCDMGraph
from tests.test_config import TestConfig


@pytest.fixture
def mock_counter_handler():
    """Create a mock CounterHandler."""
    return MagicMock()


@pytest.fixture
def editor(mock_counter_handler) -> Editor:
    """Create an Editor instance for testing."""
    dataset_endpoint = "http://example.org/dataset"
    provenance_endpoint = "http://example.org/provenance"
    resp_agent = URIRef("http://example.org/agent")

    editor = Editor(
        dataset_endpoint=dataset_endpoint,
        provenance_endpoint=provenance_endpoint,
        counter_handler=mock_counter_handler,
        resp_agent=resp_agent,
        dataset_is_quadstore=True,
    )
    return editor


@pytest.fixture
def real_editor():
    """Create an Editor instance with real test database connections."""
    dataset_endpoint = TestConfig.DATASET_DB_URL  # http://localhost:9999/sparql
    provenance_endpoint = TestConfig.PROVENANCE_DB_URL  # http://localhost:9998/sparql
    resp_agent = URIRef("http://example.org/test-agent")

    editor = Editor(
        dataset_endpoint=dataset_endpoint,
        provenance_endpoint=provenance_endpoint,
        counter_handler=TestConfig.COUNTER_HANDLER,
        resp_agent=resp_agent,
        dataset_is_quadstore=TestConfig.DATASET_IS_QUADSTORE,
    )
    return editor


@pytest.fixture(autouse=True)
def reset_editor_after_test(editor: Editor):
    """Reset editor state after each test."""
    yield
    # Reset editor state
    editor.g_set = (
        OCDMDataset(editor.counter_handler)
        if editor.dataset_is_quadstore
        else OCDMGraph(editor.counter_handler)
    )
    editor.dataset_is_quadstore = True


def test_editor_initialization(editor: Editor, mock_counter_handler) -> None:
    """Test that the Editor is initialized correctly."""
    assert editor is not None
    assert editor.dataset_endpoint == "http://example.org/dataset"
    assert editor.provenance_endpoint == "http://example.org/provenance"
    assert editor.counter_handler == mock_counter_handler
    assert editor.resp_agent == URIRef("http://example.org/agent")


def test_create_method(editor: Editor) -> None:
    """Test the create method with various data types and graph contexts."""
    # Test creating a URI triple
    subject = URIRef("http://example.org/subject")
    predicate = URIRef("http://example.org/predicate")
    uri_value = URIRef("http://example.org/object")
    graph = URIRef("http://example.org/graph")

    editor.create(subject, predicate, uri_value, graph)

    # Verify the triple was added with graph context
    assert (subject, predicate, uri_value, graph) in editor.g_set

    # Test creating a literal with datatype
    literal_value = Literal("42", datatype=XSD.integer)
    editor.create(subject, predicate, literal_value, graph)
    assert (subject, predicate, literal_value, graph) in editor.g_set

    # Test creating a string literal
    string_value = Literal("test string")
    editor.create(subject, predicate, string_value, graph)
    assert (subject, predicate, string_value, graph) in editor.g_set

    # Test creating without graph context
    editor.dataset_is_quadstore = False
    editor.create(subject, predicate, uri_value)
    assert (subject, predicate, uri_value) in editor.g_set


def test_update_method_with_and_without_graph(editor: Editor) -> None:
    """Test the update method with and without graph context."""
    subject = URIRef("http://example.org/subject")
    predicate = URIRef("http://example.org/predicate")
    old_value = Literal("old value")
    new_value = Literal("new value")
    graph = URIRef("http://example.org/graph")

    # Add initial triple
    editor.create(subject, predicate, old_value, graph)
    assert (subject, predicate, old_value, graph) in editor.g_set

    # Test update with graph context
    editor.update(subject, predicate, old_value, new_value, graph)
    assert (subject, predicate, old_value, graph) not in editor.g_set
    assert (subject, predicate, new_value, graph) in editor.g_set

    # Test update without graph context
    editor.dataset_is_quadstore = False
    editor.create(subject, predicate, old_value)
    editor.update(subject, predicate, old_value, new_value)
    assert (subject, predicate, old_value) not in editor.g_set
    assert (subject, predicate, new_value) in editor.g_set


def test_update_method_with_uri_values(editor: Editor) -> None:
    """Test the update method with URI values."""
    subject = URIRef("http://example.org/subject")
    predicate = URIRef("http://example.org/predicate")
    graph = URIRef("http://example.org/graph")
    uri_old = URIRef("http://example.org/old")
    uri_new = URIRef("http://example.org/new")

    editor.create(subject, predicate, uri_old, graph)
    assert (subject, predicate, uri_old, graph) in editor.g_set

    editor.update(subject, predicate, uri_old, uri_new, graph)
    assert (subject, predicate, uri_old, graph) not in editor.g_set
    assert (subject, predicate, uri_new, graph) in editor.g_set


def test_delete_method(editor: Editor) -> None:
    """Test the delete method with various deletion scenarios."""
    subject = URIRef("http://example.org/subject")
    predicate = URIRef("http://example.org/predicate")
    value = Literal("test value")
    graph = URIRef("http://example.org/graph")

    # Setup test data
    editor.create(subject, predicate, value, graph)
    editor.create(subject, RDF.type, URIRef("http://example.org/TestType"), graph)

    # Test deleting a specific triple
    editor.delete(subject, predicate, value, graph)
    assert (subject, predicate, value, graph) not in editor.g_set
    assert (
        subject,
        RDF.type,
        URIRef("http://example.org/TestType"),
        graph,
    ) in editor.g_set

    # Test deleting all triples with a specific predicate
    editor.create(subject, predicate, Literal("value1"), graph)
    editor.create(subject, predicate, Literal("value2"), graph)
    editor.delete(subject, predicate, graph=graph)
    assert len(list(editor.g_set.triples((subject, predicate, None)))) == 0

    # Test deleting an entire entity
    editor.delete(subject)
    assert len(list(editor.g_set.triples((subject, None, None)))) == 0


def test_create_with_provenance(real_editor: Editor) -> None:
    """Test that create operations properly handle provenance information."""
    subject = URIRef("http://example.org/subject")
    predicate = URIRef("http://example.org/predicate")
    value = Literal("test value")
    graph = URIRef("http://example.org/graph")  # Default graph for the test

    try:
        # Create a triple and verify provenance is tracked
        real_editor.create(subject, predicate, value, graph)

        # Generate and save provenance
        real_editor.save()

        # Verify the triple was actually added
        assert (subject, predicate, value, graph) in real_editor.g_set

        # Setup SPARQL wrapper for provenance database
        provenance_sparql = SPARQLWrapper(real_editor.provenance_endpoint)
        provenance_sparql.setReturnFormat(JSON)

        # Verify that the triple was added with the correct responsible agent using SPARQL
        query = """
        PREFIX prov: <http://www.w3.org/ns/prov#>
        SELECT ?snapshot ?agent ?g
        WHERE {
            GRAPH ?g {
                ?snapshot prov:specializationOf ?subject ;
                         prov:wasAttributedTo ?agent .
            }
        }
        """
        provenance_sparql.setQuery(query)
        provenance_sparql.setMethod("GET")
        provenance_sparql.addParameter("subject", str(subject))
        results = provenance_sparql.queryAndConvert()

        # Convert results to a more manageable format
        bindings = results["results"]["bindings"]

        assert len(bindings) > 0, "No provenance found"
        assert any(
            binding["agent"]["value"] == str(real_editor.resp_agent)
            for binding in bindings
        ), "Responsible agent not found in provenance"

        # If a source was specified, verify it's tracked
        if real_editor.source:
            query = """
            PREFIX prov: <http://www.w3.org/ns/prov#>
            ASK {
                GRAPH ?g {
                    ?snapshot prov:specializationOf ?subject ;
                             prov:hadPrimarySource ?source .
                    FILTER(?source = ?primary_source)
                }
            }
            """
            provenance_sparql.setQuery(query)
            provenance_sparql.addParameter("subject", str(subject))
            provenance_sparql.addParameter("primary_source", str(real_editor.source))
            result = provenance_sparql.queryAndConvert()
            assert result["boolean"], "Source not found in provenance"

    finally:
        # Cleanup: delete the test data
        # First get the entity
        entity = real_editor.g_set.get_entity(subject)
        if entity:
            real_editor.delete(subject)
            real_editor.save()


def test_update_with_provenance(real_editor: Editor) -> None:
    """Test that update operations properly handle provenance information."""
    subject = URIRef("http://example.org/subject")
    predicate = URIRef("http://example.org/predicate")
    old_value = Literal("old value")
    new_value = Literal("new value")
    graph = URIRef("http://example.org/graph")

    try:
        # Setup initial state
        real_editor.create(subject, predicate, old_value, graph)
        real_editor.save()

        # Perform update
        real_editor.update(subject, predicate, old_value, new_value, graph)
        real_editor.save()

        # Setup SPARQL wrapper for provenance database
        provenance_sparql = SPARQLWrapper(real_editor.provenance_endpoint)
        provenance_sparql.setReturnFormat(JSON)

        # Verify that the update was tracked with the correct responsible agent
        query = """
        PREFIX prov: <http://www.w3.org/ns/prov#>
        SELECT ?snapshot ?agent ?time
        WHERE {
            GRAPH ?g {
                ?snapshot prov:specializationOf ?subject ;
                         prov:wasAttributedTo ?agent ;
                         prov:generatedAtTime ?time .
            }
        }
        ORDER BY DESC(?time)
        """
        provenance_sparql.setQuery(query)
        provenance_sparql.setMethod("GET")
        provenance_sparql.addParameter("subject", str(subject))
        results = provenance_sparql.queryAndConvert()

        # Convert results to a more manageable format
        bindings = results["results"]["bindings"]

        assert len(bindings) > 0, "No provenance found"
        assert any(
            binding["agent"]["value"] == str(real_editor.resp_agent)
            for binding in bindings
        ), "Responsible agent not found in provenance"

        # If a source was specified, verify it's tracked
        if real_editor.source:
            query = """
            PREFIX prov: <http://www.w3.org/ns/prov#>
            ASK {
                GRAPH ?g {
                    ?snapshot prov:specializationOf ?subject ;
                             prov:hadPrimarySource ?source .
                    FILTER(?source = ?primary_source)
                }
            }
            """
            provenance_sparql.setQuery(query)
            provenance_sparql.addParameter("subject", str(subject))
            provenance_sparql.addParameter("primary_source", str(real_editor.source))
            result = provenance_sparql.queryAndConvert()
            assert result["boolean"], "Source not found in provenance"

    finally:
        # Cleanup: delete the test data
        # First recreate the triple to ensure it's in g_set
        real_editor.create(subject, predicate, new_value, graph)
        real_editor.delete(subject)
        real_editor.save()


def test_delete_with_provenance(real_editor: Editor) -> None:
    """Test that delete operations properly handle provenance information."""
    subject = URIRef("http://example.org/subject")
    predicate = URIRef("http://example.org/predicate")
    value = Literal("test value")
    graph = URIRef("http://example.org/graph")

    try:
        # Setup initial state
        real_editor.create(subject, predicate, value, graph)
        real_editor.save()

        # Delete the triple
        # First recreate the triple to ensure it's in g_set
        real_editor.create(subject, predicate, value, graph)
        real_editor.delete(subject, predicate, value, graph)
        real_editor.save()

        # Setup SPARQL wrapper for provenance database
        provenance_sparql = SPARQLWrapper(real_editor.provenance_endpoint)
        provenance_sparql.setReturnFormat(JSON)

        # Verify that the deletion was tracked with the correct responsible agent
        # and that snapshots form a chain with wasDerivedFrom
        query = """
        PREFIX prov: <http://www.w3.org/ns/prov#>
        SELECT ?snapshot ?agent ?time ?derived_from ?invalidated_time
        WHERE {
            GRAPH ?g {
                ?snapshot prov:specializationOf ?subject ;
                         prov:wasAttributedTo ?agent ;
                         prov:generatedAtTime ?time .
                OPTIONAL { 
                    ?snapshot prov:wasDerivedFrom ?derived_from .
                }
                OPTIONAL {
                    ?snapshot prov:invalidatedAtTime ?invalidated_time .
                }
            }
        }
        ORDER BY DESC(?time)
        """
        provenance_sparql.setQuery(query)
        provenance_sparql.setMethod("GET")
        provenance_sparql.addParameter("subject", str(subject))
        results = provenance_sparql.queryAndConvert()

        # Convert results to a more manageable format
        bindings = results["results"]["bindings"]

        assert len(bindings) > 0, "No provenance found"
        assert any(
            binding["agent"]["value"] == str(real_editor.resp_agent)
            for binding in bindings
        ), "Responsible agent not found in provenance"

        # Verify the latest snapshot is invalidated (indicating deletion)
        latest_snapshot = bindings[0]  # Results are ordered by time DESC
        assert (
            "invalidated_time" in latest_snapshot
        ), "Latest snapshot not invalidated (not marked as deleted)"

        # Verify snapshots form a chain with wasDerivedFrom
        assert (
            "derived_from" in latest_snapshot
        ), "Latest snapshot not derived from previous one"

    finally:
        # Cleanup: ensure the entity is deleted
        # First recreate the triple to ensure it's in g_set
        real_editor.create(subject, predicate, value, graph)
        real_editor.delete(subject)
        real_editor.save()


def test_batch_operations(editor: Editor) -> None:
    """Test performing multiple operations in sequence."""
    subject = URIRef("http://example.org/subject")
    predicate1 = URIRef("http://example.org/predicate1")
    predicate2 = URIRef("http://example.org/predicate2")
    value1 = Literal("value1")
    value2 = Literal("value2")
    graph = URIRef("http://example.org/graph")

    # Create multiple triples
    editor.create(subject, predicate1, value1, graph)
    editor.create(subject, predicate2, value2, graph)

    # Verify all triples were created
    assert (subject, predicate1, value1, graph) in editor.g_set
    assert (subject, predicate2, value2, graph) in editor.g_set

    # Update one triple and delete another
    editor.update(subject, predicate1, value1, Literal("new value"), graph)
    editor.delete(subject, predicate2, value2, graph)

    # Verify final state
    assert (subject, predicate1, Literal("new value"), graph) in editor.g_set
    assert (subject, predicate2, value2, graph) not in editor.g_set

    # Delete the entire entity
    editor.delete(subject)

    # Verify entity is deleted
    assert len(list(editor.g_set.triples((subject, None, None)))) == 0


def test_error_handling(editor: Editor) -> None:
    """Test error handling in various scenarios."""
    subject = URIRef("http://example.org/subject")
    predicate = URIRef("http://example.org/predicate")
    value = Literal("test value")
    graph = URIRef("http://example.org/graph")

    # Test updating non-existent triple
    with pytest.raises(Exception):
        editor.update(subject, predicate, value, Literal("new value"), graph)

    # Test deleting non-existent triple with specific value
    with pytest.raises(Exception):
        editor.delete(subject, predicate, value, graph)

    # Test deleting non-existent entity
    with pytest.raises(Exception):
        editor.delete(subject)

    # Test deleting all triples with a non-existent subject and predicate
    with pytest.raises(Exception):
        editor.delete(subject, predicate)

    # Test creating invalid triple (e.g., with None values)
    with pytest.raises(Exception):
        editor.create(None, predicate, value)

    with pytest.raises(Exception):
        editor.create(subject, None, value)


def test_complex_entity_operations(editor: Editor) -> None:
    """Test operations on complex entities with multiple properties."""
    # Create an entity with multiple properties
    subject = URIRef("http://example.org/entity1")
    type_pred = RDF.type
    type_value = URIRef("http://example.org/TestType")
    label_pred = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
    label_value = Literal("Test Entity")
    date_pred = URIRef("http://example.org/date")
    date_value = Literal("2024-03-20", datatype=XSD.date)
    graph = URIRef("http://example.org/graph")

    # Add all properties
    editor.create(subject, type_pred, type_value, graph)
    editor.create(subject, label_pred, label_value, graph)
    editor.create(subject, date_pred, date_value, graph)

    # Verify all properties were added
    assert (subject, type_pred, type_value, graph) in editor.g_set
    assert (subject, label_pred, label_value, graph) in editor.g_set
    assert (subject, date_pred, date_value, graph) in editor.g_set

    # Update some properties
    new_label = Literal("Updated Test Entity")
    editor.update(subject, label_pred, label_value, new_label, graph)

    # Delete one property
    editor.delete(subject, date_pred, date_value, graph)

    # Verify final state
    assert (subject, type_pred, type_value, graph) in editor.g_set
    assert (subject, label_pred, new_label, graph) in editor.g_set
    assert (subject, date_pred, date_value, graph) not in editor.g_set


def test_nested_entity_handling(editor: Editor) -> None:
    """Test handling of nested entities with relationships."""
    # Create main entity
    main_entity = URIRef("http://example.org/main")
    type_pred = RDF.type
    main_type = URIRef("http://example.org/MainType")

    # Create nested entity
    nested_entity = URIRef("http://example.org/nested")
    nested_type = URIRef("http://example.org/NestedType")

    # Create relationship predicate
    has_nested = URIRef("http://example.org/hasNested")

    graph = URIRef("http://example.org/graph")

    # Create the entities and their relationship
    editor.create(main_entity, type_pred, main_type, graph)
    editor.create(nested_entity, type_pred, nested_type, graph)
    editor.create(main_entity, has_nested, nested_entity, graph)

    # Verify the structure
    assert (main_entity, type_pred, main_type, graph) in editor.g_set
    assert (nested_entity, type_pred, nested_type, graph) in editor.g_set
    assert (main_entity, has_nested, nested_entity, graph) in editor.g_set

    # Delete nested entity and verify cascading effects
    editor.delete(nested_entity)

    # Main entity should still exist but relationship should be gone
    assert (main_entity, type_pred, main_type, graph) in editor.g_set
    assert (main_entity, has_nested, nested_entity, graph) not in editor.g_set
    assert len(list(editor.g_set.triples((nested_entity, None, None)))) == 0


def test_update_nonexistent_triple(editor: Editor) -> None:
    """Test error handling when updating a non-existent triple."""
    subject = URIRef("http://example.org/subject")
    predicate = URIRef("http://example.org/predicate")
    old_value = Literal("non-existent value")
    new_value = Literal("new value")
    graph = URIRef("http://example.org/graph")

    # Test with quadstore and graph
    with pytest.raises(Exception) as excinfo:
        editor.update(subject, predicate, old_value, new_value, graph)
    assert f"Triple ({subject}, {predicate}, {old_value}, {graph}) does not exist" in str(excinfo.value)

    # Test with non-quadstore
    editor.dataset_is_quadstore = False
    with pytest.raises(Exception) as excinfo:
        editor.update(subject, predicate, old_value, new_value)
    assert f"Triple ({subject}, {predicate}, {old_value}) does not exist" in str(excinfo.value)

    # Create a triple and then try to update with wrong old_value
    correct_value = Literal("correct value")
    editor.create(subject, predicate, correct_value)
    with pytest.raises(Exception) as excinfo:
        editor.update(subject, predicate, old_value, new_value)
    assert f"Triple ({subject}, {predicate}, {old_value}) does not exist" in str(excinfo.value)


def test_delete_nonexistent_triple(editor: Editor) -> None:
    """Test error handling when deleting a non-existent triple."""
    subject = URIRef("http://example.org/subject")
    predicate = URIRef("http://example.org/predicate")
    value = Literal("non-existent value")
    graph = URIRef("http://example.org/graph")

    # Test deleting a specific non-existent triple with quadstore and graph
    with pytest.raises(Exception) as excinfo:
        editor.delete(subject, predicate, value, graph)
    assert f"Triple ({subject}, {predicate}, {value}, {graph}) does not exist" in str(excinfo.value)

    # Test deleting a specific non-existent triple with non-quadstore
    editor.dataset_is_quadstore = False
    with pytest.raises(Exception) as excinfo:
        editor.delete(subject, predicate, value)
    assert f"Triple ({subject}, {predicate}, {value}) does not exist" in str(excinfo.value)

    # Test deleting all triples with a non-existent subject and predicate in quadstore
    editor.dataset_is_quadstore = True
    with pytest.raises(Exception) as excinfo:
        editor.delete(subject, predicate, graph=graph)
    assert f"No triples found with subject {subject} and predicate {predicate} in graph {graph}" in str(excinfo.value)

    # Test deleting all triples with a non-existent subject and predicate in non-quadstore
    editor.dataset_is_quadstore = False
    with pytest.raises(Exception) as excinfo:
        editor.delete(subject, predicate)
    assert f"No triples found with subject {subject} and predicate {predicate}" in str(excinfo.value)

    # Test deleting a non-existent entity
    with pytest.raises(Exception) as excinfo:
        editor.delete(subject)
    assert f"Entity {subject} does not exist" in str(excinfo.value)


def test_update_triple_removal_and_addition_non_quadstore(editor: Editor) -> None:
    """Test the removal and addition of triples in the non-quadstore context of the update method."""
    # Setup
    editor.dataset_is_quadstore = False
    subject = URIRef("http://example.org/subject")
    predicate = URIRef("http://example.org/predicate")
    old_value = Literal("old value")
    new_value = Literal("new value")

    # Create the initial triple
    editor.create(subject, predicate, old_value)
    
    # Verify the triple was created
    assert (subject, predicate, old_value) in editor.g_set
    
    # Update the triple
    editor.update(subject, predicate, old_value, new_value)
    
    # Verify the old triple was removed
    assert (subject, predicate, old_value) not in editor.g_set
    
    # Verify the new triple was added
    assert (subject, predicate, new_value) in editor.g_set
    
    # Test with string predicate that needs to be normalized to URIRef
    string_predicate = "http://example.org/string-predicate"
    editor.create(subject, string_predicate, old_value)
    
    # Verify the triple was created with normalized predicate
    assert (subject, URIRef(string_predicate), old_value) in editor.g_set
    
    # Update using string predicate
    editor.update(subject, string_predicate, old_value, new_value)
    
    # Verify the old triple was removed and new one added with normalized predicate
    assert (subject, URIRef(string_predicate), old_value) not in editor.g_set
    assert (subject, URIRef(string_predicate), new_value) in editor.g_set
    
    # Verify the responsible agent and primary source were set correctly
    # Get all triples for the subject
    triples = list(editor.g_set.triples((subject, None, None)))
    
    # Verify there are two triples (one for each predicate)
    assert len(triples) == 2
    
    # Test with URI values
    uri_old = URIRef("http://example.org/old")
    uri_new = URIRef("http://example.org/new")
    
    # Create the initial triple with URI value
    editor.create(subject, predicate, uri_old)
    
    # Update the triple
    editor.update(subject, predicate, uri_old, uri_new)
    
    # Verify the old triple was removed
    assert (subject, predicate, uri_old) not in editor.g_set
    
    # Verify the new triple was added
    assert (subject, predicate, uri_new) in editor.g_set


def test_update_resp_agent_and_primary_source_non_quadstore(editor: Editor) -> None:
    """Test the resp_agent and primary_source parameters when adding a triple in the non-quadstore context of the update method."""
    # Setup
    editor.dataset_is_quadstore = False
    subject = URIRef("http://example.org/subject")
    predicate = URIRef("http://example.org/predicate")
    old_value = Literal("old value")
    new_value = Literal("new value")
    
    # Set a custom source
    custom_source = URIRef("http://example.org/custom-source")
    editor.source = custom_source
    
    # Create the initial triple
    editor.create(subject, predicate, old_value)
    
    # Save the original g_set
    original_g_set = editor.g_set
    
    # Create a new OCDMGraph with the same counter_handler
    new_g_set = OCDMGraph(editor.counter_handler)
    
    # Add the triple to the new graph
    new_g_set.add((subject, predicate, old_value))
    
    # Replace the editor's g_set with our new one
    editor.g_set = new_g_set
    
    # Patch the add method to check if it's called with the correct parameters
    with patch.object(new_g_set, 'add', wraps=new_g_set.add) as mock_add:
        # Update the triple
        editor.update(subject, predicate, old_value, new_value)
        
        # Verify that add was called with the correct parameters
        mock_add.assert_called_with(
            (subject, predicate, new_value),
            resp_agent=editor.resp_agent,
            primary_source=custom_source
        )
    
    # Verify the triple was updated
    assert (subject, predicate, old_value) not in new_g_set
    assert (subject, predicate, new_value) in new_g_set
    
    # Restore the original g_set
    editor.g_set = original_g_set
    
    # Reset the source
    editor.source = None


def test_import_entity_method(editor: Editor) -> None:
    """Test the import_entity method which calls Reader.import_entities_from_triplestore."""
    subject = URIRef("http://example.org/entity")
    
    # Mock the Reader.import_entities_from_triplestore method
    with patch('heritrace.editor.Reader.import_entities_from_triplestore') as mock_import:
        # Call the method under test
        editor.import_entity(subject)
        
        # Verify Reader.import_entities_from_triplestore was called with the correct parameters
        mock_import.assert_called_once_with(
            editor.g_set,
            editor.dataset_endpoint,
            [subject]
        )


def test_to_posix_timestamp(editor: Editor) -> None:
    """Test the to_posix_timestamp method which converts datetime or string to POSIX timestamp."""
    # Test with datetime object
    test_datetime = datetime(2023, 1, 1, 12, 0, 0)
    expected_timestamp = test_datetime.timestamp()
    result = editor.to_posix_timestamp(test_datetime)
    assert result == expected_timestamp
    
    # Test with ISO format string
    test_string = "2023-01-01T12:00:00"
    expected_timestamp = datetime(2023, 1, 1, 12, 0, 0).timestamp()
    result = editor.to_posix_timestamp(test_string)
    assert result == expected_timestamp
    
    # Test with None value
    result = editor.to_posix_timestamp(None)
    assert result is None


def test_delete_non_quadstore(editor: Editor) -> None:
    """Test delete method behavior when dataset is not a quadstore."""
    # Setup
    editor.dataset_is_quadstore = False
    subject = URIRef("http://example.org/subject")
    predicate1 = URIRef("http://example.org/predicate1")
    predicate2 = URIRef("http://example.org/predicate2")
    value1 = Literal("value1")
    value2 = Literal("value2")
    
    # Create test triples
    editor.create(subject, predicate1, value1)
    editor.create(subject, predicate2, value2)
    
    # Verify triples were created
    assert (subject, predicate1, value1) in editor.g_set, "First triple not created"
    assert (subject, predicate2, value2) in editor.g_set, "Second triple not created"
    
    # Test deleting a specific triple
    editor.delete(subject, predicate1, value1)
    assert (subject, predicate1, value1) not in editor.g_set, "First triple not deleted"
    assert (subject, predicate2, value2) in editor.g_set, "Second triple unexpectedly deleted"
    
    # Test deleting all triples with a specific predicate
    editor.create(subject, predicate1, Literal("another value"))
    editor.delete(subject, predicate1)
    assert len(list(editor.g_set.triples((subject, predicate1, None)))) == 0, "Not all triples with predicate1 were deleted"
    assert (subject, predicate2, value2) in editor.g_set, "Triple with predicate2 unexpectedly deleted"
    
    # Test deleting an entire entity
    other_subject = URIRef("http://example.org/other-subject")
    editor.create(other_subject, predicate1, value1)
    editor.create(subject, predicate1, value1)  # Add another triple to subject
    
    # Create a triple where our subject is the object
    editor.create(other_subject, predicate2, subject)
    
    editor.delete(subject)
    
    # Verify all triples with subject are removed
    remaining_triples = list(editor.g_set.triples((subject, None, None)))
    assert len(remaining_triples) == 0, f"Entity not fully deleted, remaining triples: {remaining_triples}"
    
    # Verify triples where subject was the object are also removed
    assert (other_subject, predicate2, subject) not in editor.g_set, "Triple with subject as object not deleted"
    
    # Verify other triples are unaffected
    assert (other_subject, predicate1, value1) in editor.g_set, "Unrelated triple was affected"
    
    # Test error cases
    with pytest.raises(Exception) as excinfo:
        editor.delete(URIRef("http://example.org/nonexistent"))
    assert "Entity http://example.org/nonexistent does not exist" in str(excinfo.value)
    
    with pytest.raises(Exception) as excinfo:
        editor.delete(other_subject, URIRef("http://example.org/nonexistent-pred"))
    assert f"No triples found with subject {other_subject} and predicate http://example.org/nonexistent-pred" in str(excinfo.value)
    
    with pytest.raises(Exception) as excinfo:
        editor.delete(other_subject, predicate1, Literal("nonexistent value"))
    assert f"Triple ({other_subject}, {predicate1}, nonexistent value) does not exist" in str(excinfo.value)
