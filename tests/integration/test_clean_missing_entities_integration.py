import pytest
from SPARQLWrapper import JSON

from heritrace.scripts.clean_missing_entities import MissingEntityCleaner
from heritrace.utils.sparql_utils import get_sparql
from tests.integration.test_sparql_utils_integration import setup_test_data


@pytest.mark.usefixtures("setup_test_data")
class TestMissingEntityCleanerIntegration:
    """Integration tests for the MissingEntityCleaner class."""

    def test_find_missing_entities_with_references(self, app, setup_test_data):
        """Test finding missing entity references in the test database."""
        with app.app_context():
            # Create a reference to a missing entity (entity that doesn't exist)
            sparql = get_sparql()
            
            # Define a URI for a missing entity that doesn't exist in the dataset
            missing_uri = "http://example.org/missing1"
            
            # Create a reference to the missing entity
            reference_query = f"""
            INSERT DATA {{
                GRAPH <{setup_test_data["graph_uri"]}> {{
                    <{setup_test_data["person1_uri"]}> <http://example.org/references> <{missing_uri}> .
                }}
            }}
            """
            
            sparql.setQuery(reference_query)
            sparql.method = "POST"
            sparql.query()
            
            # Initialize the MissingEntityCleaner with is_virtuoso=True from app config
            cleaner = MissingEntityCleaner(
                endpoint=sparql.endpoint,
                is_virtuoso=app.config["DATASET_DB_TRIPLESTORE"].lower() == "virtuoso"
            )
            
            # Find missing entities with references
            missing_entities = cleaner._find_missing_entities_with_references()
            
            # Check if our test missing entity is in the results
            found_missing = False
            for entity_uri, references in missing_entities.items():
                if entity_uri == missing_uri:
                    found_missing = True
                    # Check that the reference is correct
                    assert len(references) > 0
                    assert any(ref for ref in references 
                               if ref['subject'] == setup_test_data["person1_uri"] 
                               and ref['predicate'] == "http://example.org/references")
                    break
                    
            assert found_missing, "Test missing entity was not found"
            
            # Clean up by removing the test data
            cleanup_query = f"""
            DELETE DATA {{
                GRAPH <{setup_test_data["graph_uri"]}> {{
                    <{setup_test_data["person1_uri"]}> <http://example.org/references> <{missing_uri}> .
                }}
            }}
            """
            
            sparql.setQuery(cleanup_query)
            sparql.method = "POST"
            sparql.query()

    def test_remove_references(self, app, setup_test_data):
        """Test removing references to a missing entity."""
        with app.app_context():
            # Create references to a missing entity
            sparql = get_sparql()
            
            missing_uri = "http://example.org/missing3"
            
            # Create a reference to the missing entity
            reference_query = f"""
            INSERT DATA {{
                GRAPH <{setup_test_data["graph_uri"]}> {{
                    <{setup_test_data["person1_uri"]}> <http://example.org/attendedEvent> <{missing_uri}> .
                }}
            }}
            """
            
            sparql.setQuery(reference_query)
            sparql.method = "POST"
            sparql.query()
            
            # Initialize the MissingEntityCleaner with is_virtuoso=True from app config
            cleaner = MissingEntityCleaner(
                endpoint=sparql.endpoint,
                is_virtuoso=app.config["DATASET_DB_TRIPLESTORE"].lower() == "virtuoso"
            )
            
            # Define the references to remove
            references = [
                {"subject": setup_test_data["person1_uri"], "predicate": "http://example.org/attendedEvent"}
            ]
            
            # Remove the references
            success = cleaner._remove_references(missing_uri, references)
            
            # Verify the references were removed
            assert success is True
            
            # Check that the reference no longer exists
            check_query = f"""
            ASK {{
                GRAPH <{setup_test_data["graph_uri"]}> {{
                    <{setup_test_data["person1_uri"]}> <http://example.org/attendedEvent> <{missing_uri}> .
                }}
            }}
            """
            
            sparql.setQuery(check_query)
            sparql.setReturnFormat(JSON)
            result = sparql.queryAndConvert()
            
            # The reference should no longer exist
            assert result["boolean"] is False

    def test_process_missing_entities(self, app, setup_test_data):
        """Test the full workflow for processing missing entities."""
        with app.app_context():
            sparql = get_sparql()
            
            # Create references to missing entities
            missing_uri1 = "http://example.org/missing4"
            missing_uri2 = "http://example.org/missing5"
            
            # Create references to the missing entities
            reference_query = f"""
            INSERT DATA {{
                GRAPH <{setup_test_data["graph_uri"]}> {{
                    <{setup_test_data["person1_uri"]}> <http://example.org/knows> <{missing_uri1}> .
                    <{setup_test_data["document1_uri"]}> <http://example.org/mentions> <{missing_uri2}> .
                }}
            }}
            """
            
            sparql.setQuery(reference_query)
            sparql.method = "POST"
            sparql.query()
            
            # Initialize the MissingEntityCleaner with is_virtuoso=True from app config
            cleaner = MissingEntityCleaner(
                endpoint=sparql.endpoint,
                is_virtuoso=app.config["DATASET_DB_TRIPLESTORE"].lower() == "virtuoso"
            )
            
            # Process the missing entities
            results = cleaner.process_missing_entities()
            
            # Verify our test entities are present in the results
            result_uris = [result["uri"] for result in results]
            assert missing_uri1 in result_uris
            assert missing_uri2 in result_uris
            
            # Map results by URI for easier verification
            results_map = {result["uri"]: result for result in results}
            
            # Check missing_uri1 results
            assert results_map[missing_uri1]["success"] is True
            assert len(results_map[missing_uri1]["references"]) == 1
            reference = results_map[missing_uri1]["references"][0]
            assert reference["subject"] == setup_test_data["person1_uri"]
            assert reference["predicate"] == "http://example.org/knows"
            
            # Check missing_uri2 results
            assert results_map[missing_uri2]["success"] is True
            assert len(results_map[missing_uri2]["references"]) == 1
            reference = results_map[missing_uri2]["references"][0]
            assert reference["subject"] == setup_test_data["document1_uri"]
            assert reference["predicate"] == "http://example.org/mentions"
            
            # Verify the references were actually removed from the database
            check_query = f"""
            ASK {{
                GRAPH <{setup_test_data["graph_uri"]}> {{
                    {{ <{setup_test_data["person1_uri"]}> <http://example.org/knows> <{missing_uri1}> . }}
                    UNION
                    {{ <{setup_test_data["document1_uri"]}> <http://example.org/mentions> <{missing_uri2}> . }}
                }}
            }}
            """
            
            sparql.setQuery(check_query)
            sparql.setReturnFormat(JSON)
            result = sparql.queryAndConvert()
            
            # The references should no longer exist
            assert result["boolean"] is False 