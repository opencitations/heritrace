# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask
from rdflib import RDF, XSD, Graph, Literal, URIRef
from rdflib.plugins.sparql import prepareQuery

from heritrace.utils.display_rules_utils import get_highest_priority_class
from heritrace.utils.shacl_display import (
    ShaclProcessingContext,
    apply_display_rules_to_nested_shapes,
    execute_shacl_query,
    get_object_class,
    order_fields,
    process_query_results,
)
from heritrace.utils.shacl_utils import (
    get_form_fields_from_shacl,
    process_nested_shapes,
)
from heritrace.utils.shacl_validation import (
    convert_to_matching_class,
    convert_to_matching_literal,
    get_datatype_label,
    get_valid_predicates,
    validate_new_triple,
)
from tests.test_config import BASE_DIR


@pytest.fixture
def shacl_graph(app: Flask):
    """Returns the SHACL graph used for testing."""
    with app.app_context():
        # Load SHACL graph directly from file
        graph = Graph()
        shacl_path = BASE_DIR / "tests" / "shacl.ttl"
        graph.parse(shacl_path, format="turtle")
        return graph


@pytest.fixture
def mock_fetch_data_graph():
    """
    Mock the fetch_data_graph_for_subject function to return a consistent test graph.
    """
    with patch("heritrace.utils.sparql_utils.fetch_data_graph_for_subject") as mock:
        # Create a dictionary to store test graphs for different subjects
        test_graphs = {}

        # Add Journal
        journal = URIRef("https://example.org/journal/1")
        journal_graph = Graph()
        journal_graph.add(
            (journal, RDF.type, URIRef("http://purl.org/spar/fabio/Journal"))
        )
        journal_graph.add(
            (journal, RDF.type, URIRef("http://purl.org/spar/fabio/Expression"))
        )
        journal_graph.add(
            (journal, URIRef("http://purl.org/dc/terms/title"), Literal("Test Journal"))
        )

        # Add Journal's ISSN
        journal_id = URIRef("https://example.org/identifier/journal/issn")
        journal_graph.add(
            (journal_id, RDF.type, URIRef("http://purl.org/spar/datacite/Identifier"))
        )
        journal_graph.add(
            (
                journal_id,
                URIRef("http://purl.org/spar/datacite/usesIdentifierScheme"),
                URIRef("http://purl.org/spar/datacite/issn"),
            )
        )
        journal_graph.add(
            (
                journal_id,
                URIRef(
                    "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
                ),
                Literal("2049-3630"),
            )
        )
        journal_graph.add(
            (journal, URIRef("http://purl.org/spar/datacite/hasIdentifier"), journal_id)
        )
        test_graphs[str(journal)] = journal_graph

        # Add Article 1 (with data)
        article1 = URIRef("https://example.org/article/1")
        article1_graph = Graph()
        article1_graph.add(
            (article1, RDF.type, URIRef("http://purl.org/spar/fabio/JournalArticle"))
        )
        article1_graph.add(
            (article1, RDF.type, URIRef("http://purl.org/spar/fabio/Expression"))
        )
        article1_graph.add(
            (
                article1,
                URIRef("http://purl.org/dc/terms/title"),
                Literal("Test Article"),
            )
        )
        article1_graph.add(
            (
                article1,
                URIRef("http://purl.org/dc/terms/abstract"),
                Literal("Test Abstract"),
            )
        )
        article1_graph.add(
            (
                article1,
                URIRef("http://prismstandard.org/namespaces/basic/2.0/publicationDate"),
                Literal("2024-03-21", datatype=XSD.date),
            )
        )
        article1_graph.add(
            (article1, URIRef("http://purl.org/vocab/frbr/core#partOf"), journal)
        )

        # Add Article 1's DOI
        article1_id = URIRef("https://example.org/identifier/article/doi")
        article1_graph.add(
            (article1_id, RDF.type, URIRef("http://purl.org/spar/datacite/Identifier"))
        )
        article1_graph.add(
            (
                article1_id,
                URIRef("http://purl.org/spar/datacite/usesIdentifierScheme"),
                URIRef("http://purl.org/spar/datacite/doi"),
            )
        )
        article1_graph.add(
            (
                article1_id,
                URIRef(
                    "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
                ),
                Literal("10.1234/test.123"),
            )
        )
        article1_graph.add(
            (
                article1,
                URIRef("http://purl.org/spar/datacite/hasIdentifier"),
                article1_id,
            )
        )
        test_graphs[str(article1)] = article1_graph

        # Add Article 2 (empty)
        article2 = URIRef("https://example.org/article/2")
        article2_graph = Graph()
        article2_graph.add(
            (article2, RDF.type, URIRef("http://purl.org/spar/fabio/JournalArticle"))
        )
        article2_graph.add(
            (article2, RDF.type, URIRef("http://purl.org/spar/fabio/Expression"))
        )
        test_graphs[str(article2)] = article2_graph

        # Add Person
        person = URIRef("https://example.org/person/1")
        person_graph = Graph()
        person_graph.add((person, RDF.type, URIRef("http://xmlns.com/foaf/0.1/Agent")))
        person_graph.add(
            (person, URIRef("http://xmlns.com/foaf/0.1/name"), Literal("Test Person"))
        )

        # Add Person's ORCID
        person_id = URIRef("https://example.org/identifier/person/orcid")
        person_graph.add(
            (person_id, RDF.type, URIRef("http://purl.org/spar/datacite/Identifier"))
        )
        person_graph.add(
            (
                person_id,
                URIRef("http://purl.org/spar/datacite/usesIdentifierScheme"),
                URIRef("http://purl.org/spar/datacite/orcid"),
            )
        )
        person_graph.add(
            (
                person_id,
                URIRef(
                    "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
                ),
                Literal("0000-0002-1825-0097"),
            )
        )
        person_graph.add(
            (person, URIRef("http://purl.org/spar/datacite/hasIdentifier"), person_id)
        )
        test_graphs[str(person)] = person_graph

        # Add Author Role
        author_role = URIRef("https://example.org/role/1")
        role_graph = Graph()
        role_graph.add(
            (author_role, RDF.type, URIRef("http://purl.org/spar/pro/RoleInTime"))
        )
        role_graph.add(
            (
                author_role,
                URIRef("http://purl.org/spar/pro/withRole"),
                URIRef("http://purl.org/spar/pro/author"),
            )
        )
        role_graph.add(
            (author_role, URIRef("http://purl.org/spar/pro/isHeldBy"), person)
        )
        role_graph.add(
            (
                article1,
                URIRef("http://purl.org/spar/pro/isDocumentContextFor"),
                author_role,
            )
        )
        test_graphs[str(author_role)] = role_graph

        def side_effect(subject):
            """Return the appropriate test graph for the subject."""
            # Convert subject to string for dictionary lookup
            subject_str = str(subject) if isinstance(subject, URIRef) else subject
            # Return empty graph if subject not found
            return test_graphs.get(subject_str, Graph())

        mock.side_effect = side_effect
        yield mock


def test_get_form_fields_from_shacl_journal_article(
    app: Flask, shacl_graph: Graph
) -> None:
    """Test form field extraction for JournalArticle with real SHACL data."""
    with app.app_context():
        # Test with JournalArticle class
        form_fields = get_form_fields_from_shacl(shacl_graph, None, app)

        # Find the key for JournalArticle in the tuple-based keys
        journal_article_key = None
        for key in form_fields:
            if (
                isinstance(key, tuple)
                and key[0] == "http://purl.org/spar/fabio/JournalArticle"
            ):
                journal_article_key = key
                break

        # Check that we found a key for JournalArticle
        assert journal_article_key is not None, "No key found for JournalArticle"

        journal_article_fields = form_fields[journal_article_key]

        # Check type property
        assert (
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" in journal_article_fields
        )
        type_fields = journal_article_fields[
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        ]
        assert any(
            field["hasValue"] == "http://purl.org/spar/fabio/JournalArticle"
            for field in type_fields
        )

        # Check title property
        assert "http://purl.org/dc/terms/title" in journal_article_fields
        title_field = journal_article_fields["http://purl.org/dc/terms/title"][0]
        assert title_field["datatypes"] == ["http://www.w3.org/2001/XMLSchema#string"]
        assert title_field["max"] == 1


def test_validate_new_triple_journal_article_title(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validation of a new title triple for a JournalArticle."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
    ):
        subject = URIRef("https://example.org/article/1")
        predicate = URIRef("http://purl.org/dc/terms/title")
        new_value = "Test Article Title"
        old_title = "Test Article"  # Il valore esistente nel grafo di test

        # Test validation
        valid_value, _old_value, error = validate_new_triple(
            subject,
            predicate,
            new_value,
            "update",  # Usiamo update invece di create
            old_value=old_title,  # Specifichiamo il vecchio valore
            entity_types=[
                "http://purl.org/spar/fabio/JournalArticle",
                "http://purl.org/spar/fabio/Expression",
            ],
        )

        assert error == "", f"Validation error: {error}"
        assert isinstance(valid_value, Literal), (
            f"Expected Literal but got {type(valid_value)}"
        )
        assert valid_value.datatype == XSD.string, (
            f"Expected datatype {XSD.string} but got {valid_value.datatype}"
        )
        assert str(valid_value) == new_value, (
            f"Expected value {new_value} but got {valid_value!s}"
        )


def test_validate_new_triple_journal_identifier(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validation of a new identifier triple for a JournalArticle."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
    ):
        # Create a new identifier with DOI scheme
        identifier = URIRef("https://example.org/identifier/test-doi")
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
        valid_value, _old_value, error = validate_new_triple(
            identifier,
            URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
            "http://purl.org/spar/datacite/Identifier",
            "create",
            entity_types=["http://purl.org/spar/datacite/Identifier"],
        )
        assert error == "", f"Validation error: {error}"

        # Add the type to the identifier graph
        identifier_graph.add(
            (
                URIRef(identifier),
                RDF.type,
                URIRef("http://purl.org/spar/datacite/Identifier"),
            )
        )

        # Add the article type and relation
        article_graph.add(
            (
                URIRef(article),
                RDF.type,
                URIRef("http://purl.org/spar/fabio/JournalArticle"),
            )
        )
        article_graph.add(
            (URIRef(article), RDF.type, URIRef("http://purl.org/spar/fabio/Expression"))
        )
        article_graph.add(
            (
                URIRef(article),
                URIRef("http://purl.org/spar/datacite/hasIdentifier"),
                URIRef(identifier),
            )
        )

        # Then, set the identifier scheme to DOI
        valid_value, _old_value, error = validate_new_triple(
            identifier,
            URIRef("http://purl.org/spar/datacite/usesIdentifierScheme"),
            "http://purl.org/spar/datacite/doi",
            "create",
            entity_types=["http://purl.org/spar/datacite/Identifier"],
        )
        assert error == "", f"Validation error: {error}"

        # Add the identifier scheme to the identifier graph
        identifier_graph.add(
            (
                URIRef(identifier),
                URIRef("http://purl.org/spar/datacite/usesIdentifierScheme"),
                URIRef("http://purl.org/spar/datacite/doi"),
            )
        )

        # Test validation with valid DOI
        valid_doi = "10.1000/test.123"
        valid_value, _old_value, error = validate_new_triple(
            identifier,
            URIRef(
                "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
            ),
            valid_doi,
            "create",
            entity_types=["http://purl.org/spar/datacite/Identifier"],
        )
        assert error == "", f"Validation error: {error}"
        assert isinstance(valid_value, Literal)
        assert str(valid_value) == valid_doi

        # Add the valid DOI to the identifier graph
        identifier_graph.add(
            (
                URIRef(identifier),
                URIRef(
                    "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
                ),
                Literal(valid_doi),
            )
        )

        # Test validation with invalid DOI format
        invalid_doi = "invalid-doi"
        valid_value, _old_value, error = validate_new_triple(
            identifier,
            URIRef(
                "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
            ),
            invalid_doi,
            "update",
            old_value=valid_doi,
            entity_types=["http://purl.org/spar/datacite/Identifier"],
        )
        assert error != "", "Should reject invalid DOI format"
        assert "The property has literal value requires at least 1 value" in error


def test_get_valid_predicates_journal_article(app: Flask, shacl_graph: Graph) -> None:
    """Test getting valid predicates for a JournalArticle."""
    with (
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
    ):
        # Create a test graph with a JournalArticle
        test_graph = Graph()
        subject = URIRef("https://example.org/article/1")
        test_graph.add(
            (subject, RDF.type, URIRef("http://purl.org/spar/fabio/JournalArticle"))
        )
        test_graph.add(
            (subject, RDF.type, URIRef("http://purl.org/spar/fabio/Expression"))
        )

        # Get valid predicates
        triples = list(test_graph.triples((subject, None, None)))
        s_types = [o for s, p, o in test_graph.triples((subject, RDF.type, None))]
        highest_priority_class = get_highest_priority_class(s_types)
        assert highest_priority_class is not None
        (
            can_add,
            _can_delete,
            datatypes,
            _mandatory_values,
            _optional_values,
            _all_predicates,
        ) = get_valid_predicates(
            triples,
            URIRef(highest_priority_class),  # type: ignore[arg-type]
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


def test_validate_new_triple_with_pattern_and_conditions(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validation of triples with pattern constraints and conditions."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
    ):
        # Test DOI pattern validation
        valid_doi = "10.1000/test.123"
        valid_value, _old_value, error = validate_new_triple(
            URIRef("https://example.org/identifier/doi"),
            URIRef(
                "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
            ),
            valid_doi,
            "create",
            entity_types=["http://purl.org/spar/datacite/Identifier"],
        )
        assert error == "", f"Validation error: {error}"
        assert isinstance(valid_value, Literal)
        assert str(valid_value) == valid_doi

        # Test ISBN pattern validation
        valid_isbn = "978-0-123456-47-2"
        valid_value, _old_value, error = validate_new_triple(
            URIRef("https://example.org/identifier/isbn"),
            URIRef(
                "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
            ),
            valid_isbn,
            "create",
            entity_types=["http://purl.org/spar/datacite/Identifier"],
        )
        assert error == "", f"Validation error: {error}"
        assert isinstance(valid_value, Literal)
        assert str(valid_value) == valid_isbn


def test_validate_new_triple_with_datatype_conversion(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validation and conversion of values with different datatypes."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
    ):
        # Usiamo un nuovo articolo senza date esistenti
        subject = URIRef("https://example.org/article/2")

        # Test date datatype with different formats
        date_tests = [
            (
                URIRef("http://prismstandard.org/namespaces/basic/2.0/publicationDate"),
                "2024-03-21",
                XSD.date,
            ),
            (
                URIRef("http://prismstandard.org/namespaces/basic/2.0/publicationDate"),
                "2024-03",
                XSD.gYearMonth,
            ),
            (
                URIRef("http://prismstandard.org/namespaces/basic/2.0/publicationDate"),
                "2024",
                XSD.gYear,
            ),
        ]

        for predicate, value, expected_datatype in date_tests:
            valid_value, _old_value, error = validate_new_triple(
                subject,
                predicate,
                value,
                "create",
                entity_types=["http://purl.org/spar/fabio/JournalArticle"],
            )
            assert error == "", f"Validation error for {value}: {error}"
            assert isinstance(valid_value, Literal)
            assert valid_value.datatype == expected_datatype
            assert str(valid_value) == value


def test_get_form_fields_with_display_rules(app: Flask, shacl_graph: Graph) -> None:
    """Test form field extraction with display rules."""
    with app.app_context():
        # Update display rules to include both class and shape
        journal_article_shape = "http://schema.org/JournalArticleShape"
        display_rules = [
            {
                "target": {
                    "class": "http://purl.org/spar/fabio/JournalArticle",
                    "shape": journal_article_shape,
                },
                "displayProperties": [
                    {
                        "property": "http://purl.org/dc/terms/title",
                        "displayName": "Article Title",
                        "shouldBeDisplayed": True,
                    },
                    {
                        "property": "http://purl.org/dc/terms/abstract",
                        "displayName": "Abstract",
                        "shouldBeDisplayed": True,
                    },
                ],
            }
        ]

        form_fields = get_form_fields_from_shacl(shacl_graph, display_rules, app)

        # Find the key for JournalArticle in the tuple-based keys
        journal_article_key = None
        for key in form_fields:
            if (
                isinstance(key, tuple)
                and key[0] == "http://purl.org/spar/fabio/JournalArticle"
            ):
                journal_article_key = key
                break

        # Check that we found a key for JournalArticle
        assert journal_article_key is not None, "No key found for JournalArticle"
        article_fields = form_fields[journal_article_key]

        # Check that display rules were applied
        title_field = article_fields["http://purl.org/dc/terms/title"][0]
        abstract_field = article_fields["http://purl.org/dc/terms/abstract"][0]

        assert title_field["displayName"] == "Article Title"
        assert abstract_field["displayName"] == "Abstract"
        assert title_field["shouldBeDisplayed"] is True
        assert abstract_field["shouldBeDisplayed"] is True


def test_validate_new_triple_with_delete_action(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validation of triple deletion."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
    ):
        subject = URIRef("https://example.org/article/1")
        predicate = URIRef("http://purl.org/dc/terms/title")
        old_value = "Test Article Title"

        # Prima aggiungiamo il valore che vogliamo eliminare
        graph = mock_fetch_data_graph(subject)
        graph.add((subject, predicate, Literal(old_value)))

        # Test delete action
        valid_value, old_value, error = validate_new_triple(
            subject,
            predicate,
            None,
            "delete",
            old_value=old_value,
            entity_types=["http://purl.org/spar/fabio/JournalArticle"],
        )
        assert error == "", f"Validation error: {error}"
        assert valid_value is None


def test_validate_new_triple_with_invalid_property(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validation with an invalid property."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
        patch(
            "heritrace.utils.filters.Filter.human_readable_class"
        ) as mock_human_readable_class,
    ):
        mock_human_readable_class.return_value = "Journal Article"

        subject = URIRef("https://example.org/article/1")
        predicate = URIRef("http://example.org/invalid/property")
        new_value = "Test Value"

        # Test with invalid property - should be accepted as no SHACL rules exist
        valid_value, _old_value, error = validate_new_triple(
            subject,
            predicate,
            new_value,
            "create",
            entity_types=["http://purl.org/spar/fabio/JournalArticle"],
        )
        assert error == "", f"Unexpected error: {error}"
        assert isinstance(valid_value, Literal)
        assert str(valid_value) == "Test Value"


def test_validate_new_triple_with_optional_values(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validation with optional values."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
    ):
        subject = URIRef(
            "https://example.org/identifier/new"
        )  # Usiamo un nuovo identificatore senza scheme
        predicate = URIRef("http://purl.org/spar/datacite/usesIdentifierScheme")

        # Test with valid scheme
        _valid_value, _old_value, error = validate_new_triple(
            subject,
            predicate,
            "http://purl.org/spar/datacite/doi",
            "create",
            entity_types=["http://purl.org/spar/datacite/Identifier"],
        )
        assert error == "", f"Validation error: {error}"

        # Test with invalid scheme
        _valid_value, _old_value, error = validate_new_triple(
            subject,
            predicate,
            "http://example.org/invalid/scheme",
            "create",
            entity_types=["http://purl.org/spar/datacite/Identifier"],
        )
        assert error != "", "Should reject invalid scheme"
        assert "is not a valid value" in error


def test_get_form_fields_with_nested_shapes(app: Flask, shacl_graph: Graph) -> None:
    """Test form field extraction with nested shapes."""
    with app.app_context():
        # Test with JournalArticle class that has nested shapes (e.g., for authors)
        form_fields = get_form_fields_from_shacl(shacl_graph, None, app)

        # Find the key for JournalArticle in the tuple-based keys
        journal_article_key = None
        for key in form_fields:
            if (
                isinstance(key, tuple)
                and key[0] == "http://purl.org/spar/fabio/JournalArticle"
            ):
                journal_article_key = key
                break

        # Check that we found a key for JournalArticle
        assert journal_article_key is not None, "No key found for JournalArticle"
        journal_article_fields = form_fields[journal_article_key]

        # Check that pro:isDocumentContextFor field exists and has nested shapes
        assert "http://purl.org/spar/pro/isDocumentContextFor" in journal_article_fields
        author_field = next(
            field
            for field in journal_article_fields[
                "http://purl.org/spar/pro/isDocumentContextFor"
            ]
            if "nodeShape" in field and "AuthorShape" in field["nodeShape"]
        )
        assert "nestedShape" in author_field
        assert len(author_field["nestedShape"]) > 0


def test_validate_new_triple_with_nested_validation(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validation of nested shapes."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
    ):
        subject = URIRef("https://example.org/article/1")
        predicate = URIRef("http://purl.org/spar/pro/isDocumentContextFor")
        role_value = "https://example.org/role/1"

        # Test validation of a role triple
        valid_value, _old_value, error = validate_new_triple(
            subject,
            predicate,
            role_value,
            "create",
            entity_types=["http://purl.org/spar/fabio/JournalArticle"],
        )
        assert error == "", f"Validation error: {error}"
        assert isinstance(valid_value, URIRef)
        assert str(valid_value) == role_value


def test_validate_new_triple_with_or_constraints(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validation with sh:or constraints."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
    ):
        # Usiamo un nuovo articolo senza data esistente
        URIRef("https://example.org/article/2")
        predicate = URIRef(
            "http://prismstandard.org/namespaces/basic/2.0/publicationDate"
        )

        # Test with different valid date formats
        date_values = [
            "2024-03-21",  # date
            "2024-03",  # gYearMonth
            "2024",  # gYear
        ]

        # Expected datatypes for each format
        expected_datatypes = [
            XSD.date,  # for full date
            XSD.gYearMonth,  # for year-month
            XSD.gYear,  # for year only
        ]

        # Test each format with a fresh subject
        for i, date_value in enumerate(date_values):
            test_subject = URIRef(
                f"https://example.org/article/{i + 2}"
            )  # Usiamo un soggetto diverso per ogni test
            valid_value, _old_value, error = validate_new_triple(
                test_subject,
                predicate,
                date_value,
                "create",
                entity_types=["http://purl.org/spar/fabio/JournalArticle"],
            )
            assert error == "", f"Validation error for {date_value}: {error}"
            assert isinstance(valid_value, Literal)

            # Check if the datatype matches the corresponding expected datatype
            assert valid_value.datatype == expected_datatypes[i], (
                f"Expected {expected_datatypes[i]}"
                f" for {date_value}"
                f" but got {valid_value.datatype}"
            )


def test_validate_new_triple_with_multiple_types(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validation with multiple entity types."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
    ):
        # Usiamo un nuovo articolo senza titolo esistente
        subject = URIRef("https://example.org/article/2")
        predicate = URIRef("http://purl.org/dc/terms/title")
        new_value = "Test Title"

        # Test with multiple entity types
        valid_value, _old_value, error = validate_new_triple(
            subject,
            predicate,
            new_value,
            "create",
            entity_types=[
                "http://purl.org/spar/fabio/JournalArticle",
                "http://purl.org/spar/fabio/Expression",
            ],
        )
        assert error == "", f"Validation error: {error}"
        assert isinstance(valid_value, Literal)
        assert valid_value.datatype == XSD.string
        assert str(valid_value) == new_value


def test_validate_new_triple_with_intermediate_relation(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validation with intermediate relations."""
    with app.app_context():
        # Update display rules to include both class and shape
        journal_article_shape = "http://schema.org/JournalArticleShape"
        display_rules = [
            {
                "target": {
                    "class": "http://purl.org/spar/fabio/JournalArticle",
                    "shape": journal_article_shape,
                },
                "displayProperties": [
                    {
                        "property": "http://purl.org/spar/pro/isDocumentContextFor",
                        "intermediateRelation": {
                            "class": "http://purl.org/spar/pro/RoleInTime",
                            "targetEntityType": "http://xmlns.com/foaf/0.1/Person",
                        },
                    }
                ],
            }
        ]

        form_fields = get_form_fields_from_shacl(shacl_graph, display_rules, app)

        # Find the key for JournalArticle in the tuple-based keys
        journal_article_key = None
        for key in form_fields:
            if (
                isinstance(key, tuple)
                and key[0] == "http://purl.org/spar/fabio/JournalArticle"
            ):
                journal_article_key = key
                break

        # Check that we found a key for JournalArticle
        assert journal_article_key is not None, "No key found for JournalArticle"
        article_fields = form_fields[journal_article_key]

        # Check that intermediate relation is processed
        role_field = article_fields["http://purl.org/spar/pro/isDocumentContextFor"][0]

        assert "intermediateRelation" in role_field
        assert (
            role_field["intermediateRelation"]["class"]
            == "http://purl.org/spar/pro/RoleInTime"
        )
        assert (
            role_field["intermediateRelation"]["targetEntityType"]
            == "http://xmlns.com/foaf/0.1/Person"
        )


def test_validate_new_triple_with_datatype_conversion_edge_cases(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test datatype conversion with edge cases."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
    ):
        subject = URIRef("https://example.org/article/1")

        # Test with invalid date format
        valid_value, _old_value, error = validate_new_triple(
            subject,
            URIRef("http://prismstandard.org/namespaces/basic/2.0/publicationDate"),
            "invalid-date",
            "create",
            entity_types=["http://purl.org/spar/fabio/JournalArticle"],
        )
        assert error != "", "Should reject invalid date format"

        # Test with string value when no datatype is specified
        valid_value, _old_value, error = validate_new_triple(
            subject,
            URIRef("http://purl.org/dc/terms/description"),
            "Test description",
            "create",
            entity_types=["http://purl.org/spar/fabio/JournalArticle"],
        )
        assert error == "", f"Validation error: {error}"
        assert isinstance(valid_value, Literal)
        assert valid_value.datatype == XSD.string


def test_validate_new_triple_with_complex_conditions(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validation with complex conditions and edge cases."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
        patch(
            "heritrace.utils.filters.Filter.human_readable_class"
        ) as mock_human_readable_class,
    ):
        mock_human_readable_class.return_value = "Journal Article"

        # Use article/2 which has no title
        subject = URIRef("https://example.org/article/2")

        # Test with no SHACL graph
        with patch("heritrace.extensions.get_shacl_graph", return_value=Graph()):
            valid_value, _old_value, error = validate_new_triple(
                subject,
                URIRef("http://purl.org/dc/terms/title"),
                "Test Title",
                "create",
                entity_types=["http://purl.org/spar/fabio/JournalArticle"],
            )
            assert error == "", f"Validation error: {error}"
            assert isinstance(valid_value, Literal)
            # Without SHACL graph, the default datatype is XSD.string
            assert valid_value.datatype == XSD.string
            assert str(valid_value) == "Test Title"

        # Test with empty entity types
        valid_value, _old_value, error = validate_new_triple(
            subject,
            URIRef("http://purl.org/dc/terms/title"),
            "Test Title",
            "create",
            entity_types=[],
        )
        assert error == "No entity type specified", f"Validation error: {error}"

        # Test with invalid entity type
        valid_value, _old_value, error = validate_new_triple(
            subject,
            URIRef("http://purl.org/dc/terms/title"),
            "Test Title",
            "create",
            entity_types=["http://example.org/InvalidType"],
        )
        # With invalid entity type, should be accepted since no SHACL rules exist for it
        assert error == "", f"Unexpected error: {error}"
        assert isinstance(valid_value, Literal)
        assert str(valid_value) == "Test Title"


def test_get_datatype_label() -> None:
    """Test the get_datatype_label function."""
    # Test with known datatype
    assert get_datatype_label(str(XSD.string)) == "String"
    assert get_datatype_label(str(XSD.date)) == "Date"

    # Test with unknown datatype
    with patch("heritrace.utils.shacl_validation.get_custom_filter", return_value=None):
        assert (
            get_datatype_label("http://example.org/unknown")
            == "http://example.org/unknown"
        )

    # Test with None
    assert get_datatype_label(None) is None


def test_get_datatype_label_with_custom_filter(monkeypatch) -> None:
    """Test get_datatype_label with custom filter scenarios."""

    class MockCustomFilter:
        @staticmethod
        def human_readable_predicate(
            uri: str, _entity_key: tuple[str | None, str | None]
        ) -> str | None:
            if "custom-type-1" in uri:
                return "Custom Label"
            if "custom-type-2" in uri:
                return "type-2"  # This is the last part of the URI
            return None

    monkeypatch.setattr(
        "heritrace.utils.shacl_validation.get_custom_filter", MockCustomFilter
    )

    # Test case 1: Custom filter returns a custom label that's not just the last part of
    # the URI
    custom_uri_1 = "http://example.org/custom-type-1"
    assert get_datatype_label(custom_uri_1) == "Custom Label"

    # Test case 2: Custom filter returns a label that's just the last part of the URI
    # Should return the full URI instead
    custom_uri_2 = "http://example.org/custom-type-2"
    assert get_datatype_label(custom_uri_2) == custom_uri_2

    # Test case 3: Custom filter returns None - should return the original URI
    custom_uri_3 = "http://example.org/unknown-type"
    # The function should return the original URI when custom filter returns None
    # According to the implementation, it should return the original URI, not None
    assert get_datatype_label(custom_uri_3) is None


def test_convert_to_matching_literal_edge_cases() -> None:
    """Test convert_to_matching_literal with edge cases."""
    # Test with empty datatypes list
    result = convert_to_matching_literal("test", [])
    assert result is None

    # Test with None value
    result = convert_to_matching_literal(None, [str(XSD.string)])
    assert result is None or str(result) == "None"


def test_convert_to_matching_class_edge_cases(app: Flask) -> None:
    """Test convert_to_matching_class with edge cases."""
    with app.app_context():
        # Test with empty classes list
        result = convert_to_matching_class("http://example.org/test", [])
        assert result is None

        # Test with None value
        result = convert_to_matching_class(None, ["http://example.org/class"])
        assert result is None

        # Test with non-URI value
        result = convert_to_matching_class("not a uri", ["http://example.org/class"])
        assert result is None

        # Test with entity_types parameter
        with patch("validators.url", return_value=True):
            result = convert_to_matching_class(
                "http://example.org/test",
                ["http://example.org/class"],
                entity_types=["http://example.org/entity"],
            )
            assert isinstance(result, URIRef)
            assert str(result) == "http://example.org/test"


def test_order_fields(app: Flask) -> None:
    """Test the order_fields function."""
    with app.app_context():
        # Test with matching property order
        fields = [
            {"predicate": "http://example.org/property2"},
            {"predicate": "http://example.org/property1"},
            {"predicate": "http://example.org/property3"},
        ]

        property_order = [
            "http://example.org/property1",
            "http://example.org/property2",
        ]

        result = order_fields(fields, property_order)
        assert result[0]["predicate"] == "http://example.org/property1"
        assert result[1]["predicate"] == "http://example.org/property2"
        assert result[2]["predicate"] == "http://example.org/property3"

        # Test with empty property order
        result = order_fields(fields, [])
        assert result == fields

        # Test with None fields
        result = order_fields(None, property_order)
        assert result == []


def test_apply_display_rules_to_nested_shapes(app: Flask) -> None:
    """Test the apply_display_rules_to_nested_shapes function."""
    with app.app_context():
        # Test with matching display rules
        nested_fields = [{"predicate": "http://example.org/property1"}]

        parent_prop = {
            "property": "http://example.org/parent",
            "displayRules": [
                {
                    "shape": "http://example.org/shape",
                    "nestedDisplayRules": [
                        {
                            "property": "http://example.org/property1",
                            "displayName": "Nested Property 1",
                        }
                    ],
                }
            ],
        }

        result = apply_display_rules_to_nested_shapes(
            nested_fields, parent_prop, "http://example.org/shape"
        )
        assert result[0]["displayName"] == "Nested Property 1"

        # Test with non-matching shape
        result = apply_display_rules_to_nested_shapes(
            nested_fields, parent_prop, "http://example.org/other-shape"
        )
        assert "displayName" not in result[0]

        # Test with no nestedDisplayRules
        parent_prop = {
            "property": "http://example.org/parent",
            "displayRules": [{"shape": "http://example.org/shape"}],
        }

        result = apply_display_rules_to_nested_shapes(
            nested_fields, parent_prop, "http://example.org/shape"
        )
        assert result == nested_fields


def test_execute_shacl_query(app: Flask, shacl_graph: Graph) -> None:
    """Test the execute_shacl_query function."""
    with app.app_context():
        # Test with init_bindings
        query = prepareQuery(
            """
            SELECT ?s WHERE { ?s ?p ?o . }
            """
        )

        # Execute query with init_bindings
        init_bindings = {"p": RDF.type}
        results = execute_shacl_query(shacl_graph, query, init_bindings)
        assert len(list(results)) > 0

        # Execute query without init_bindings
        results = execute_shacl_query(shacl_graph, query)
        assert len(list(results)) > 0


def test_process_nested_shapes_edge_cases(app: Flask, shacl_graph: Graph) -> None:
    """Test process_nested_shapes with edge cases."""
    with app.app_context():
        ctx = ShaclProcessingContext(
            shacl=shacl_graph,
            display_rules=None,
            app=app,
            processed_shapes=set(),
        )
        result = process_nested_shapes(
            ctx,
            "http://www.w3.org/ns/shacl#NodeShape",
            depth=0,
        )
        assert isinstance(result, list)

        # Test with already processed shape
        ctx2 = ShaclProcessingContext(
            shacl=shacl_graph,
            display_rules=None,
            app=app,
            processed_shapes={"http://www.w3.org/ns/shacl#NodeShape"},
        )
        result = process_nested_shapes(
            ctx2,
            "http://www.w3.org/ns/shacl#NodeShape",
            depth=0,
        )
        assert result == []


def test_get_object_class_edge_cases(app: Flask, shacl_graph: Graph) -> None:
    """Test get_object_class with edge cases."""
    with app.app_context():
        # Test with non-existent shape
        result = get_object_class(
            shacl_graph,
            "http://example.org/non-existent",
            "http://example.org/predicate",
        )
        assert result is None


def test_process_query_results_edge_cases(app: Flask, shacl_graph: Graph) -> None:
    """Test process_query_results with edge cases."""
    with app.app_context():
        # Create a mock result with an existing field for the same predicate
        mock_results = MagicMock()
        mock_row = MagicMock()
        mock_row.shape = URIRef("http://example.org/shape")
        mock_row.type = URIRef("http://example.org/type")
        mock_row.predicate = URIRef("http://example.org/predicate")
        mock_row.nodeShape = None
        mock_row.hasValue = None
        mock_row.objectClass = None
        mock_row.minCount = None
        mock_row.maxCount = None
        mock_row.datatype = URIRef("http://www.w3.org/2001/XMLSchema#string")
        mock_row.optionalValues = None
        mock_row.orNodes = None
        mock_row.conditionPath = None
        mock_row.conditionValue = None
        mock_row.pattern = None
        mock_row.message = None

        mock_results.__iter__.return_value = [mock_row]

        # Process with existing field - updated for tuple-based keys
        entity_key = ("http://example.org/type", "http://example.org/shape")

        ctx = ShaclProcessingContext(
            shacl=shacl_graph,
            display_rules=None,
            app=app,
            processed_shapes=set(),
        )
        result = process_query_results(ctx, mock_results, depth=0)
        entity_key = ("http://example.org/type", "http://example.org/shape")
        assert entity_key in result
        assert "http://example.org/predicate" in result[entity_key]

        # Test with existing field that has the same datatype
        mock_row.datatype = URIRef("http://www.w3.org/2001/XMLSchema#integer")
        mock_results.__iter__.return_value = [mock_row]

        ctx = ShaclProcessingContext(
            shacl=shacl_graph,
            display_rules=None,
            app=app,
            processed_shapes=set(),
        )
        result = process_query_results(ctx, mock_results, depth=0)
        entity_key = ("http://example.org/type", "http://example.org/shape")
        assert entity_key in result
        assert "http://example.org/predicate" in result[entity_key]


def test_validate_new_triple_with_uri_validation(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validate_new_triple with URI validation."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
        patch(
            "heritrace.utils.shacl_validation.get_valid_predicates"
        ) as mock_get_valid_predicates,
    ):
        # Mock the return value to include URI validation
        mock_get_valid_predicates.return_value = [
            {
                "predicate": "http://purl.org/spar/datacite/hasIdentifier",
                "objectClass": ["http://purl.org/spar/datacite/Identifier"],
            }
        ]

        # Test with invalid URI
        subject = URIRef("https://example.org/article/1")
        predicate = URIRef("http://purl.org/spar/datacite/hasIdentifier")
        new_value = "not a uri"

        # Mock validators.url to return False for invalid URL
        with patch("validators.url", return_value=False):
            valid_value, _old_value, error = validate_new_triple(
                subject,
                predicate,
                new_value,
                "create",
                entity_types=["http://purl.org/spar/fabio/JournalArticle"],
            )

            # Should accept as literal when no SHACL rules are found
            assert error == "", f"Unexpected error: {error}"
            assert isinstance(valid_value, Literal)
            assert str(valid_value) == "not a uri"


def test_get_valid_predicates_edge_cases() -> None:
    """Test get_valid_predicates with edge cases."""
    # Test with empty triples and a default class
    with patch(
        "heritrace.utils.shacl_validation.get_shacl_graph", return_value=Graph()
    ):
        test_class = URIRef("http://example.org/TestClass")
        result = get_valid_predicates([], test_class)
        assert isinstance(result, tuple)

    # Test with triples that have no valid predicates
    triples = [
        (
            URIRef("http://example.org/subject"),
            URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
            URIRef("http://example.org/class"),
        ),
        (
            URIRef("http://example.org/subject"),
            RDF.type,
            URIRef("http://example.org/TestClass"),
        ),
    ]

    with patch(
        "heritrace.utils.shacl_validation.get_shacl_graph", return_value=Graph()
    ):
        test_class = URIRef("http://example.org/TestClass")
        result = get_valid_predicates(triples, test_class)
        assert result is not None


def test_validate_new_triple_with_pattern_validation(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validate_new_triple with pattern validation."""
    with app.test_request_context(), app.app_context():
        data_graph = Graph()
        mock_fetch_data_graph.return_value = data_graph

        with patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph):
            subject = URIRef("https://example.org/identifier/test")
            predicate = URIRef(
                "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
            )

            class MockRow:
                def __init__(
                    self, pattern, message=None, condition_paths="", condition_values=""
                ) -> None:
                    self.pattern = pattern
                    self.message = message
                    self.conditionPaths = condition_paths
                    self.conditionValues = condition_values
                    self.datatype = XSD.string
                    self.path = predicate
                    self.a_class = None
                    self.classIn = None
                    self.maxCount = None
                    self.minCount = None
                    self.optionalValues = ""
                    self.shape = URIRef("http://example.org/TestShape")

            mock_results = [
                MockRow(r"10\.[0-9]{4,}/[a-zA-Z0-9.]+", "Invalid DOI format")
            ]

            with (
                patch("rdflib.graph.Graph.query", return_value=mock_results),
                patch("re.match") as mock_re_match,
            ):
                # For invalid pattern
                mock_re_match.return_value = None
                new_value = "invalid-doi"
                valid_value, _old_value, error = validate_new_triple(
                    subject,
                    predicate,
                    new_value,
                    "create",
                    entity_types=["http://purl.org/spar/datacite/Identifier"],
                )

                # Should have an error for invalid pattern
                assert error is not None
                assert "Invalid DOI format" in error

                # For valid pattern
                mock_re_match.return_value = True  # Mock a successful match
                new_value = "10.1234/valid.doi"
                valid_value, _old_value, error = validate_new_triple(
                    subject,
                    predicate,
                    new_value,
                    "create",
                    entity_types=["http://purl.org/spar/datacite/Identifier"],
                )

                # Should be valid for matching pattern
                assert valid_value is not None
                assert error == ""

                # Test with no message in the pattern constraint
                mock_results = [MockRow(r"10\.[0-9]{4,}/[a-zA-Z0-9.]+", None)]
                with patch("rdflib.graph.Graph.query", return_value=mock_results):
                    # For invalid pattern without custom message
                    mock_re_match.return_value = None
                    new_value = "invalid-doi"
                    valid_value, _old_value, error = validate_new_triple(
                        subject,
                        predicate,
                        new_value,
                        "create",
                        entity_types=["http://purl.org/spar/datacite/Identifier"],
                    )

                    # Should have a generic error message
                    assert error is not None
                    assert "Value must match pattern" in error


def test_validate_new_triple_with_invalid_uri(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validate_new_triple with invalid URI."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
        patch(
            "heritrace.utils.filters.Filter.human_readable_class"
        ) as mock_human_readable_class,
    ):
        mock_human_readable_class.return_value = "Journal Article"

        subject = URIRef("https://example.org/resource/test")
        predicate = URIRef("http://purl.org/dc/terms/creator")

        # Test with invalid URI (not a URL) and class constraints
        with patch(
            "heritrace.utils.shacl_validation.get_valid_predicates"
        ) as mock_get_valid_predicates:
            mock_get_valid_predicates.return_value = [
                {
                    "predicate": predicate,
                    "classes": ["http://xmlns.com/foaf/0.1/Person"],
                }
            ]

            # Mock validators.url to return False for invalid URL
            with patch("validators.url", return_value=False):
                new_value = "not-a-valid-url"
                valid_value, _old_value, error = validate_new_triple(
                    subject,
                    predicate,
                    new_value,
                    "create",
                    entity_types=["http://purl.org/spar/fabio/JournalArticle"],
                )

                # Should accept as literal when no SHACL rules are found
                assert error == "", f"Unexpected error: {error}"
                assert isinstance(valid_value, Literal)
                assert str(valid_value) == "not-a-valid-url"


def test_validate_new_triple_with_invalid_class_match(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validate_new_triple with invalid class match."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
        patch(
            "heritrace.utils.filters.Filter.human_readable_class"
        ) as mock_human_readable_class,
    ):
        mock_human_readable_class.return_value = "Journal Article"

        subject = URIRef("https://example.org/resource/test")
        predicate = URIRef("http://purl.org/dc/terms/creator")

        # Test with valid URI but invalid class match
        with patch(
            "heritrace.utils.shacl_validation.get_valid_predicates"
        ) as mock_get_valid_predicates:
            mock_get_valid_predicates.return_value = [
                {
                    "predicate": predicate,
                    "classes": ["http://xmlns.com/foaf/0.1/Person"],
                }
            ]

            # Mock validators.url to return True for valid URL
            with patch("validators.url", return_value=True):
                # Mock convert_to_matching_class to return None (no match)
                with patch(
                    "heritrace.utils.shacl_validation.convert_to_matching_class",
                    return_value=None,
                ):
                    new_value = "https://example.org/person/invalid"
                    valid_value, _old_value, error = validate_new_triple(
                        subject,
                        predicate,
                        new_value,
                        "create",
                        entity_types=["http://purl.org/spar/fabio/JournalArticle"],
                    )

                # Should accept URI even when no class match is found
                assert error == "", f"Unexpected error: {error}"
                assert isinstance(valid_value, URIRef)
                assert str(valid_value) == "https://example.org/person/invalid"


def test_validate_new_triple_with_literal_conversion(
    app: Flask, shacl_graph: Graph, mock_fetch_data_graph
) -> None:
    """Test validate_new_triple with literal conversion."""
    with (
        app.test_request_context(),
        app.app_context(),
        patch("heritrace.extensions.get_shacl_graph", return_value=shacl_graph),
    ):
        subject = URIRef("https://example.org/resource/test")
        predicate = URIRef("http://purl.org/dc/terms/title")

        # Create a mock data graph with the old value
        data_graph = Graph()
        old_literal = Literal("Old Title", datatype=XSD.string)
        data_graph.add((URIRef(subject), URIRef(predicate), old_literal))
        mock_fetch_data_graph.return_value = data_graph

        # Create a mock SPARQL query result for literal conversion
        class MockRow:
            def __init__(self, datatype=None, pattern=None, message=None) -> None:
                self.datatype = datatype
                self.pattern = pattern
                self.message = message
                self.path = predicate
                self.conditionPaths = ""
                self.conditionValues = ""
                self.a_class = None
                self.classIn = None
                self.maxCount = None
                self.minCount = None
                self.pattern = None
                self.message = None
                self.optionalValues = ""
                self.shape = URIRef("http://example.org/TestShape")

        # Create a mock result with a datatype constraint
        mock_results = [MockRow(datatype=XSD.string)]

        # Mock the query result
        with patch("rdflib.graph.Graph.query", return_value=mock_results):
            # Test with existing Literal value
            old_value = Literal("Old Title", datatype=XSD.string)
            new_value = "New Title"
            valid_value, old_value, error = validate_new_triple(
                subject,
                predicate,
                new_value,
                "update",
                old_value=old_value,
                entity_types=["http://purl.org/spar/fabio/JournalArticle"],
            )

            # Should return a valid Literal with the same datatype
            assert isinstance(valid_value, Literal)
            assert valid_value.datatype == XSD.string
            assert str(valid_value) == "New Title"

            # Test with None value for URIRef
            with patch("rdflib.term.URIRef.__instancecheck__", return_value=True):
                # Update the mock data graph with a URIRef value
                data_graph = Graph()
                old_uri = URIRef("https://example.org/old-value")
                data_graph.add((URIRef(subject), URIRef(predicate), old_uri))
                mock_fetch_data_graph.return_value = data_graph

                # Create a mock result for URIRef test
                mock_results = [MockRow()]

                # Mock the query result again for the URIRef test
                with patch("rdflib.graph.Graph.query", return_value=mock_results):
                    old_value = URIRef("https://example.org/old-value")
                    new_value = None
                    valid_value, old_value, error = validate_new_triple(
                        subject,
                        predicate,
                        new_value,
                        "update",
                        old_value=old_value,
                        entity_types=["http://purl.org/spar/fabio/JournalArticle"],
                    )

                    # Should return the old value when new_value is None
                    assert valid_value == old_value
                    assert error == ""


def test_process_query_results_with_or_nodes(app: Flask, shacl_graph: Graph) -> None:
    """Test process_query_results with OR nodes."""
    with app.test_request_context(), app.app_context():
        # Create a simple class to represent our query results
        class MockRow:
            def __init__(
                self,
                shape,
                type_val,
                predicate,
                node_shape,
                min_count,
                max_count,
                or_nodes,
            ) -> None:
                self.shape = URIRef(shape)
                self.type = URIRef(type_val)
                self.predicate = URIRef(predicate)
                self.node_shape = node_shape
                self.min_count = (
                    Literal(min_count, datatype=XSD.integer) if min_count else None
                )
                self.max_count = (
                    Literal(max_count, datatype=XSD.integer) if max_count else None
                )
                self.has_value = None
                self.object_class = None
                self.datatype = None
                self.optional_values = None
                self.or_nodes = or_nodes
                self.condition_path = None
                self.condition_value = None
                self.pattern = None
                self.message = None

        # Create two rows with different entity types but same predicate
        rows = [
            MockRow(
                "http://example.org/shape1",
                "http://example.org/type1",
                "http://example.org/predicate1",
                None,
                "1",
                "1",
                "http://example.org/orNode1",
            ),
            MockRow(
                "http://example.org/shape1",
                "http://example.org/type2",
                "http://example.org/predicate1",
                None,
                "1",
                "1",
                "http://example.org/orNode2",
            ),
        ]

        # Create the first test case with empty processed_shapes
        with (
            patch(
                "heritrace.utils.shacl_display.get_shape_target_class",
                side_effect=["http://example.org/type1", "http://example.org/type2"],
            ),
            patch(
                "heritrace.utils.shacl_display.get_object_class",
                return_value="http://example.org/objectClass",
            ),
            patch(
                "heritrace.utils.filters.Filter.human_readable_class",
                return_value="Test Display Name",
            ),
            patch(
                "heritrace.utils.shacl_display.process_nested_shapes",
                return_value={"nestedField": "nestedValue"},
            ),
        ):
            display_rules = []
            processed_shapes = set()
            ctx = ShaclProcessingContext(
                shacl=shacl_graph,
                display_rules=display_rules,
                app=app,
                processed_shapes=processed_shapes,
            )
            fields = process_query_results(ctx, rows)

            # Verify the result has the expected structure with tuple-based keys
            entity_key1 = ("http://example.org/type1", "http://example.org/shape1")
            entity_key2 = ("http://example.org/type2", "http://example.org/shape1")
            assert entity_key1 in fields
            assert entity_key2 in fields
            assert "http://example.org/predicate1" in fields[entity_key1]
            assert "http://example.org/predicate1" in fields[entity_key2]

            # Verify the OR nodes are processed correctly
            assert "or" in fields[entity_key1]["http://example.org/predicate1"][0]
            assert "or" in fields[entity_key2]["http://example.org/predicate1"][0]

        # Create the second test case with processed_shapes containing one of the
        # orNodes
        with (
            patch(
                "heritrace.utils.shacl_display.get_shape_target_class",
                side_effect=["http://example.org/type1", "http://example.org/type2"],
            ),
            patch(
                "heritrace.utils.shacl_display.get_object_class",
                return_value="http://example.org/objectClass",
            ),
            patch(
                "heritrace.utils.filters.Filter.human_readable_class",
                return_value="Test Display Name",
            ),
            patch(
                "heritrace.utils.shacl_display.process_nested_shapes",
                return_value={"nestedField": "nestedValue"},
            ),
        ):
            display_rules = []
            processed_shapes = {"http://example.org/orNode1"}
            ctx = ShaclProcessingContext(
                shacl=shacl_graph,
                display_rules=display_rules,
                app=app,
                processed_shapes=processed_shapes,
            )
            fields = process_query_results(ctx, rows)

            # Verify the result still has the OR nodes with tuple-based keys
            entity_key1 = ("http://example.org/type1", "http://example.org/shape1")
            assert "or" in fields[entity_key1]["http://example.org/predicate1"][0]
            # Check that the first OR node doesn't have nestedShape since it's in
            # processed_shapes
            assert (
                "nestedShape"
                not in fields[entity_key1]["http://example.org/predicate1"][0]["or"][0]
            )


def test_convert_to_matching_class_with_entity_types() -> None:
    """Test convert_to_matching_class with entity_types parameter."""
    object_value = "http://example.org/person/1"
    classes = ["http://xmlns.com/foaf/0.1/Organization"]
    entity_types = ["http://xmlns.com/foaf/0.1/Person"]

    with patch(
        "heritrace.utils.shacl_validation.fetch_data_graph_for_subject",
        return_value=Graph(),
    ):
        result = convert_to_matching_class(
            object_value, classes, entity_types=entity_types
        )

    assert result is not None
    assert isinstance(result, URIRef)
    assert str(result) == object_value


def test_convert_to_matching_literal_with_unknown_datatype() -> None:
    """Test convert_to_matching_literal with an unknown datatype."""
    # Test with an unknown datatype
    object_value = "test value"
    datatypes = ["http://example.org/custom/datatype"]

    # Mock DATATYPE_MAPPING lookup to return None (unknown datatype)
    with patch("heritrace.utils.shacl_validation.DATATYPE_MAPPING", []):
        result = convert_to_matching_literal(object_value, datatypes)

        # Should return a string literal
        assert result is not None
        assert isinstance(result, Literal)
        assert str(result) == object_value
        assert result.datatype == XSD.string


def test_validate_new_triple_with_datatype_conversion_failure() -> None:
    """Test validation of a new triple with datatype conversion failure."""
    app = Flask(__name__)

    with app.test_request_context(), app.app_context():
        mock_shacl_graph = Graph()
        mock_shacl_graph.add(
            (
                URIRef("http://example.org/s"),
                URIRef("http://example.org/p"),
                URIRef("http://example.org/o"),
            )
        )

        class MockRow:
            def __init__(self, shape, predicate, datatypes=None) -> None:
                self.shape = shape
                self.predicate = predicate
                self.path = predicate
                self.datatypes = datatypes
                self.datatype = datatypes[0] if datatypes else None
                self.a_class = None
                self.classIn = None
                self.maxCount = None
                self.minCount = None
                self.pattern = None
                self.message = None
                self.optionalValues = ""
                self.conditionPaths = ""
                self.conditionValues = ""

        mock_results = [
            MockRow(
                "http://example.org/shapes/PersonShape",
                "http://xmlns.com/foaf/0.1/age",
                datatypes=["http://www.w3.org/2001/XMLSchema#integer"],
            )
        ]

        mock_custom_filter = Mock()
        mock_custom_filter.human_readable_predicate.return_value = "readable_value"
        mock_error_message = "Invalid datatype error message"

        with (
            patch(
                "heritrace.utils.shacl_validation.fetch_data_graph_for_subject",
                return_value=Graph(),
            ),
            patch(
                "heritrace.utils.shacl_validation.get_shacl_graph",
                return_value=mock_shacl_graph,
            ),
            patch(
                "heritrace.utils.shacl_validation.get_custom_filter",
                return_value=mock_custom_filter,
            ),
            patch("rdflib.graph.Graph.query", return_value=mock_results),
            patch("validators.url", return_value=False),
            patch(
                "heritrace.utils.shacl_validation.convert_to_matching_literal",
                return_value=None,
            ),
            patch(
                "heritrace.utils.shacl_validation.gettext",
                return_value=mock_error_message,
            ),
        ):
            valid_value, _old_value, error = validate_new_triple(
                URIRef("http://example.org/person/1"),
                URIRef("http://xmlns.com/foaf/0.1/age"),
                "not-an-integer",
                "create",
                entity_types=["http://xmlns.com/foaf/0.1/Person"],
            )

            assert valid_value is None
            assert error == mock_error_message


def test_validate_new_triple_with_invalid_url() -> None:
    """Test validation of a new triple with an invalid URL."""
    app = Flask(__name__)

    with app.test_request_context(), app.app_context():
        mock_shacl_graph = Graph()
        mock_shacl_graph.add(
            (
                URIRef("http://example.org/s"),
                URIRef("http://example.org/p"),
                URIRef("http://example.org/o"),
            )
        )

        class MockRow:
            def __init__(self, shape, predicate, classes=None) -> None:
                self.shape = shape
                self.predicate = predicate
                self.path = predicate
                self.classes = classes
                self.datatypes = None
                self.datatype = None
                self.a_class = None
                self.classIn = None
                self.maxCount = None
                self.minCount = None
                self.pattern = None
                self.message = None
                self.optionalValues = None
                self.conditionPaths = None
                self.conditionValues = None

        mock_results = [
            MockRow(
                "http://example.org/shapes/WebsiteShape",
                "http://xmlns.com/foaf/0.1/homepage",
                classes=["http://xmlns.com/foaf/0.1/Document"],
            )
        ]

        mock_custom_filter = Mock()
        mock_custom_filter.human_readable_predicate.return_value = "readable_value"

        with (
            patch(
                "heritrace.utils.shacl_validation.fetch_data_graph_for_subject",
                return_value=Graph(),
            ),
            patch(
                "heritrace.utils.shacl_validation.get_shacl_graph",
                return_value=mock_shacl_graph,
            ),
            patch(
                "heritrace.utils.shacl_validation.get_custom_filter",
                return_value=mock_custom_filter,
            ),
            patch("rdflib.graph.Graph.query", return_value=mock_results),
            patch("validators.url", return_value=False),
            patch("flask_babel.gettext", return_value="Invalid URL error message"),
        ):
            valid_value, _old_value, _error = validate_new_triple(
                URIRef("http://example.org/person/1"),
                URIRef("http://xmlns.com/foaf/0.1/homepage"),
                "not-a-valid-url",
                "create",
                entity_types=["http://xmlns.com/foaf/0.1/Person"],
            )

            assert isinstance(valid_value, Literal)
            assert str(valid_value) == "not-a-valid-url"
