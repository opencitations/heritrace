# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from functools import partial
from unittest.mock import MagicMock, call, patch

import pytest
from flask import Flask
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from rdflib_ocdm.ocdm_graph import OCDMDataset, OCDMGraph
from SPARQLWrapper import JSON

from heritrace.counter_handler import TransactionalCounterHandler
from heritrace.editor import Editor, EditorError, EndpointConfig

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


def _record_upload(events: list[object], endpoint: str) -> bool:
    events.append(endpoint)
    return True


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
    with patch("heritrace.editor.SPARQLWrapperWithRetry") as mock_sparql:
        mock_instance = MagicMock()
        mock_sparql.return_value = mock_instance
        mock_instance.query.return_value.convert.return_value = {
            "results": {"bindings": []}  # Default: no results
        }
        yield mock_instance  # Yield the instance for configuration in tests


@pytest.fixture
def mock_reader():
    """Fixture for mocking Reader.import_entities_from_triplestore
    and simulating the population of entity_index."""

    def mock_import_and_index(g_set, _endpoint, entities_to_import) -> None:
        """Mock function that simulates indexing with required keys."""
        for entity_uri in entities_to_import:
            if entity_uri not in g_set.entity_index:
                g_set.entity_index[entity_uri] = {
                    "to_be_deleted": False,
                    "is_restored": False,
                    "source": None,
                    "resp_agent": None,
                }

    # Mock the static method directly on the class
    with patch(
        "heritrace.editor.Reader.import_entities_from_triplestore",
        side_effect=mock_import_and_index,
    ) as mock_import:
        yield mock_import  # Yield the mock static method itself


@pytest.fixture
def mock_storer():
    """Fixture for mocking Storer class and its methods."""
    with patch("heritrace.editor.Storer") as mock_storer_cls:
        mock_instance = MagicMock()
        mock_storer_cls.return_value = mock_instance
        mock_instance.upload_all.return_value = True
        yield mock_storer_cls


@pytest.fixture
def editor_instance(mock_counter_handler, mock_reader, mock_storer):
    """Fixture for an Editor instance using real OCDMGraph/ConjunctiveGraph."""
    return Editor(
        EndpointConfig(
            dataset=DATASET_ENDPOINT,
            provenance=PROVENANCE_ENDPOINT,
            is_quadstore=True,
        ),
        mock_counter_handler,
        RESP_AGENT,
    )


@pytest.fixture
def editor_instance_non_quadstore(mock_counter_handler, mock_reader, mock_storer):
    """Fixture for an Editor instance configured for non-quadstore."""
    return Editor(
        EndpointConfig(
            dataset=DATASET_ENDPOINT,
            provenance=PROVENANCE_ENDPOINT,
            is_quadstore=False,
        ),
        mock_counter_handler,
        RESP_AGENT,
    )


def test_save_plugin_runs_after_uploads_and_before_commit(
    mock_counter_handler, mock_storer
) -> None:
    events = []
    save_plugin = MagicMock()
    editor = Editor(
        EndpointConfig(
            dataset=DATASET_ENDPOINT,
            provenance=PROVENANCE_ENDPOINT,
            is_quadstore=True,
        ),
        mock_counter_handler,
        RESP_AGENT,
        save_plugin=save_plugin,
    )

    mock_storer.return_value.upload_all.side_effect = partial(_record_upload, events)

    def record_plugin(_graph: object) -> None:
        events.append("plugin")

    save_plugin.persist.side_effect = record_plugin

    with (
        patch.object(
            editor.g_set,
            "generate_provenance",
            side_effect=lambda: events.append("provenance"),
        ),
        patch.object(
            editor.g_set,
            "commit_changes",
            side_effect=lambda: events.append("commit"),
        ),
    ):
        editor.save()

    assert events == [
        "provenance",
        DATASET_ENDPOINT,
        PROVENANCE_ENDPOINT,
        "plugin",
        "commit",
    ]
    save_plugin.persist.assert_called_once_with(editor.g_set)


def test_save_commits_transactional_counter_after_graph_commit(mock_storer) -> None:
    events = []
    counter_handler = MagicMock(spec=TransactionalCounterHandler)
    counter_handler.begin_counter_transaction.side_effect = lambda: events.append(
        "counter_begin"
    )
    counter_handler.commit_counter_transaction.side_effect = lambda: events.append(
        "counter_commit"
    )
    save_plugin = MagicMock()
    editor = Editor(
        EndpointConfig(
            dataset=DATASET_ENDPOINT,
            provenance=PROVENANCE_ENDPOINT,
            is_quadstore=True,
        ),
        counter_handler,
        RESP_AGENT,
        save_plugin=save_plugin,
    )

    mock_storer.return_value.upload_all.side_effect = partial(_record_upload, events)
    save_plugin.persist.side_effect = lambda _graph: events.append("plugin")

    with (
        patch.object(
            editor.g_set,
            "generate_provenance",
            side_effect=lambda: events.append("provenance"),
        ),
        patch.object(
            editor.g_set,
            "commit_changes",
            side_effect=lambda: events.append("graph_commit"),
        ),
    ):
        editor.save()

    assert events == [
        "counter_begin",
        "provenance",
        DATASET_ENDPOINT,
        PROVENANCE_ENDPOINT,
        "plugin",
        "graph_commit",
        "counter_commit",
    ]
    counter_handler.rollback_counter_transaction.assert_not_called()


def test_save_rolls_back_transactional_counter_on_failure(mock_storer) -> None:
    counter_handler = MagicMock(spec=TransactionalCounterHandler)
    save_plugin = MagicMock()
    save_plugin.persist.side_effect = OSError("RDF file write failed")
    editor = Editor(
        EndpointConfig(
            dataset=DATASET_ENDPOINT,
            provenance=PROVENANCE_ENDPOINT,
            is_quadstore=True,
        ),
        counter_handler,
        RESP_AGENT,
        save_plugin=save_plugin,
    )

    with (
        patch.object(editor.g_set, "generate_provenance"),
        patch.object(editor.g_set, "commit_changes") as commit_changes,
        pytest.raises(OSError, match="RDF file write failed"),
    ):
        editor.save()

    counter_handler.begin_counter_transaction.assert_called_once_with()
    counter_handler.commit_counter_transaction.assert_not_called()
    counter_handler.rollback_counter_transaction.assert_called_once_with()
    commit_changes.assert_not_called()


@pytest.mark.parametrize(
    ("upload_results", "expected_error", "expected_calls"),
    [
        (
            [False],
            "Failed to update the dataset triplestore",
            [call(DATASET_ENDPOINT)],
        ),
        (
            [True, False],
            "Failed to update the provenance triplestore",
            [call(DATASET_ENDPOINT), call(PROVENANCE_ENDPOINT)],
        ),
    ],
)
def test_save_rejects_failed_triplestore_upload(
    mock_storer,
    upload_results: list[bool],
    expected_error: str,
    expected_calls: list[object],
) -> None:
    counter_handler = MagicMock(spec=TransactionalCounterHandler)
    save_plugin = MagicMock()
    editor = Editor(
        EndpointConfig(
            dataset=DATASET_ENDPOINT,
            provenance=PROVENANCE_ENDPOINT,
            is_quadstore=True,
        ),
        counter_handler,
        RESP_AGENT,
        save_plugin=save_plugin,
    )
    mock_storer.return_value.upload_all.side_effect = upload_results

    with (
        patch.object(editor.g_set, "generate_provenance"),
        patch.object(editor.g_set, "commit_changes") as commit_changes,
        pytest.raises(EditorError, match=expected_error),
    ):
        editor.save()

    assert mock_storer.return_value.upload_all.call_args_list == expected_calls
    save_plugin.persist.assert_not_called()
    commit_changes.assert_not_called()
    counter_handler.commit_counter_transaction.assert_not_called()
    counter_handler.rollback_counter_transaction.assert_called_once_with()


def test_merge_basic(
    editor_instance, mock_sparql_wrapper, mock_reader, mock_storer
) -> None:
    """Test basic merge functionality with incoming and outgoing triples."""
    mock_sparql_wrapper.setQuery.side_effect = lambda _query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        # Response for incoming query
        {
            "results": {
                "bindings": [
                    {
                        "s": {"type": "uri", "value": str(INCOMING_SUBJ_URI)},
                        "p": {"type": "uri", "value": str(PROP_INCOMING)},
                    }
                ]
            }
        },
        # Response for outgoing query
        {
            "results": {
                "bindings": [
                    {
                        "p": {"type": "uri", "value": str(PROP_OUTGOING)},
                        "o": {"type": "uri", "value": str(OUTGOING_OBJ_URI)},
                    },
                    {
                        "p": {"type": "uri", "value": str(PROP_LITERAL)},
                        "o": {"type": "literal", "value": str(LITERAL_VALUE)},
                    },
                    {
                        "p": {"type": "uri", "value": str(RDF.type)},
                        "o": {"type": "uri", "value": str(TYPE_TO_DELETE_URI)},
                    },
                ]
            }
        },
    ]

    # Call the merge function
    editor_instance.merge(KEEP_URI, DELETE_URI)

    # --- Assertions ---
    # 1. Assert SPARQL queries were made correctly
    expected_incoming_query = (
        "SELECT DISTINCT ?s ?p WHERE {"
        f" ?s ?p <{DELETE_URI}> ."
        f" FILTER (?s != <{KEEP_URI}>)"
        " }"
    )
    expected_outgoing_query = f"""
                PREFIX rdf: <{RDF}>
                SELECT DISTINCT ?p ?o WHERE {{
                    <{DELETE_URI}> ?p ?o .
                    FILTER (?p != rdf:type)
                }}
            """

    def normalize_ws(s):
        return " ".join(s.strip().split())

    actual_calls = [
        normalize_ws(call[0][0]) for call in mock_sparql_wrapper.setQuery.call_args_list
    ]
    assert normalize_ws(expected_incoming_query) in actual_calls
    assert normalize_ws(expected_outgoing_query) in actual_calls
    assert mock_sparql_wrapper.setReturnFormat.call_args_list == [
        call(JSON),
        call(JSON),
    ]
    assert mock_sparql_wrapper.query.call_count == 2

    # 2. Assert Reader.import_entities_from_triplestore was called correctly
    expected_import_entities = {
        KEEP_URI,
        DELETE_URI,
        INCOMING_SUBJ_URI,
        OUTGOING_OBJ_URI,
        TYPE_TO_DELETE_URI,
    }
    mock_reader.assert_called_once()
    call_args, _call_kwargs = mock_reader.call_args
    # The first arg to import_entities_from_triplestore is the graph set instance
    assert isinstance(call_args[0], OCDMDataset)  # Check it's the real graph
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == expected_import_entities

    # 3. Assert save sequence was called (Storer init, upload_all)
    # Storer class should be called twice (for dataset and provenance)
    assert mock_storer.call_count == 2
    # Check arguments passed to Storer.__init__
    init_call_args_list = mock_storer.call_args_list
    assert isinstance(
        init_call_args_list[0][0][0], OCDMDataset
    )  # First call with dataset graph
    assert isinstance(
        init_call_args_list[1][0][0], Graph
    )  # Second call with provenance graph (g_set.provenance)

    # Check calls to the mocked Storer instance's upload_all method
    mock_storer_instance = mock_storer.return_value
    # Since Storer() is called twice, return_value is the *second* instance.
    # We need to check the upload_all calls on *both* instances. Let's use
    # call_args_list on the instance mock.
    # No, mock_storer is the CLASS mock. mock_storer.return_value is the INSTANCE mock
    # returned by __init__.
    # Need to check calls on the instances returned by the two __init__ calls.
    # Easier: check the total call count on the method of the return_value mock.
    assert mock_storer_instance.upload_all.call_count == 2
    # Check the endpoints passed to upload_all
    upload_calls = mock_storer_instance.upload_all.call_args_list
    assert upload_calls[0] == call(DATASET_ENDPOINT)
    assert upload_calls[1] == call(PROVENANCE_ENDPOINT)


def test_merge_no_incoming(
    editor_instance, mock_sparql_wrapper, mock_reader, mock_storer
) -> None:
    """Test merge when the entity to be deleted has no incoming references."""
    mock_sparql_wrapper.setQuery.side_effect = lambda _query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        {"results": {"bindings": []}},  # No incoming
        {
            "results": {
                "bindings": [
                    {
                        "p": {"type": "uri", "value": str(PROP_LITERAL)},
                        "o": {"type": "literal", "value": "Test Value"},
                    }
                ]
            }
        },  # Outgoing
    ]

    editor_instance.merge(KEEP_URI, DELETE_URI)

    expected_import_entities = {KEEP_URI, DELETE_URI}
    mock_reader.assert_called_once()
    call_args, _ = mock_reader.call_args
    assert isinstance(call_args[0], OCDMDataset)
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == expected_import_entities

    # Assert save sequence happened
    assert mock_storer.call_count == 2
    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2


# Test 3: Merge with no outgoing properties (except rdf:type)
def test_merge_no_outgoing(
    editor_instance, mock_sparql_wrapper, mock_reader, mock_storer
) -> None:
    """
    Test merge when the entity to be deleted has no outgoing properties (except
    rdf:type).
    """
    mock_sparql_wrapper.setQuery.side_effect = lambda _query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        {
            "results": {
                "bindings": [
                    {
                        "s": {"type": "uri", "value": str(INCOMING_SUBJ_URI)},
                        "p": {"type": "uri", "value": str(PROP_INCOMING)},
                    }
                ]
            }
        },  # Incoming
        {"results": {"bindings": []}},  # No outgoing
    ]

    editor_instance.merge(KEEP_URI, DELETE_URI)

    expected_import_entities = {KEEP_URI, DELETE_URI, INCOMING_SUBJ_URI}
    mock_reader.assert_called_once()
    call_args, _ = mock_reader.call_args
    assert isinstance(call_args[0], OCDMDataset)
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == expected_import_entities

    # Assert save sequence happened
    assert mock_storer.call_count == 2
    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2


def test_merge_self(editor_instance, mock_storer) -> None:
    """Test attempting to merge an entity with itself raises ValueError."""
    with pytest.raises(ValueError, match=r"Cannot merge an entity with itself\."):
        editor_instance.merge(KEEP_URI, KEEP_URI)

    # Ensure Storer was not called
    mock_storer.assert_not_called()


def test_merge_sparql_error(
    editor_instance, mock_sparql_wrapper, mock_reader, mock_storer
) -> None:
    """Test that an exception during SPARQL query prevents saving."""
    mock_sparql_wrapper.query.side_effect = Exception("SPARQL endpoint unavailable")

    with pytest.raises(Exception, match="SPARQL endpoint unavailable"):
        editor_instance.merge(KEEP_URI, DELETE_URI)

    # Assert that Reader and Storer were not called
    mock_reader.assert_not_called()
    mock_storer.assert_not_called()


def test_merge_reader_error(
    editor_instance, mock_sparql_wrapper, mock_reader, mock_storer
) -> None:
    """Test that an exception during entity import prevents saving."""
    mock_sparql_wrapper.setQuery.side_effect = lambda _query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        {"results": {"bindings": []}},
        {"results": {"bindings": []}},
    ]
    mock_reader.side_effect = Exception("Import failed")  # Make the mocked method raise

    with pytest.raises(Exception, match="Import failed"):
        editor_instance.merge(KEEP_URI, DELETE_URI)

    # Assert that import was attempted but Storer was not called
    mock_reader.assert_called_once()
    mock_storer.assert_not_called()


def test_merge_literal_types(
    editor_instance, mock_sparql_wrapper, mock_reader, mock_storer
) -> None:
    """Test merge with literals having language tags and datatypes."""
    prop_lang = URIRef("http://example.org/prop/langLiteral")
    prop_dtype = URIRef("http://example.org/prop/dtypeLiteral")

    mock_sparql_wrapper.setQuery.side_effect = lambda _query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        {"results": {"bindings": []}},  # Incoming
        {
            "results": {
                "bindings": [  # Outgoing
                    {
                        "p": {"type": "uri", "value": str(prop_lang)},
                        "o": {"type": "literal", "value": "Bonjour", "xml:lang": "fr"},
                    },
                    {
                        "p": {"type": "uri", "value": str(prop_dtype)},
                        "o": {
                            "type": "typed-literal",
                            "value": "123",
                            "datatype": "http://www.w3.org/2001/XMLSchema#integer",
                        },
                    },
                ]
            }
        },
    ]

    editor_instance.merge(KEEP_URI, DELETE_URI)

    # Primary check: Did the operation complete by calling Storer?
    assert mock_storer.call_count == 2
    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2


def test_merge_non_quadstore(
    editor_instance_non_quadstore, mock_sparql_wrapper, mock_reader, mock_storer
) -> None:
    """
    Test merge behavior when editor is configured for a non-quadstore (triple store).
    """
    # Use the specific fixture editor_instance_non_quadstore
    editor = editor_instance_non_quadstore

    mock_sparql_wrapper.setQuery.side_effect = lambda _query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        {"results": {"bindings": []}},  # No incoming
        {"results": {"bindings": []}},  # No outgoing
    ]

    editor.merge(KEEP_URI, DELETE_URI)

    # Assertions
    # 1. SPARQL queries
    assert mock_sparql_wrapper.setQuery.call_count == 2
    assert mock_sparql_wrapper.query.call_count == 2

    # 2. Reader import uses the correct graph instance (OCDMGraph)
    mock_reader.assert_called_once()
    call_args, _ = mock_reader.call_args
    assert isinstance(call_args[0], OCDMGraph)  # Check it's the non-conjunctive graph
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == {
        KEEP_URI,
        DELETE_URI,
    }  # Only keep/delete URIs expected here

    # 3. Save sequence uses correct graph instance
    assert mock_storer.call_count == 2
    init_call_args_list = mock_storer.call_args_list
    assert isinstance(
        init_call_args_list[0][0][0], OCDMGraph
    )  # First call with dataset graph
    assert isinstance(
        init_call_args_list[1][0][0], Graph
    )  # Second call with provenance graph

    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2
    upload_calls = mock_storer_instance.upload_all.call_args_list
    assert upload_calls[0] == call(DATASET_ENDPOINT)
    assert upload_calls[1] == call(PROVENANCE_ENDPOINT)


def test_merge_skip_blank_node(
    editor_instance, mock_sparql_wrapper, mock_reader, mock_storer
) -> None:
    """
    Test that non-URI/Literal objects (e.g., blank nodes) are skipped with a warning.
    """
    bnode_prop = URIRef("http://example.org/prop/bnodeRef")
    bnode_id = "bnode123"
    literal_prop_2 = URIRef("http://example.org/prop/anotherLiteral")
    literal_value_2 = Literal("Another value")

    mock_sparql_wrapper.setQuery.side_effect = lambda _query: None
    mock_sparql_wrapper.query.return_value.convert.side_effect = [
        # Incoming query (empty)
        {"results": {"bindings": []}},
        # Outgoing query (with bnode and literal)
        {
            "results": {
                "bindings": [
                    {
                        "p": {"type": "uri", "value": str(bnode_prop)},
                        "o": {"type": "bnode", "value": bnode_id},  # Blank Node
                    },
                    {
                        "p": {"type": "uri", "value": str(literal_prop_2)},
                        "o": {"type": "literal", "value": str(literal_value_2)},
                    },
                ]
            }
        },
    ]

    app = Flask(__name__)
    with app.app_context():
        editor_instance.merge(KEEP_URI, DELETE_URI)

    # Assert Reader was called (only keep/delete URIs, as bnode and its prop aren't
    # imported)
    expected_import_entities = {KEEP_URI, DELETE_URI}
    mock_reader.assert_called_once()
    call_args, _ = mock_reader.call_args
    assert isinstance(call_args[0], OCDMDataset)  # Assuming quadstore instance
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == expected_import_entities

    # Assert save sequence completed, indicating the literal was processed
    assert mock_storer.call_count == 2
    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2
