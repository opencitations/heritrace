# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from functools import partial
from unittest.mock import MagicMock, call, patch

import pytest
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
GRAPH_URI = URIRef("http://example.org/graph")


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
                    "graph_iri": None,
                }
        if KEEP_URI in entities_to_import and DELETE_URI in entities_to_import:
            if isinstance(g_set, OCDMDataset):
                g_set.add((KEEP_URI, RDF.type, TYPE_TO_DELETE_URI, GRAPH_URI))
                g_set.add((DELETE_URI, RDF.type, TYPE_TO_DELETE_URI, GRAPH_URI))
            else:
                g_set.add((KEEP_URI, RDF.type, TYPE_TO_DELETE_URI))
                g_set.add((DELETE_URI, RDF.type, TYPE_TO_DELETE_URI))

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
    mock_sparql_wrapper.query.return_value.convert.return_value = {
        "results": {
            "bindings": [{"s": {"type": "uri", "value": str(INCOMING_SUBJ_URI)}}]
        }
    }

    editor_instance.merge(KEEP_URI, DELETE_URI)

    expected_incoming_query = (
        "SELECT DISTINCT ?s WHERE {"
        f" ?s ?p <{DELETE_URI}> ."
        f" FILTER (?s != <{KEEP_URI}>)"
        " }"
    )
    assert mock_sparql_wrapper.setQuery.call_args_list == [
        call(expected_incoming_query)
    ]
    assert mock_sparql_wrapper.setReturnFormat.call_args_list == [call(JSON)]
    assert mock_sparql_wrapper.query.call_count == 1

    expected_import_entities = {
        KEEP_URI,
        DELETE_URI,
        INCOMING_SUBJ_URI,
    }
    mock_reader.assert_called_once()
    call_args, _call_kwargs = mock_reader.call_args
    assert isinstance(call_args[0], OCDMDataset)
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == expected_import_entities

    assert mock_storer.call_count == 2
    init_call_args_list = mock_storer.call_args_list
    assert isinstance(init_call_args_list[0][0][0], OCDMDataset)
    assert isinstance(init_call_args_list[1][0][0], Graph)

    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2
    upload_calls = mock_storer_instance.upload_all.call_args_list
    assert upload_calls[0] == call(DATASET_ENDPOINT)
    assert upload_calls[1] == call(PROVENANCE_ENDPOINT)


def test_merge_transfers_outgoing_statements_and_incoming_links(
    editor_instance, mock_sparql_wrapper, mock_reader
) -> None:
    mock_sparql_wrapper.query.return_value.convert.return_value = {
        "results": {
            "bindings": [{"s": {"type": "uri", "value": str(INCOMING_SUBJ_URI)}}]
        }
    }

    def import_merge_entities(g_set, _endpoint, _entities) -> None:
        g_set.add((KEEP_URI, RDF.type, TYPE_TO_DELETE_URI, GRAPH_URI))
        g_set.add((DELETE_URI, RDF.type, TYPE_TO_DELETE_URI, GRAPH_URI))
        g_set.add((DELETE_URI, PROP_OUTGOING, OUTGOING_OBJ_URI, GRAPH_URI))
        g_set.add((DELETE_URI, PROP_LITERAL, LITERAL_VALUE, GRAPH_URI))
        g_set.add((INCOMING_SUBJ_URI, PROP_INCOMING, DELETE_URI, GRAPH_URI))

    mock_reader.side_effect = import_merge_entities

    with patch.object(editor_instance, "save"):
        editor_instance.merge(KEEP_URI, DELETE_URI)

    assert set(editor_instance.g_set.quads((KEEP_URI, PROP_OUTGOING, None, None))) == {
        (KEEP_URI, PROP_OUTGOING, OUTGOING_OBJ_URI, GRAPH_URI)
    }
    assert set(editor_instance.g_set.quads((KEEP_URI, PROP_LITERAL, None, None))) == {
        (KEEP_URI, PROP_LITERAL, LITERAL_VALUE, GRAPH_URI)
    }
    assert set(
        editor_instance.g_set.quads((INCOMING_SUBJ_URI, PROP_INCOMING, None, None))
    ) == {(INCOMING_SUBJ_URI, PROP_INCOMING, KEEP_URI, GRAPH_URI)}
    assert set(editor_instance.g_set.quads((DELETE_URI, None, None, None))) == set()


def test_merge_no_incoming(
    editor_instance, mock_sparql_wrapper, mock_reader, mock_storer
) -> None:
    """Test merge when the entity to be deleted has no incoming references."""
    editor_instance.merge(KEEP_URI, DELETE_URI)

    expected_import_entities = {KEEP_URI, DELETE_URI}
    mock_reader.assert_called_once()
    call_args, _ = mock_reader.call_args
    assert isinstance(call_args[0], OCDMDataset)
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == expected_import_entities

    assert mock_storer.call_count == 2
    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2


def test_merge_separates_initial_and_empty_operation_sources(
    mock_counter_handler, mock_sparql_wrapper, mock_reader, mock_storer
) -> None:
    initial_source = URIRef("https://example.org/initial-dataset")
    editor = Editor(
        EndpointConfig(
            dataset=DATASET_ENDPOINT,
            provenance=PROVENANCE_ENDPOINT,
            is_quadstore=True,
        ),
        mock_counter_handler,
        RESP_AGENT,
        initial_source,
    )
    operation_sources: dict[URIRef, URIRef | None] = {}

    def capture_operation_sources() -> None:
        operation_sources.update(
            {
                subject: metadata["source"]
                for subject, metadata in editor.g_set.entity_index.items()
            }
        )

    original_preexisting_finished = editor.g_set.preexisting_finished
    with (
        patch.object(
            editor.g_set,
            "preexisting_finished",
            side_effect=original_preexisting_finished,
        ) as mock_preexisting_finished,
        patch.object(
            editor.g_set,
            "generate_provenance",
            side_effect=capture_operation_sources,
        ),
    ):
        editor.merge(KEEP_URI, DELETE_URI, primary_source=None)

    mock_preexisting_finished.assert_called_once_with(
        RESP_AGENT, initial_source, editor.c_time
    )
    assert operation_sources == {KEEP_URI: None, DELETE_URI: None}


def test_merge_with_incoming_reference(
    editor_instance, mock_sparql_wrapper, mock_reader, mock_storer
) -> None:
    mock_sparql_wrapper.query.return_value.convert.return_value = {
        "results": {
            "bindings": [{"s": {"type": "uri", "value": str(INCOMING_SUBJ_URI)}}]
        }
    }

    editor_instance.merge(KEEP_URI, DELETE_URI)

    expected_import_entities = {KEEP_URI, DELETE_URI, INCOMING_SUBJ_URI}
    mock_reader.assert_called_once()
    call_args, _ = mock_reader.call_args
    assert isinstance(call_args[0], OCDMDataset)
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == expected_import_entities

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
    mock_reader.side_effect = Exception("Import failed")

    with pytest.raises(Exception, match="Import failed"):
        editor_instance.merge(KEEP_URI, DELETE_URI)

    mock_reader.assert_called_once()
    mock_storer.assert_not_called()


def test_merge_non_quadstore(
    editor_instance_non_quadstore, mock_sparql_wrapper, mock_reader, mock_storer
) -> None:
    """
    Test merge behavior when editor is configured for a non-quadstore (triple store).
    """
    # Use the specific fixture editor_instance_non_quadstore
    editor = editor_instance_non_quadstore

    editor.merge(KEEP_URI, DELETE_URI)

    assert mock_sparql_wrapper.setQuery.call_count == 1
    assert mock_sparql_wrapper.query.call_count == 1

    mock_reader.assert_called_once()
    call_args, _ = mock_reader.call_args
    assert isinstance(call_args[0], OCDMGraph)
    assert call_args[1] == DATASET_ENDPOINT
    assert set(call_args[2]) == {KEEP_URI, DELETE_URI}

    assert mock_storer.call_count == 2
    init_call_args_list = mock_storer.call_args_list
    assert isinstance(init_call_args_list[0][0][0], OCDMGraph)
    assert isinstance(init_call_args_list[1][0][0], Graph)

    mock_storer_instance = mock_storer.return_value
    assert mock_storer_instance.upload_all.call_count == 2
    upload_calls = mock_storer_instance.upload_all.call_args_list
    assert upload_calls[0] == call(DATASET_ENDPOINT)
    assert upload_calls[1] == call(PROVENANCE_ENDPOINT)
