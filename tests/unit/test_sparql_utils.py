"""
Tests for the SPARQL utilities module.
"""

from unittest.mock import MagicMock, patch

import pytest
from heritrace.utils.sparql_utils import (
    build_sort_clause,
    fetch_current_state_with_related_entities,
    fetch_data_graph_for_subject,
    find_orphaned_entities,
    get_available_classes,
    get_catalog_data,
    get_entities_for_class,
    import_entity_graph,
)
from rdflib import URIRef, Graph, ConjunctiveGraph, Literal, XSD


@pytest.fixture
def mock_sparql_wrapper():
    """Mock SPARQLWrapper for testing."""
    with patch("heritrace.utils.sparql_utils.get_sparql") as mock_get_sparql:
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql

        # Configure the mock to return a valid response
        mock_results = {"results": {"bindings": []}}
        mock_sparql.query.return_value.convert.return_value = mock_results

        yield mock_sparql


@pytest.fixture
def mock_custom_filter():
    """Mock custom filter for testing."""
    with patch("heritrace.utils.sparql_utils.get_custom_filter") as mock_get_filter:
        mock_filter = MagicMock()
        mock_get_filter.return_value = mock_filter

        # Configure the mock to return readable labels
        mock_filter.human_readable_predicate.return_value = "Human Readable Class"
        mock_filter.human_readable_entity.return_value = "Human Readable Entity"
        mock_filter.format_agent_reference.return_value = "Test Agent"

        yield mock_filter


@pytest.fixture
def mock_display_rules():
    """Mock display rules for testing."""
    with patch("heritrace.utils.sparql_utils.display_rules") as mock_rules:
        mock_rules_data = [
            {
                "target": {
                    "class": "http://example.org/Person"
                },
                "displayProperties": [
                    {"displayName": "Name", "property": "http://example.org/name"},
                    {
                        "displayName": "Knows",
                        "property": "http://example.org/knows",
                        "intermediateRelation": {
                            "class": "http://example.org/Relationship"
                        },
                    },
                ],
                "sortableBy": [
                    {"property": "http://example.org/name", "label": "Name"}
                ],
            }
        ]
        mock_rules.__iter__.return_value = iter(mock_rules_data)
        yield mock_rules_data


@pytest.fixture
def mock_virtuoso():
    """Mock virtuoso detection for testing."""
    with patch("heritrace.utils.sparql_utils.is_virtuoso") as mock_is_virtuoso:
        mock_is_virtuoso.return_value = True
        yield mock_is_virtuoso


@pytest.fixture
def mock_quadstore():
    """Mock quadstore detection for testing."""
    with patch(
        "heritrace.utils.sparql_utils.get_dataset_is_quadstore"
    ) as mock_is_quadstore:
        mock_is_quadstore.return_value = True
        yield mock_is_quadstore


class TestGetAvailableClasses:
    """Tests for the get_available_classes function."""

    def test_get_available_classes_virtuoso(
        self, mock_sparql_wrapper, mock_custom_filter, mock_virtuoso
    ):
        """Test getting available classes from a Virtuoso store."""
        # Configure mock to return some classes
        mock_sparql_wrapper.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {
                        "class": {"value": "http://example.org/Person"},
                        "count": {"value": "10"},
                    },
                    {
                        "class": {"value": "http://example.org/Document"},
                        "count": {"value": "5"},
                    },
                ]
            }
        }

        # Configure the custom filter to return specific labels for sorting
        mock_custom_filter.human_readable_predicate.side_effect = lambda uri, _: (
            "Person" if uri == "http://example.org/Person" else "Document"
        )

        # Configure visibility check to allow all classes
        with patch(
            "heritrace.utils.sparql_utils.is_entity_type_visible", return_value=True
        ):
            classes = get_available_classes()

            # Verify the results
            assert len(classes) == 2

            # Get the classes by URI to avoid sorting issues
            person_class = next(
                c for c in classes if c["uri"] == "http://example.org/Person"
            )
            document_class = next(
                c for c in classes if c["uri"] == "http://example.org/Document"
            )

            # Verify the counts
            assert person_class["count"] == 10
            assert document_class["count"] == 5

            # Verify the correct query was used (Virtuoso-specific)
            mock_sparql_wrapper.setQuery.assert_called_once()
            query = mock_sparql_wrapper.setQuery.call_args[0][0]
            assert "GRAPH ?g" in query
            assert "FILTER(?g NOT IN" in query
            
    def test_get_available_classes_non_virtuoso(
        self, mock_sparql_wrapper, mock_custom_filter
    ):
        """Test getting available classes from a non-Virtuoso store."""
        # Configure mock to return some classes
        mock_sparql_wrapper.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {
                        "class": {"value": "http://example.org/Person"},
                        "count": {"value": "10"},
                    },
                    {
                        "class": {"value": "http://example.org/Document"},
                        "count": {"value": "5"},
                    },
                ]
            }
        }

        # Configure the custom filter to return specific labels for sorting
        mock_custom_filter.human_readable_predicate.side_effect = lambda uri, _: (
            "Person" if uri == "http://example.org/Person" else "Document"
        )

        # Configure is_virtuoso to return False
        with patch(
            "heritrace.utils.sparql_utils.is_virtuoso", return_value=False
        ), patch(
            "heritrace.utils.sparql_utils.is_entity_type_visible", return_value=True
        ):
            classes = get_available_classes()

            # Verify the results
            assert len(classes) == 2

            # Get the classes by URI to avoid sorting issues
            person_class = next(
                c for c in classes if c["uri"] == "http://example.org/Person"
            )
            document_class = next(
                c for c in classes if c["uri"] == "http://example.org/Document"
            )

            # Verify the counts
            assert person_class["count"] == 10
            assert document_class["count"] == 5

            # Verify the correct query was used (non-Virtuoso-specific)
            mock_sparql_wrapper.setQuery.assert_called_once()
            query = mock_sparql_wrapper.setQuery.call_args[0][0]
            assert "GRAPH ?g" not in query
            assert "FILTER(?g NOT IN" not in query


class TestBuildSortClause:
    """Tests for the build_sort_clause function."""

    def test_build_sort_clause_with_valid_property(self, mock_display_rules):
        """Test building a sort clause with a valid property."""
        entity_type = "http://example.org/Person"
        sort_property = "http://example.org/name"

        sort_clause = build_sort_clause(sort_property, entity_type, mock_display_rules)

        assert (
            sort_clause == "OPTIONAL { ?subject <http://example.org/name> ?sortValue }"
        )

    def test_build_sort_clause_with_invalid_property(self, mock_display_rules):
        """Test building a sort clause with an invalid property."""
        entity_type = "http://example.org/Person"
        sort_property = "http://example.org/invalid"

        sort_clause = build_sort_clause(sort_property, entity_type, mock_display_rules)

        assert sort_clause == ""

    def test_build_sort_clause_with_no_display_rules(self):
        """Test building a sort clause with no display rules."""
        entity_type = "http://example.org/Person"
        sort_property = "http://example.org/name"

        sort_clause = build_sort_clause(sort_property, entity_type, None)

        assert sort_clause == ""


class TestGetEntitiesForClass:
    """Tests for the get_entities_for_class function."""

    def test_get_entities_for_class_virtuoso(
        self, mock_sparql_wrapper, mock_custom_filter, mock_virtuoso
    ):
        """Test getting entities for a class from a Virtuoso store."""
        # Configure mock to return some entities
        mock_sparql_wrapper.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {
                        "subject": {"value": "http://example.org/person1"},
                    },
                    {
                        "subject": {"value": "http://example.org/person2"},
                    },
                ]
            }
        }

        # Configure the count query result
        count_result = {"results": {"bindings": [{"count": {"value": "2"}}]}}

        # Set up the mock to return the count result for the first query
        mock_sparql_wrapper.query.return_value.convert.side_effect = [
            count_result,
            mock_sparql_wrapper.query.return_value.convert.return_value,
        ]

        entities, total_count = get_entities_for_class(
            "http://example.org/Person", 1, 10
        )

        # Verify the results
        assert total_count == 2
        assert len(entities) == 2
        assert entities[0]["uri"] == "http://example.org/person1"
        assert entities[1]["uri"] == "http://example.org/person2"

        # Verify the correct queries were used
        assert mock_sparql_wrapper.setQuery.call_count == 2
        count_query = mock_sparql_wrapper.setQuery.call_args_list[0][0][0]
        entities_query = mock_sparql_wrapper.setQuery.call_args_list[1][0][0]

        assert "COUNT(DISTINCT ?subject)" in count_query
        assert "GRAPH ?g" in count_query
        assert "FILTER(?g NOT IN" in count_query

        assert "SELECT DISTINCT ?subject" in entities_query
        assert "GRAPH ?g" in entities_query
        assert "FILTER(?g NOT IN" in entities_query
        assert "LIMIT 10" in entities_query
        assert "OFFSET 0" in entities_query
        
    def test_get_entities_for_class_non_virtuoso(
        self, mock_sparql_wrapper, mock_custom_filter
    ):
        """Test getting entities for a class from a non-Virtuoso store."""
        # Configure mock to return some entities
        mock_sparql_wrapper.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {
                        "subject": {"value": "http://example.org/person1"},
                    },
                    {
                        "subject": {"value": "http://example.org/person2"},
                    },
                ]
            }
        }

        # Configure the count query result
        count_result = {"results": {"bindings": [{"count": {"value": "2"}}]}}

        # Set up the mock to return the count result for the first query
        mock_sparql_wrapper.query.return_value.convert.side_effect = [
            count_result,
            mock_sparql_wrapper.query.return_value.convert.return_value,
        ]

        # Configure is_virtuoso to return False
        with patch("heritrace.utils.sparql_utils.is_virtuoso", return_value=False):
            entities, total_count = get_entities_for_class(
                "http://example.org/Person", 1, 10
            )

            # Verify the results
            assert total_count == 2
            assert len(entities) == 2
            assert entities[0]["uri"] == "http://example.org/person1"
            assert entities[1]["uri"] == "http://example.org/person2"

            # Verify the correct queries were used
            assert mock_sparql_wrapper.setQuery.call_count == 2
            count_query = mock_sparql_wrapper.setQuery.call_args_list[0][0][0]
            entities_query = mock_sparql_wrapper.setQuery.call_args_list[1][0][0]

            assert "COUNT(DISTINCT ?subject)" in count_query
            assert "GRAPH ?g" not in count_query
            assert "FILTER(?g NOT IN" not in count_query

            assert "SELECT DISTINCT ?subject" in entities_query
            assert "GRAPH ?g" not in entities_query
            assert "FILTER(?g NOT IN" not in entities_query
            assert "LIMIT 10" in entities_query
            assert "OFFSET 0" in entities_query


class TestGetCatalogData:
    """Tests for the get_catalog_data function."""

    def test_get_catalog_data_with_default_sort_property(
        self, mock_sparql_wrapper, mock_custom_filter, mock_virtuoso
    ):
        """Test get_catalog_data when sort_property is not provided but sortable_properties exist."""
        # Configure mock to return some entities
        mock_sparql_wrapper.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {
                        "subject": {"value": "http://example.org/person1"},
                    },
                    {
                        "subject": {"value": "http://example.org/person2"},
                    },
                ]
            }
        }

        # Configure the count query result
        count_result = {"results": {"bindings": [{"count": {"value": "2"}}]}}

        # Set up the mock to return the count result for the first query
        mock_sparql_wrapper.query.return_value.convert.side_effect = [
            count_result,
            mock_sparql_wrapper.query.return_value.convert.return_value,
        ]

        # Mock sortable properties
        sortable_properties = [
            {"property": "http://example.org/name", "label": "Name"},
            {"property": "http://example.org/age", "label": "Age"},
        ]

        # Patch get_sortable_properties to return our mock sortable properties
        with patch(
            "heritrace.utils.sparql_utils.get_sortable_properties",
            return_value=sortable_properties,
        ):
            # Call get_catalog_data without providing a sort_property
            catalog_data = get_catalog_data(
                "http://example.org/Person", 1, 10, sort_property=None
            )

            # Verify that sort_property was set from the first sortable property
            assert catalog_data["sort_property"] == "http://example.org/name"
            assert catalog_data["sortable_properties"] == sortable_properties
            
            # Verify other catalog data
            assert catalog_data["total_count"] == 2
            assert catalog_data["current_page"] == 1
            assert catalog_data["per_page"] == 10
            assert len(catalog_data["entities"]) == 2


class TestFetchDataGraphForSubject:
    """Tests for the fetch_data_graph_for_subject function."""

    def test_fetch_data_graph_virtuoso_quadstore(
        self, mock_sparql_wrapper, mock_virtuoso, mock_quadstore
    ):
        """Test fetching data for a subject from a Virtuoso quadstore."""
        # Configure mock to return some triples
        mock_sparql_wrapper.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {
                        "predicate": {
                            "value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
                        },
                        "object": {"type": "uri", "value": "http://example.org/Person"},
                        "g": {"value": "http://example.org/graph1"},
                    },
                    {
                        "predicate": {"value": "http://example.org/name"},
                        "object": {"type": "literal", "value": "John Doe"},
                        "g": {"value": "http://example.org/graph1"},
                    },
                ]
            }
        }

        graph = fetch_data_graph_for_subject("http://example.org/person1")

        # Verify the graph contains the expected triples
        assert len(graph) == 2

        # Verify the correct query was used
        mock_sparql_wrapper.setQuery.assert_called_once()
        query = mock_sparql_wrapper.setQuery.call_args[0][0]
        assert "GRAPH ?g" in query
        assert "FILTER(?g NOT IN" in query
        assert "<http://example.org/person1> ?predicate ?object" in query
        
    def test_fetch_data_graph_non_virtuoso_triplestore(
        self, mock_sparql_wrapper
    ):
        """Test fetching data for a subject from a non-Virtuoso triplestore (not quadstore)."""
        # Configure mock to return some triples
        mock_sparql_wrapper.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {
                        "predicate": {
                            "value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
                        },
                        "object": {"type": "uri", "value": "http://example.org/Person"},
                    },
                    {
                        "predicate": {"value": "http://example.org/name"},
                        "object": {"type": "literal", "value": "John Doe"},
                    },
                ]
            }
        }

        # Configure is_virtuoso and get_dataset_is_quadstore to return False
        with patch("heritrace.utils.sparql_utils.is_virtuoso", return_value=False), \
             patch("heritrace.utils.sparql_utils.get_dataset_is_quadstore", return_value=False):
            
            graph = fetch_data_graph_for_subject("http://example.org/person1")

            # Verify the graph contains the expected triples
            assert len(graph) == 2
            assert isinstance(graph, Graph)  # Should be a regular Graph, not ConjunctiveGraph
            
            # Verify that the specific triples were added correctly
            subject_uri = URIRef("http://example.org/person1")
            type_predicate = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
            name_predicate = URIRef("http://example.org/name")
            person_object = URIRef("http://example.org/Person")
            name_object = Literal("John Doe")  # RDFLib automatically adds XSD.string datatype
            
            # Check that both triples exist in the graph
            assert (subject_uri, type_predicate, person_object) in graph
            assert (subject_uri, name_predicate, name_object) in graph

            # Verify the correct query was used
            mock_sparql_wrapper.setQuery.assert_called_once()
            query = mock_sparql_wrapper.setQuery.call_args[0][0]
            assert "GRAPH ?g" not in query  # Regular triplestore query doesn't use GRAPH
            assert "FILTER(?g NOT IN" not in query
            assert "<http://example.org/person1> ?predicate ?object" in query


class TestFindOrphanedEntities:
    """Tests for the find_orphaned_entities function."""

    def test_find_orphaned_entities(self, mock_sparql_wrapper, mock_display_rules):
        """Test finding orphaned entities."""
        # Configure mock to return some orphaned entities
        mock_sparql_wrapper.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {
                        "entity": {"value": "http://example.org/orphan1"},
                        "type": {"value": "http://example.org/Document"},
                    }
                ]
            }
        }

        with patch(
            "heritrace.utils.sparql_utils.get_display_rules",
            return_value=mock_display_rules,
        ):
            orphaned, intermediate_orphans = find_orphaned_entities(
                "http://example.org/person1", "http://example.org/Person"
            )

            # Verify the results
            assert len(orphaned) == 1
            assert orphaned[0]["uri"] == "http://example.org/orphan1"
            assert orphaned[0]["type"] == "http://example.org/Document"

            # Verify the correct queries were used
            assert mock_sparql_wrapper.setQuery.call_count == 2


class TestImportEntityGraph:
    """Tests for the import_entity_graph function."""

    def test_import_entity_graph(self):
        """Test importing an entity graph."""
        # Create a mock editor
        mock_editor = MagicMock()

        # Mock the SPARQLWrapper
        with patch("heritrace.utils.sparql_utils.SPARQLWrapper") as mock_sparql_wrapper:
            # Configure mock to return some connected entities
            mock_sparql_wrapper.return_value.query.return_value.convert.return_value = {
                "results": {
                    "bindings": [
                        {
                            "p": {"value": "http://example.org/knows"},
                            "o": {"value": "http://example.org/person2"},
                        }
                    ]
                }
            }

            # Call the function
            result = import_entity_graph(
                mock_editor, "http://example.org/person1", max_depth=2
            )

            # Verify the editor was used correctly
            assert mock_editor.import_entity.call_count == 2
            mock_editor.import_entity.assert_any_call(
                URIRef("http://example.org/person1")
            )
            mock_editor.import_entity.assert_any_call(
                URIRef("http://example.org/person2")
            )

            # Verify the result
            assert result == mock_editor


class TestFetchCurrentStateWithRelatedEntities:
    """Tests for the fetch_current_state_with_related_entities function."""

    def test_fetch_current_state_with_related_entities_triplestore(self, mock_quadstore):
        """Test fetching current state with related entities from a triplestore (not quadstore)."""
        # Configure mock to return False for quadstore check
        mock_quadstore.return_value = False

        # Create test data
        provenance = {
            "http://example.org/person1": {"version": "1"},
            "http://example.org/person2": {"version": "2"},
        }

        # Create mock graphs to be returned by fetch_data_graph_for_subject
        person1_graph = Graph()
        person1_graph.add(
            (
                URIRef("http://example.org/person1"),
                URIRef("http://example.org/name"),
                Literal("Person 1"),
            )
        )

        person2_graph = Graph()
        person2_graph.add(
            (
                URIRef("http://example.org/person2"),
                URIRef("http://example.org/name"),
                Literal("Person 2"),
            )
        )

        # Mock fetch_data_graph_for_subject to return our test graphs
        with patch(
            "heritrace.utils.sparql_utils.fetch_data_graph_for_subject"
        ) as mock_fetch:
            mock_fetch.side_effect = lambda uri: (
                person1_graph if uri == "http://example.org/person1" else person2_graph
            )

            # Call the function
            result = fetch_current_state_with_related_entities(provenance)

            # Verify the result is a Graph (not a ConjunctiveGraph)
            assert isinstance(result, Graph)
            assert not isinstance(result, ConjunctiveGraph)

            # Verify all triples were added to the combined graph
            assert len(result) == 2
            assert (
                URIRef("http://example.org/person1"),
                URIRef("http://example.org/name"),
                Literal("Person 1"),
            ) in result
            assert (
                URIRef("http://example.org/person2"),
                URIRef("http://example.org/name"),
                Literal("Person 2"),
            ) in result

            # Verify fetch_data_graph_for_subject was called for each entity
            assert mock_fetch.call_count == 2
            mock_fetch.assert_any_call("http://example.org/person1")
            mock_fetch.assert_any_call("http://example.org/person2")
