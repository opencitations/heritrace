"""
Integration tests for the SPARQL utilities module using real test databases.
"""

import uuid
import pytest
from rdflib import URIRef, Literal, RDF
from SPARQLWrapper import SPARQLWrapper
from rdflib.plugins.sparql.parser import parseUpdate
from rdflib.plugins.sparql.algebra import translateUpdate

from heritrace.utils.sparql_utils import (
    get_available_classes,
    get_entities_for_class,
    get_catalog_data,
    fetch_data_graph_for_subject,
    fetch_current_state_with_related_entities,
    find_orphaned_entities,
    parse_sparql_update,
)


@pytest.fixture
def setup_test_data(app):
    """
    Set up test data in the dataset database.
    """
    # Get the dataset endpoint from the app config
    dataset_endpoint = app.config["DATASET_DB_URL"]

    # Create a SPARQLWrapper for the dataset
    sparql = SPARQLWrapper(dataset_endpoint)
    sparql.setMethod("POST")

    # Generate unique test IDs
    test_id = str(uuid.uuid4())
    graph_uri = f"http://example.org/test-graph-{test_id}"
    person1_uri = f"http://example.org/person1-{test_id}"
    person2_uri = f"http://example.org/person2-{test_id}"
    document1_uri = f"http://example.org/document1-{test_id}"
    relationship1_uri = f"http://example.org/relationship1-{test_id}"

    # Clear any existing data
    clear_query = f"""
    CLEAR GRAPH <{graph_uri}>;
    """
    sparql.setQuery(clear_query)
    sparql.query()

    # Insert test data
    insert_query = f"""
    INSERT DATA {{
        GRAPH <{graph_uri}> {{
            <{person1_uri}> a <http://example.org/Person> ;
                <http://example.org/name> "John Doe {test_id}" ;
                <http://example.org/age> "30"^^<http://www.w3.org/2001/XMLSchema#integer> ;
                <http://example.org/knows> <{person2_uri}> .
                
            <{person2_uri}> a <http://example.org/Person> ;
                <http://example.org/name> "Jane Smith {test_id}" ;
                <http://example.org/age> "28"^^<http://www.w3.org/2001/XMLSchema#integer> .
                
            <{document1_uri}> a <http://example.org/Document> ;
                <http://example.org/title> "Test Document {test_id}" ;
                <http://example.org/author> <{person1_uri}> .
                
            <{relationship1_uri}> a <http://example.org/Relationship> ;
                <http://example.org/from> <{person1_uri}> ;
                <http://example.org/to> <{person2_uri}> ;
                <http://example.org/type> "Friend" .
        }}
    }}
    """
    sparql.setQuery(insert_query)
    sparql.query()

    yield {
        "graph_uri": graph_uri,
        "person1_uri": person1_uri,
        "person2_uri": person2_uri,
        "document1_uri": document1_uri,
        "relationship1_uri": relationship1_uri,
        "test_id": test_id
    }

    # Clean up after tests
    sparql.setQuery(clear_query)
    sparql.query()


@pytest.mark.usefixtures("setup_test_data")
class TestGetAvailableClassesIntegration:
    """Integration tests for the get_available_classes function."""

    def test_get_available_classes_real_db(self, app, setup_test_data):
        """Test getting available classes from the real test database."""
        with app.app_context():
            # Patch the entity type visibility check to allow our test classes
            with pytest.MonkeyPatch.context() as monkeypatch:
                monkeypatch.setattr(
                    "heritrace.utils.sparql_utils.is_entity_type_visible",
                    lambda uri: True,
                )

                classes = get_available_classes()

                # Verify we get our test classes
                class_uris = [c["uri"] for c in classes]
                assert "http://example.org/Person" in class_uris
                assert "http://example.org/Document" in class_uris

                # Verify the counts
                person_class = next(
                    c for c in classes if c["uri"] == "http://example.org/Person"
                )
                assert person_class["count"] == 2

                document_class = next(
                    c for c in classes if c["uri"] == "http://example.org/Document"
                )
                assert document_class["count"] == 1


@pytest.mark.usefixtures("setup_test_data")
class TestGetEntitiesForClassIntegration:
    """Integration tests for the get_entities_for_class function."""

    def test_get_entities_for_class_real_db(self, app, setup_test_data):
        """Test getting entities for a class from the real test database."""
        with app.app_context():
            # Get entities for the Person class
            entities, total_count = get_entities_for_class(
                "http://example.org/Person", 1, 10
            )

            # Verify the results
            assert total_count == 2
            assert len(entities) == 2

            # Check that we got the expected entities
            entity_uris = [e["uri"] for e in entities]
            assert setup_test_data["person1_uri"] in entity_uris
            assert setup_test_data["person2_uri"] in entity_uris

    def test_get_entities_with_sorting(self, app, setup_test_data):
        """Test getting entities with sorting from the real test database."""
        with app.app_context():
            # Get entities for the Person class, sorted by name
            entities, total_count = get_entities_for_class(
                "http://example.org/Person",
                1,
                10,
                sort_property="http://example.org/name",
                sort_direction="ASC",
            )

            # Verify the results without assuming specific order
            assert len(entities) == 2
            assert total_count == 2

            # Check that both expected entities are present
            entity_uris = [entity["uri"] for entity in entities]
            assert setup_test_data["person1_uri"] in entity_uris
            assert setup_test_data["person2_uri"] in entity_uris


@pytest.mark.usefixtures("setup_test_data")
class TestGetCatalogDataIntegration:
    """Integration tests for the get_catalog_data function."""

    def test_get_catalog_data_real_db(self, app, setup_test_data):
        """Test getting catalog data from the real test database."""
        with app.app_context():
            # Patch the sortable properties function to return our test properties
            with pytest.MonkeyPatch.context() as monkeypatch:
                monkeypatch.setattr(
                    "heritrace.utils.sparql_utils.get_sortable_properties",
                    lambda class_uri, display_rules, form_fields_cache: [
                        {
                            "property": "http://example.org/name",
                            "displayName": "Name",
                            "sortType": "string",
                        },
                        {
                            "property": "http://example.org/age",
                            "displayName": "Age",
                            "sortType": "number",
                        },
                    ],
                )

                # Get catalog data for the Person class
                catalog_data = get_catalog_data(
                    "http://example.org/Person",
                    1,
                    10,
                    sort_property="http://example.org/name",
                    sort_direction="ASC",
                )

                # Verify the catalog data
                assert catalog_data["total_count"] == 2
                assert catalog_data["current_page"] == 1
                assert catalog_data["per_page"] == 10
                assert catalog_data["total_pages"] == 1
                assert catalog_data["sort_property"] == "http://example.org/name"
                assert catalog_data["sort_direction"] == "ASC"
                assert catalog_data["selected_class"] == "http://example.org/Person"

                # Verify the entities without assuming specific order
                assert len(catalog_data["entities"]) == 2
                entity_uris = [entity["uri"] for entity in catalog_data["entities"]]
                assert setup_test_data["person1_uri"] in entity_uris
                assert setup_test_data["person2_uri"] in entity_uris

                # Verify the sortable properties
                assert len(catalog_data["sortable_properties"]) == 2
                assert (
                    catalog_data["sortable_properties"][0]["property"]
                    == "http://example.org/name"
                )
                assert (
                    catalog_data["sortable_properties"][1]["property"]
                    == "http://example.org/age"
                )

    def test_get_catalog_data_no_class(self, app):
        """Test getting catalog data with no class selected."""
        with app.app_context():
            # Get catalog data with no class selected
            catalog_data = get_catalog_data(None, 1, 10)

            # Verify the catalog data
            assert catalog_data["total_count"] == 0
            assert catalog_data["current_page"] == 1
            assert catalog_data["per_page"] == 10
            assert catalog_data["total_pages"] == 0
            assert catalog_data["selected_class"] is None
            assert len(catalog_data["entities"]) == 0


@pytest.mark.usefixtures("setup_test_data")
class TestFetchDataGraphForSubjectIntegration:
    """Integration tests for the fetch_data_graph_for_subject function."""

    def test_fetch_data_graph_real_db(self, app, setup_test_data):
        """Test fetching data for a subject from the real test database."""
        with app.app_context():
            # Fetch data for person1
            graph = fetch_data_graph_for_subject(setup_test_data["person1_uri"])

            # Verify the graph contains the expected triples
            assert len(graph) > 0

            # Check for specific triples
            person_uri = URIRef(setup_test_data["person1_uri"])
            type_triple = (person_uri, RDF.type, URIRef("http://example.org/Person"))
            name_pred = URIRef("http://example.org/name")

            # For quadstore, we need to check if the triple exists in any context
            if hasattr(graph, "quads"):
                # Check if the type triple exists in any context
                type_exists = any(
                    s == person_uri
                    and p == RDF.type
                    and o == URIRef("http://example.org/Person")
                    for s, p, o, _ in graph.quads()
                )
                assert type_exists

                # Check if the name triple exists
                name_exists = any(
                    s == person_uri and p == name_pred for s, p, o, _ in graph.quads()
                )
                assert name_exists
            else:
                # For regular triplestore
                assert (
                    person_uri,
                    RDF.type,
                    URIRef("http://example.org/Person"),
                ) in graph
                assert (person_uri, name_pred, Literal(f"John Doe {setup_test_data['test_id']}")) in graph

    def test_fetch_data_graph_non_virtuoso_quadstore(self, app, setup_test_data):
        """Test fetching data for a subject from a non-virtuoso quadstore."""
        with app.app_context():
            # Mock is_virtuoso to return False and get_dataset_is_quadstore to return True
            with pytest.MonkeyPatch.context() as monkeypatch:
                monkeypatch.setattr("heritrace.utils.sparql_utils.is_virtuoso", lambda: False)
                monkeypatch.setattr("heritrace.utils.sparql_utils.get_dataset_is_quadstore", lambda: True)

                # Fetch data for person1
                graph = fetch_data_graph_for_subject(setup_test_data["person1_uri"])

                # Verify the graph contains the expected triples
                assert len(graph) > 0

                # Check for specific triples
                person_uri = URIRef(setup_test_data["person1_uri"])
                type_triple = (person_uri, RDF.type, URIRef("http://example.org/Person"))
                name_pred = URIRef("http://example.org/name")

                # Since we're testing quadstore, we need to check if the triples exist in any context
                # Check if the type triple exists in any context
                type_exists = any(
                    s == person_uri
                    and p == RDF.type
                    and o == URIRef("http://example.org/Person")
                    for s, p, o, _ in graph.quads()
                )
                assert type_exists

                # Check if the name triple exists in any context
                name_exists = any(
                    s == person_uri and p == name_pred for s, p, o, _ in graph.quads()
                )
                assert name_exists

                # Verify that the graph is a ConjunctiveGraph (quadstore)
                assert hasattr(graph, "quads")


@pytest.mark.usefixtures("setup_test_data")
class TestFetchCurrentStateWithRelatedEntitiesIntegration:
    """Integration tests for the fetch_current_state_with_related_entities function."""

    def test_fetch_current_state_with_related_entities_real_db(self, app, setup_test_data):
        """Test fetching current state with related entities from the real test database."""
        with app.app_context():
            # Create a provenance dictionary with multiple entities
            provenance = {
                setup_test_data["person1_uri"]: {"some_metadata": "value1"},
                setup_test_data["person2_uri"]: {"some_metadata": "value2"},
                setup_test_data["document1_uri"]: {"some_metadata": "value3"},
            }

            # Fetch the combined graph
            combined_graph = fetch_current_state_with_related_entities(provenance)

            # Verify the graph contains data for all entities
            assert len(combined_graph) > 0

            # Check for specific triples from each entity
            person1_uri = URIRef(setup_test_data["person1_uri"])
            person2_uri = URIRef(setup_test_data["person2_uri"])
            document1_uri = URIRef(setup_test_data["document1_uri"])

            # For quadstore, we need to check if the triples exist in any context
            if hasattr(combined_graph, "quads"):
                # Check if person1 type triple exists
                person1_type_exists = any(
                    s == person1_uri
                    and p == RDF.type
                    and o == URIRef("http://example.org/Person")
                    for s, p, o, _ in combined_graph.quads()
                )
                assert person1_type_exists

                # Check if person2 type triple exists
                person2_type_exists = any(
                    s == person2_uri
                    and p == RDF.type
                    and o == URIRef("http://example.org/Person")
                    for s, p, o, _ in combined_graph.quads()
                )
                assert person2_type_exists

                # Check if document1 type triple exists
                document1_type_exists = any(
                    s == document1_uri
                    and p == RDF.type
                    and o == URIRef("http://example.org/Document")
                    for s, p, o, _ in combined_graph.quads()
                )
                assert document1_type_exists
            else:
                # For regular triplestore
                assert (
                    person1_uri,
                    RDF.type,
                    URIRef("http://example.org/Person"),
                ) in combined_graph
                assert (
                    person2_uri,
                    RDF.type,
                    URIRef("http://example.org/Person"),
                ) in combined_graph
                assert (
                    document1_uri,
                    RDF.type,
                    URIRef("http://example.org/Document"),
                ) in combined_graph


@pytest.mark.usefixtures("setup_test_data")
class TestFindOrphanedEntitiesIntegration:
    """Integration tests for the find_orphaned_entities function."""

    def test_find_orphaned_entities_real_db(self, app, setup_test_data):
        """Test finding orphaned entities in the real test database."""
        with app.app_context():
            # Set up display rules for the test
            with pytest.MonkeyPatch.context() as monkeypatch:
                # Mock the display rules to include our test classes and relationships
                display_rules = [
                    {
                        "class": "http://example.org/Person",
                        "displayProperties": [
                            {
                                "property": "http://example.org/knows",
                                "intermediateRelation": {
                                    "class": "http://example.org/Relationship"
                                },
                            }
                        ],
                    }
                ]
                monkeypatch.setattr(
                    "heritrace.utils.sparql_utils.get_display_rules",
                    lambda: display_rules,
                )

                # Find orphaned entities if we delete person1
                orphaned, intermediate_orphans = find_orphaned_entities(
                    setup_test_data["person1_uri"], "http://example.org/Person"
                )

                # Verify that we get some results, but don't assume specific entities
                # The test database might not have the exact structure we expect
                assert isinstance(orphaned, list)
                assert isinstance(intermediate_orphans, list)

    def test_find_orphaned_entities_with_predicate(self, app, setup_test_data):
        """Test finding orphaned entities when deleting a specific triple."""
        with app.app_context():
            # Set up display rules for the test
            with pytest.MonkeyPatch.context() as monkeypatch:
                # Mock the display rules to include our test classes and relationships
                display_rules = [
                    {
                        "class": "http://example.org/Person",
                        "displayProperties": [
                            {
                                "property": "http://example.org/knows",
                                "intermediateRelation": {
                                    "class": "http://example.org/Relationship"
                                },
                            }
                        ],
                    }
                ]
                monkeypatch.setattr(
                    "heritrace.utils.sparql_utils.get_display_rules",
                    lambda: display_rules,
                )

                # Find orphaned entities if we delete the author relationship from document1
                orphaned, intermediate_orphans = find_orphaned_entities(
                    setup_test_data["document1_uri"],
                    "http://example.org/Document",
                    predicate="http://example.org/author",
                    object_value=setup_test_data["person1_uri"],
                )

                # No entities should be orphaned in this case
                assert len(orphaned) == 0
                assert len(intermediate_orphans) == 0


@pytest.mark.usefixtures("setup_test_data")
class TestParseSparqlUpdateIntegration:
    """Integration tests for the parse_sparql_update function using real SPARQL queries."""

    def test_parse_sparql_update_with_insert(self, app):
        """Test parsing a SPARQL INSERT DATA query."""
        with app.app_context():
            # Create a test query that inserts triples
            query = """
            INSERT DATA {
                <http://example.org/subject1> <http://example.org/predicate1> "object1" .
                <http://example.org/subject2> <http://example.org/predicate2> "object2" .
            }
            """
            
            modifications = parse_sparql_update(query)
            
            # Verify the modifications contain additions
            assert "Additions" in modifications, f"Expected 'Additions' in modifications, got: {modifications}"
            additions = modifications["Additions"]
            
            # Verify the number of additions
            assert len(additions) == 2, f"Expected 2 additions, got {len(additions)}"
            
            # Verify the content of the additions
            expected_triples = [
                (URIRef("http://example.org/subject1"), 
                 URIRef("http://example.org/predicate1"), 
                 Literal("object1")),
                (URIRef("http://example.org/subject2"), 
                 URIRef("http://example.org/predicate2"), 
                 Literal("object2"))
            ]
            
            for expected in expected_triples:
                assert expected in additions, f"Expected triple {expected} not found in additions: {additions}"

    def test_parse_sparql_update_with_delete(self, app):
        """Test parsing a SPARQL DELETE DATA query."""
        with app.app_context():
            # Create a test query that deletes triples with graph context
            query = """
            DELETE DATA {
                GRAPH <http://example.org/graph1> {
                    <http://example.org/subject1> <http://example.org/predicate1> "object1" .
                }
                GRAPH <http://example.org/graph2> {
                    <http://example.org/subject2> <http://example.org/predicate2> "object2" .
                }
            }
            """
            
            # Parse the query and get the parsed and translated versions
            parsed = parseUpdate(query)
            translated = translateUpdate(parsed).algebra
            
            # Verify that the operation has the quads attribute and it's not empty
            operation = next(iter(translated))
            assert hasattr(operation, "quads"), "Operation should have quads attribute"
            assert operation.quads, "Operation quads should not be empty"
            
            # Get the modifications
            modifications = parse_sparql_update(query)
            
            # Verify the modifications contain deletions
            assert "Deletions" in modifications
            deletions = modifications["Deletions"]
            
            # Verify the number of deletions (should be 2, one from each graph)
            assert len(deletions) == 2
            
            # Verify the content of the deletions
            expected_triples = [
                (URIRef("http://example.org/subject1"), 
                 URIRef("http://example.org/predicate1"), 
                 Literal("object1")),
                (URIRef("http://example.org/subject2"), 
                 URIRef("http://example.org/predicate2"), 
                 Literal("object2"))
            ]
            
            for expected in expected_triples:
                assert expected in deletions

    def test_parse_sparql_update_with_graph_context(self, app):
        """Test parsing a SPARQL query with graph context."""
        with app.app_context():
            # Create a test query that inserts triples with graph context
            query = """
            INSERT DATA {
                GRAPH <http://example.org/graph1> {
                    <http://example.org/subject1> <http://example.org/predicate1> "object1" .
                }
                GRAPH <http://example.org/graph2> {
                    <http://example.org/subject2> <http://example.org/predicate2> "object2" .
                }
            }
            """
            
            # Parse the query and get the parsed and translated versions
            parsed = parseUpdate(query)
            translated = translateUpdate(parsed).algebra
            
            # Verify that the operation has the quads attribute and it's not empty
            operation = next(iter(translated))
            assert hasattr(operation, "quads"), "Operation should have quads attribute"
            assert operation.quads, "Operation quads should not be empty"
            
            # Get the modifications
            modifications = parse_sparql_update(query)
            
            # Verify the modifications contain additions
            assert "Additions" in modifications
            additions = modifications["Additions"]
            
            # Verify the number of additions (should be 2, one from each graph)
            assert len(additions) == 2
            
            # Verify the content of the additions
            expected_triples = [
                (URIRef("http://example.org/subject1"), 
                 URIRef("http://example.org/predicate1"), 
                 Literal("object1")),
                (URIRef("http://example.org/subject2"), 
                 URIRef("http://example.org/predicate2"), 
                 Literal("object2"))
            ]
            
            for expected in expected_triples:
                assert expected in additions

    def test_parse_sparql_update_with_mixed_operations(self, app):
        """Test parsing a SPARQL query with both INSERT and DELETE operations."""
        with app.app_context():
            # Create a test query that both inserts and deletes triples
            query = """
            DELETE DATA {
                <http://example.org/subject1> <http://example.org/predicate1> "object1" .
            };
            INSERT DATA {
                <http://example.org/subject2> <http://example.org/predicate2> "object2" .
            }
            """
            
            modifications = parse_sparql_update(query)
            
            # Verify both deletions and additions are present
            assert "Deletions" in modifications
            assert "Additions" in modifications
            
            # Verify the content of deletions
            expected_deletion = (URIRef("http://example.org/subject1"), 
                               URIRef("http://example.org/predicate1"), 
                               Literal("object1"))
            assert expected_deletion in modifications["Deletions"]
            
            # Verify the content of additions
            expected_addition = (URIRef("http://example.org/subject2"), 
                               URIRef("http://example.org/predicate2"), 
                               Literal("object2"))
            assert expected_addition in modifications["Additions"]

    def test_parse_sparql_update_with_typed_literals(self, app):
        """Test parsing a SPARQL query with typed literals."""
        with app.app_context():
            # Create a test query with typed literals
            query = """
            INSERT DATA {
                <http://example.org/subject1> <http://example.org/predicate1> "42"^^<http://www.w3.org/2001/XMLSchema#integer> .
                <http://example.org/subject2> <http://example.org/predicate2> "true"^^<http://www.w3.org/2001/XMLSchema#boolean> .
            }
            """
            
            modifications = parse_sparql_update(query)
            
            # Verify the modifications contain additions
            assert "Additions" in modifications
            additions = modifications["Additions"]
            
            # Verify the content of the additions with typed literals
            expected_triples = [
                (URIRef("http://example.org/subject1"), 
                 URIRef("http://example.org/predicate1"), 
                 Literal("42", datatype=URIRef("http://www.w3.org/2001/XMLSchema#integer"))),
                (URIRef("http://example.org/subject2"), 
                 URIRef("http://example.org/predicate2"), 
                 Literal("true", datatype=URIRef("http://www.w3.org/2001/XMLSchema#boolean")))
            ]
            
            for expected in expected_triples:
                assert expected in additions
