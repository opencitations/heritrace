# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

"""
Tests for display_rules_utils.py
"""

from unittest.mock import MagicMock, patch

import pytest
from rdflib import RDF, Graph, Literal, URIRef

from heritrace.utils.display_rules_utils import (
    GroupingContext,
    find_matching_rule,
    get_grouped_triples,
    get_highest_priority_class,
    get_similarity_properties,
    get_sortable_properties,
    process_default_property,
    process_ordering,
)
from heritrace.utils.filters import Filter
from heritrace.utils.shacl_presentation import read_presentation


@pytest.fixture
def mock_display_rules():
    """Mock display rules for testing."""
    return [
        {
            "target": {"class": "http://example.org/Person"},
            "displayProperties": [
                {
                    "property": "http://example.org/knows",
                    "orderedBy": "http://example.org/order",
                },
            ],
            "sortableBy": [
                {
                    "property": "http://example.org/name",
                }
            ],
        },
        {
            "target": {"class": "http://example.org/Document"},
            "displayProperties": [
                {
                    "property": "http://example.org/title",
                }
            ],
        },
    ]


@pytest.fixture
def mock_form_fields_cache():
    """Mock form fields cache for testing."""
    return {
        ("http://example.org/Person", None): {
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


class TestGetSortableProperties:
    """Tests for get_sortable_properties function."""

    @pytest.fixture(autouse=True)
    def property_names(self):
        names = {
            "http://example.org/name": "Person Name",
            "http://example.org/height": "Height",
            "http://example.org/unknown": "Unknown",
            "http://example.org/birthDate": "Birth Date",
            "http://example.org/isActive": "Is Active",
            "http://example.org/description": "Description",
        }
        custom_filter = MagicMock()
        custom_filter.human_readable_predicate.side_effect = lambda p, _key: names[p]
        with patch(
            "heritrace.utils.display_rules_utils.get_custom_filter",
            return_value=custom_filter,
        ):
            yield

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_with_rules(
        self,
        mock_get_form_fields,
        mock_get_display_rules,
        mock_display_rules,
        mock_form_fields_cache,
    ) -> None:
        """Test getting sortable properties with display rules."""
        mock_get_display_rules.return_value = mock_display_rules
        mock_get_form_fields.return_value = mock_form_fields_cache

        result = get_sortable_properties(("http://example.org/Person", None))

        assert len(result) == 1
        assert result[0]["property"] == "http://example.org/name"
        assert result[0]["displayName"] == "Person Name"
        assert result[0]["sortType"] == "string"

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_no_rules(
        self, mock_get_form_fields, mock_get_display_rules, mock_form_fields_cache
    ) -> None:
        """Test getting sortable properties with no display rules."""
        mock_get_display_rules.return_value = []
        mock_get_form_fields.return_value = mock_form_fields_cache

        result = get_sortable_properties(("http://example.org/Person", None))

        assert result == []

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_class_not_in_rules(
        self,
        mock_get_form_fields,
        mock_get_display_rules,
        mock_display_rules,
        mock_form_fields_cache,
    ) -> None:
        """Test getting sortable properties for a class not in display rules."""
        mock_get_display_rules.return_value = mock_display_rules
        mock_get_form_fields.return_value = mock_form_fields_cache

        result = get_sortable_properties(("http://example.org/Unknown", None))

        assert result == []

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_with_number_type_and_shape(
        self,
        mock_get_form_fields,
        mock_get_display_rules,
        mock_display_rules,
        mock_form_fields_cache,
    ) -> None:
        """Test getting sortable properties with number datatype and shape."""
        modified_rules = mock_display_rules.copy()
        modified_rules[0]["target"]["shape"] = "http://example.org/PersonShape"
        modified_rules[0]["sortableBy"].append(
            {
                "property": "http://example.org/height",
            }
        )

        modified_form_fields = mock_form_fields_cache.copy()
        modified_form_fields[
            ("http://example.org/Person", "http://example.org/PersonShape")
        ] = {
            "http://example.org/height": [
                {
                    "datatypes": ["http://www.w3.org/2001/XMLSchema#decimal"],
                }
            ]
        }

        mock_get_display_rules.return_value = modified_rules
        mock_get_form_fields.return_value = modified_form_fields

        result = get_sortable_properties(
            ("http://example.org/Person", "http://example.org/PersonShape")
        )

        assert len(result) == 2
        number_prop = next(
            p for p in result if p["property"] == "http://example.org/height"
        )
        assert number_prop["sortType"] == "number"

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_no_form_fields(
        self, mock_get_form_fields, mock_get_display_rules, mock_display_rules
    ) -> None:
        """Test getting sortable properties with no form fields cache."""
        mock_get_display_rules.return_value = mock_display_rules
        mock_get_form_fields.return_value = None

        result = get_sortable_properties(("http://example.org/Person", None))

        assert len(result) == 1
        assert "sortType" in result[0]
        assert result[0]["sortType"] == "string"

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_with_missing_form_fields(
        self, mock_get_form_fields, mock_get_display_rules, mock_display_rules
    ) -> None:
        """
        Test getting sortable properties when form fields are missing for a property.
        """
        mock_form_fields_cache = {"http://example.org/Person": {}}

        modified_display_rules = [
            {
                "target": {"class": "http://example.org/Person"},
                "sortableBy": [{"property": "http://example.org/name"}],
                "displayProperties": [{"property": "http://example.org/name"}],
            }
        ]
        mock_get_display_rules.return_value = modified_display_rules
        mock_get_form_fields.return_value = mock_form_fields_cache

        result = get_sortable_properties(("http://example.org/Person", None))

        assert len(result) == 1
        assert result[0]["property"] == "http://example.org/name"

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_with_default_sort_type(
        self, mock_get_form_fields, mock_get_display_rules, mock_form_fields_cache
    ) -> None:
        """Test getting sortable properties with default sort type."""
        modified_display_rules = [
            {
                "target": {"class": "http://example.org/Person"},
                "sortableBy": [{"property": "http://example.org/unknown"}],
                "displayProperties": [{"property": "http://example.org/unknown"}],
            }
        ]

        mock_form_fields_cache_empty = {
            "http://example.org/Person": {
                "http://example.org/unknown": [{}]  # No datatype or nodeShape
            }
        }

        mock_get_display_rules.return_value = modified_display_rules
        mock_get_form_fields.return_value = mock_form_fields_cache_empty

        result = get_sortable_properties(("http://example.org/Person", None))

        assert len(result) == 1
        assert result[0]["property"] == "http://example.org/unknown"
        assert result[0]["sortType"] == "string"

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_with_date_type_and_shape(
        self,
        mock_get_form_fields,
        mock_get_display_rules,
        mock_display_rules,
        mock_form_fields_cache,
    ) -> None:
        """Test getting sortable properties with date datatype and shape."""
        modified_rules = mock_display_rules.copy()
        modified_rules[0]["target"]["shape"] = "http://example.org/PersonShape"
        modified_rules[0]["sortableBy"].append(
            {
                "property": "http://example.org/birthDate",
            }
        )

        modified_form_fields = mock_form_fields_cache.copy()
        modified_form_fields[
            ("http://example.org/Person", "http://example.org/PersonShape")
        ] = {
            "http://example.org/birthDate": [
                {
                    "datatypes": ["http://www.w3.org/2001/XMLSchema#date"],
                }
            ]
        }

        mock_get_display_rules.return_value = modified_rules
        mock_get_form_fields.return_value = modified_form_fields

        result = get_sortable_properties(
            ("http://example.org/Person", "http://example.org/PersonShape")
        )

        assert len(result) == 2
        date_prop = next(
            p for p in result if p["property"] == "http://example.org/birthDate"
        )
        assert date_prop["sortType"] == "date"

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_with_boolean_type_and_shape(
        self,
        mock_get_form_fields,
        mock_get_display_rules,
        mock_display_rules,
        mock_form_fields_cache,
    ) -> None:
        """Test getting sortable properties with boolean datatype and shape."""
        modified_rules = mock_display_rules.copy()
        modified_rules[0]["target"]["shape"] = "http://example.org/PersonShape"
        modified_rules[0]["sortableBy"].append(
            {
                "property": "http://example.org/isActive",
            }
        )

        modified_form_fields = mock_form_fields_cache.copy()
        modified_form_fields[
            ("http://example.org/Person", "http://example.org/PersonShape")
        ] = {
            "http://example.org/isActive": [
                {
                    "datatypes": ["http://www.w3.org/2001/XMLSchema#boolean"],
                }
            ]
        }

        mock_get_display_rules.return_value = modified_rules
        mock_get_form_fields.return_value = modified_form_fields

        result = get_sortable_properties(
            ("http://example.org/Person", "http://example.org/PersonShape")
        )

        assert len(result) == 2
        boolean_prop = next(
            p for p in result if p["property"] == "http://example.org/isActive"
        )
        assert boolean_prop["sortType"] == "boolean"

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_with_string_type(
        self,
        mock_get_form_fields,
        mock_get_display_rules,
        mock_display_rules,
        mock_form_fields_cache,
    ) -> None:
        """Test getting sortable properties with string datatype."""
        modified_rules = mock_display_rules.copy()
        modified_rules[0]["sortableBy"].append(
            {
                "property": "http://example.org/description",
            }
        )

        mock_get_display_rules.return_value = modified_rules
        mock_get_form_fields.return_value = mock_form_fields_cache

        result = get_sortable_properties(("http://example.org/Person", None))

        assert len(result) == 2
        string_prop = next(
            p for p in result if p["property"] == "http://example.org/description"
        )
        assert string_prop["sortType"] == "string"


class TestGetHighestPriorityClass:
    @staticmethod
    def _shapes_for(class_uri_counts: dict[str, int]) -> MagicMock:
        presentation = MagicMock()
        presentation.fixed_type_count.side_effect = lambda shape: (
            class_uri_counts[shape] if shape else 0
        )
        return presentation

    def test_prefers_the_class_whose_shape_fixes_the_most_types(self) -> None:
        article = "http://example.org/Article"
        expression = "http://example.org/Expression"
        unconfigured = "http://example.org/Unconfigured"
        shapes = {article: "ArticleShape", expression: "ExpressionShape"}
        with (
            patch(
                "heritrace.utils.shacl_utils.determine_shape_for_classes",
                side_effect=lambda classes: shapes.get(classes[0]),
            ),
            patch(
                "heritrace.utils.display_rules_utils.get_presentation",
                return_value=self._shapes_for(
                    {"ArticleShape": 2, "ExpressionShape": 1}
                ),
            ),
        ):
            assert (
                get_highest_priority_class([unconfigured, expression, article])
                == article
            )

    def test_returns_none_without_classes(self) -> None:
        with patch(
            "heritrace.utils.display_rules_utils.get_presentation",
            return_value=self._shapes_for({}),
        ):
            assert get_highest_priority_class([]) is None

    def test_keeps_the_first_class_on_a_tie(self) -> None:
        with (
            patch(
                "heritrace.utils.shacl_utils.determine_shape_for_classes",
                return_value=None,
            ),
            patch(
                "heritrace.utils.display_rules_utils.get_presentation",
                return_value=self._shapes_for({}),
            ),
        ):
            assert (
                get_highest_priority_class(
                    ["http://example.org/Person", "http://example.org/Organization"]
                )
                == "http://example.org/Person"
            )


class TestProcessOrdering:
    """Tests for process_ordering function."""

    def test_process_ordering_with_sparql(self, mock_sparql) -> None:
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
            ctx = GroupingContext(
                subject=subject,
                triples=[],
                grouped_triples=grouped_triples,
                fetched_values_map=fetched_values_map,
                relevant_properties=set(),
                historical_snapshot=None,
                highest_priority_class=None,
                highest_priority_shape=None,
                value_shapes={},
                value_triples={},
            )
            process_ordering(
                ctx,
                prop,
                order_property,
                display_name,
            )

            assert (
                grouped_triples[display_name]["triples"][0]["object"]
                == "http://example.org/person2"
            )
            assert (
                grouped_triples[display_name]["triples"][1]["object"]
                == "http://example.org/person3"
            )

    @patch("heritrace.utils.display_rules_utils.get_sparql")
    def test_process_ordering_with_historical_snapshot(
        self, _mock_get_sparql, mock_historical_snapshot
    ) -> None:
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

        ctx = GroupingContext(
            subject=subject,
            triples=[],
            grouped_triples=grouped_triples,
            fetched_values_map=fetched_values_map,
            relevant_properties=set(),
            historical_snapshot=mock_historical_snapshot,
            highest_priority_class=None,
            highest_priority_shape=None,
            value_shapes={},
            value_triples={},
        )
        process_ordering(
            ctx,
            prop,
            order_property,
            display_name,
        )

        assert len(grouped_triples[display_name]["triples"]) == 2


class TestProcessDefaultProperty:
    """Tests for process_default_property function."""

    def test_process_default_property(self, mock_triples) -> None:
        """Test processing default property."""
        prop_uri = "http://example.org/age"
        grouped_triples = {}

        process_default_property(prop_uri, mock_triples, grouped_triples)

        assert prop_uri in grouped_triples
        assert grouped_triples[prop_uri]["property"] == prop_uri
        assert len(grouped_triples[prop_uri]["triples"]) == 1
        assert grouped_triples[prop_uri]["objectShape"] is None


class TestGetSimilarityProperties:
    """Tests for get_similarity_properties function."""

    @pytest.fixture
    def mock_display_rules_with_similarity(self):
        """Mock display rules with similarity_properties."""
        return [
            {
                "target": {"class": "http://example.org/Person"},
                "similarity_properties": [
                    "http://example.org/name",
                    "http://example.org/email",
                ],
            },
            {
                "target": {"class": "http://example.org/Organization"},
                "similarity_properties": [],  # Empty list
            },
            {
                "target": {"class": "http://example.org/Document"},
            },
            {
                "target": {"class": "http://example.org/Event"},
                "similarity_properties": "not a list",  # Invalid format
            },
            {
                "target": {"class": "http://example.org/Place"},
                "similarity_properties": ["prop1", 123],  # Invalid item type
            },
        ]

    def test_get_similarity_properties_found(
        self, mock_display_rules_with_similarity
    ) -> None:
        """Test when similarity_properties are found and valid."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules_with_similarity,
        ):
            result = get_similarity_properties(("http://example.org/Person", None))
            assert result == ["http://example.org/name", "http://example.org/email"]

    def test_get_similarity_properties_empty_list(
        self, mock_display_rules_with_similarity
    ) -> None:
        """Test when similarity_properties is an empty list."""
        mock_rules = mock_display_rules_with_similarity.copy()
        mock_rules[0]["similarity_properties"] = []

        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_rules,
        ):
            result = get_similarity_properties(("http://example.org/Person", None))
            assert result is None  # Should return None if list is empty

    def test_get_similarity_properties_missing_key(
        self, mock_display_rules_with_similarity
    ) -> None:
        """Test when similarity_properties key is missing for the class."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules_with_similarity,
        ):
            result = get_similarity_properties(("http://example.org/Document", None))
            assert result is None

    def test_get_similarity_properties_class_not_found(
        self, mock_display_rules_with_similarity
    ) -> None:
        """Test when the entity type is not found in the rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules_with_similarity,
        ):
            result = get_similarity_properties(("http://example.org/Unknown", None))
            assert result is None

    def test_get_similarity_properties_invalid_format_not_list(
        self, mock_display_rules_with_similarity, capsys
    ) -> None:
        """Test when similarity_properties is not a list."""
        entity_type = "http://example.org/Event"
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules_with_similarity,
        ):
            result = get_similarity_properties((entity_type, None))
            assert result is None

    def test_get_similarity_properties_invalid_format_item_type(
        self, mock_display_rules_with_similarity, caplog
    ) -> None:
        """Test when similarity_properties list contains non-string items."""
        entity_type = "http://example.org/Place"
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules_with_similarity,
        ):
            result = get_similarity_properties((entity_type, None))
            assert result is None
            assert any(
                "Invalid item format in similarity_properties list for class"
                in record.message
                and entity_type in record.message
                for record in caplog.records
            )

    def test_get_similarity_properties_with_and_structure(self, caplog) -> None:
        """Test get_similarity_properties with valid and invalid 'and' structures."""
        entity_type = "http://example.org/TestAnd"
        mock_rules_and = [
            {
                "target": {"class": entity_type},
                "similarity_properties": [
                    "prop1",
                    {"and": ["prop2", "prop3"]},  # Valid
                ],
            },
            {
                "target": {"class": "http://example.org/InvalidAndValue"},
                "similarity_properties": [{"and": "not_a_list"}],
            },
            {
                "target": {"class": "http://example.org/InvalidAndListItem"},
                "similarity_properties": [{"and": ["prop4", 555]}],
            },
            {
                "target": {"class": "http://example.org/InvalidAndDict"},
                "similarity_properties": [{"and": ["prop4"], "or": ["prop5"]}],
            },
        ]

        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_rules_and,
        ):
            result_valid = get_similarity_properties((entity_type, None))
            assert result_valid == ["prop1", {"and": ["prop2", "prop3"]}]

            invalid_type1 = "http://example.org/InvalidAndValue"
            caplog.clear()
            result_invalid_value = get_similarity_properties((invalid_type1, None))
            assert result_invalid_value is None
            assert any(
                "Invalid 'and' group" in r.message and invalid_type1 in r.message
                for r in caplog.records
            )

            invalid_type2 = "http://example.org/InvalidAndListItem"
            caplog.clear()
            result_invalid_item = get_similarity_properties((invalid_type2, None))
            assert result_invalid_item is None
            assert any(
                "Invalid 'and' group" in r.message and invalid_type2 in r.message
                for r in caplog.records
            )

            invalid_type3 = "http://example.org/InvalidAndDict"
            caplog.clear()
            result_invalid_dict = get_similarity_properties((invalid_type3, None))
            assert result_invalid_dict is None
            assert any(
                "Invalid item format" in r.message and invalid_type3 in r.message
                for r in caplog.records
            )

    def test_get_similarity_properties_no_rules(self) -> None:
        """Test when get_display_rules returns empty list."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules", return_value=[]
        ):
            result = get_similarity_properties(("http://example.org/Person", None))
            assert result is None

    def test_get_similarity_properties_no_rules_none(self) -> None:
        """Test when get_display_rules returns None."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules", return_value=None
        ):
            result = get_similarity_properties(("http://example.org/Person", None))
            assert result is None


class TestFindMatchingRule:
    """Tests for find_matching_rule function."""

    def test_exact_match_class_and_shape(self) -> None:
        """Test Case 1: Both class and shape match (exact match)."""
        class_uri = "http://example.org/Person"
        shape_uri = "http://example.org/PersonShape"

        mock_rules = [
            {
                "target": {
                    "class": "http://example.org/Document",
                    "shape": "http://example.org/DocumentShape",
                },
                "displayProperties": [],
            },
            {
                "target": {
                    "class": "http://example.org/Person",
                    "shape": "http://example.org/PersonShape",
                },
                "displayProperties": [],
            },
            {
                "target": {"class": "http://example.org/Person"},
                "displayProperties": [],
            },
        ]

        result = find_matching_rule(class_uri, shape_uri, mock_rules)

        assert result == mock_rules[1]


GROUPING_SHAPES = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix shui: <http://www.w3.org/ns/shacl-ui/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

[] a sh:ShapesGraph ;
  sh:declare [ sh:prefix "ex" ; sh:namespace "http://example.org/"^^xsd:anyURI ] .

ex:ArticleShape a sh:NodeShape ;
  sh:targetClass ex:Article ;
  sh:property [ sh:path ex:title ; sh:name "Title" ; sh:order 1 ] ;
  sh:property [
    sh:path ex:contributor ; sh:node ex:EditorShape ; sh:name "Editor" ; sh:order 3
  ] ;
  sh:property [
    sh:path ex:contributor ; sh:node ex:AuthorShape ; sh:name "Author" ; sh:order 2
  ] .

ex:AuthorShape a sh:NodeShape ;
  sh:targetClass ex:Role ;
  sh:property [ sh:path ex:withRole ; sh:hasValue ex:author ] ;
  sh:property [
    sh:path rdfs:label ;
    shui:propertyRole shui:LabelRole ;
    sh:values [
      sh:select "SELECT ?name WHERE { $this ex:heldBy/ex:name ?name }"
    ] ;
  ] .

ex:EditorShape a sh:NodeShape ;
  sh:targetClass ex:Role ;
  sh:property [ sh:path ex:withRole ; sh:hasValue ex:editor ] .
"""


def test_grouped_triples_follow_the_shapes() -> None:
    ex = "http://example.org/"
    shapes = Graph().parse(data=GROUPING_SHAPES, format="turtle")
    presentation = read_presentation(shapes)
    article, author, editor, agent = (
        URIRef(ex + name) for name in ("article", "author", "editor", "agent")
    )
    snapshot = Graph()
    for triple in [
        (article, URIRef(ex + "title"), Literal("Dune")),
        (article, URIRef(ex + "contributor"), author),
        (article, URIRef(ex + "contributor"), editor),
        (author, RDF.type, URIRef(ex + "Role")),
        (author, URIRef(ex + "withRole"), URIRef(ex + "author")),
        (author, URIRef(ex + "heldBy"), agent),
        (agent, URIRef(ex + "name"), Literal("Frank Herbert")),
        (editor, RDF.type, URIRef(ex + "Role")),
        (editor, URIRef(ex + "withRole"), URIRef(ex + "editor")),
    ]:
        snapshot.add(triple)
    entity_key = (ex + "Article", ex + "ArticleShape")
    form_fields = {
        entity_key: {
            ex + "contributor": [
                {
                    "nodeShape": ex + "AuthorShape",
                    "detailsViewer": True,
                    "nestedShape": [
                        {
                            "uri": ex + "withRole",
                            "displayName": "Role",
                            "hidden": False,
                            "nodeShapes": [],
                            "entityType": ex + "Role",
                            "subjectShape": ex + "AuthorShape",
                        },
                        {
                            "uri": ex + "heldBy",
                            "displayName": "Held By",
                            "hidden": False,
                            "nodeShape": ex + "AgentShape",
                            "nodeShapes": [ex + "AgentShape"],
                        },
                    ],
                }
            ]
        }
    }
    rules: list[dict] = []
    module = "heritrace.utils.display_rules_utils"
    with (
        patch(f"{module}.get_presentation", return_value=presentation),
        patch(
            f"{module}.get_custom_filter",
            return_value=Filter({}, presentation, MagicMock),
        ),
        patch(f"{module}.get_form_fields", return_value=form_fields),
        patch(f"{module}.get_display_rules", return_value=rules),
        patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shapes),
        patch(
            "heritrace.utils.shacl_utils.get_presentation", return_value=presentation
        ),
    ):
        grouped, relevant = get_grouped_triples(
            article,
            list(snapshot.triples((article, None, None))),
            [ex + "title", ex + "contributor", ex + "extra"],
            historical_snapshot=snapshot,
            entity_key=entity_key,
        )

    assert relevant == {ex + "title", ex + "contributor", ex + "extra"}
    assert [
        (name, group["objectShape"])
        for name, group in grouped.items()
        if name != ex + "extra"
    ] == [
        ("Title", None),
        ("Author", ex + "AuthorShape"),
        ("Editor", ex + "EditorShape"),
    ]
    assert grouped["Title"]["triples"] == [
        {
            "object": "Dune",
            "subjectClass": ex + "Article",
            "subjectShape": ex + "ArticleShape",
            "objectShape": None,
            "triple": (str(article), ex + "title", Literal("Dune")),
        }
    ]
    assert grouped["Author"]["triples"] == [
        {
            "object": str(author),
            "subjectClass": ex + "Article",
            "subjectShape": ex + "ArticleShape",
            "objectShape": ex + "AuthorShape",
            "triple": (str(article), ex + "contributor", "Frank Herbert"),
            "external_entity": str(author),
            "details": [
                {
                    "name": "Role",
                    "values": [{"label": ex + "author", "uri": None}],
                },
                {
                    "name": "Held By",
                    "values": [{"label": str(agent), "uri": str(agent)}],
                },
            ],
        }
    ]
    assert grouped["Editor"]["triples"] == [
        {
            "object": str(editor),
            "subjectClass": ex + "Article",
            "subjectShape": ex + "ArticleShape",
            "objectShape": ex + "EditorShape",
            "triple": (str(article), ex + "contributor", editor),
        }
    ]
    assert grouped[ex + "extra"]["triples"] == []
