# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from unittest.mock import MagicMock, patch

from rdflib import RDF, URIRef

from heritrace.routes.api import _process_delete_change
from heritrace.routes.entity._creation import create_nested_entity
from heritrace.routes.entity._validation import validate_entity_data
from heritrace.utils.inverse_paths import (
    existing_inverse_links,
    expand_inverse_changes,
    new_inverse_entities,
    without_inverse_properties,
)
from heritrace.utils.sparql_utils import find_orphaned_entities

ARTICLE = "urn:article"
CITATION = "urn:citation"
CITING = "urn:hasCitingEntity"
PATH = f"^{CITING}"
KEY = ("urn:Article", "urn:ArticleShape")
NEW_CITATION = {
    "entity_type": "urn:Citation",
    "entity_shape": "urn:CitationShape",
    "properties": {"urn:hasCitedEntity": ["urn:other"]},
}
LINKED = {"is_existing_entity": True, "entity_uri": "urn:issue"}
DATA = {
    "entity_type": "urn:Article",
    "properties": {"urn:title": ["Dune"], PATH: [NEW_CITATION, LINKED]},
}


def _citation_with_back_link() -> dict:
    return {
        **NEW_CITATION,
        "properties": {
            **NEW_CITATION["properties"],
            CITING: [{"is_existing_entity": True, "entity_uri": ARTICLE}],
        },
    }


def test_properties_with_inverse_paths_are_set_apart() -> None:
    assert without_inverse_properties(DATA)["properties"] == {"urn:title": ["Dune"]}
    assert new_inverse_entities(DATA, ARTICLE) == [_citation_with_back_link()]
    assert existing_inverse_links(DATA) == [("urn:issue", CITING)]


def test_a_creation_splits_into_the_entity_its_children_and_its_links() -> None:
    change = {"action": "create", "subject": ARTICLE, "data": DATA}

    assert expand_inverse_changes([change]) == [
        {
            "action": "create",
            "subject": ARTICLE,
            "data": {
                "entity_type": "urn:Article",
                "properties": {"urn:title": ["Dune"]},
            },
        },
        {"action": "create", "subject": None, "data": _citation_with_back_link()},
        {
            "action": "add_link",
            "subject": "urn:issue",
            "predicate": CITING,
            "object": ARTICLE,
        },
    ]


def test_a_creation_with_only_inverse_values_has_no_main_change() -> None:
    data = {"entity_type": "urn:Article", "properties": {PATH: [NEW_CITATION]}}

    assert expand_inverse_changes(
        [{"action": "create", "subject": ARTICLE, "data": data}]
    ) == [{"action": "create", "subject": None, "data": _citation_with_back_link()}]


def _deletion() -> dict:
    return {
        "action": "delete",
        "subject": ARTICLE,
        "predicate": PATH,
        "object": CITATION,
        "entity_type": KEY[0],
        "entity_shape": KEY[1],
    }


def test_removing_an_inverse_value_removes_the_link_from_the_child() -> None:
    assert expand_inverse_changes([_deletion()]) == [
        {
            "action": "delete",
            "subject": CITATION,
            "predicate": CITING,
            "object": ARTICLE,
        }
    ]


def test_a_plain_inverse_value_leaves_no_affected_entities() -> None:
    with (
        patch("heritrace.utils.sparql_utils.get_sparql") as get_sparql,
        patch("heritrace.utils.sparql_utils._composite_fields", return_value={}),
    ):
        found = find_orphaned_entities(URIRef(ARTICLE), KEY[0], URIRef(PATH), CITATION)

    assert found == ([], [])
    get_sparql.return_value.query.assert_not_called()


def test_other_changes_pass_through() -> None:
    change = {"action": "delete", "subject": ARTICLE, "predicate": "urn:title"}

    assert expand_inverse_changes([change]) == [change]


def test_a_nested_entity_writes_its_inverse_values() -> None:
    editor = MagicMock()
    nested = {**DATA, "entity_shape": "urn:ArticleShape"}
    form_fields = {KEY: {}, ("urn:Citation", "urn:CitationShape"): {}}

    with (
        patch(
            "heritrace.routes.entity._creation.get_form_fields",
            return_value=form_fields,
        ),
        patch(
            "heritrace.routes.entity._creation.generate_unique_uri",
            return_value=URIRef(CITATION),
        ),
    ):
        create_nested_entity(editor, URIRef(ARTICLE), nested, None)

    written = {call.args[:3] for call in editor.create.call_args_list}
    assert (URIRef(CITATION), RDF.type, URIRef("urn:Citation")) in written
    assert (URIRef(CITATION), URIRef(CITING), URIRef(ARTICLE)) in written
    assert (URIRef("urn:issue"), URIRef(CITING), URIRef(ARTICLE)) in written
    assert not any(str(triple[1]).startswith("^") for triple in written)


def test_validation_leaves_inverse_values_to_their_own_entity() -> None:
    data = {
        "entity_type": "urn:Article",
        "entity_shape": "urn:ArticleShape",
        "properties": {PATH: [NEW_CITATION]},
    }

    with (
        patch(
            "heritrace.routes.entity._validation.get_form_fields",
            return_value={KEY: {}},
        ),
        patch("heritrace.routes.entity._validation.get_custom_filter"),
    ):
        assert validate_entity_data(data) == []


def test_a_link_on_a_deleted_child_is_not_removed_again() -> None:
    change = expand_inverse_changes([_deletion()])[0]

    with patch("heritrace.routes.api.delete_logic") as delete_logic:
        _process_delete_change(MagicMock(), change, None, {URIRef(CITATION)})

    delete_logic.assert_not_called()
