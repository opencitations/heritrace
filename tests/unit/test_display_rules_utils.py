"""
Tests for display_rules_utils.py
"""

from unittest.mock import MagicMock, patch
from collections import OrderedDict

import pytest
from heritrace.utils.display_rules_utils import (
    execute_historical_query,
    execute_sparql_query,
    find_matching_rule,
    get_class_priority,
    get_grouped_triples,
    get_highest_priority_class,
    get_property_order_from_rules,
    get_sortable_properties,
    is_entity_type_visible,
    process_default_property,
    process_display_rule,
    process_ordering,
    get_similarity_properties,
)
from rdflib import Graph, Literal, URIRef


@pytest.fixture
def mock_display_rules():
    """Mock display rules for testing."""
    return [
        {
            "target": {
                "class": "http://example.org/Person"
            },
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
            "target": {
                "class": "http://example.org/Document"
            },
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


class TestInitialization:
    """Test the initialization of the module."""

    def test_get_class_priority(self, monkeypatch):
        """Test that get_class_priority returns the correct priority."""
        mock_rules = [
            {"target": {"class": "http://example.org/Person"}, "priority": 10},
            {"target": {"class": "http://example.org/Organization"}, "priority": 5},
        ]

        monkeypatch.setattr(
            "heritrace.utils.display_rules_utils.get_display_rules", lambda: mock_rules
        )

        assert get_class_priority(("http://example.org/Person", None)) == 10
        assert get_class_priority(("http://example.org/Organization", None)) == 5
        assert get_class_priority(("http://example.org/Unknown", None)) == float('inf')

    def test_get_class_priority_no_rules(self, monkeypatch):
        """Test that get_class_priority returns float('inf') when there are no rules."""
        monkeypatch.setattr(
            "heritrace.utils.display_rules_utils.get_display_rules", lambda: {}
        )

        assert get_class_priority(("http://example.org/Person", None)) == float('inf')


class TestIsEntityTypeVisible:
    """Tests for is_entity_type_visible function."""

    def test_entity_type_visible_true(self, mock_display_rules):
        """Test when entity type should be displayed."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules,
        ):
            result = is_entity_type_visible(("http://example.org/Person", None))
            assert result is True

    def test_entity_type_visible_false(self, mock_display_rules):
        """Test when entity type should not be displayed."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules,
        ):
            assert is_entity_type_visible(("http://example.org/Document", None)) is False

    def test_entity_type_not_in_rules(self, mock_display_rules):
        """Test when entity type is not in display rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules,
        ):
            assert is_entity_type_visible(("http://example.org/Unknown", None)) is True

    def test_no_display_rules(self):
        """Test when there are no display rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules", return_value=None
        ):
            result = is_entity_type_visible("http://example.org/Person")
            assert result is True


class TestGetSortableProperties:
    """Tests for get_sortable_properties function."""

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_with_rules(
        self, mock_get_form_fields, mock_get_display_rules, mock_display_rules, mock_form_fields_cache
    ):
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
    ):
        """Test getting sortable properties with no display rules."""
        mock_get_display_rules.return_value = []
        mock_get_form_fields.return_value = mock_form_fields_cache
        
        result = get_sortable_properties(("http://example.org/Person", None))
        
        assert result == []

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_class_not_in_rules(
        self, mock_get_form_fields, mock_get_display_rules, mock_display_rules, mock_form_fields_cache
    ):
        """Test getting sortable properties for a class not in display rules."""
        mock_get_display_rules.return_value = mock_display_rules
        mock_get_form_fields.return_value = mock_form_fields_cache
        
        result = get_sortable_properties(("http://example.org/Unknown", None))
        
        assert result == []


    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_with_number_type_and_shape(
        self, mock_get_form_fields, mock_get_display_rules, mock_display_rules, mock_form_fields_cache
    ):
        """Test getting sortable properties with number datatype and shape."""
        modified_rules = mock_display_rules.copy()
        modified_rules[0]["target"]["shape"] = "http://example.org/PersonShape"
        modified_rules[0]["sortableBy"].append(
            {
                "property": "http://example.org/height",
                "displayName": "Height",
            }
        )
        
        modified_form_fields = mock_form_fields_cache.copy()
        modified_form_fields[("http://example.org/Person", "http://example.org/PersonShape")] = {
            "http://example.org/height": [
                {
                    "datatypes": ["http://www.w3.org/2001/XMLSchema#decimal"],
                }
            ]
        }
        
        mock_get_display_rules.return_value = modified_rules
        mock_get_form_fields.return_value = modified_form_fields

        result = get_sortable_properties(("http://example.org/Person", "http://example.org/PersonShape"))
        
        assert len(result) == 2
        number_prop = next(
            p for p in result if p["property"] == "http://example.org/height"
        )
        assert number_prop["sortType"] == "number"

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_no_form_fields(
        self, mock_get_form_fields, mock_get_display_rules, mock_display_rules
    ):
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
    ):
        """Test getting sortable properties when form fields are missing for a property."""
        mock_form_fields_cache = {"http://example.org/Person": {}}

        modified_display_rules = [
            {
                "target": {
                    "class": "http://example.org/Person"
                },
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
        mock_get_display_rules.return_value = modified_display_rules
        mock_get_form_fields.return_value = mock_form_fields_cache

        result = get_sortable_properties(("http://example.org/Person", None))

        assert len(result) == 1
        assert result[0]["property"] == "http://example.org/name"

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_with_default_sort_type(
        self, mock_get_form_fields, mock_get_display_rules, mock_form_fields_cache
    ):
        """Test getting sortable properties with default sort type."""
        modified_display_rules = [
            {
                "target": {
                    "class": "http://example.org/Person"
                },
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
        self, mock_get_form_fields, mock_get_display_rules, mock_display_rules, mock_form_fields_cache
    ):
        """Test getting sortable properties with date datatype and shape."""
        modified_rules = mock_display_rules.copy()
        modified_rules[0]["target"]["shape"] = "http://example.org/PersonShape"
        modified_rules[0]["sortableBy"].append(
            {
                "property": "http://example.org/birthDate",
                "displayName": "Birth Date",
            }
        )
        
        modified_form_fields = mock_form_fields_cache.copy()
        modified_form_fields[("http://example.org/Person", "http://example.org/PersonShape")] = {
            "http://example.org/birthDate": [
                {
                    "datatypes": ["http://www.w3.org/2001/XMLSchema#date"],
                }
            ]
        }
        
        mock_get_display_rules.return_value = modified_rules
        mock_get_form_fields.return_value = modified_form_fields

        result = get_sortable_properties(("http://example.org/Person", "http://example.org/PersonShape"))
        
        assert len(result) == 2
        date_prop = next(
            p for p in result if p["property"] == "http://example.org/birthDate"
        )
        assert date_prop["sortType"] == "date"

    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_with_boolean_type_and_shape(
        self, mock_get_form_fields, mock_get_display_rules, mock_display_rules, mock_form_fields_cache
    ):
        """Test getting sortable properties with boolean datatype and shape."""
        modified_rules = mock_display_rules.copy()
        modified_rules[0]["target"]["shape"] = "http://example.org/PersonShape"
        modified_rules[0]["sortableBy"].append(
            {
                "property": "http://example.org/isActive",
                "displayName": "Is Active",
            }
        )
        
        modified_form_fields = mock_form_fields_cache.copy()
        modified_form_fields[("http://example.org/Person", "http://example.org/PersonShape")] = {
            "http://example.org/isActive": [
                {
                    "datatypes": ["http://www.w3.org/2001/XMLSchema#boolean"],
                }
            ]
        }
        
        mock_get_display_rules.return_value = modified_rules
        mock_get_form_fields.return_value = modified_form_fields

        result = get_sortable_properties(("http://example.org/Person", "http://example.org/PersonShape"))
        
        assert len(result) == 2
        boolean_prop = next(
            p for p in result if p["property"] == "http://example.org/isActive"
        )
        assert boolean_prop["sortType"] == "boolean"


    @patch("heritrace.utils.display_rules_utils.get_display_rules")
    @patch("heritrace.utils.display_rules_utils.get_form_fields")
    def test_get_sortable_properties_with_string_type(
        self, mock_get_form_fields, mock_get_display_rules, mock_display_rules, mock_form_fields_cache
    ):
        """Test getting sortable properties with string datatype."""
        modified_rules = mock_display_rules.copy()
        modified_rules[0]["sortableBy"].append(
            {
                "property": "http://example.org/description",
                "displayName": "Description",
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
    @patch("heritrace.utils.display_rules_utils.get_class_priority")
    def test_get_highest_priority_class(self, mock_get_class_priority):
        mock_get_class_priority.side_effect = lambda entity_key: {
            ("http://example.org/Person", None): 1,
            ("http://example.org/Organization", None): 5,
            ("http://example.org/Event", None): 10,
        }.get(entity_key, 100)

        subject_classes = [
            "http://example.org/Person",
            "http://example.org/Organization",
            "http://example.org/Event",
        ]
        result = get_highest_priority_class(subject_classes)
        assert result == "http://example.org/Person"

        subject_classes = [
            "http://example.org/Event",
            "http://example.org/Organization",
            "http://example.org/Person",
        ]
        result = get_highest_priority_class(subject_classes)
        assert result == "http://example.org/Person"

    @patch("heritrace.utils.display_rules_utils.get_class_priority")
    def test_get_highest_priority_class_empty_list(self, mock_get_class_priority):
        subject_classes = []
        result = get_highest_priority_class(subject_classes)
        assert result is None

    @patch("heritrace.utils.display_rules_utils.get_class_priority")
    def test_get_highest_priority_class_same_priority(self, mock_get_class_priority):
        mock_get_class_priority.return_value = 5

        subject_classes = [
            "http://example.org/Person",
            "http://example.org/Organization",
        ]
        result = get_highest_priority_class(subject_classes)
        assert result == "http://example.org/Person"  # First one should be returned


class TestGetGroupedTriples:
    """Tests for get_grouped_triples function."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_triples, mock_subject_classes, mock_valid_predicates_info, mock_form_fields_cache):
        """Setup common mocks for all test methods."""
        self.highest_priority_class = URIRef("http://example.org/Person")
        self.subject_shape = "http://example.org/PersonShape"
        
        self.get_display_rules_patch = patch(
            "heritrace.utils.display_rules_utils.get_display_rules"
        )
        self.mock_get_display_rules = self.get_display_rules_patch.start()
        
        self.get_form_fields_patch = patch(
            "heritrace.utils.display_rules_utils.get_form_fields"
        )
        self.mock_get_form_fields = self.get_form_fields_patch.start()
        
        self.get_highest_priority_class_patch = patch(
            "heritrace.utils.display_rules_utils.get_highest_priority_class",
            return_value=self.highest_priority_class
        )
        self.mock_get_highest_priority_class = self.get_highest_priority_class_patch.start()
        
        self.determine_shape_for_classes_patch = patch(
            "heritrace.utils.shacl_utils.determine_shape_for_classes",
            return_value=self.subject_shape
        )
        self.mock_determine_shape_for_classes = self.determine_shape_for_classes_patch.start()
        
        self.find_matching_rule_patch = patch(
            "heritrace.utils.display_rules_utils.find_matching_rule",
            return_value={
                "target": {"class": "http://example.org/Person", "shape": "http://example.org/PersonShape"},
                "displayProperties": [
                    {
                        "property": "http://example.org/name",
                        "displayName": "Name",
                    },
                    {
                        "property": "http://example.org/age",
                        "displayName": "Age",
                    },
                    {
                        "property": "http://example.org/knows",
                        "displayName": "Knows",
                        "intermediateRelation": {"class": "http://example.org/Relationship"},
                    },
                    {
                        "property": "http://example.org/simple",
                        "displayName": "Simple Property",
                        "intermediateRelation": {"class": "http://example.org/SimpleRelationship"},
                    }
                ],
                "priority": 1,
                "shouldBeDisplayed": True
            }
        )
        self.mock_find_matching_rule = self.find_matching_rule_patch.start()
        
        self.mock_display_rules = [
            {
                "target": {"class": "http://example.org/Person", "shape": "http://example.org/PersonShape"},
                "displayProperties": [
                    {
                        "property": "http://example.org/name",
                        "displayName": "Name",
                        "displayRules": [
                            {
                                "displayName": "Person Name",
                                "fetchValueFromQuery": "SELECT ?label WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label }"
                            }
                        ]
                    },
                    {
                        "property": "http://example.org/age",
                        "displayName": "Age",
                        "displayRules": [
                            {
                                "displayName": "Person Age"
                            }
                        ]
                    },
                    {
                        "property": "http://example.org/knows",
                        "displayName": "Knows",
                        "displayRules": [
                            {
                                "displayName": "Person Knows",
                                "fetchValueFromQuery": "SELECT ?label WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label }"
                            }
                        ]
                    }
                ],
                "priority": 1,
                "shouldBeDisplayed": True
            }
        ]
        self.mock_get_display_rules.return_value = self.mock_display_rules
        
        self.mock_find_matching_rule.return_value = {
            "target": {"class": "http://example.org/Person", "shape": "http://example.org/PersonShape"},
            "displayProperties": [],
            "priority": 1,
            "shouldBeDisplayed": True
        }
        
        self.mock_form_fields = {
            (self.highest_priority_class, self.subject_shape): {
                "http://example.org/name": [
                    {"nodeShape": "http://example.org/PersonShape"}
                ],
                "http://example.org/age": [
                    {"nodeShape": None}
                ],
                "http://example.org/knows": [
                    {"nodeShape": "http://example.org/PersonShape"}
                ],
                "http://example.org/simple": [
                    {"nodeShape": "http://example.org/SimpleShape"}
                ]
            }
        }
        self.mock_get_form_fields.return_value = self.mock_form_fields
        
        self.mock_display_rules[0]["displayProperties"].extend([
            {
                "property": "http://example.org/knows",
                "displayName": "Knows",
                "orderedBy": "http://example.org/order",
                "intermediateRelation": {
                    "class": "http://example.org/Relationship"
                }
            },
            {
                "property": "http://example.org/simple",
                "displayName": "Simple Property",
                "intermediateRelation": {
                    "class": "http://example.org/SimpleRelationship"
                },
                "shape": "http://example.org/SimpleShape"
            }
        ])
        
        yield
        
        self.get_display_rules_patch.stop()
        self.get_form_fields_patch.stop()
        self.get_highest_priority_class_patch.stop()
        self.determine_shape_for_classes_patch.stop()
        self.find_matching_rule_patch.stop()

    def test_get_grouped_triples_with_rules(
        self,
        mock_triples,
        mock_valid_predicates_info,
    ):
        """Test getting grouped triples with display rules."""
        
        self.mock_find_matching_rule.return_value = {
            "target": {"class": "http://example.org/Person", "shape": "http://example.org/PersonShape"},
            "displayProperties": [
                {
                    "property": "http://example.org/name",
                    "displayName": "Name",
                    "displayRules": [
                        {
                            "displayName": "Person Name",
                        }
                    ]
                },
                {
                    "property": "http://example.org/age",
                    "displayName": "Age",
                    "displayRules": [
                        {
                            "displayName": "Person Age",
                        }
                    ]
                },
                {
                    "property": "http://example.org/knows",
                    "displayName": "Knows",
                    "displayRules": [
                        {
                            "displayName": "Person Knows",
                        }
                    ]
                }
            ],
            "priority": 1,
            "shouldBeDisplayed": True
        }
        
        
        with patch(
            "heritrace.utils.display_rules_utils.process_default_property"
        ) as mock_process_default_property:
            
            grouped_triples = OrderedDict()
            relevant_properties = set(["http://example.org/name", "http://example.org/age", "http://example.org/knows"])
            
            grouped_triples["Person Name"] = {
                "property": "http://example.org/name",
                "triples": [{"triple": ("http://example.org/person1", "http://example.org/name", "mock_value")}],
                "subjectShape": "http://example.org/PersonShape",
                "objectShape": None,
            }
            grouped_triples["Person Age"] = {
                "property": "http://example.org/age",
                "triples": [{"triple": ("http://example.org/person1", "http://example.org/age", "mock_value")}],
                "subjectShape": "http://example.org/PersonShape",
                "objectShape": None,
            }
            grouped_triples["Person Knows"] = {
                "property": "http://example.org/knows",
                "triples": [{"triple": ("http://example.org/person1", "http://example.org/knows", "mock_value")}],
                "subjectShape": "http://example.org/PersonShape",
                "objectShape": None,
            }
            
            assert isinstance(grouped_triples, dict)
            
            assert "Person Name" in grouped_triples
            assert "Person Age" in grouped_triples
            assert "Person Knows" in grouped_triples
            
            assert "http://example.org/name" in relevant_properties
            assert "http://example.org/age" in relevant_properties
            assert "http://example.org/knows" in relevant_properties

    def test_get_grouped_triples_no_rules(
        self, mock_triples, mock_valid_predicates_info
    ):
        """Test getting grouped triples with no display rules."""
        self.get_display_rules_patch.return_value = []
        
        def mock_process_default_property(prop_uri, triples, grouped_triples, subject_shape=None):
            display_name = prop_uri.split("/")[-1]
            if display_name not in grouped_triples:
                grouped_triples[display_name] = {
                    "property": prop_uri,
                    "triples": [{"triple": ("http://example.org/person1", prop_uri, "mock_value")}],
                    "subjectShape": self.subject_shape,
                    "objectShape": None,
                }

        with patch(
            "heritrace.utils.display_rules_utils.process_default_property",
            side_effect=mock_process_default_property,
        ):
            result = get_grouped_triples(
                "http://example.org/person1",
                mock_triples,
                mock_valid_predicates_info,
                highest_priority_class=self.highest_priority_class
            )
            grouped_triples, relevant_properties = result
            assert isinstance(grouped_triples, dict)
            assert isinstance(relevant_properties, set)
            assert len(grouped_triples) > 0
            # Verify bug fix: relevant_properties should contain all valid predicates when no rules exist
            assert relevant_properties == set(mock_valid_predicates_info), \
                f"Expected all valid predicates in relevant_properties, got {relevant_properties}"

    def test_get_grouped_triples_no_matching_rule(
        self, mock_triples, mock_valid_predicates_info
    ):
        """Test getting grouped triples when display rules exist but no rule matches the entity class/shape."""
        # Set up display rules for a different class that won't match
        self.get_display_rules_patch.return_value = [
            {
                "target": {
                    "class": "http://example.org/DifferentClass"
                },
                "priority": 1,
                "shouldBeDisplayed": True,
                "displayProperties": [
                    {
                        "property": "http://example.org/differentProperty",
                        "displayName": "Different Property"
                    }
                ]
            }
        ]
        
        # Mock find_matching_rule to return None (no matching rule)
        self.mock_find_matching_rule.return_value = None
        
        def mock_process_default_property(prop_uri, triples, grouped_triples, subject_shape=None):
            display_name = prop_uri.split("/")[-1]
            if display_name not in grouped_triples:
                grouped_triples[display_name] = {
                    "property": prop_uri,
                    "triples": [{"triple": ("http://example.org/person1", prop_uri, "mock_value")}],
                    "subjectShape": self.subject_shape,
                    "objectShape": None,
                }

        with patch(
            "heritrace.utils.display_rules_utils.process_default_property",
            side_effect=mock_process_default_property,
        ):
            result = get_grouped_triples(
                "http://example.org/person1",
                mock_triples,
                mock_valid_predicates_info,
                highest_priority_class=self.highest_priority_class
            )
            grouped_triples, relevant_properties = result
            assert isinstance(grouped_triples, dict)
            assert isinstance(relevant_properties, set)
            assert len(grouped_triples) > 0
            # Verify bug fix: relevant_properties should contain all valid predicates when no matching rule exists
            assert relevant_properties == set(mock_valid_predicates_info), \
                f"Expected all valid predicates in relevant_properties, got {relevant_properties}"

    def test_type_consistency_for_filtering_in_entity_about(
        self, mock_triples, mock_valid_predicates_info
    ):
        """Test that verifies type consistency between can_be_added/can_be_deleted and relevant_properties.
        
        This test simulates the scenario in entity.py where can_be_added and can_be_deleted 
        are filtered by relevant_properties. Both should contain the same data types (strings)
        to ensure the filtering works correctly.
        """
        # Simulate no display rules (the scenario where the bug occurred)
        self.get_display_rules_patch.return_value = []
        
        def mock_process_default_property(prop_uri, triples, grouped_triples, subject_shape=None):
            display_name = prop_uri.split("/")[-1]
            if display_name not in grouped_triples:
                grouped_triples[display_name] = {
                    "property": prop_uri,
                    "triples": [{"triple": ("http://example.org/person1", prop_uri, "mock_value")}],
                    "subjectShape": self.subject_shape,
                    "objectShape": None,
                }

        with patch(
            "heritrace.utils.display_rules_utils.process_default_property",
            side_effect=mock_process_default_property,
        ):
            result = get_grouped_triples(
                "http://example.org/person1",
                mock_triples,
                mock_valid_predicates_info,
                highest_priority_class=self.highest_priority_class
            )
            grouped_triples, relevant_properties = result
            
            # Simulate the filtering that happens in entity.py
            # This would fail before the fix due to type mismatch
            mock_can_be_added = mock_valid_predicates_info.copy()  # These are strings
            mock_can_be_deleted = mock_valid_predicates_info.copy()  # These are strings
            
            # This filtering should work because both are strings now
            filtered_can_be_added = [uri for uri in mock_can_be_added if uri in relevant_properties]
            filtered_can_be_deleted = [uri for uri in mock_can_be_deleted if uri in relevant_properties]
            
            # Verify the filtering works correctly
            assert filtered_can_be_added == mock_valid_predicates_info, \
                f"Filtering failed for can_be_added: {filtered_can_be_added} != {mock_valid_predicates_info}"
            assert filtered_can_be_deleted == mock_valid_predicates_info, \
                f"Filtering failed for can_be_deleted: {filtered_can_be_deleted} != {mock_valid_predicates_info}"
            
            # Verify all items in relevant_properties are strings
            assert all(isinstance(prop, str) for prop in relevant_properties), \
                f"relevant_properties should contain only strings, got: {[type(prop) for prop in relevant_properties]}"

    def test_get_grouped_triples_with_intermediate_relation(
        self,
        mock_triples,
        mock_valid_predicates_info,
    ):
        """Test getting grouped triples with intermediate relation."""
        self.mock_find_matching_rule.return_value = {
            "target": {"class": "http://example.org/Person", "shape": "http://example.org/PersonShape"},
            "displayProperties": [
                {
                    "property": "http://example.org/knows",
                    "displayName": "Knows",
                    "intermediateRelation": {"class": "http://example.org/Relationship"},
                    "shape": "http://example.org/PersonShape",
                    "displayRules": [
                        {
                            "displayName": "Person Knows",
                            "intermediateRelation": {"class": "http://example.org/Relationship"}
                        }
                    ]
                }
            ],
            "priority": 1,
            "shouldBeDisplayed": True,
        }
        
        def mock_process_default_property(prop_uri, triples, grouped_triples, subject_shape=None):
            if prop_uri == "http://example.org/knows":
                display_name = "Knows"
                if display_name not in grouped_triples:
                    grouped_triples[display_name] = {
                        "property": prop_uri,
                        "triples": [{"triple": ("http://example.org/person1", prop_uri, "mock_value")}],
                        "subjectShape": subject_shape,
                        "objectShape": "http://example.org/PersonShape",
                        "intermediateRelation": {"class": "http://example.org/Relationship"},
                    }
        
        with patch(
            "heritrace.utils.display_rules_utils.process_display_rule"
        ) as mock_process_display_rule, patch(
            "heritrace.utils.display_rules_utils.process_default_property",
            side_effect=mock_process_default_property
        ) as mock_process_default_property:
            result = get_grouped_triples(
                "http://example.org/person1",
                mock_triples,
                mock_valid_predicates_info,
                highest_priority_class=self.highest_priority_class
            )
            
            grouped_triples, relevant_properties = result
            
            assert isinstance(grouped_triples, dict)
            assert isinstance(relevant_properties, set)
            
            assert mock_process_default_property.called
            
            assert "Person Knows" in grouped_triples
            assert grouped_triples["Person Knows"]["intermediateRelation"] == {"class": "http://example.org/Relationship"}
            
            assert "http://example.org/knows" in relevant_properties
            

    def test_top_level_intermediate_relation_condition(self,
        mock_triples,
        mock_valid_predicates_info,
    ):
        """Test the 'intermediateRelation' condition in top-level display rules with fetchValueFromQuery."""
        self.mock_find_matching_rule.return_value = {
            "target": {"class": "http://example.org/Person", "shape": "http://example.org/PersonShape"},
            "displayProperties": [
                {
                    "displayName": "Knows",
                    "property": "http://example.org/knows",
                    "intermediateRelation": {"class": "http://example.org/Relationship"},
                    "fetchValueFromQuery": "SELECT ?label WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label }",
                }
            ],
            "priority": 1,
            "shouldBeDisplayed": True,
        }

        def mock_execute_sparql_query(query, subject, value):
            return "Label for " + str(value), None

        def mock_process_default_property(prop_uri, triples, grouped_triples, subject_shape=None):
            if prop_uri == "http://example.org/knows":
                display_name = "Knows"
                if display_name not in grouped_triples:
                    grouped_triples[display_name] = {
                        "property": prop_uri,
                        "triples": [{"triple": ("http://example.org/person1", prop_uri, "mock_value")}],
                        "subjectShape": subject_shape,
                        "objectShape": None,
                        "intermediateRelation": {"class": "http://example.org/Relationship"},
                    }

        with patch(
            "heritrace.utils.display_rules_utils.execute_sparql_query",
            side_effect=mock_execute_sparql_query
        ), patch(
            "heritrace.utils.display_rules_utils.process_default_property",
            side_effect=mock_process_default_property
        ) as mock_process_default_property:
            grouped_triples, relevant_properties = get_grouped_triples(
                "http://example.org/person1",
                mock_triples,
                mock_valid_predicates_info,
                highest_priority_class=URIRef("http://example.org/Person")
            )

            assert mock_process_default_property.called
            
            assert "Knows" in grouped_triples
            assert grouped_triples["Knows"]["intermediateRelation"] == {"class": "http://example.org/Relationship"}
            assert grouped_triples["Knows"]["property"] == "http://example.org/knows"
            assert "triples" in grouped_triples["Knows"]
                
    def test_nested_intermediate_relation_condition(
        self,
        mock_triples,
        mock_valid_predicates_info,
    ):
        """Test the 'intermediateRelation' condition in nested display rules."""
        self.mock_find_matching_rule.return_value = {
            "target": {"class": "http://example.org/Person", "shape": "http://example.org/PersonShape"},
            "displayProperties": [
                {
                    "property": "http://example.org/knows",
                    "displayName": "Knows",
                    "displayRules": [
                        {
                            "displayName": "Knows (with relationship)",
                            "fetchValueFromQuery": "SELECT ?label ?entity WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label . BIND([[value]] AS ?entity) }",
                            "intermediateRelation": {"class": "http://example.org/Relationship"}
                        }
                    ],
                    "shape": "http://example.org/PersonShape"
                }
            ],
            "priority": 1,
            "shouldBeDisplayed": True,
        }

        def mock_process_default_property(prop_uri, triples, grouped_triples, subject_shape=None):
            if prop_uri == "http://example.org/knows":
                display_name = "Knows (with relationship)"
                if display_name not in grouped_triples:
                    grouped_triples[display_name] = {
                        "property": prop_uri,
                        "triples": [{"triple": ("http://example.org/person1", prop_uri, "mock_value")}],
                        "subjectShape": subject_shape,
                        "objectShape": "http://example.org/PersonShape",
                        "intermediateRelation": {"class": "http://example.org/Relationship"},
                    }

        def mock_execute_sparql_query(query, subject, value):
            return "Label for " + str(value), str(value)

        with patch(
            "heritrace.utils.display_rules_utils.execute_sparql_query",
            side_effect=mock_execute_sparql_query
        ), patch(
            "heritrace.utils.display_rules_utils.process_default_property",
            side_effect=mock_process_default_property
        ) as mock_process_default_property:
            grouped_triples, relevant_properties = get_grouped_triples(
                "http://example.org/person1",
                mock_triples,
                mock_valid_predicates_info,
                highest_priority_class=self.highest_priority_class
            )

            assert mock_process_default_property.called
            
            assert "Knows (with relationship)" in grouped_triples
            assert grouped_triples["Knows (with relationship)"]["intermediateRelation"] == {"class": "http://example.org/Relationship"}

    def test_inherited_intermediate_relation_condition(
        self,
        mock_triples,
        mock_valid_predicates_info,
    ):
        """Test the 'intermediateRelation' condition when inherited from parent property."""
        self.mock_find_matching_rule.return_value = {
            "target": {"class": "http://example.org/Person", "shape": "http://example.org/PersonShape"},
            "displayProperties": [
                {
                    "property": "http://example.org/knows",
                    "displayName": "Knows",
                    "intermediateRelation": {"class": "http://example.org/Relationship"},
                    "displayRules": [
                        {
                            "displayName": "Knows (with inherited relationship)",
                            "fetchValueFromQuery": "SELECT ?label ?entity WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label . BIND([[value]] AS ?entity) }",
                            "shape": "http://example.org/PersonShape"
                        }
                    ]
                }
            ],
            "priority": 1,
            "shouldBeDisplayed": True,
        }

        def mock_process_default_property(prop_uri, triples, grouped_triples, subject_shape=None):
            if prop_uri == "http://example.org/knows":
                display_name = "Knows (with inherited relationship)"
                if display_name not in grouped_triples:
                    grouped_triples[display_name] = {
                        "property": prop_uri,
                        "triples": [{"triple": ("http://example.org/person1", prop_uri, "mock_value")}],
                        "subjectShape": subject_shape,
                        "objectShape": "http://example.org/PersonShape",
                        "intermediateRelation": {"class": "http://example.org/Relationship"},
                    }

        def mock_execute_sparql_query(query, subject, value):
            return "Label for " + str(value), str(value)

        with patch(
            "heritrace.utils.display_rules_utils.execute_sparql_query",
            side_effect=mock_execute_sparql_query
        ), patch(
            "heritrace.utils.display_rules_utils.process_default_property",
            side_effect=mock_process_default_property
        ) as mock_process_default_property:
            grouped_triples, relevant_properties = get_grouped_triples(
                "http://example.org/person1",
                mock_triples,
                mock_valid_predicates_info,
                highest_priority_class=self.highest_priority_class
            )

            assert mock_process_default_property.called
            
            assert "Knows (with inherited relationship)" in grouped_triples
            assert grouped_triples["Knows (with inherited relationship)"]["intermediateRelation"] == {"class": "http://example.org/Relationship"}
            assert grouped_triples["Knows (with inherited relationship)"]["property"] == "http://example.org/knows"

    def test_simple_display_name_with_ordered_by(
        self,
        mock_triples,
        mock_valid_predicates_info,
    ):
        """Test the 'orderedBy' condition in simple display name section."""
        simple_ordered_rules = [
            {
                "target": {
                    "class": "http://example.org/Person"
                },
                "displayProperties": [
                    {
                        "displayName": "Simple Property",
                        "property": "http://example.org/simple",
                        "orderedBy": "http://example.org/order",
                        "shape": "http://example.org/SimpleShape"
                    }
                ],
                "priority": 1,
                "shouldBeDisplayed": True,
            }
        ]
        
        extended_predicates_info = mock_valid_predicates_info + ["http://example.org/simple"]
        
        def mock_process_display_rule(*args, **kwargs):
            pass
        
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=simple_ordered_rules,
        ):
            with patch(
                "heritrace.utils.display_rules_utils.get_highest_priority_class",
                return_value=URIRef("http://example.org/Person"),
            ):
                with patch(
                    "heritrace.utils.display_rules_utils.process_display_rule",
                    side_effect=mock_process_display_rule,
                ):
                    with patch("heritrace.utils.display_rules_utils.process_ordering"):
                        grouped_triples, relevant_properties = get_grouped_triples(
                            "http://example.org/person1",
                            mock_triples,
                            extended_predicates_info,
                            highest_priority_class=URIRef("http://example.org/Person")
                        )

                        assert "http://example.org/simple" in grouped_triples
                        prop_data = grouped_triples["http://example.org/simple"]
                        assert prop_data["property"] == "http://example.org/simple"
                        
    def test_simple_display_name_with_intermediate_relation(
        self,
        mock_triples,
        mock_valid_predicates_info,
    ):
        """Test the 'intermediateRelation' condition in simple display name section."""
        self.mock_find_matching_rule.return_value = {
            "target": {"class": "http://example.org/Person", "shape": "http://example.org/PersonShape"},
            "displayProperties": [
                {
                    "displayName": "Simple Property",
                    "property": "http://example.org/simple",
                    "intermediateRelation": {"class": "http://example.org/SimpleRelationship"},
                    "shape": "http://example.org/SimpleShape"
                }
            ],
            "priority": 1,
            "shouldBeDisplayed": True
        }

        extended_predicates_info = mock_valid_predicates_info + ["http://example.org/simple"]

        def mock_process_default_property(prop_uri, triples, grouped_triples, subject_shape=None):
            if prop_uri == "http://example.org/simple":
                display_name = "Simple Property"
                if display_name not in grouped_triples:
                    grouped_triples[display_name] = {
                        "property": prop_uri,
                        "triples": [{"triple": ("http://example.org/person1", prop_uri, "mock_value")}],
                        "subjectShape": subject_shape,
                        "objectShape": "http://example.org/SimpleShape",
                        "intermediateRelation": {"class": "http://example.org/SimpleRelationship"},
                    }

        with patch(
            "heritrace.utils.display_rules_utils.process_default_property",
            side_effect=mock_process_default_property
        ) as mock_process_default_property:
            result = get_grouped_triples(
                "http://example.org/person1",
                mock_triples,
                extended_predicates_info,
                highest_priority_class=self.highest_priority_class
            )

            assert mock_process_default_property.called
            
            grouped_triples, relevant_properties = result
            
            assert "Simple Property" in grouped_triples
            assert grouped_triples["Simple Property"]["property"] == "http://example.org/simple"
            assert grouped_triples["Simple Property"]["intermediateRelation"] == {"class": "http://example.org/SimpleRelationship"}
            
            assert "http://example.org/simple" in relevant_properties

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
        subject_shape = "http://example.org/PersonShape"

        with patch(
            "heritrace.utils.display_rules_utils.execute_sparql_query",
            return_value=("John Doe", "http://example.org/name1"),
        ):
            with patch(
                "heritrace.utils.shacl_utils.determine_shape_for_classes",
                return_value=subject_shape,
            ):
                process_display_rule(
                    display_name,
                    prop_uri,
                    rule,
                    subject,
                    mock_triples,
                    grouped_triples,
                    fetched_values_map,
                    subject_shape=subject_shape,
                    object_shape=rule["shape"]
                )

            assert display_name in grouped_triples
            assert len(grouped_triples[display_name]["triples"]) == 1
            assert grouped_triples[display_name]["property"] == prop_uri
            assert grouped_triples[display_name]["objectShape"] == "http://example.org/PersonShape"
            assert grouped_triples[display_name]["subjectShape"] == subject_shape
            assert grouped_triples[display_name]["triples"][0]["triple"][2] == "John Doe"
            assert fetched_values_map.get("John Doe") == "http://example.org/name1"

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
            with patch(
                "heritrace.utils.shacl_utils.determine_shape_for_classes",
                return_value="http://example.org/PersonShape",
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

    def test_process_display_rule_without_fetch_value(self, app):
        """Test processing display rule without fetchValueFromQuery."""
        display_name = "Age"
        prop_uri = "http://example.org/age"
        rule = {
            "shape": "http://example.org/AgeShape",
        }
        subject = "http://example.org/person1"
        grouped_triples = {}
        fetched_values_map = {}
        subject_shape = "http://example.org/AgeShape"
        object_shape = "http://example.org/AgeShape"

        test_triples = [
            (
                URIRef("http://example.org/person1"),
                URIRef("http://example.org/age"),
                URIRef("http://example.org/age1"),
            )
        ]

        with app.app_context():
            with patch(
                "heritrace.utils.shacl_utils.determine_shape_for_classes",
                return_value=subject_shape,
            ):
                process_display_rule(
                    display_name,
                    prop_uri,
                    rule,
                    subject,
                    test_triples,
                    grouped_triples,
                    fetched_values_map,
                    subject_shape=subject_shape,
                    object_shape=object_shape
                )

        assert display_name in grouped_triples
        assert len(grouped_triples[display_name]["triples"]) == 1
        assert grouped_triples[display_name]["property"] == prop_uri
        assert grouped_triples[display_name]["objectShape"] == object_shape
        assert grouped_triples[display_name]["subjectShape"] == subject_shape
        assert str(grouped_triples[display_name]["triples"][0]["triple"][2]) == "http://example.org/age1"

    def test_current_prop_config_orderedby_without_display_rules(
        self,
        mock_triples,
        mock_valid_predicates_info,
    ):
        """Test orderedBy in current_prop_config without displayRules."""
        self.mock_find_matching_rule.return_value = {
            "target": {"class": "http://example.org/Person"},
            "displayProperties": [
                {
                    "property": "http://example.org/ordered_prop",
                    "displayName": "Ordered Property",
                    "orderedBy": "http://example.org/order_prop",
                    "shape": "http://example.org/OrderedShape"
                }
            ],
            "priority": 1,
            "shouldBeDisplayed": True
        }

        extended_predicates_info = mock_valid_predicates_info + ["http://example.org/ordered_prop"]
        
        with patch("heritrace.utils.display_rules_utils.process_display_rule"), \
             patch("heritrace.utils.display_rules_utils.process_ordering"):
            
            grouped_triples, relevant_properties = get_grouped_triples(
                "http://example.org/person1",
                mock_triples,
                extended_predicates_info,
                highest_priority_class=self.highest_priority_class
            )

            assert "Ordered Property" in grouped_triples
            ordered_prop = grouped_triples["Ordered Property"]
            assert ordered_prop["property"] == "http://example.org/ordered_prop"
            assert ordered_prop["is_draggable"] is True
            assert ordered_prop["ordered_by"] == "http://example.org/order_prop"

    def test_current_prop_config_intermediate_relation_without_display_rules(
        self,
        mock_triples,
        mock_valid_predicates_info,
    ):
        """Test intermediateRelation in current_prop_config without displayRules."""
        self.mock_find_matching_rule.return_value = {
            "target": {"class": "http://example.org/Person"},
            "displayProperties": [
                {
                    "property": "http://example.org/related_prop",
                    "displayName": "Related Property",
                    "intermediateRelation": {"class": "http://example.org/IntermediateClass"},
                    "shape": "http://example.org/RelatedShape"
                }
            ],
            "priority": 1,
            "shouldBeDisplayed": True
        }

        extended_predicates_info = mock_valid_predicates_info + ["http://example.org/related_prop"]
        
        with patch("heritrace.utils.display_rules_utils.process_display_rule"):
            
            grouped_triples, relevant_properties = get_grouped_triples(
                "http://example.org/person1",
                mock_triples,
                extended_predicates_info,
                highest_priority_class=self.highest_priority_class
            )

            assert "Related Property" in grouped_triples
            related_prop = grouped_triples["Related Property"]
            assert related_prop["property"] == "http://example.org/related_prop"
            assert related_prop["intermediateRelation"] == {"class": "http://example.org/IntermediateClass"}

    def test_no_current_prop_config_calls_process_default_property(
        self,
        mock_triples,
        mock_valid_predicates_info,
    ):
        """Test that process_default_property is called when current_prop_config is None."""
        self.mock_find_matching_rule.return_value = {
            "target": {"class": "http://example.org/Person"},
            "displayProperties": [
                {
                    "property": "http://example.org/other_prop",
                    "displayName": "Other Property"
                }
            ],
            "priority": 1,
            "shouldBeDisplayed": True
        }

        extended_predicates_info = mock_valid_predicates_info + ["http://example.org/unknown_prop"]
        
        with patch("heritrace.utils.display_rules_utils.process_default_property") as mock_process_default:
            
            grouped_triples, relevant_properties = get_grouped_triples(
                "http://example.org/person1",
                mock_triples,
                extended_predicates_info,
                highest_priority_class=self.highest_priority_class
            )

            mock_process_default.assert_called()
            call_args_list = mock_process_default.call_args_list
            unknown_prop_calls = [call for call in call_args_list if call[0][0] == "http://example.org/unknown_prop"]
            assert len(unknown_prop_calls) > 0, "process_default_property should be called for unknown_prop"

    def test_no_display_rules_calls_process_default_property(
        self,
        mock_triples,
        mock_valid_predicates_info,
    ):
        """Test that process_default_property is called when there are no display rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=[]
        ), patch(
            "heritrace.utils.display_rules_utils.process_default_property"
        ) as mock_process_default:
            
            grouped_triples, relevant_properties = get_grouped_triples(
                "http://example.org/person1",
                mock_triples,
                mock_valid_predicates_info,
                highest_priority_class=self.highest_priority_class
            )

            mock_process_default.assert_called()
            assert mock_process_default.call_count >= len(mock_valid_predicates_info)

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
        assert grouped_triples[prop_uri]["objectShape"] is None


class TestExecuteHistoricalQuery:
    """Tests for execute_historical_query function."""

    def test_execute_historical_query_with_results(self, mock_historical_snapshot):
        """Test executing historical query with results."""
        query = "SELECT ?label ?entity WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label . BIND([[value]] AS ?entity) }"
        subject = "http://example.org/person1"
        value = "http://example.org/name1"

        mock_historical_snapshot.add(
            (
                URIRef(value),
                URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
                Literal("John Doe"),
            )
        )

        original_query = mock_historical_snapshot.query

        def mock_query(q):
            return [(Literal("John Doe"), URIRef(value))]

        mock_historical_snapshot.query = mock_query

        result, external_entity = execute_historical_query(
            query, subject, value, mock_historical_snapshot
        )

        assert result == "John Doe"
        assert external_entity == value

        mock_historical_snapshot.query = original_query

    def test_execute_historical_query_no_results(self, mock_historical_snapshot):
        """Test executing historical query with no results."""
        query = "SELECT ?label ?entity WHERE { [[value]] <http://www.w3.org/2000/01/rdf-schema#label> ?label . BIND([[value]] AS ?entity) }"
        subject = "http://example.org/person1"
        value = "http://example.org/unknown"

        original_query = mock_historical_snapshot.query
        mock_historical_snapshot.query = lambda q: []

        result, external_entity = execute_historical_query(
            query, subject, value, mock_historical_snapshot
        )

        assert result is None
        assert external_entity is None

        mock_historical_snapshot.query = original_query


class TestGetPropertyOrderFromRules:
    """Tests for get_property_order_from_rules function."""

    def test_get_property_order_from_rules(
        self, mock_display_rules, mock_subject_classes
    ):
        """Test getting property order from rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules
        ):
            result = get_property_order_from_rules(
                "http://example.org/Person"
            )

            assert len(result) == 3
            assert result[0] == "http://example.org/name"
            assert result[1] == "http://example.org/age"
            assert result[2] == "http://example.org/knows"

    def test_get_property_order_from_rules_no_matching_class(self, mock_display_rules):
        """Test getting property order from rules with no matching class."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules
        ):
            result = get_property_order_from_rules(
                "http://example.org/Unknown"
            )

            assert result == []

    def test_get_property_order_from_rules_no_rules(self, mock_subject_classes):
        """Test getting property order from rules with no rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=[]
        ):
            result = get_property_order_from_rules("http://example.org/Person")

            assert result == []

    def test_get_property_order_from_rules_no_highest_priority_class(
        self, mock_display_rules
    ):
        """Test getting property order from rules with no highest priority class."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules
        ):
            result = get_property_order_from_rules(None)

            assert result == []

    def test_get_property_order_from_rules_with_ordered_display_names(self):
        """Test getting property order from rules with ordered display names."""
        mock_display_rules = [
            {
                "target": {
                    "class": "http://example.org/Person"
                },
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

        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules,
        ):
            ordered_properties = get_property_order_from_rules(
                "http://example.org/Person"
            )

            assert "http://example.org/name" in ordered_properties
            assert "http://example.org/age" in ordered_properties

    def test_get_property_order_from_rules_with_shape_uri(self):
        """Test getting property order from rules when shape_uri is provided."""
        mock_display_rules = [
            {
                "target": {
                    "class": "http://example.org/Person",
                    "shape": "http://example.org/PersonShape"
                },
                "displayProperties": [
                    {
                        "displayName": "Full Name",
                        "property": "http://example.org/fullName",
                    },
                    {
                        "displayName": "Birth Date",
                        "property": "http://example.org/birthDate",
                    },
                    {
                        "displayName": "Email",
                        "property": "http://example.org/email",
                    },
                ],
            },
            {
                "target": {
                    "class": "http://example.org/Person"
                },
                "displayProperties": [
                    {
                        "displayName": "Name",
                        "property": "http://example.org/name",
                    },
                    {
                        "displayName": "Age",
                        "property": "http://example.org/age",
                    },
                ],
            },
        ]
        
        shape_uri = "http://example.org/PersonShape"

        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules
        ):
            ordered_properties = get_property_order_from_rules(
                "http://example.org/Person", shape_uri
            )

            assert len(ordered_properties) == 3
            assert ordered_properties[0] == "http://example.org/fullName"
            assert ordered_properties[1] == "http://example.org/birthDate"
            assert ordered_properties[2] == "http://example.org/email"
            
            assert "http://example.org/name" not in ordered_properties
            assert "http://example.org/age" not in ordered_properties


class TestGetSimilarityProperties:
    """Tests for get_similarity_properties function."""

    @pytest.fixture
    def mock_display_rules_with_similarity(self):
        """Mock display rules with similarity_properties."""
        return [
            {
                "target": {
                    "class": "http://example.org/Person"
                },
                "priority": 1,
                "similarity_properties": [
                    "http://example.org/name",
                    "http://example.org/email",
                ],
            },
            {
                "target": {
                    "class": "http://example.org/Organization"
                },
                "priority": 2,
                "similarity_properties": [],  # Empty list
            },
            {
                "target": {
                    "class": "http://example.org/Document"
                },
                "priority": 3,
            },
            {
                "target": {
                    "class": "http://example.org/Event"
                },
                "priority": 4,
                "similarity_properties": "not a list",  # Invalid format
            },
             {
                "target": {
                    "class": "http://example.org/Place"
                },
                "priority": 5,
                "similarity_properties": ["prop1", 123],  # Invalid item type
            },
        ]

    def test_get_similarity_properties_found(self, mock_display_rules_with_similarity):
        """Test when similarity_properties are found and valid."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules_with_similarity,
        ):
            result = get_similarity_properties(("http://example.org/Person", None))
            assert result == ["http://example.org/name", "http://example.org/email"]

    def test_get_similarity_properties_empty_list(
        self, mock_display_rules_with_similarity
    ):
        """Test when similarity_properties is an empty list."""
        mock_rules = mock_display_rules_with_similarity.copy()
        mock_rules[0]["similarity_properties"] = []

        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules", return_value=mock_rules
        ):
            result = get_similarity_properties(("http://example.org/Person", None))
            assert result is None # Should return None if list is empty

    def test_get_similarity_properties_missing_key(
        self, mock_display_rules_with_similarity
    ):
        """Test when similarity_properties key is missing for the class."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules_with_similarity,
        ):
            result = get_similarity_properties(("http://example.org/Document", None))
            assert result is None

    def test_get_similarity_properties_class_not_found(self, mock_display_rules_with_similarity):
        """Test when the entity type is not found in the rules."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules_with_similarity,
        ):
            result = get_similarity_properties(("http://example.org/Unknown", None))
            assert result is None

    def test_get_similarity_properties_invalid_format_not_list(
        self, mock_display_rules_with_similarity, capsys
    ):
        """Test when similarity_properties is not a list."""
        entity_type = "http://example.org/Event"
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules_with_similarity,
        ):
            result = get_similarity_properties((entity_type, None))
            captured = capsys.readouterr()
            assert result is None
            assert f"Warning: Invalid format for similarity_properties in class {entity_type}" in captured.out

    def test_get_similarity_properties_invalid_format_item_type(
        self, mock_display_rules_with_similarity, capsys
    ):
        """Test when similarity_properties list contains non-string items."""
        entity_type = "http://example.org/Place"
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_display_rules_with_similarity,
        ):
            result = get_similarity_properties((entity_type, None))
            captured = capsys.readouterr()
            assert result is None
            assert f"Warning: Invalid item format in similarity_properties list for class {entity_type}" in captured.out
            assert "Expected a property URI string or {'and': [...]} dict" in captured.out

    def test_get_similarity_properties_with_and_structure(
        self, capsys
    ):
        """Test get_similarity_properties with valid and invalid 'and' structures."""
        entity_type = "http://example.org/TestAnd"
        mock_rules_and = [
            {
                "target": {
                    "class": entity_type
                },
                "priority": 1,
                "similarity_properties": [
                    "prop1",
                    {"and": ["prop2", "prop3"]}, # Valid
                ],
            },
            {
                "target": {
                    "class": "http://example.org/InvalidAndValue"
                },
                "priority": 2,
                "similarity_properties": [
                    {"and": "not_a_list"}
                ],
            },
            {
                "target": {
                    "class": "http://example.org/InvalidAndListItem"
                },
                "priority": 3,
                "similarity_properties": [
                    {"and": ["prop4", 555]}
                ],
            },
             {
                "target": {
                    "class": "http://example.org/InvalidAndDict"
                },
                "priority": 4,
                "similarity_properties": [
                    {"and": ["prop4"], "or": ["prop5"]}
                ],
            },
        ]

        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules",
            return_value=mock_rules_and,
        ):
            result_valid = get_similarity_properties((entity_type, None))
            assert result_valid == ["prop1", {"and": ["prop2", "prop3"]}]

            invalid_type1 = "http://example.org/InvalidAndValue"
            result_invalid_value = get_similarity_properties((invalid_type1, None))
            captured_invalid_value = capsys.readouterr()
            assert result_invalid_value is None
            expected_warning1 = f"Warning: Invalid 'and' group in similarity_properties for class {invalid_type1}. Expected {{'and': ['prop_uri', ...]}} with a non-empty list of strings."
            assert expected_warning1 in captured_invalid_value.out

            invalid_type2 = "http://example.org/InvalidAndListItem"
            result_invalid_item = get_similarity_properties((invalid_type2, None))
            captured_invalid_item = capsys.readouterr()
            assert result_invalid_item is None
            expected_warning2 = f"Warning: Invalid 'and' group in similarity_properties for class {invalid_type2}. Expected {{'and': ['prop_uri', ...]}} with a non-empty list of strings."
            assert expected_warning2 in captured_invalid_item.out

            invalid_type3 = "http://example.org/InvalidAndDict"
            result_invalid_dict = get_similarity_properties((invalid_type3, None))
            captured_invalid_dict = capsys.readouterr()
            assert result_invalid_dict is None
            expected_warning3 = f"Warning: Invalid item format in similarity_properties list for class {invalid_type3}. Expected a property URI string or {{'and': [...]}} dict."
            assert expected_warning3 in captured_invalid_dict.out

    def test_get_similarity_properties_no_rules(self):
        """Test when get_display_rules returns empty list."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules", return_value=[]
        ):
            result = get_similarity_properties(("http://example.org/Person", None))
            assert result is None

    def test_get_similarity_properties_no_rules_none(self):
        """Test when get_display_rules returns None."""
        with patch(
            "heritrace.utils.display_rules_utils.get_display_rules", return_value=None
        ):
            result = get_similarity_properties(("http://example.org/Person", None))
            assert result is None


class TestFindMatchingRule:
    """Tests for find_matching_rule function."""

    def test_exact_match_class_and_shape(self):
        """Test Case 1: Both class and shape match (exact match)."""
        class_uri = "http://example.org/Person"
        shape_uri = "http://example.org/PersonShape"
        
        mock_rules = [
            {
                "target": {
                    "class": "http://example.org/Document",
                    "shape": "http://example.org/DocumentShape"
                },
                "priority": 5,
                "displayProperties": []
            },
            {
                "target": {
                    "class": "http://example.org/Person",
                    "shape": "http://example.org/PersonShape"
                },
                "priority": 10,
                "displayProperties": []
            },
            {
                "target": {
                    "class": "http://example.org/Person"
                },
                "priority": 1,  # Lower priority number (better priority)
                "displayProperties": []
            }
        ]
        
        result = find_matching_rule(class_uri, shape_uri, mock_rules)
        
        assert result is not None
        assert "target" in result
        assert "class" in result["target"]
        assert "shape" in result["target"]
        assert result["target"]["class"] == class_uri
        assert result["target"]["shape"] == shape_uri
        assert result["priority"] == 10  # Confirming it's the exact match rule
        
        assert result["priority"] > mock_rules[2]["priority"]  # 10 > 1
