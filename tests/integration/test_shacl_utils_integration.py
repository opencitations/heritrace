import os
from unittest.mock import patch

from flask import Flask
import pytest
from heritrace.utils.shacl_utils import (get_form_fields_from_shacl,
                                         get_valid_predicates,
                                         validate_new_triple,
                                         get_form_fields_from_shacl,
                                         process_query_results,
                                         convert_to_matching_class,
                                         convert_to_matching_literal)
from rdflib import RDF, XSD, Graph, Literal, URIRef
from tests.test_config import BASE_HERITRACE_DIR


@pytest.fixture
def shacl_graph(app: Flask):
    """Returns the SHACL graph used for testing."""
    with app.app_context():
        # Load SHACL graph directly from file
        graph = Graph()
        shacl_path = os.path.join(BASE_HERITRACE_DIR, "resources", "shacl.ttl")
        graph.parse(shacl_path, format="turtle")
        return graph

@pytest.fixture
def mock_fetch_data_graph():
    """Mock the fetch_data_graph_for_subject function to return a consistent test graph."""
    with patch("heritrace.utils.shacl_utils.fetch_data_graph_for_subject") as mock:
        # Create a dictionary to store test graphs for different subjects
        test_graphs = {}
        
        # Add Journal
        journal = URIRef("https://example.org/journal/1")
        journal_graph = Graph()
        journal_graph.add((journal, RDF.type, URIRef("http://purl.org/spar/fabio/Journal")))
        journal_graph.add((journal, RDF.type, URIRef("http://purl.org/spar/fabio/Expression")))
        journal_graph.add((journal, URIRef("http://purl.org/dc/terms/title"), Literal("Test Journal")))
        
        # Add Journal's ISSN
        journal_id = URIRef("https://example.org/identifier/journal/issn")
        journal_graph.add((journal_id, RDF.type, URIRef("http://purl.org/spar/datacite/Identifier")))
        journal_graph.add((journal_id, URIRef("http://purl.org/spar/datacite/usesIdentifierScheme"), URIRef("http://purl.org/spar/datacite/issn")))
        journal_graph.add((journal_id, URIRef("http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"), Literal("2049-3630")))
        journal_graph.add((journal, URIRef("http://purl.org/spar/datacite/hasIdentifier"), journal_id))
        test_graphs[str(journal)] = journal_graph
        
        # Add Article 1 (with data)
        article1 = URIRef("https://example.org/article/1")
        article1_graph = Graph()
        article1_graph.add((article1, RDF.type, URIRef("http://purl.org/spar/fabio/JournalArticle")))
        article1_graph.add((article1, RDF.type, URIRef("http://purl.org/spar/fabio/Expression")))
        article1_graph.add((article1, URIRef("http://purl.org/dc/terms/title"), Literal("Test Article")))
        article1_graph.add((article1, URIRef("http://purl.org/dc/terms/abstract"), Literal("Test Abstract")))
        article1_graph.add((article1, URIRef("http://prismstandard.org/namespaces/basic/2.0/publicationDate"), Literal("2024-03-21", datatype=XSD.date)))
        article1_graph.add((article1, URIRef("http://purl.org/vocab/frbr/core#partOf"), journal))
        
        # Add Article 1's DOI
        article1_id = URIRef("https://example.org/identifier/article/doi")
        article1_graph.add((article1_id, RDF.type, URIRef("http://purl.org/spar/datacite/Identifier")))
        article1_graph.add((article1_id, URIRef("http://purl.org/spar/datacite/usesIdentifierScheme"), URIRef("http://purl.org/spar/datacite/doi")))
        article1_graph.add((article1_id, URIRef("http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"), Literal("10.1234/test.123")))
        article1_graph.add((article1, URIRef("http://purl.org/spar/datacite/hasIdentifier"), article1_id))
        test_graphs[str(article1)] = article1_graph
        
        # Add Article 2 (empty)
        article2 = URIRef("https://example.org/article/2")
        article2_graph = Graph()
        article2_graph.add((article2, RDF.type, URIRef("http://purl.org/spar/fabio/JournalArticle")))
        article2_graph.add((article2, RDF.type, URIRef("http://purl.org/spar/fabio/Expression")))
        test_graphs[str(article2)] = article2_graph
        
        # Add Person
        person = URIRef("https://example.org/person/1")
        person_graph = Graph()
        person_graph.add((person, RDF.type, URIRef("http://xmlns.com/foaf/0.1/Agent")))
        person_graph.add((person, URIRef("http://xmlns.com/foaf/0.1/name"), Literal("Test Person")))
        
        # Add Person's ORCID
        person_id = URIRef("https://example.org/identifier/person/orcid")
        person_graph.add((person_id, RDF.type, URIRef("http://purl.org/spar/datacite/Identifier")))
        person_graph.add((person_id, URIRef("http://purl.org/spar/datacite/usesIdentifierScheme"), URIRef("http://purl.org/spar/datacite/orcid")))
        person_graph.add((person_id, URIRef("http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"), Literal("0000-0002-1825-0097")))
        person_graph.add((person, URIRef("http://purl.org/spar/datacite/hasIdentifier"), person_id))
        test_graphs[str(person)] = person_graph
        
        # Add Author Role
        author_role = URIRef("https://example.org/role/1")
        role_graph = Graph()
        role_graph.add((author_role, RDF.type, URIRef("http://purl.org/spar/pro/RoleInTime")))
        role_graph.add((author_role, URIRef("http://purl.org/spar/pro/withRole"), URIRef("http://purl.org/spar/pro/author")))
        role_graph.add((author_role, URIRef("http://purl.org/spar/pro/isHeldBy"), person))
        role_graph.add((article1, URIRef("http://purl.org/spar/pro/isDocumentContextFor"), author_role))
        test_graphs[str(author_role)] = role_graph

        def side_effect(subject):
            """Return the appropriate test graph for the subject."""
            # Convert subject to string for dictionary lookup
            subject_str = str(subject) if isinstance(subject, URIRef) else subject
            # Return empty graph if subject not found
            return test_graphs.get(subject_str, Graph())

        mock.side_effect = side_effect
        yield mock

def test_get_form_fields_from_shacl_journal_article(app: Flask, shacl_graph: Graph):
    """Test form field extraction for JournalArticle with real SHACL data."""
    with app.app_context():
        # Test with JournalArticle class
        form_fields = get_form_fields_from_shacl(shacl_graph, None)
        
        # Check that JournalArticle class exists in form fields
        assert "http://purl.org/spar/fabio/JournalArticle" in form_fields
        
        # Check required properties for JournalArticle
        journal_article_fields = form_fields["http://purl.org/spar/fabio/JournalArticle"]
        
        # Check type properties
        assert "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" in journal_article_fields
        type_fields = journal_article_fields["http://www.w3.org/1999/02/22-rdf-syntax-ns#type"]
        assert any(field["hasValue"] == "http://purl.org/spar/fabio/Expression" for field in type_fields)
        assert any(field["hasValue"] == "http://purl.org/spar/fabio/JournalArticle" for field in type_fields)
        
        # Check title property
        assert "http://purl.org/dc/terms/title" in journal_article_fields
        title_field = journal_article_fields["http://purl.org/dc/terms/title"][0]
        assert title_field["datatypes"] == ["http://www.w3.org/2001/XMLSchema#string"]
        assert title_field["max"] == 1

def test_validate_new_triple_journal_article_title(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation of a new title triple for a JournalArticle."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                subject = "https://example.org/article/1"
                predicate = "http://purl.org/dc/terms/title"
                new_value = "Test Article Title"
                old_title = "Test Article"  # Il valore esistente nel grafo di test
                
                # Test validation
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    predicate,
                    new_value,
                    "update",  # Usiamo update invece di create
                    old_value=old_title,  # Specifichiamo il vecchio valore
                    entity_types=["http://purl.org/spar/fabio/JournalArticle", "http://purl.org/spar/fabio/Expression"]
                )
                
                assert error == "", f"Validation error: {error}"
                assert isinstance(valid_value, Literal), f"Expected Literal but got {type(valid_value)}"
                assert valid_value.datatype == XSD.string, f"Expected datatype {XSD.string} but got {valid_value.datatype}"
                assert str(valid_value) == new_value, f"Expected value {new_value} but got {str(valid_value)}"

def test_validate_new_triple_journal_identifier(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation of a new identifier triple for a JournalArticle."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                # Create a new identifier with DOI scheme
                identifier = "https://example.org/identifier/test-doi"
                article = "https://example.org/article/2"
                
                # Create test graphs
                test_graphs = {}
                
                # Create identifier graph
                identifier_graph = Graph()
                test_graphs[identifier] = identifier_graph
                
                # Create article graph
                article_graph = Graph()
                test_graphs[article] = article_graph
                
                # Mock the fetch_data_graph_for_subject function
                def side_effect(subject):
                    return test_graphs.get(subject, Graph())
                mock_fetch_data_graph.side_effect = side_effect
                
                # First, set the type to Identifier
                valid_value, old_value, error = validate_new_triple(
                    identifier,
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                    "http://purl.org/spar/datacite/Identifier",
                    "create",
                    entity_types=["http://purl.org/spar/datacite/Identifier"]
                )
                assert error == "", f"Validation error: {error}"
                
                # Add the type to the identifier graph
                identifier_graph.add((URIRef(identifier), RDF.type, URIRef("http://purl.org/spar/datacite/Identifier")))
                
                # Add the article type and relation
                article_graph.add((URIRef(article), RDF.type, URIRef("http://purl.org/spar/fabio/JournalArticle")))
                article_graph.add((URIRef(article), RDF.type, URIRef("http://purl.org/spar/fabio/Expression")))
                article_graph.add((URIRef(article), URIRef("http://purl.org/spar/datacite/hasIdentifier"), URIRef(identifier)))
                
                # Then, set the identifier scheme to DOI
                valid_value, old_value, error = validate_new_triple(
                    identifier,
                    "http://purl.org/spar/datacite/usesIdentifierScheme",
                    "http://purl.org/spar/datacite/doi",
                    "create",
                    entity_types=["http://purl.org/spar/datacite/Identifier"]
                )
                assert error == "", f"Validation error: {error}"
                
                # Add the identifier scheme to the identifier graph
                identifier_graph.add((URIRef(identifier), URIRef("http://purl.org/spar/datacite/usesIdentifierScheme"), URIRef("http://purl.org/spar/datacite/doi")))
                
                # Test validation with valid DOI
                valid_doi = "10.1000/test.123"
                valid_value, old_value, error = validate_new_triple(
                    identifier,
                    "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue",
                    valid_doi,
                    "create",
                    entity_types=["http://purl.org/spar/datacite/Identifier"]
                )
                assert error == "", f"Validation error: {error}"
                assert isinstance(valid_value, Literal)
                assert str(valid_value) == valid_doi
                
                # Add the valid DOI to the identifier graph
                identifier_graph.add((URIRef(identifier), URIRef("http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"), Literal(valid_doi)))

                # Test validation with invalid DOI format
                invalid_doi = "invalid-doi"
                valid_value, old_value, error = validate_new_triple(
                    identifier,
                    "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue",
                    invalid_doi,
                    "update",
                    old_value=valid_doi,
                    entity_types=["http://purl.org/spar/datacite/Identifier"]
                )
                assert error != "", "Should reject invalid DOI format"
                assert "DOI must start with '10.' followed by a prefix" in error

def test_get_valid_predicates_journal_article(app: Flask, shacl_graph: Graph):
    """Test getting valid predicates for a JournalArticle."""
    with app.app_context():
        with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
            # Create a test graph with a JournalArticle
            test_graph = Graph()
            subject = URIRef("https://example.org/article/1")
            test_graph.add((subject, RDF.type, URIRef("http://purl.org/spar/fabio/JournalArticle")))
            test_graph.add((subject, RDF.type, URIRef("http://purl.org/spar/fabio/Expression")))
            
            # Get valid predicates
            can_add, can_delete, datatypes, mandatory_values, optional_values, s_types, all_predicates = get_valid_predicates(
                list(test_graph.triples((subject, None, None)))
            )
            
            # Convert URIRefs to strings for comparison
            can_add_str = [str(x) for x in can_add]
            
            # Check that essential predicates are included
            assert "http://purl.org/dc/terms/title" in can_add_str
            assert "http://purl.org/dc/terms/abstract" in can_add_str
            assert "http://purl.org/spar/datacite/hasIdentifier" in can_add_str
            
            # Check datatypes
            assert "http://purl.org/dc/terms/title" in datatypes
            assert str(XSD.string) in datatypes["http://purl.org/dc/terms/title"]

def test_validate_new_triple_with_pattern_and_conditions(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation of triples with pattern constraints and conditions."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                # Test DOI pattern validation
                valid_doi = "10.1000/test.123"
                valid_value, old_value, error = validate_new_triple(
                    "https://example.org/identifier/doi",
                    "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue",
                    valid_doi,
                    "create",
                    entity_types=["http://purl.org/spar/datacite/Identifier"]
                )
                assert error == "", f"Validation error: {error}"
                assert isinstance(valid_value, Literal)
                assert str(valid_value) == valid_doi
                
                # Test ISBN pattern validation
                valid_isbn = "978-0-123456-47-2"
                valid_value, old_value, error = validate_new_triple(
                    "https://example.org/identifier/isbn",
                    "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue",
                    valid_isbn,
                    "create",
                    entity_types=["http://purl.org/spar/datacite/Identifier"]
                )
                assert error == "", f"Validation error: {error}"
                assert isinstance(valid_value, Literal)
                assert str(valid_value) == valid_isbn

def test_validate_new_triple_with_datatype_conversion(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation and conversion of values with different datatypes."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                # Usiamo un nuovo articolo senza date esistenti
                subject = "https://example.org/article/2"
                
                # Test date datatype with different formats
                date_tests = [
                    ("http://prismstandard.org/namespaces/basic/2.0/publicationDate", "2024-03-21", XSD.date),
                    ("http://prismstandard.org/namespaces/basic/2.0/publicationDate", "2024-03", XSD.gYearMonth),
                    ("http://prismstandard.org/namespaces/basic/2.0/publicationDate", "2024", XSD.gYear)
                ]
                
                for predicate, value, expected_datatype in date_tests:
                    valid_value, old_value, error = validate_new_triple(
                        subject,
                        predicate,
                        value,
                        "create",
                        entity_types=["http://purl.org/spar/fabio/JournalArticle"]
                    )
                    assert error == "", f"Validation error for {value}: {error}"
                    assert isinstance(valid_value, Literal)
                    assert valid_value.datatype == expected_datatype
                    assert str(valid_value) == value

def test_get_form_fields_with_display_rules(app: Flask, shacl_graph: Graph):
    """Test form field extraction with display rules."""
    with app.app_context():
        display_rules = [
            {
                "class": "http://purl.org/spar/fabio/JournalArticle",
                "displayProperties": [
                    {
                        "property": "http://purl.org/dc/terms/title",
                        "displayName": "Article Title",
                        "shouldBeDisplayed": True
                    },
                    {
                        "property": "http://purl.org/dc/terms/abstract",
                        "displayName": "Abstract",
                        "shouldBeDisplayed": True
                    }
                ]
            }
        ]
        
        form_fields = get_form_fields_from_shacl(shacl_graph, display_rules)
        
        # Check that display names are applied
        article_fields = form_fields["http://purl.org/spar/fabio/JournalArticle"]
        title_field = article_fields["http://purl.org/dc/terms/title"][0]
        abstract_field = article_fields["http://purl.org/dc/terms/abstract"][0]
        
        assert title_field["displayName"] == "Article Title"
        assert abstract_field["displayName"] == "Abstract"
        assert title_field["shouldBeDisplayed"] is True
        assert abstract_field["shouldBeDisplayed"] is True

def test_validate_new_triple_with_delete_action(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation of triple deletion."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                subject = "https://example.org/article/1"
                predicate = "http://purl.org/dc/terms/title"
                old_value = "Test Article Title"
                
                # Prima aggiungiamo il valore che vogliamo eliminare
                graph = mock_fetch_data_graph(subject)
                graph.add((URIRef(subject), URIRef(predicate), Literal(old_value)))
                
                # Test delete action
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    predicate,
                    None,
                    "delete",
                    old_value=old_value,
                    entity_types=["http://purl.org/spar/fabio/JournalArticle"]
                )
                assert error == "", f"Validation error: {error}"
                assert valid_value is None

def test_validate_new_triple_with_invalid_property(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation with an invalid property."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                subject = "https://example.org/article/1"
                predicate = "http://example.org/invalid/property"
                new_value = "Test Value"
                
                # Test with invalid property
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    predicate,
                    new_value,
                    "create",
                    entity_types=["http://purl.org/spar/fabio/JournalArticle"]
                )
                assert error != "", "Should reject invalid property"
                assert "is not allowed for resources of type" in error

def test_validate_new_triple_with_cardinality_constraints(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation of cardinality constraints."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                # Usiamo un nuovo articolo senza titolo esistente
                subject = "https://example.org/article/2"
                predicate = "http://purl.org/dc/terms/title"
                new_value = "Test Title"
                
                # First title should be accepted
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    predicate,
                    new_value,
                    "create",
                    entity_types=["http://purl.org/spar/fabio/JournalArticle"]
                )
                assert error == "", f"Validation error: {error}"
                assert isinstance(valid_value, Literal)
                assert valid_value.datatype == XSD.string
                assert str(valid_value) == new_value
                
                # Add the first title to the graph
                test_graph = mock_fetch_data_graph(subject)
                test_graph.add((URIRef(subject), URIRef(predicate), valid_value))
                
                # Second title should be rejected
                second_value = "Another Title"
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    predicate,
                    second_value,
                    "create",
                    entity_types=["http://purl.org/spar/fabio/JournalArticle"]
                )
                assert error != "", "Should reject second title"
                assert "allows at most 1 value" in error

def test_validate_new_triple_with_optional_values(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation with optional values."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                subject = "https://example.org/identifier/new"  # Usiamo un nuovo identificatore senza scheme
                predicate = "http://purl.org/spar/datacite/usesIdentifierScheme"
                
                # Test with valid scheme
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    predicate,
                    "http://purl.org/spar/datacite/doi",
                    "create",
                    entity_types=["http://purl.org/spar/datacite/Identifier"]
                )
                assert error == "", f"Validation error: {error}"
                
                # Test with invalid scheme
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    predicate,
                    "http://example.org/invalid/scheme",
                    "create",
                    entity_types=["http://purl.org/spar/datacite/Identifier"]
                )
                assert error != "", "Should reject invalid scheme"
                assert "is not a valid value" in error 

def test_get_form_fields_with_nested_shapes(app: Flask, shacl_graph: Graph):
    """Test form field extraction with nested shapes."""
    with app.app_context():
        # Test with JournalArticle class that has nested shapes (e.g., for authors)
        form_fields = get_form_fields_from_shacl(shacl_graph, None)
        
        # Check that JournalArticle class exists in form fields
        assert "http://purl.org/spar/fabio/JournalArticle" in form_fields
        journal_article_fields = form_fields["http://purl.org/spar/fabio/JournalArticle"]
        
        # Check that pro:isDocumentContextFor field exists and has nested shapes
        assert "http://purl.org/spar/pro/isDocumentContextFor" in journal_article_fields
        author_field = next(
            field for field in journal_article_fields["http://purl.org/spar/pro/isDocumentContextFor"]
            if "nodeShape" in field and "AuthorShape" in field["nodeShape"]
        )
        assert "nestedShape" in author_field
        assert len(author_field["nestedShape"]) > 0

def test_validate_new_triple_with_nested_validation(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation of nested shapes."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                subject = "https://example.org/article/1"
                predicate = "http://purl.org/spar/pro/isDocumentContextFor"
                role_value = "https://example.org/role/1"
                
                # Test validation of a role triple
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    predicate,
                    role_value,
                    "create",
                    entity_types=["http://purl.org/spar/fabio/JournalArticle"]
                )
                assert error == "", f"Validation error: {error}"
                assert isinstance(valid_value, URIRef)
                assert str(valid_value) == role_value

def test_validate_new_triple_with_or_constraints(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation with OR constraints."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                # Usiamo un nuovo articolo senza data esistente
                subject = "https://example.org/article/2"
                predicate = "http://prismstandard.org/namespaces/basic/2.0/publicationDate"
                
                # Test with different valid date formats
                date_values = [
                    "2024-03-21",  # date
                    "2024-03",     # gYearMonth
                    "2024"         # gYear
                ]
                
                # Test each format with a fresh subject
                for i, date_value in enumerate(date_values):
                    test_subject = f"https://example.org/article/{i+2}"  # Usiamo un soggetto diverso per ogni test
                    valid_value, old_value, error = validate_new_triple(
                        test_subject,
                        predicate,
                        date_value,
                        "create",
                        entity_types=["http://purl.org/spar/fabio/JournalArticle"]
                    )
                    assert error == "", f"Validation error for {date_value}: {error}"
                    assert isinstance(valid_value, Literal)

def test_validate_new_triple_with_multiple_types(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation with multiple entity types."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                # Usiamo un nuovo articolo senza titolo esistente
                subject = "https://example.org/article/2"
                predicate = "http://purl.org/dc/terms/title"
                new_value = "Test Title"
                
                # Test with multiple entity types
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    predicate,
                    new_value,
                    "create",
                    entity_types=[
                        "http://purl.org/spar/fabio/JournalArticle",
                        "http://purl.org/spar/fabio/Expression"
                    ]
                )
                assert error == "", f"Validation error: {error}"
                assert isinstance(valid_value, Literal)
                assert valid_value.datatype == XSD.string
                assert str(valid_value) == new_value

def test_validate_new_triple_with_intermediate_relation(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation with intermediate relations."""
    with app.app_context():
        display_rules = [
            {
                "class": "http://purl.org/spar/fabio/JournalArticle",
                "displayProperties": [
                    {
                        "property": "http://purl.org/spar/pro/isDocumentContextFor",
                        "intermediateRelation": {
                            "class": "http://purl.org/spar/pro/RoleInTime",
                            "targetEntityType": "http://xmlns.com/foaf/0.1/Person"
                        }
                    }
                ]
            }
        ]
        
        form_fields = get_form_fields_from_shacl(shacl_graph, display_rules)
        
        # Check that intermediate relation is processed
        article_fields = form_fields["http://purl.org/spar/fabio/JournalArticle"]
        role_field = article_fields["http://purl.org/spar/pro/isDocumentContextFor"][0]
        
        assert "intermediateRelation" in role_field
        assert role_field["intermediateRelation"]["class"] == "http://purl.org/spar/pro/RoleInTime"
        assert role_field["intermediateRelation"]["targetEntityType"] == "http://xmlns.com/foaf/0.1/Person"

def test_validate_new_triple_with_datatype_conversion_edge_cases(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test datatype conversion with edge cases."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                subject = "https://example.org/article/1"
                
                # Test with invalid date format
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    "http://prismstandard.org/namespaces/basic/2.0/publicationDate",
                    "invalid-date",
                    "create",
                    entity_types=["http://purl.org/spar/fabio/JournalArticle"]
                )
                assert error != "", "Should reject invalid date format"
                
                # Test with string value when no datatype is specified
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    "http://purl.org/dc/terms/description",
                    "Test description",
                    "create",
                    entity_types=["http://purl.org/spar/fabio/JournalArticle"]
                )
                assert error == "", f"Validation error: {error}"
                assert isinstance(valid_value, Literal)
                assert valid_value.datatype == XSD.string 

def test_validate_new_triple_with_complex_conditions(app: Flask, shacl_graph: Graph, mock_fetch_data_graph):
    """Test validation with complex conditions and edge cases."""
    with app.test_request_context():
        with app.app_context():
            with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shacl_graph):
                # Use article/2 which has no title
                subject = "https://example.org/article/2"
                
                # Test with no SHACL graph
                with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=Graph()):
                    valid_value, old_value, error = validate_new_triple(
                        subject,
                        "http://purl.org/dc/terms/title",
                        "Test Title",
                        "create",
                        entity_types=["http://purl.org/spar/fabio/JournalArticle"]
                    )
                    assert error == "", f"Validation error: {error}"
                    assert isinstance(valid_value, Literal)
                    # Without SHACL graph, no datatype is enforced
                    assert valid_value.datatype is None
                    assert str(valid_value) == "Test Title"
                
                # Test with empty entity types
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    "http://purl.org/dc/terms/title",
                    "Test Title",
                    "create",
                    entity_types=[]
                )
                assert error == "", f"Validation error: {error}"
                assert isinstance(valid_value, Literal)
                assert valid_value.datatype == XSD.string
                assert str(valid_value) == "Test Title"
                
                # Test with invalid entity type
                valid_value, old_value, error = validate_new_triple(
                    subject,
                    "http://purl.org/dc/terms/title",
                    "Test Title",
                    "create",
                    entity_types=["http://example.org/InvalidType"]
                )
                assert error == "", f"Validation error: {error}"
                assert isinstance(valid_value, Literal)
                assert valid_value.datatype == XSD.string
                assert str(valid_value) == "Test Title" 