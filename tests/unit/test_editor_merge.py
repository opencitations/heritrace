from unittest.mock import MagicMock, call, patch

import pytest
from heritrace.editor import Editor
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from rdflib_ocdm.ocdm_graph import OCDMConjunctiveGraph, OCDMGraph
from SPARQLWrapper import JSON

DATASET_ENDPOINT = "http://localhost:9999/blazegraph/sparql"
PROVENANCE_ENDPOINT = "http://localhost:9998/blazegraph/sparql"
RESP_AGENT = URIRef("http://example.org/agent")
KEEP_URI = URIRef("http://example.org/entity/keep")
DELETE_URI = URIRef("http://example.org/entity/delete")
INCOMING_SUBJ_URI = URIRef("http://example.org/entity/incoming")
OUTGOING_OBJ_URI = URIRef("http://example.org/entity/outgoing")
PROP_INCOMING = URIRef("http://example.org/prop/incomingRef")
PROP_OUTGOING = URIRef("http://example.org/prop/outgoingRef")
PROP_LITERAL = URIRef("http://example.org/prop/literal")
LITERAL_VALUE = Literal("Some value")
TYPE_TO_DELETE_URI = URIRef("http://example.org/TypeToDelete")


@pytest.fixture
def mock_counter_handler():
    """Fixture for a mocked CounterHandler."""
    mock = MagicMock(spec=CounterHandler)
    mock.read_counter.return_value = 1
    mock.set_counter.return_value = None
    return mock

@pytest.fixture
def mock_sparql_wrapper():
    """Fixture for a mocked SPARQLWrapperWithRetry."""
    with patch('heritrace.editor.SPARQLWrapperWithRetry') as mock_sparql:
        mock_instance = MagicMock()
        mock_sparql.return_value = mock_instance
        mock_instance.query.return_value.convert.return_value = {
            "results": {"bindings": []} # Default: no results
        }
        yield mock_instance # Yield the instance for configuration in tests

@pytest.fixture
def mock_reader():
    """Fixture for mocking Reader.import_entities_from_triplestore 
        and simulating the population of entity_index."""
    
    def mock_import_and_index(g_set, endpoint, entities_to_import):
        """Mock function that simulates indexing with required keys."""
        for entity_uri in entities_to_import:
            if entity_uri not in g_set.entity_index:
                g_set.entity_index[entity_uri] = {
                    'to_be_deleted': False,
                    'is_restored': False,
                    'source': None, 
                    'resp_agent': None
                }

    # Mock the static method directly on the class
    with patch('heritrace.editor.Reader.import_entities_from_triplestore', side_effect=mock_import_and_index) as mock_import:
        yield mock_import # Yield the mock static method itself

@pytest.fixture
def mock_storer():
    """Fixture for mocking Storer class and its methods."""
    with patch('heritrace.editor.Storer') as mock_storer_cls:
        mock_instance = MagicMock()
        mock_storer_cls.return_value = mock_instance
        mock_instance.upload_all.return_value = None
        yield mock_storer_cls


@pytest.fixture
def editor_instance(mock_counter_handler, mock_reader, mock_storer):
    """Fixture for an Editor instance using real OCDMGraph/ConjunctiveGraph."""
    editor = Editor(
        dataset_endpoint=DATASET_ENDPOINT,
        provenance_endpoint=PROVENANCE_ENDPOINT,
        counter_handler=mock_counter_handler,
        resp_agent=RESP_AGENT,
        dataset_is_quadstore=True # Use OCDMConjunctiveGraph
    )
    return editor

@pytest.fixture
def editor_instance_non_quadstore(mock_counter_handler, mock_reader, mock_storer):
    """Fixture for an Editor instance configured for non-quadstore."""
    editor = Editor(
        dataset_endpoint=DATASET_ENDPOINT,
        provenance_endpoint=PROVENANCE_ENDPOINT,
        counter_handler=mock_counter_handler,
        resp_agent=RESP_AGENT,
        dataset_is_quadstore=False # Use OCDMGraph
    )
    return editor


def test_merge_basic(editor_instance, mock_sparql_wrapper, mock_reader, mock_storer):
    """Test basic merge functionality with incoming and outgoing triples."""
    mock_sparql_wrapper.setQuery.side_effect = lambda query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        # Response for incoming query
        {"results": {"bindings": [{"s": {"type": "uri", "value": str(INCOMING_SUBJ_URI)}, "p": {"type": "uri", "value": str(PROP_INCOMING)}}]}},
        # Response for outgoing query
        {"results": {"bindings": [
            {"p": {"type": "uri", "value": str(PROP_OUTGOING)}, "o": {"type": "uri", "value": str(OUTGOING_OBJ_URI)}},
            {"p": {"type": "uri", "value": str(PROP_LITERAL)}, "o": {"type": "literal", "value": str(LITERAL_VALUE)}},
            {"p": {"type": "uri", "value": str(RDF.type)}, "o": {"type": "uri", "value": str(TYPE_TO_DELETE_URI)}}
        ]}}
    ]

    # Call the merge function
    editor_instance.merge(KEEP_URI, DELETE_URI)

    # --- Assertions ---
    # 1. Assert SPARQL queries were made correctly
    expected_incoming_query = f"SELECT DISTINCT ?s ?p WHERE {{ ?s ?p <{DELETE_URI}> . FILTER (?s != <{KEEP_URI}>) }}"
    expected_outgoing_query = f"""
                PREFIX rdf: <{RDF}>
                SELECT DISTINCT ?p ?o WHERE {{
                    <{DELETE_URI}> ?p ?o .
                    FILTER (?p != rdf:type)
                }}
            """
    normalize_ws = lambda s: " ".join(s.strip().split())
    actual_calls = [normalize_ws(call[0][0]) for call in mock_sparql_wrapper.setQuery.call_args_list]
    assert normalize_ws(expected_incoming_query) in actual_calls
    assert normalize_ws(expected_outgoing_query) in actual_calls
    assert mock_sparql_wrapper.setReturnFormat.call_args_list == [call(JSON), call(JSON)]
    assert mock_sparql_wrapper.query.call_count == 2

    # 2. Assert Reader.import_entities_from_triplestore was called correctly
    expected_import_entities = {KEEP_URI, DELETE_URI, INCOMING_SUBJ_URI, OUTGOING_OBJ_URI, TYPE_TO_DELETE_URI}
    mock_reader.assert_called_once()
    call_args, call_kwargs = mock_reader.call_args
    # The first arg to import_entities_from_triplestore is the graph set instance
    assert isinstance(call_args[0], OCDMConjunctiveGraph) # Check it's the real graph
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == expected_import_entities

    # 3. Assert save sequence was called (Storer init, upload_all)
    # Storer class should be called twice (for dataset and provenance)
    assert mock_storer.call_count == 2
    # Check arguments passed to Storer.__init__
    init_call_args_list = mock_storer.call_args_list
    assert isinstance(init_call_args_list[0][0][0], OCDMConjunctiveGraph) # First call with dataset graph
    assert isinstance(init_call_args_list[1][0][0], Graph) # Second call with provenance graph (g_set.provenance)

    # Check calls to the mocked Storer instance's upload_all method
    mock_storer_instance = mock_storer.return_value
    # Since Storer() is called twice, return_value is the *second* instance.
    # We need to check the upload_all calls on *both* instances. Let's use call_args_list on the instance mock.
    # No, mock_storer is the CLASS mock. mock_storer.return_value is the INSTANCE mock returned by __init__.
    # Need to check calls on the instances returned by the two __init__ calls.
    # Easier: check the total call count on the method of the return_value mock.
    assert mock_storer_instance.upload_all.call_count == 2
    # Check the endpoints passed to upload_all
    upload_calls = mock_storer_instance.upload_all.call_args_list
    assert upload_calls[0] == call(DATASET_ENDPOINT)
    assert upload_calls[1] == call(PROVENANCE_ENDPOINT)


def test_merge_no_incoming(editor_instance, mock_sparql_wrapper, mock_reader, mock_storer):
    """Test merge when the entity to be deleted has no incoming references."""
    mock_sparql_wrapper.setQuery.side_effect = lambda query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        {"results": {"bindings": []}}, # No incoming
        {"results": {"bindings": [{"p": {"type": "uri", "value": str(PROP_LITERAL)}, "o": {"type": "literal", "value": "Test Value"}}]}} # Outgoing
    ]

    editor_instance.merge(KEEP_URI, DELETE_URI)

    expected_import_entities = {KEEP_URI, DELETE_URI}
    mock_reader.assert_called_once()
    call_args, _ = mock_reader.call_args
    assert isinstance(call_args[0], OCDMConjunctiveGraph)
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == expected_import_entities

    # Assert save sequence happened
    assert mock_storer.call_count == 2
    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2


# Test 3: Merge with no outgoing properties (except rdf:type)
def test_merge_no_outgoing(editor_instance, mock_sparql_wrapper, mock_reader, mock_storer):
    """Test merge when the entity to be deleted has no outgoing properties (except rdf:type)."""
    mock_sparql_wrapper.setQuery.side_effect = lambda query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        {"results": {"bindings": [{"s": {"type": "uri", "value": str(INCOMING_SUBJ_URI)}, "p": {"type": "uri", "value": str(PROP_INCOMING)}}]}}, # Incoming
        {"results": {"bindings": []}} # No outgoing
    ]

    editor_instance.merge(KEEP_URI, DELETE_URI)

    expected_import_entities = {KEEP_URI, DELETE_URI, INCOMING_SUBJ_URI}
    mock_reader.assert_called_once()
    call_args, _ = mock_reader.call_args
    assert isinstance(call_args[0], OCDMConjunctiveGraph)
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == expected_import_entities

    # Assert save sequence happened
    assert mock_storer.call_count == 2
    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2


def test_merge_self(editor_instance, mock_storer):
    """Test attempting to merge an entity with itself raises ValueError."""
    with pytest.raises(ValueError, match="Cannot merge an entity with itself."):
        editor_instance.merge(KEEP_URI, KEEP_URI)

    # Ensure Storer was not called
    mock_storer.assert_not_called()


def test_merge_sparql_error(editor_instance, mock_sparql_wrapper, mock_reader, mock_storer):
    """Test that an exception during SPARQL query prevents saving."""
    mock_sparql_wrapper.query.side_effect = Exception("SPARQL endpoint unavailable")

    with pytest.raises(Exception, match="SPARQL endpoint unavailable"):
        editor_instance.merge(KEEP_URI, DELETE_URI)

    # Assert that Reader and Storer were not called
    mock_reader.assert_not_called()
    mock_storer.assert_not_called()


def test_merge_reader_error(editor_instance, mock_sparql_wrapper, mock_reader, mock_storer):
    """Test that an exception during entity import prevents saving."""
    mock_sparql_wrapper.setQuery.side_effect = lambda query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        {"results": {"bindings": []}}, {"results": {"bindings": []}}
    ]
    mock_reader.side_effect = Exception("Import failed") # Make the mocked method raise

    with pytest.raises(Exception, match="Import failed"):
        editor_instance.merge(KEEP_URI, DELETE_URI)

    # Assert that import was attempted but Storer was not called
    mock_reader.assert_called_once()
    mock_storer.assert_not_called()


# def test_merge_storer_error(editor_instance, mock_sparql_wrapper, mock_reader, mock_storer):
#     """Test that an exception during Storer upload prevents commit."""
#     mock_sparql_wrapper.setQuery.side_effect = lambda query: None
#     mock_sparql_wrapper.query.return_value.convert.side_effect = [
#         {"results": {"bindings": []}}, {"results": {"bindings": []}}
#     ]

#     mock_storer_instance = mock_storer.return_value
#     mock_storer_instance.upload_all.side_effect = Exception("Upload failed") 

#     # Expect the Exception from upload_all
#     with pytest.raises(Exception, match="Upload failed"):
#         editor_instance.merge(KEEP_URI, DELETE_URI)

#     mock_reader.assert_called_once()
#     # Assert that Storer constructor was called, and upload was attempted
#     assert mock_storer.call_count >= 1 # Called at least once for dataset storer
#     mock_storer_instance.upload_all.assert_called_once_with(DATASET_ENDPOINT)
#     # We can't easily assert commit_changes wasn't called on the real graph


def test_merge_literal_types(editor_instance, mock_sparql_wrapper, mock_reader, mock_storer):
    """Test merge with literals having language tags and datatypes."""
    PROP_LANG = URIRef("http://example.org/prop/langLiteral")
    PROP_DTYPE = URIRef("http://example.org/prop/dtypeLiteral")

    mock_sparql_wrapper.setQuery.side_effect = lambda query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        {"results": {"bindings": []}}, # Incoming
        {"results": {"bindings": [ # Outgoing
            {"p": {"type": "uri", "value": str(PROP_LANG)}, "o": {"type": "literal", "value": "Bonjour", "xml:lang": "fr"}},
            {"p": {"type": "uri", "value": str(PROP_DTYPE)}, "o": {"type": "typed-literal", "value": "123", "datatype": "http://www.w3.org/2001/XMLSchema#integer"}}
        ]}}
    ]

    editor_instance.merge(KEEP_URI, DELETE_URI)

    # Primary check: Did the operation complete by calling Storer?
    assert mock_storer.call_count == 2
    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2


def test_merge_non_quadstore(editor_instance_non_quadstore, mock_sparql_wrapper, mock_reader, mock_storer):
    """Test merge behavior when editor is configured for a non-quadstore (triple store)."""
    # Use the specific fixture editor_instance_non_quadstore
    editor = editor_instance_non_quadstore

    mock_sparql_wrapper.setQuery.side_effect = lambda query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        {"results": {"bindings": []}}, # No incoming
        {"results": {"bindings": []}}, # No outgoing
    ]

    editor.merge(KEEP_URI, DELETE_URI)

    # Assertions
    # 1. SPARQL queries
    assert mock_sparql_wrapper.setQuery.call_count == 2
    assert mock_sparql_wrapper.query.call_count == 2

    # 2. Reader import uses the correct graph instance (OCDMGraph)
    mock_reader.assert_called_once()
    call_args, _ = mock_reader.call_args
    assert isinstance(call_args[0], OCDMGraph) # Check it's the non-conjunctive graph
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == {KEEP_URI, DELETE_URI} # Only keep/delete URIs expected here

    # 3. Save sequence uses correct graph instance
    assert mock_storer.call_count == 2
    init_call_args_list = mock_storer.call_args_list
    assert isinstance(init_call_args_list[0][0][0], OCDMGraph) # First call with dataset graph
    assert isinstance(init_call_args_list[1][0][0], Graph) # Second call with provenance graph

    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2
    upload_calls = mock_storer_instance.upload_all.call_args_list
    assert upload_calls[0] == call(DATASET_ENDPOINT)
    assert upload_calls[1] == call(PROVENANCE_ENDPOINT)


def test_merge_skip_blank_node(editor_instance, mock_sparql_wrapper, mock_reader, mock_storer):
    """Test that non-URI/Literal objects (e.g., blank nodes) are skipped with a warning."""
    BNODE_PROP = URIRef("http://example.org/prop/bnodeRef")
    BNODE_ID = "bnode123"
    LITERAL_PROP_2 = URIRef("http://example.org/prop/anotherLiteral")
    LITERAL_VALUE_2 = Literal("Another value")

    mock_sparql_wrapper.setQuery.side_effect = lambda query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        # Incoming query (empty)
        {"results": {"bindings": []}},
        # Outgoing query (with bnode and literal)
        {
            "results": {
                "bindings": [
                    {
                        "p": {"type": "uri", "value": str(BNODE_PROP)},
                        "o": {"type": "bnode", "value": BNODE_ID}, # Blank Node
                    },
                    {
                        "p": {"type": "uri", "value": str(LITERAL_PROP_2)},
                        "o": {"type": "literal", "value": str(LITERAL_VALUE_2)},
                    },
                ]
            }
        },
    ]

    # Patch print to capture the warning
    with patch('builtins.print') as mock_print:
        editor_instance.merge(KEEP_URI, DELETE_URI)

        expected_warning = f"Warning: Skipping non-URI/Literal object type 'bnode' from {DELETE_URI} via {BNODE_PROP}"
        # Check if any call to print matches the warning
        found_warning = False
        for call_args, call_kwargs in mock_print.call_args_list:
            if call_args and call_args[0] == expected_warning:
                found_warning = True
                break
        assert found_warning, f"Expected warning '{expected_warning}' was not printed."

    # Assert Reader was called (only keep/delete URIs, as bnode and its prop aren't imported)
    expected_import_entities = {KEEP_URI, DELETE_URI}
    mock_reader.assert_called_once()
    call_args, _ = mock_reader.call_args
    assert isinstance(call_args[0], OCDMConjunctiveGraph) # Assuming quadstore instance
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == expected_import_entities

    # Assert save sequence completed, indicating the literal was processed
    assert mock_storer.call_count == 2
    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2