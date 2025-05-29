"""
Tests for the SPARQL utilities module.
"""

from unittest.mock import MagicMock, patch

import pytest
from heritrace.utils.sparql_utils import (
    _get_entities_with_enhanced_shape_detection,
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
    with patch("heritrace.utils.sparql_utils.get_display_rules") as mock_get_rules:
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
        mock_get_rules.return_value = mock_rules_data
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

        # Mock determine_shape_for_classes
        with patch(
            "heritrace.utils.sparql_utils.determine_shape_for_classes",
            return_value="http://example.org/PersonShape"
        ) as mock_determine_shape:
            # Configure the custom filter to return specific labels
            mock_custom_filter.human_readable_class.side_effect = lambda entity_key: (
                "Person" if entity_key[0] == "http://example.org/Person" else "Document"
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

        # Mock determine_shape_for_classes
        with patch(
            "heritrace.utils.sparql_utils.determine_shape_for_classes",
            return_value="http://example.org/PersonShape"
        ) as mock_determine_shape:
            # Configure the custom filter to return specific labels
            mock_custom_filter.human_readable_class.side_effect = lambda entity_key: (
                "Person" if entity_key[0] == "http://example.org/Person" else "Document"
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
        
        with patch("heritrace.utils.sparql_utils.find_matching_rule") as mock_find_rule:
            mock_find_rule.return_value = {
                "sortableBy": [{
                    "property": "http://example.org/name",
                    "label": "Name"
                }]
            }
            sort_clause = build_sort_clause(sort_property, entity_type)

            assert (
                sort_clause == "OPTIONAL { ?subject <http://example.org/name> ?sortValue }"
            )

    def test_build_sort_clause_with_invalid_property(self, mock_display_rules):
        """Test building a sort clause with an invalid property."""
        entity_type = "http://example.org/Person"
        sort_property = "http://example.org/invalid"

        with patch("heritrace.utils.sparql_utils.find_matching_rule") as mock_find_rule:
            mock_find_rule.return_value = {
                "sortableBy": [{
                    "property": "http://example.org/name",
                    "label": "Name"
                }]
            }
            sort_clause = build_sort_clause(sort_property, entity_type)

            assert sort_clause == ""

    def test_build_sort_clause_with_no_display_rules(self):
        """Test building a sort clause with no display rules."""
        entity_type = "http://example.org/Person"
        sort_property = "http://example.org/name"

        with patch("heritrace.utils.sparql_utils.find_matching_rule") as mock_find_rule:
            mock_find_rule.return_value = None
            sort_clause = build_sort_clause(sort_property, entity_type)

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

        # Create mock available_classes
        available_classes = [
            {
                "uri": "http://example.org/Person",
                "label": "Person",
                "count": 10,
                "shape": "http://example.org/PersonShape"
            }
        ]

        # Patch get_sortable_properties to return our mock sortable properties
        with patch(
            "heritrace.utils.sparql_utils.get_sortable_properties",
            return_value=sortable_properties,
        ):
            # Call get_catalog_data with the new parameter structure
            catalog_data = get_catalog_data(
                "http://example.org/Person", 1, 10, sort_property=None, selected_shape="http://example.org/PersonShape"
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
        mock_editor = MagicMock()

        # Mock get_sparql to return a mock SPARQLWrapper
        with patch("heritrace.utils.sparql_utils.get_sparql") as mock_get_sparql:
            mock_sparql_wrapper = mock_get_sparql.return_value
            mock_sparql_wrapper.query.return_value.convert.return_value = {
                "results": {
                    "bindings": [
                        {
                            "p": {"value": "http://example.org/knows"},
                            "o": {"value": "http://example.org/person2"},
                        }
                    ]
                }
            }

            result = import_entity_graph(
                mock_editor, "http://example.org/person1", max_depth=2
            )
            assert mock_editor.import_entity.call_count == 2
            mock_editor.import_entity.assert_any_call(
                URIRef("http://example.org/person1")
            )
            mock_editor.import_entity.assert_any_call(
                URIRef("http://example.org/person2")
            )

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

            result = fetch_current_state_with_related_entities(provenance)

            assert isinstance(result, Graph)
            assert not isinstance(result, ConjunctiveGraph)

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

            assert mock_fetch.call_count == 2
            mock_fetch.assert_any_call("http://example.org/person1")
            mock_fetch.assert_any_call("http://example.org/person2")


class TestGetEntitiesWithEnhancedShapeDetection:
    """Tests for the _get_entities_with_enhanced_shape_detection function."""

    def test_get_entities_with_enhanced_shape_detection_virtuoso(self):
        """Test enhanced shape detection with Virtuoso."""
        class_uri = "http://example.org/Person"
        classes_with_multiple_shapes = {"http://example.org/Person"}
        
        mock_sparql_results = {
            "results": {
                "bindings": [
                    {
                        "subject": {"value": "http://example.org/person1"},
                        "p": {"value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"},
                        "o": {"value": "http://example.org/Person"}
                    },
                    {
                        "subject": {"value": "http://example.org/person1"},
                        "p": {"value": "http://example.org/name"},
                        "o": {"value": "John Doe"}
                    },
                    {
                        "subject": {"value": "http://example.org/person2"},
                        "p": {"value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"},
                        "o": {"value": "http://example.org/Person"}
                    },
                    {
                        "subject": {"value": "http://example.org/person2"},
                        "p": {"value": "http://example.org/age"},
                        "o": {"value": "30"}
                    }
                ]
            }
        }

        with patch("heritrace.utils.sparql_utils.get_sparql") as mock_get_sparql, \
             patch("heritrace.utils.sparql_utils.is_virtuoso", return_value=True), \
             patch("heritrace.utils.sparql_utils.determine_shape_for_entity_triples") as mock_determine_shape, \
             patch("heritrace.utils.sparql_utils.is_entity_type_visible", return_value=True):
            
            mock_sparql = mock_get_sparql.return_value
            mock_sparql.query.return_value.convert.return_value = mock_sparql_results
            
            mock_determine_shape.side_effect = lambda triples: (
                "http://example.org/PersonShapeA" if any("name" in str(t) for t in triples)
                else "http://example.org/PersonShapeB"
            )
            
            result = _get_entities_with_enhanced_shape_detection(class_uri, classes_with_multiple_shapes)
            
            mock_sparql.setQuery.assert_called_once()
            query = mock_sparql.setQuery.call_args[0][0]
            assert "GRAPH ?g" in query
            assert "FILTER(?g NOT IN" in query
            assert f"?subject a <{class_uri}>" in query
            
            assert len(result) == 2
            assert "http://example.org/PersonShapeA" in result
            assert "http://example.org/PersonShapeB" in result
            
            shape_a_entities = result["http://example.org/PersonShapeA"]
            shape_b_entities = result["http://example.org/PersonShapeB"]
            
            assert len(shape_a_entities) == 1
            assert shape_a_entities[0]["uri"] == "http://example.org/person1"
            assert shape_a_entities[0]["class"] == class_uri
            assert shape_a_entities[0]["shape"] == "http://example.org/PersonShapeA"
            
            assert len(shape_b_entities) == 1
            assert shape_b_entities[0]["uri"] == "http://example.org/person2"
            assert shape_b_entities[0]["class"] == class_uri
            assert shape_b_entities[0]["shape"] == "http://example.org/PersonShapeB"

    def test_get_entities_with_enhanced_shape_detection_non_virtuoso(self):
        """Test enhanced shape detection with non-Virtuoso store."""
        class_uri = "http://example.org/Document"
        classes_with_multiple_shapes = {"http://example.org/Document"}
        
        mock_sparql_results = {
            "results": {
                "bindings": [
                    {
                        "subject": {"value": "http://example.org/doc1"},
                        "p": {"value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"},
                        "o": {"value": "http://example.org/Document"}
                    },
                    {
                        "subject": {"value": "http://example.org/doc1"},
                        "p": {"value": "http://example.org/title"},
                        "o": {"value": "Test Document"}
                    }
                ]
            }
        }

        with patch("heritrace.utils.sparql_utils.get_sparql") as mock_get_sparql, \
             patch("heritrace.utils.sparql_utils.is_virtuoso", return_value=False), \
             patch("heritrace.utils.sparql_utils.determine_shape_for_entity_triples", return_value="http://example.org/DocumentShape"), \
             patch("heritrace.utils.sparql_utils.is_entity_type_visible", return_value=True):
            
            mock_sparql = mock_get_sparql.return_value
            mock_sparql.query.return_value.convert.return_value = mock_sparql_results
            
            result = _get_entities_with_enhanced_shape_detection(class_uri, classes_with_multiple_shapes)
            
            mock_sparql.setQuery.assert_called_once()
            query = mock_sparql.setQuery.call_args[0][0]
            assert "GRAPH ?g" not in query
            assert "FILTER(?g NOT IN" not in query
            assert f"?subject a <{class_uri}>" in query
            
            assert len(result) == 1
            assert "http://example.org/DocumentShape" in result
            assert len(result["http://example.org/DocumentShape"]) == 1
            assert result["http://example.org/DocumentShape"][0]["uri"] == "http://example.org/doc1"

    def test_get_entities_with_enhanced_shape_detection_invisible_entities(self):
        """Test that invisible entities are filtered out."""
        class_uri = "http://example.org/Person"
        classes_with_multiple_shapes = {"http://example.org/Person"}
        
        mock_sparql_results = {
            "results": {
                "bindings": [
                    {
                        "subject": {"value": "http://example.org/person1"},
                        "p": {"value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"},
                        "o": {"value": "http://example.org/Person"}
                    }
                ]
            }
        }

        with patch("heritrace.utils.sparql_utils.get_sparql") as mock_get_sparql, \
             patch("heritrace.utils.sparql_utils.is_virtuoso", return_value=False), \
             patch("heritrace.utils.sparql_utils.determine_shape_for_entity_triples", return_value="http://example.org/PersonShape"), \
             patch("heritrace.utils.sparql_utils.is_entity_type_visible", return_value=False):
            
            mock_sparql = mock_get_sparql.return_value
            mock_sparql.query.return_value.convert.return_value = mock_sparql_results
            
            result = _get_entities_with_enhanced_shape_detection(class_uri, classes_with_multiple_shapes)
            
            assert len(result) == 0


class TestGetAvailableClassesMultipleShapes:
    """Tests for the multiple shapes branch in get_available_classes function."""

    def test_get_available_classes_with_multiple_shapes(self):
        """Test get_available_classes when a class has multiple shapes."""
        mock_classes_results = {
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

        mock_shape_to_entities = {
            "http://example.org/PersonShapeA": [
                {"uri": "http://example.org/person1", "class": "http://example.org/Person", "shape": "http://example.org/PersonShapeA"},
                {"uri": "http://example.org/person2", "class": "http://example.org/Person", "shape": "http://example.org/PersonShapeA"}
            ],
            "http://example.org/PersonShapeB": [
                {"uri": "http://example.org/person3", "class": "http://example.org/Person", "shape": "http://example.org/PersonShapeB"}
            ]
        }

        with patch("heritrace.utils.sparql_utils.get_sparql") as mock_get_sparql, \
             patch("heritrace.utils.sparql_utils.get_custom_filter") as mock_get_filter, \
             patch("heritrace.utils.sparql_utils.is_virtuoso", return_value=False), \
             patch("heritrace.utils.sparql_utils.get_classes_with_multiple_shapes", return_value={"http://example.org/Person"}), \
             patch("heritrace.utils.sparql_utils._get_entities_with_enhanced_shape_detection", return_value=mock_shape_to_entities), \
             patch("heritrace.utils.sparql_utils.determine_shape_for_classes", return_value="http://example.org/DocumentShape"), \
             patch("heritrace.utils.sparql_utils.is_entity_type_visible", return_value=True):
            
            mock_sparql = mock_get_sparql.return_value
            mock_sparql.query.return_value.convert.return_value = mock_classes_results
            
            mock_filter = mock_get_filter.return_value
            mock_filter.human_readable_class.side_effect = lambda entity_key: {
                ("http://example.org/Person", "http://example.org/PersonShapeA"): "Person (Type A)",
                ("http://example.org/Person", "http://example.org/PersonShapeB"): "Person (Type B)",
                ("http://example.org/Document", "http://example.org/DocumentShape"): "Document"
            }.get(entity_key, "Unknown")
            
            classes = get_available_classes()
            
            assert len(classes) == 3  # 2 person shapes + 1 document shape
            
            person_shape_a = next((c for c in classes if c["shape"] == "http://example.org/PersonShapeA"), None)
            person_shape_b = next((c for c in classes if c["shape"] == "http://example.org/PersonShapeB"), None)
            document_class = next((c for c in classes if c["uri"] == "http://example.org/Document"), None)
            
            assert person_shape_a is not None
            assert person_shape_a["uri"] == "http://example.org/Person"
            assert person_shape_a["label"] == "Person (Type A)"
            assert person_shape_a["count"] == 2
            assert person_shape_a["shape"] == "http://example.org/PersonShapeA"
            
            assert person_shape_b is not None
            assert person_shape_b["uri"] == "http://example.org/Person"
            assert person_shape_b["label"] == "Person (Type B)"
            assert person_shape_b["count"] == 1
            assert person_shape_b["shape"] == "http://example.org/PersonShapeB"
            
            assert document_class is not None
            assert document_class["uri"] == "http://example.org/Document"
            assert document_class["label"] == "Document"
            assert document_class["count"] == 5
            assert document_class["shape"] == "http://example.org/DocumentShape"

    def test_get_available_classes_multiple_shapes_empty_results(self):
        """Test get_available_classes when enhanced shape detection returns empty results."""
        mock_classes_results = {
            "results": {
                "bindings": [
                    {
                        "class": {"value": "http://example.org/Person"},
                        "count": {"value": "10"},
                    }
                ]
            }
        }

        mock_shape_to_entities = {}

        with patch("heritrace.utils.sparql_utils.get_sparql") as mock_get_sparql, \
             patch("heritrace.utils.sparql_utils.get_custom_filter") as mock_get_filter, \
             patch("heritrace.utils.sparql_utils.is_virtuoso", return_value=False), \
             patch("heritrace.utils.sparql_utils.get_classes_with_multiple_shapes", return_value={"http://example.org/Person"}), \
             patch("heritrace.utils.sparql_utils._get_entities_with_enhanced_shape_detection", return_value=mock_shape_to_entities):
            
            mock_sparql = mock_get_sparql.return_value
            mock_sparql.query.return_value.convert.return_value = mock_classes_results
            
            mock_filter = mock_get_filter.return_value
            
            classes = get_available_classes()
            
            assert len(classes) == 0


class TestGetEntitiesForClassShapeFiltering:
    """Tests for the shape filtering branch in get_entities_for_class function."""

    def test_get_entities_for_class_with_shape_filtering_virtuoso(self):
        """Test get_entities_for_class with shape filtering on Virtuoso."""
        selected_class = "http://example.org/Person"
        selected_shape = "http://example.org/PersonShapeA"
        classes_with_multiple_shapes = {"http://example.org/Person"}
        
        mock_sparql_results = {
            "results": {
                "bindings": [
                    {
                        "subject": {"value": "http://example.org/person1"},
                        "p": {"value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"},
                        "o": {"value": "http://example.org/Person"}
                    },
                    {
                        "subject": {"value": "http://example.org/person1"},
                        "p": {"value": "http://example.org/name"},
                        "o": {"value": "John Doe"}
                    },
                    {
                        "subject": {"value": "http://example.org/person2"},
                        "p": {"value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"},
                        "o": {"value": "http://example.org/Person"}
                    },
                    {
                        "subject": {"value": "http://example.org/person2"},
                        "p": {"value": "http://example.org/age"},
                        "o": {"value": "30"}
                    }
                ]
            }
        }

        with patch("heritrace.utils.sparql_utils.get_sparql") as mock_get_sparql, \
             patch("heritrace.utils.sparql_utils.get_custom_filter") as mock_get_filter, \
             patch("heritrace.utils.sparql_utils.is_virtuoso", return_value=True), \
             patch("heritrace.utils.sparql_utils.get_classes_with_multiple_shapes", return_value=classes_with_multiple_shapes), \
             patch("heritrace.utils.sparql_utils.determine_shape_for_entity_triples") as mock_determine_shape:
            
            mock_sparql = mock_get_sparql.return_value
            mock_sparql.query.return_value.convert.return_value = mock_sparql_results
            
            mock_filter = mock_get_filter.return_value
            mock_filter.human_readable_entity.side_effect = lambda uri, entity_key, graph: f"Entity {uri.split('/')[-1]}"
            
            mock_determine_shape.side_effect = lambda triples: (
                selected_shape if any("name" in str(t) for t in triples)
                else "http://example.org/PersonShapeB"
            )
            
            entities, total_count = get_entities_for_class(
                selected_class, 1, 10, selected_shape=selected_shape
            )
            
            mock_sparql.setQuery.assert_called_once()
            query = mock_sparql.setQuery.call_args[0][0]
            assert "GRAPH ?g" in query
            assert "FILTER(?g NOT IN" in query
            assert f"?subject a <{selected_class}>" in query
            
            assert total_count == 1
            assert len(entities) == 1
            assert entities[0]["uri"] == "http://example.org/person1"
            assert entities[0]["label"] == "Entity person1"

    def test_get_entities_for_class_with_shape_filtering_non_virtuoso(self):
        """Test get_entities_for_class with shape filtering on non-Virtuoso."""
        selected_class = "http://example.org/Document"
        selected_shape = "http://example.org/DocumentShapeA"
        classes_with_multiple_shapes = {"http://example.org/Document"}
        
        mock_sparql_results = {
            "results": {
                "bindings": [
                    {
                        "subject": {"value": "http://example.org/doc1"},
                        "p": {"value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"},
                        "o": {"value": "http://example.org/Document"}
                    },
                    {
                        "subject": {"value": "http://example.org/doc1"},
                        "p": {"value": "http://example.org/title"},
                        "o": {"value": "Document Title"}
                    }
                ]
            }
        }

        with patch("heritrace.utils.sparql_utils.get_sparql") as mock_get_sparql, \
             patch("heritrace.utils.sparql_utils.get_custom_filter") as mock_get_filter, \
             patch("heritrace.utils.sparql_utils.is_virtuoso", return_value=False), \
             patch("heritrace.utils.sparql_utils.get_classes_with_multiple_shapes", return_value=classes_with_multiple_shapes), \
             patch("heritrace.utils.sparql_utils.determine_shape_for_entity_triples", return_value=selected_shape):
            
            mock_sparql = mock_get_sparql.return_value
            mock_sparql.query.return_value.convert.return_value = mock_sparql_results
            
            mock_filter = mock_get_filter.return_value
            mock_filter.human_readable_entity.return_value = "Test Document"
            
            entities, total_count = get_entities_for_class(
                selected_class, 1, 10, selected_shape=selected_shape
            )
            
            mock_sparql.setQuery.assert_called_once()
            query = mock_sparql.setQuery.call_args[0][0]
            assert "GRAPH ?g" not in query
            assert "FILTER(?g NOT IN" not in query
            assert f"?subject a <{selected_class}>" in query
            
            assert total_count == 1
            assert len(entities) == 1
            assert entities[0]["uri"] == "http://example.org/doc1"
            assert entities[0]["label"] == "Test Document"

    def test_get_entities_for_class_with_shape_filtering_and_sorting(self):
        """Test get_entities_for_class with shape filtering and sorting."""
        selected_class = "http://example.org/Person"
        selected_shape = "http://example.org/PersonShapeA"
        classes_with_multiple_shapes = {"http://example.org/Person"}
        
        mock_sparql_results = {
            "results": {
                "bindings": [
                    {
                        "subject": {"value": "http://example.org/person1"},
                        "p": {"value": "http://example.org/name"},
                        "o": {"value": "Alice"}
                    },
                    {
                        "subject": {"value": "http://example.org/person2"},
                        "p": {"value": "http://example.org/name"},
                        "o": {"value": "Bob"}
                    }
                ]
            }
        }

        with patch("heritrace.utils.sparql_utils.get_sparql") as mock_get_sparql, \
             patch("heritrace.utils.sparql_utils.get_custom_filter") as mock_get_filter, \
             patch("heritrace.utils.sparql_utils.is_virtuoso", return_value=False), \
             patch("heritrace.utils.sparql_utils.get_classes_with_multiple_shapes", return_value=classes_with_multiple_shapes), \
             patch("heritrace.utils.sparql_utils.determine_shape_for_entity_triples", return_value=selected_shape):
            
            mock_sparql = mock_get_sparql.return_value
            mock_sparql.query.return_value.convert.return_value = mock_sparql_results
            
            mock_filter = mock_get_filter.return_value
            mock_filter.human_readable_entity.side_effect = lambda uri, entity_key, graph: uri.split('/')[-1]
            
            entities_asc, total_count_asc = get_entities_for_class(
                selected_class, 1, 10, sort_property="http://example.org/name", 
                sort_direction="ASC", selected_shape=selected_shape
            )
            
            assert total_count_asc == 2
            assert len(entities_asc) == 2
            assert entities_asc[0]["uri"] == "http://example.org/person1"  # Alice should come first
            assert entities_asc[1]["uri"] == "http://example.org/person2"  # Bob should come second
            
            entities_desc, total_count_desc = get_entities_for_class(
                selected_class, 1, 10, sort_property="http://example.org/name", 
                sort_direction="DESC", selected_shape=selected_shape
            )
            
            assert total_count_desc == 2
            assert len(entities_desc) == 2
            assert entities_desc[0]["uri"] == "http://example.org/person2"  # Bob should come first
            assert entities_desc[1]["uri"] == "http://example.org/person1"  # Alice should come second

    def test_get_entities_for_class_with_shape_filtering_pagination(self):
        """Test get_entities_for_class with shape filtering and pagination."""
        selected_class = "http://example.org/Person"
        selected_shape = "http://example.org/PersonShapeA"
        classes_with_multiple_shapes = {"http://example.org/Person"}
        
        mock_sparql_results = {
            "results": {
                "bindings": [
                    {
                        "subject": {"value": f"http://example.org/person{i}"},
                        "p": {"value": "http://example.org/name"},
                        "o": {"value": f"Person {i}"}
                    } for i in range(1, 6)
                ]
            }
        }

        with patch("heritrace.utils.sparql_utils.get_sparql") as mock_get_sparql, \
             patch("heritrace.utils.sparql_utils.get_custom_filter") as mock_get_filter, \
             patch("heritrace.utils.sparql_utils.is_virtuoso", return_value=False), \
             patch("heritrace.utils.sparql_utils.get_classes_with_multiple_shapes", return_value=classes_with_multiple_shapes), \
             patch("heritrace.utils.sparql_utils.determine_shape_for_entity_triples", return_value=selected_shape):
            
            mock_sparql = mock_get_sparql.return_value
            mock_sparql.query.return_value.convert.return_value = mock_sparql_results
            
            mock_filter = mock_get_filter.return_value
            mock_filter.human_readable_entity.side_effect = lambda uri, entity_key, graph: f"Entity {uri.split('/')[-1]}"
            
            entities_page1, total_count = get_entities_for_class(
                selected_class, 1, 3, selected_shape=selected_shape
            )
            
            assert total_count == 5
            assert len(entities_page1) == 3
            assert entities_page1[0]["uri"] == "http://example.org/person1"
            assert entities_page1[1]["uri"] == "http://example.org/person2"
            assert entities_page1[2]["uri"] == "http://example.org/person3"
            
            entities_page2, total_count = get_entities_for_class(
                selected_class, 2, 3, selected_shape=selected_shape
            )
            
            assert total_count == 5
            assert len(entities_page2) == 2
            assert entities_page2[0]["uri"] == "http://example.org/person4"
            assert entities_page2[1]["uri"] == "http://example.org/person5"
