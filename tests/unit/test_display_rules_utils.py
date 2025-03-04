"""
Tests for display_rules_utils.py
"""

from unittest.mock import MagicMock, patch

import pytest
from heritrace.utils.display_rules_utils import (
    execute_historical_query,
    execute_sparql_query,
    get_class_priority,
    get_grouped_triples,
    get_highest_priority_class,
    get_property_order_from_rules,
    get_sortable_properties,
    is_entity_type_visible,
    process_default_property,
    process_display_rule,
    process_ordering,
)
from rdflib import Graph, Literal, URIRef


@pytest.fixture
def mock_display_rules():
    """Mock display rules for testing."""
    return [
        {
            "class": "http://example.org/Person",
            "priority": 1,
            "shouldBeDisplayed": True,
            "displayProperties": [
                {
                    "property": "http://example.org/name",
                    "displayName": "Name",
                    "displayRules": [
                        {
                            "displayName": "Person Name",
                            "fetchValueFromQuery": "SELECT ?label ?entity WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label . BIND([[value]] AS ?entity) }",
                            "shape": "http://example.org/PersonShape",
                        }
                    ],
                },
                {
                    "property": "http://example.org/age",
                    "displayName": "Age",
                },
                {
                    "property": "http://example.org/knows",
                    "displayName": "Knows",
                    "orderedBy": "http://example.org/order",
                    "intermediateRelation": {
                        "class": "http://example.org/Relationship"
                    },
                },
            ],
            "sortableBy": [
                {
                    "property": "http://example.org/name",
                    "displayName": "Name",
                }
            ],
        },
        {
            "class": "http://example.org/Document",
            "priority": 2,
            "shouldBeDisplayed": False,
            "displayProperties": [
                {
                    "property": "http://example.org/title",
                    "displayName": "Title",
                }
            ],
        },
    ]


@pytest.fixture
def mock_form_fields_cache():
    """Mock form fields cache for testing."""
    return {
        "http://example.org/Person": {
            "http://example.org/name": [
                {
                    "nodeShape": "http://example.org/PersonShape",
                }
            ],
            "http://example.org/age": [
                {
                    "datatypes": ["http://www.w3.org/2001/XMLSchema#integer"],
                }
            ],
            "http://example.org/birthDate": [
                {
                    "datatypes": ["http://www.w3.org/2001/XMLSchema#date"],
                }
            ],
            "http://example.org/height": [
                {
                    "datatypes": ["http://www.w3.org/2001/XMLSchema#decimal"],
                }
            ],
            "http://example.org/description": [
                {
                    "datatypes": ["http://www.w3.org/2001/XMLSchema#string"],
                }
            ],
        }
    }


@pytest.fixture
def mock_triples():
    """Mock triples for testing."""
    return [
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/name"),
            URIRef("http://example.org/name1"),
        ),
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/age"),
            Literal("30"),
        ),
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/knows"),
            URIRef("http://example.org/person2"),
        ),
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/knows"),
            URIRef("http://example.org/person3"),
        ),
    ]


@pytest.fixture
def mock_subject_classes():
    """Mock subject classes for testing."""
    return [URIRef("http://example.org/Person"), URIRef("http://example.org/Agent")]


@pytest.fixture
def mock_valid_predicates_info():
    """Mock valid predicates info for testing."""
    return [
        "http://example.org/name",
        "http://example.org/age",
        "http://example.org/knows",
    ]


@pytest.fixture
def mock_sparql():
    """Mock SPARQL wrapper for testing."""
    mock = MagicMock()
    mock.query.return_value.convert.return_value = {
        "results": {
            "bindings": [
                {
                    "label": {"value": "John Doe"},
                    "entity": {"value": "http://example.org/name1"},
                }
            ]
        }
    }
    return mock


@pytest.fixture
def mock_historical_snapshot():
    """Mock historical snapshot for testing."""
    graph = Graph()
    graph.add(
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/name"),
            Literal("John Doe"),
        )
    )
    graph.add(
        (
            URIRef("http://example.org/person2"),
            URIRef("http://example.org/order"),
            URIRef("http://example.org/person3"),
        )
    )
    graph.add(
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/knows"),
            URIRef("http://example.org/person2"),
        )
    )
    graph.add(
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/knows"),
            URIRef("http://example.org/person3"),
        )
    )
    return graph


class TestInitialization:
    """Test the initialization of the module."""

    def test_get_class_priority(self, monkeypatch):
        """Test that get_class_priority returns the correct priority."""
        # Mock display rules with class priorities
        mock_rules = [
            {"class": "http://example.org/Person", "priority": 10},
            {"class": "http://example.org/Organization", "priority": 5},
        ]

        # Mock the get_display_rules function
        monkeypatch.setattr(
            "heritrace.utils.display_rules_utils.get_display_rules", lambda: mock_rules
        )

        # Test get_class_priority function
        assert get_class_priority("http://example.org/Person") == 10
        assert get_class_priority("http://example.org/Organization") == 5
        assert get_class_priority("http://example.org/Unknown") == 0

    def test_get_class_priority_no_rules(self, monkeypatch):
        """Test that get_class_priority returns 0 when there are no rules."""
        # Mock empty display rules
        monkeypatch.setattr(
            "heritrace.utils.display_rules_utils.get_display_rules", lambda: {}
        )

        # Test get_class_priority function
        assert get_class_priority("http://example.org/Person") == 0


class TestIsEntityTypeVisible:
    """Tests for is_entity_type_visible function."""

    def test_entity_type_visible_true(self, mock_display_rules):
        """Test when entity type should be displayed."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules,
        ):
            result = is_entity_type_visible("http://example.org/Person")
            assert result is True

    def test_entity_type_visible_false(self, mock_display_rules):
        """Test when entity type should not be displayed."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules,
        ):
            result = is_entity_type_visible("http://example.org/Document")
            assert result is False

    def test_entity_type_not_in_rules(self, mock_display_rules):
        """Test when entity type is not in display rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules,
        ):
            result = is_entity_type_visible("http://example.org/Unknown")
            assert result is True

    def test_no_display_rules(self):
        """Test when there are no display rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules", return_value=[]
        ):
            result = is_entity_type_visible("http://example.org/Person")
            assert result is True


class TestGetSortableProperties:
    """Tests for get_sortable_properties function."""

    def test_get_sortable_properties_with_rules(
        self, mock_display_rules, mock_form_fields_cache
    ):
        """Test getting sortable properties with display rules."""
        result = get_sortable_properties(
            "http://example.org/Person", mock_display_rules, mock_form_fields_cache
        )
        assert len(result) == 1
        assert result[0]["property"] == "http://example.org/name"
        assert result[0]["displayName"] == "Person Name"
        assert result[0]["sortType"] == "string"

    def test_get_sortable_properties_no_rules(self, mock_form_fields_cache):
        """Test getting sortable properties with no display rules."""
        result = get_sortable_properties(
            "http://example.org/Person", [], mock_form_fields_cache
        )
        assert result == []

    def test_get_sortable_properties_class_not_in_rules(
        self, mock_display_rules, mock_form_fields_cache
    ):
        """Test getting sortable properties for a class not in display rules."""
        result = get_sortable_properties(
            "http://example.org/Unknown", mock_display_rules, mock_form_fields_cache
        )
        assert result == []

    def test_get_sortable_properties_with_date_type(
        self, mock_display_rules, mock_form_fields_cache
    ):
        """Test getting sortable properties with date datatype."""
        # Modify mock_display_rules to include a date property
        modified_rules = mock_display_rules.copy()
        modified_rules[0]["sortableBy"].append(
            {
                "property": "http://example.org/birthDate",
                "displayName": "Birth Date",
            }
        )

        result = get_sortable_properties(
            "http://example.org/Person", modified_rules, mock_form_fields_cache
        )
        assert len(result) == 2
        date_prop = next(
            p for p in result if p["property"] == "http://example.org/birthDate"
        )
        assert date_prop["sortType"] == "date"

    def test_get_sortable_properties_with_number_type(
        self, mock_display_rules, mock_form_fields_cache
    ):
        """Test getting sortable properties with number datatype."""
        # Modify mock_display_rules to include a number property
        modified_rules = mock_display_rules.copy()
        modified_rules[0]["sortableBy"].append(
            {
                "property": "http://example.org/height",
                "displayName": "Height",
            }
        )

        result = get_sortable_properties(
            "http://example.org/Person", modified_rules, mock_form_fields_cache
        )
        assert len(result) == 2
        number_prop = next(
            p for p in result if p["property"] == "http://example.org/height"
        )
        assert number_prop["sortType"] == "number"

    def test_get_sortable_properties_no_form_fields(self, mock_display_rules):
        """Test getting sortable properties with no form fields cache."""
        result = get_sortable_properties(
            "http://example.org/Person", mock_display_rules, None
        )
        assert len(result) == 1
        assert "sortType" not in result[0]

    def test_get_sortable_properties_with_missing_form_fields(self, mock_display_rules):
        """Test getting sortable properties when form fields are missing for a property."""
        # Create a form fields cache with missing entries
        mock_form_fields_cache = {"http://example.org/Person": {}}

        # Create a modified display rules with a sortType property
        modified_display_rules = [
            {
                "class": "http://example.org/Person",
                "sortableBy": [
                    {"property": "http://example.org/name", "displayName": "Name"}
                ],
                "displayProperties": [
                    {"property": "http://example.org/name", "displayName": "Name"}
                ],
                "priority": 1,
                "shouldBeDisplayed": True,
            }
        ]

        result = get_sortable_properties(
            "http://example.org/Person", modified_display_rules, mock_form_fields_cache
        )

        # Verify the result has the expected property
        assert len(result) == 1
        assert result[0]["property"] == "http://example.org/name"
        # Note: sortType is not added when the property is not in form_fields_cache

    def test_get_sortable_properties_with_default_sort_type(
        self, mock_form_fields_cache
    ):
        """Test getting sortable properties with default sort type."""
        # Create a modified display rules with a property not in form_fields_cache
        modified_display_rules = [
            {
                "class": "http://example.org/Person",
                "sortableBy": [
                    {"property": "http://example.org/unknown", "displayName": "Unknown"}
                ],
                "displayProperties": [
                    {"property": "http://example.org/unknown", "displayName": "Unknown"}
                ],
                "priority": 1,
                "shouldBeDisplayed": True,
            }
        ]

        # Create a form fields cache with the property but no datatype or nodeShape
        mock_form_fields_cache_empty = {
            "http://example.org/Person": {
                "http://example.org/unknown": [{}]  # No datatype or nodeShape
            }
        }

        result = get_sortable_properties(
            "http://example.org/Person",
            modified_display_rules,
            mock_form_fields_cache_empty,
        )

        # Verify the result has the default string sort type
        assert len(result) == 1
        assert result[0]["property"] == "http://example.org/unknown"
        assert result[0]["sortType"] == "string"

    def test_get_sortable_properties_with_boolean_type(
        self, mock_display_rules, mock_form_fields_cache
    ):
        """Test getting sortable properties with boolean datatype."""
        # Modify mock_display_rules to include a boolean property
        modified_rules = mock_display_rules.copy()
        modified_rules[0]["sortableBy"].append(
            {
                "property": "http://example.org/isActive",
                "displayName": "Is Active",
            }
        )

        # Add boolean property to form_fields_cache
        mock_form_fields_cache["http://example.org/Person"]["http://example.org/isActive"] = [
            {
                "datatypes": ["http://www.w3.org/2001/XMLSchema#boolean"],
            }
        ]

        result = get_sortable_properties(
            "http://example.org/Person", modified_rules, mock_form_fields_cache
        )
        assert len(result) == 2
        boolean_prop = next(
            p for p in result if p["property"] == "http://example.org/isActive"
        )
        assert boolean_prop["sortType"] == "boolean"

    def test_get_sortable_properties_with_string_type(
        self, mock_display_rules, mock_form_fields_cache
    ):
        """Test getting sortable properties with string datatype."""
        # Modify mock_display_rules to include a string property
        modified_rules = mock_display_rules.copy()
        modified_rules[0]["sortableBy"].append(
            {
                "property": "http://example.org/description",
                "displayName": "Description",
            }
        )

        result = get_sortable_properties(
            "http://example.org/Person", modified_rules, mock_form_fields_cache
        )
        assert len(result) == 2
        string_prop = next(
            p for p in result if p["property"] == "http://example.org/description"
        )
        assert string_prop["sortType"] == "string"


class TestGetHighestPriorityClass:
    @patch("heritrace.utils.display_rules_utils.get_class_priority")
    def test_get_highest_priority_class(self, mock_get_class_priority):
        # Mock get_class_priority to return specific values
        mock_get_class_priority.side_effect = lambda class_uri: {
            "http://example.org/Person": 10,
            "http://example.org/Organization": 5,
            "http://example.org/Event": 3,
        }.get(class_uri, 0)

        # Test with multiple classes
        subject_classes = [
            "http://example.org/Person",
            "http://example.org/Organization",
            "http://example.org/Event",
        ]
        result = get_highest_priority_class(subject_classes)
        assert result == "http://example.org/Event"

        # Test with different order
        subject_classes = [
            "http://example.org/Event",
            "http://example.org/Organization",
            "http://example.org/Person",
        ]
        result = get_highest_priority_class(subject_classes)
        assert result == "http://example.org/Event"

    @patch("heritrace.utils.display_rules_utils.get_class_priority")
    def test_get_highest_priority_class_empty_list(self, mock_get_class_priority):
        # Test with empty list
        subject_classes = []
        result = get_highest_priority_class(subject_classes)
        assert result is None

    @patch("heritrace.utils.display_rules_utils.get_class_priority")
    def test_get_highest_priority_class_same_priority(self, mock_get_class_priority):
        # Mock get_class_priority to return same priority for all classes
        mock_get_class_priority.return_value = 5

        # Test with classes having same priority
        subject_classes = [
            "http://example.org/Person",
            "http://example.org/Organization",
        ]
        result = get_highest_priority_class(subject_classes)
        assert result == "http://example.org/Person"  # First one should be returned


class TestGetGroupedTriples:
    """Tests for get_grouped_triples function."""

    def test_get_grouped_triples_with_rules(
        self,
        mock_display_rules,
        mock_triples,
        mock_subject_classes,
        mock_valid_predicates_info,
    ):
        """Test getting grouped triples with display rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules,
        ):
            with patch(
                "heritrace.utils.display_rules_utils.get_highest_priority_class",
                return_value=URIRef("http://example.org/Person"),
            ):
                # Mock process_display_rule to actually create the expected structure
                def mock_process_display_rule(
                    display_name,
                    prop_uri,
                    rule,
                    subject,
                    triples,
                    grouped_triples,
                    fetched_values_map,
                    historical_snapshot=None,
                ):
                    if display_name not in grouped_triples:
                        grouped_triples[display_name] = {
                            "property": prop_uri,
                            "triples": [],
                            "shape": rule.get("shape"),
                            "intermediateRelation": rule.get("intermediateRelation"),
                        }

                with patch(
                    "heritrace.utils.display_rules_utils.process_display_rule",
                    side_effect=mock_process_display_rule,
                ):
                    with patch("heritrace.utils.display_rules_utils.process_ordering"):
                        grouped_triples, relevant_properties = get_grouped_triples(
                            "http://example.org/person1",
                            mock_triples,
                            mock_subject_classes,
                            mock_valid_predicates_info,
                        )
                        assert isinstance(grouped_triples, dict)
                        assert isinstance(relevant_properties, set)

    def test_get_grouped_triples_no_rules(
        self, mock_triples, mock_subject_classes, mock_valid_predicates_info
    ):
        """Test getting grouped triples with no display rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules", return_value=[]
        ):
            with patch("heritrace.utils.display_rules_utils.process_default_property"):
                grouped_triples, relevant_properties = get_grouped_triples(
                    "http://example.org/person1",
                    mock_triples,
                    mock_subject_classes,
                    mock_valid_predicates_info,
                )
                assert isinstance(grouped_triples, dict)
                assert isinstance(relevant_properties, set)

    def test_get_grouped_triples_with_ordered_properties(
        self,
        mock_display_rules,
        mock_triples,
        mock_subject_classes,
        mock_valid_predicates_info,
    ):
        """Test getting grouped triples with ordered properties."""
        # Create display rules with orderedBy property
        ordered_display_rules = [
            {
                "class": "http://example.org/Person",
                "displayProperties": [
                    {
                        "displayName": "Name",
                        "property": "http://example.org/name",
                        "orderedBy": "http://example.org/order",
                        "displayRules": [{"displayName": "Person Name"}],
                    }
                ],
                "priority": 1,
                "shouldBeDisplayed": True,
            }
        ]

        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=ordered_display_rules,
        ):
            with patch(
                "heritrace.utils.display_rules_utils.get_highest_priority_class",
                return_value=URIRef("http://example.org/Person"),
            ):
                with patch(
                    "heritrace.utils.display_rules_utils.process_display_rule",
                    side_effect=lambda display_name, prop_uri, display_rule, subject, triples, grouped_triples, fetched_values_map, historical_snapshot: grouped_triples.update(
                        {"Person Name": {}}
                    ),
                ):
                    with patch("heritrace.utils.display_rules_utils.process_ordering"):
                        grouped_triples, relevant_properties = get_grouped_triples(
                            "http://example.org/person1",
                            mock_triples,
                            mock_subject_classes,
                            mock_valid_predicates_info,
                        )

                        # Verify the is_draggable property is set
                        assert "Person Name" in grouped_triples
                        assert grouped_triples["Person Name"]["is_draggable"] is True
                        assert (
                            grouped_triples["Person Name"]["ordered_by"]
                            == "http://example.org/order"
                        )

    def test_get_grouped_triples_with_intermediate_relation(
        self,
        mock_display_rules,
        mock_triples,
        mock_subject_classes,
        mock_valid_predicates_info,
    ):
        """Test getting grouped triples with intermediate relation."""
        # Create display rules with intermediateRelation property
        intermediate_display_rules = [
            {
                "class": "http://example.org/Person",
                "displayProperties": [
                    {
                        "displayName": "Name",
                        "property": "http://example.org/name",
                        "intermediateRelation": "http://example.org/related",
                        "displayRules": [{"displayName": "Person Name"}],
                    }
                ],
                "priority": 1,
                "shouldBeDisplayed": True,
            }
        ]

        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=intermediate_display_rules,
        ):
            with patch(
                "heritrace.utils.display_rules_utils.get_highest_priority_class",
                return_value=URIRef("http://example.org/Person"),
            ):
                with patch(
                    "heritrace.utils.display_rules_utils.process_display_rule",
                    side_effect=lambda display_name, prop_uri, display_rule, subject, triples, grouped_triples, fetched_values_map, historical_snapshot: grouped_triples.update(
                        {"Person Name": {}}
                    ),
                ):
                    grouped_triples, relevant_properties = get_grouped_triples(
                        "http://example.org/person1",
                        mock_triples,
                        mock_subject_classes,
                        mock_valid_predicates_info,
                    )

                    # Verify the intermediateRelation property is set
                    assert "Person Name" in grouped_triples
                    assert (
                        grouped_triples["Person Name"]["intermediateRelation"]
                        == "http://example.org/related"
                    )


class TestProcessDisplayRule:
    """Tests for process_display_rule function."""

    def test_process_display_rule_with_fetch_value(self, mock_triples):
        """Test processing display rule with fetchValueFromQuery."""
        display_name = "Person Name"
        prop_uri = "http://example.org/name"
        rule = {
            "fetchValueFromQuery": "SELECT ?label ?entity WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label . BIND([[value]] AS ?entity) }",
            "shape": "http://example.org/PersonShape",
        }
        subject = "http://example.org/person1"
        grouped_triples = {}
        fetched_values_map = {}

        with patch(
            "heritrace.utils.display_rules_utils.execute_sparql_query",
            return_value=("John Doe", "http://example.org/name1"),
        ):
            process_display_rule(
                display_name,
                prop_uri,
                rule,
                subject,
                mock_triples,
                grouped_triples,
                fetched_values_map,
            )

            assert display_name in grouped_triples
            assert len(grouped_triples[display_name]["triples"]) == 1
            assert grouped_triples[display_name]["property"] == prop_uri
            assert (
                grouped_triples[display_name]["shape"]
                == "http://example.org/PersonShape"
            )
            assert fetched_values_map["John Doe"] == "http://example.org/name1"

    def test_process_display_rule_with_historical_snapshot(
        self, mock_triples, mock_historical_snapshot
    ):
        """Test processing display rule with historical snapshot."""
        display_name = "Person Name"
        prop_uri = "http://example.org/name"
        rule = {
            "fetchValueFromQuery": "SELECT ?label ?entity WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label . BIND([[value]] AS ?entity) }",
            "shape": "http://example.org/PersonShape",
        }
        subject = "http://example.org/person1"
        grouped_triples = {}
        fetched_values_map = {}

        with patch(
            "heritrace.utils.display_rules_utils.execute_historical_query",
            return_value=("John Doe", "http://example.org/name1"),
        ):
            process_display_rule(
                display_name,
                prop_uri,
                rule,
                subject,
                mock_triples,
                grouped_triples,
                fetched_values_map,
                mock_historical_snapshot,
            )

            assert display_name in grouped_triples
            assert len(grouped_triples[display_name]["triples"]) == 1

    def test_process_display_rule_without_fetch_value(self, mock_triples):
        """Test processing display rule without fetchValueFromQuery."""
        display_name = "Age"
        prop_uri = "http://example.org/age"
        rule = {
            "shape": "http://example.org/AgeShape",
        }
        subject = "http://example.org/person1"
        grouped_triples = {}
        fetched_values_map = {}

        process_display_rule(
            display_name,
            prop_uri,
            rule,
            subject,
            mock_triples,
            grouped_triples,
            fetched_values_map,
        )

        assert display_name in grouped_triples
        assert len(grouped_triples[display_name]["triples"]) == 1
        assert grouped_triples[display_name]["property"] == prop_uri
        assert grouped_triples[display_name]["shape"] == "http://example.org/AgeShape"


class TestExecuteSparqlQuery:
    """Tests for execute_sparql_query function."""

    def test_execute_sparql_query_with_results(self, mock_sparql):
        """Test executing SPARQL query with results."""
        query = "SELECT ?label ?entity WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label . BIND([[value]] AS ?entity) }"
        subject = "http://example.org/person1"
        value = "http://example.org/name1"

        with patch(
            "heritrace.utils.display_rules_utils.get_sparql", return_value=mock_sparql
        ):
            with patch("heritrace.utils.display_rules_utils.parseQuery"):
                with patch(
                    "heritrace.utils.display_rules_utils.translateQuery"
                ) as mock_translate:
                    mock_translate.return_value.algebra = {"PV": ["label", "entity"]}
                    result, external_entity = execute_sparql_query(
                        query, subject, value
                    )

                    assert result == "John Doe"
                    assert external_entity == "http://example.org/name1"
                    mock_sparql.setQuery.assert_called_once()
                    mock_sparql.setReturnFormat.assert_called_once()

    def test_execute_sparql_query_no_results(self, mock_sparql):
        """Test executing SPARQL query with no results."""
        query = "SELECT ?label ?entity WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label . BIND([[value]] AS ?entity) }"
        subject = "http://example.org/person1"
        value = "http://example.org/name1"

        mock_sparql.query.return_value.convert.return_value = {
            "results": {"bindings": []}
        }

        with patch(
            "heritrace.utils.display_rules_utils.get_sparql", return_value=mock_sparql
        ):
            result, external_entity = execute_sparql_query(query, subject, value)

            assert result is None
            assert external_entity is None


class TestProcessOrdering:
    """Tests for process_ordering function."""

    def test_process_ordering_with_sparql(self, mock_sparql):
        """Test processing ordering with SPARQL."""
        subject = "http://example.org/person1"
        prop = {
            "property": "http://example.org/knows",
        }
        order_property = "http://example.org/order"
        grouped_triples = {
            "Knows": {
                "triples": [
                    {
                        "triple": (
                            "http://example.org/person1",
                            "http://example.org/knows",
                            "http://example.org/person2",
                        ),
                        "object": "http://example.org/person2",
                    },
                    {
                        "triple": (
                            "http://example.org/person1",
                            "http://example.org/knows",
                            "http://example.org/person3",
                        ),
                        "object": "http://example.org/person3",
                    },
                ],
            },
        }
        display_name = "Knows"
        fetched_values_map = {}

        # Mock SPARQL results for ordering
        mock_sparql.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {
                        "orderedEntity": {"value": "http://example.org/person2"},
                        "nextValue": {"value": "http://example.org/person3"},
                    },
                    {
                        "orderedEntity": {"value": "http://example.org/person3"},
                        "nextValue": {"value": "NONE"},
                    },
                ],
            },
        }

        with patch(
            "heritrace.utils.display_rules_utils.get_sparql", return_value=mock_sparql
        ):
            process_ordering(
                subject,
                prop,
                order_property,
                grouped_triples,
                display_name,
                fetched_values_map,
            )

            # Check that triples are ordered correctly
            assert (
                grouped_triples[display_name]["triples"][0]["object"]
                == "http://example.org/person2"
            )
            assert (
                grouped_triples[display_name]["triples"][1]["object"]
                == "http://example.org/person3"
            )

    def test_process_ordering_with_historical_snapshot(self, mock_historical_snapshot):
        """Test processing ordering with historical snapshot."""
        subject = "http://example.org/person1"
        prop = {
            "property": "http://example.org/knows",
        }
        order_property = "http://example.org/order"
        grouped_triples = {
            "Knows": {
                "triples": [
                    {
                        "triple": (
                            "http://example.org/person1",
                            "http://example.org/knows",
                            "http://example.org/person2",
                        ),
                        "object": "http://example.org/person2",
                    },
                    {
                        "triple": (
                            "http://example.org/person1",
                            "http://example.org/knows",
                            "http://example.org/person3",
                        ),
                        "object": "http://example.org/person3",
                    },
                ],
            },
        }
        display_name = "Knows"
        fetched_values_map = {}

        process_ordering(
            subject,
            prop,
            order_property,
            grouped_triples,
            display_name,
            fetched_values_map,
            mock_historical_snapshot,
        )

        # Check that triples are ordered correctly based on the historical snapshot
        assert len(grouped_triples[display_name]["triples"]) == 2


class TestProcessDefaultProperty:
    """Tests for process_default_property function."""

    def test_process_default_property(self, mock_triples):
        """Test processing default property."""
        prop_uri = "http://example.org/age"
        grouped_triples = {}

        process_default_property(prop_uri, mock_triples, grouped_triples)

        assert prop_uri in grouped_triples
        assert grouped_triples[prop_uri]["property"] == prop_uri
        assert len(grouped_triples[prop_uri]["triples"]) == 1
        assert grouped_triples[prop_uri]["shape"] is None


class TestExecuteHistoricalQuery:
    """Tests for execute_historical_query function."""

    def test_execute_historical_query_with_results(self, mock_historical_snapshot):
        """Test executing historical query with results."""
        query = "SELECT ?label ?entity WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label . BIND([[value]] AS ?entity) }"
        subject = "http://example.org/person1"
        value = "http://example.org/name1"

        # Add a test triple to the mock historical snapshot
        mock_historical_snapshot.add(
            (
                URIRef(value),
                URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
                Literal("John Doe"),
            )
        )

        # Mock the query method to return our expected results
        original_query = mock_historical_snapshot.query

        def mock_query(q):
            # Return a list with a single result tuple
            return [(Literal("John Doe"), URIRef(value))]

        mock_historical_snapshot.query = mock_query

        result, external_entity = execute_historical_query(
            query, subject, value, mock_historical_snapshot
        )

        assert result == "John Doe"
        assert external_entity == value

        # Restore original query method
        mock_historical_snapshot.query = original_query

    def test_execute_historical_query_no_results(self, mock_historical_snapshot):
        """Test executing historical query with no results."""
        query = "SELECT ?label ?entity WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label . BIND([[value]] AS ?entity) }"
        subject = "http://example.org/person1"
        value = "http://example.org/unknown"

        # Mock the query method to return empty results
        original_query = mock_historical_snapshot.query
        mock_historical_snapshot.query = lambda q: []

        result, external_entity = execute_historical_query(
            query, subject, value, mock_historical_snapshot
        )

        assert result is None
        assert external_entity is None

        # Restore original query method
        mock_historical_snapshot.query = original_query


class TestGetPropertyOrderFromRules:
    """Tests for get_property_order_from_rules function."""

    def test_get_property_order_from_rules(
        self, mock_display_rules, mock_subject_classes
    ):
        """Test getting property order from rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_highest_priority_class",
            return_value=URIRef("http://example.org/Person"),
        ):
            result = get_property_order_from_rules(
                mock_subject_classes, mock_display_rules
            )

            assert len(result) == 3
            assert result[0] == "http://example.org/name"
            assert result[1] == "http://example.org/age"
            assert result[2] == "http://example.org/knows"

    def test_get_property_order_from_rules_no_matching_class(self, mock_display_rules):
        """Test getting property order from rules with no matching class."""
        with patch(
            "heritrace.utils.display_rules_utils.get_highest_priority_class",
            return_value=URIRef("http://example.org/Unknown"),
        ):
            result = get_property_order_from_rules(
                [URIRef("http://example.org/Unknown")], mock_display_rules
            )

            assert result == []

    def test_get_property_order_from_rules_no_rules(self, mock_subject_classes):
        """Test getting property order from rules with no rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_highest_priority_class",
            return_value=URIRef("http://example.org/Person"),
        ):
            result = get_property_order_from_rules(mock_subject_classes, [])

            assert result == []

    def test_get_property_order_from_rules_no_highest_priority_class(
        self, mock_display_rules
    ):
        """Test getting property order from rules with no highest priority class."""
        with patch(
            "heritrace.utils.display_rules_utils.get_highest_priority_class",
            return_value=None,
        ):
            result = get_property_order_from_rules([], mock_display_rules)

            assert result == []

    def test_get_property_order_from_rules_with_ordered_display_names(self):
        """Test getting property order from rules with ordered display names."""
        # Create display rules with ordered display names
        mock_display_rules = [
            {
                "class": "http://example.org/Person",
                "displayProperties": [
                    {
                        "displayName": "Name",
                        "property": "http://example.org/name",
                        "displayRules": [{"displayName": "Person Name"}],
                    },
                    {
                        "displayName": "Age",
                        "property": "http://example.org/age",
                    },
                ],
                "priority": 1,
                "shouldBeDisplayed": True,
            }
        ]

        # Create mock subject classes
        subject_classes = [URIRef("http://example.org/Person")]

        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules,
        ):
            with patch(
                "heritrace.utils.display_rules_utils.get_highest_priority_class",
                return_value=URIRef("http://example.org/Person"),
            ):
                # Call the function with the correct parameters
                ordered_properties = get_property_order_from_rules(
                    subject_classes, mock_display_rules
                )

                # Verify the ordered properties
                assert "http://example.org/name" in ordered_properties
                assert "http://example.org/age" in ordered_properties
