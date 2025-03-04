"""
Tests for the editor module.
"""

from unittest.mock import MagicMock
from SPARQLWrapper import JSON, SPARQLWrapper

import pytest

# Import the editor module
from heritrace.editor import Editor
from rdflib import RDF, XSD, Literal, URIRef
from rdflib_ocdm.ocdm_graph import OCDMConjunctiveGraph, OCDMGraph
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
        OCDMConjunctiveGraph(editor.counter_handler)
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
