# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import os
import shutil
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

import pytest
from filelock import Timeout
from flask import Flask
from flask.testing import FlaskClient
from rdflib import DCTERMS, FOAF, OWL, PROV, RDF, XSD, Dataset, Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.term import Node
from rdflib_ocdm.counter_handler.in_memory_counter_handler import InMemoryCounterHandler

from heritrace import create_app, extensions
from heritrace.configuration.entity import (
    EDITOR_FILE,
    GENID,
    PROVENANCE_FILE,
    ROOT,
    SHAPE_NAMESPACE,
    SYSTEM_AGENT,
    canonical,
    configuration_lock,
    ensure_configuration_entity,
    read_shacl,
)
from heritrace.configuration.shapes import (
    read_duplicate_keys,
    read_shapes,
    shapes_to_graph,
    unsupported_parts,
)
from heritrace.configuration.vocabulary import DASH, META, SH
from heritrace.scripts.seed_config import seed_config
from tests.test_config import TestConfig, test_example_dir

ADMIN = "0000-0000-0000-0000"
EDITOR_SHAPES = test_example_dir / "configuration_editor" / "shacl.ttl"
IDENTIFIER_SHAPE = URIRef("http://schema.org/IdentifierShape")
JOURNAL_ARTICLE_SHAPE = URIRef("http://schema.org/JournalArticleShape")
HAS_IDENTIFIER = URIRef("http://purl.org/spar/datacite/hasIdentifier")
LITERAL_VALUE = URIRef(
    "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
)


@pytest.fixture
def config_app(tmp_path: Path) -> Generator[Flask, None, None]:
    shutil.copyfile(EDITOR_SHAPES, tmp_path / "shacl.ttl")
    seed_config(tmp_path, test_example_dir)
    an_hour_ago = time.time() - 3600
    os.utime(tmp_path / "shacl.ttl", (an_hour_ago, an_hour_ago))

    class Config(TestConfig):
        CONFIG_DIR = tmp_path

    app = create_app(Config)
    with app.app_context():
        yield app


@pytest.fixture
def empty_config_app(tmp_path: Path) -> Generator[Flask, None, None]:
    seed_config(tmp_path, test_example_dir)
    (tmp_path / "shacl.ttl").unlink()

    class Config(TestConfig):
        CONFIG_DIR = tmp_path

    app = create_app(Config)
    with app.app_context():
        yield app


def _signed_in(app: Flask) -> FlaskClient:
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = ADMIN
        session["user_name"] = "Admin"
        session["_fresh"] = True
    return client


@pytest.fixture
def admin_client(config_app: Flask) -> FlaskClient:
    return _signed_in(config_app)


def _data(app: Flask) -> Graph:
    return Graph().parse(app.config["CONFIG_DIR"] / EDITOR_FILE, format="turtle")


def _literal_property(graph: Graph) -> URIRef:
    for property_shape in graph.objects(IDENTIFIER_SHAPE, SH.property):
        if (property_shape, SH.path, LITERAL_VALUE) in graph:
            return URIRef(str(property_shape))
    raise AssertionError


def _update(
    client: FlaskClient, subject: URIRef, predicate: URIRef, old: str, new: str
) -> tuple[int, dict]:
    response = client.post(
        "/api/configuration/apply_changes",
        json=[
            {
                "subject": str(subject),
                "action": "update",
                "predicate": str(predicate),
                "object": old,
                "newObject": new,
                "primary_source": "",
            }
        ],
    )
    return response.status_code, response.get_json()


def _history(client: FlaskClient, entity: URIRef) -> list[dict]:
    response = client.get(
        f"/api/configuration/entity-history/{quote(str(entity), safe='')}"
    )
    return response.get_json()["snapshots"]


def test_root_holds_every_entity_type(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    response = admin_client.get(
        f"/api/configuration/entity/{quote(str(ROOT), safe='')}"
    )

    parts = next(
        group
        for group in response.get_json()["groups"]
        if group["property"] == str(DCTERMS.hasPart)
    )
    assert {triple["object"] for triple in parts["triples"]} == {
        str(shape) for shape in _data(config_app).objects(ROOT, DCTERMS.hasPart)
    }


def _entity_type_labels(client: FlaskClient) -> dict[str, str]:
    response = client.get(f"/api/configuration/entity/{quote(str(ROOT), safe='')}")
    parts = next(
        group
        for group in response.get_json()["groups"]
        if group["property"] == str(DCTERMS.hasPart)
    )
    return {triple["object"]: triple["value"] for triple in parts["triples"]}


def test_entity_types_with_the_same_name_show_where_they_are_used(
    admin_client: FlaskClient,
) -> None:
    labels = _entity_type_labels(admin_client)

    name, owners = labels["http://schema.org/BookIdentifierShape"].split(" · ")
    assert name == "Identifier"
    assert set(owners.split(", ")) == {"Monograph", "Dictionary", "Thesis"}
    assert labels["http://schema.org/AuthorShape"] == "Agent Role · Author"
    assert labels["http://schema.org/BookShape"] == "Monograph"


def test_an_entity_type_without_a_name_is_named_after_its_class(
    admin_client: FlaskClient,
) -> None:
    response = admin_client.post(
        "/api/configuration/apply_changes",
        json=[
            {
                "subject": "http://schema.org/BookShape",
                "action": "delete",
                "predicate": str(SH.name),
                "object": "Monograph",
                "primary_source": "",
            }
        ],
    )
    assert response.status_code == 200

    labels = _entity_type_labels(admin_client)

    assert labels["http://schema.org/BookShape"] == "book"
    _, owners = labels["http://schema.org/BookIdentifierShape"].split(" · ")
    assert set(owners.split(", ")) == {"book", "Dictionary", "Thesis"}


def test_fields_are_listed_by_name(admin_client: FlaskClient) -> None:
    response = admin_client.get(
        f"/api/configuration/entity/{quote('http://schema.org/VolumeShape', safe='')}"
    )

    fields = next(
        group
        for group in response.get_json()["groups"]
        if group["property"] == str(SH.property)
    )
    assert sorted(triple["value"] for triple in fields["triples"]) == [
        "Description",
        "Display label",
        "Journal",
        "Number",
        "Type",
        "Type",
    ]


def test_editing_a_field_keeps_its_history(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    field = _literal_property(_data(config_app))

    assert _update(admin_client, field, SH.name, "Literal Value", "Value") == (
        200,
        {"message": "Changes applied successfully", "status": "success"},
    )
    assert set(_data(config_app).objects(field, SH.name)) == {Literal("Value")}

    created = _history(admin_client, field)[0]["timestamp"]
    # Snapshot timestamps have a resolution of one second: the restore must
    # fall in a later second than the edit for the history to order them.
    time.sleep(1)
    response = admin_client.post(
        f"/api/configuration/entity-restore/{quote(str(field), safe='')}/"
        f"{quote(created, safe='')}"
    )

    assert response.get_json() == {"status": "success"}
    assert set(_data(config_app).objects(field, SH.name)) == {Literal("Literal Value")}
    assert [snapshot["description"] for snapshot in _history(admin_client, field)] == [
        "The entity 'Literal Value' has been created.",
        "The entity 'Value' was modified.",
        "The entity 'Literal Value' was modified.",
    ]


def test_showing_a_hidden_entity_type_keeps_its_duplicate_keys(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    status, _ = _update(admin_client, IDENTIFIER_SHAPE, DASH.hidden, "true", "false")

    data = _data(config_app)
    assert status == 200
    shown = Literal("false", datatype=XSD.boolean)
    assert set(data.objects(IDENTIFIER_SHAPE, DASH.hidden)) == {shown}
    assert read_duplicate_keys(data, IDENTIFIER_SHAPE) == [
        [str(LITERAL_VALUE), "http://purl.org/spar/datacite/usesIdentifierScheme"]
    ]


def test_a_field_can_stop_depending_on_its_entity(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    field = next(
        URIRef(str(property_shape))
        for property_shape in _data(config_app).objects(
            JOURNAL_ARTICLE_SHAPE, SH.property
        )
        if (property_shape, SH.path, HAS_IDENTIFIER) in _data(config_app)
    )

    status, _ = _update(admin_client, field, DASH.composite, "true", "false")

    assert status == 200
    assert set(_data(config_app).objects(field, DASH.composite)) == {
        Literal("false", datatype=XSD.boolean)
    }


def test_a_change_reads_the_snapshot_counters_while_holding_the_lock(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    field = _literal_property(_data(config_app))
    held: list[bool] = []
    read_counters = extensions.provenance_counter_handler

    def record_lock(provenance_path: Path) -> InMemoryCounterHandler:
        other_worker = configuration_lock(config_app.config["CONFIG_DIR"])
        try:
            other_worker.acquire(timeout=0)
        except Timeout:
            held.append(True)
        else:
            other_worker.release()
            held.append(False)
        return read_counters(provenance_path)

    with patch("heritrace.extensions.provenance_counter_handler", record_lock):
        status, _ = _update(admin_client, field, SH.name, "Literal Value", "Value")

    assert status == 200
    assert held == [True]


def test_an_invalid_configuration_is_not_saved(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    config_dir = config_app.config["CONFIG_DIR"]
    files = [config_dir / name for name in ("shacl.ttl", EDITOR_FILE, PROVENANCE_FILE)]
    before = [path.read_bytes() for path in files]
    field = _literal_property(_data(config_app))

    assert _update(admin_client, field, SH.minCount, "1", "5") == (
        422,
        {
            "errors": [
                "shapes.4.properties.2.maxCount: The maximum is lower than the minimum"
            ],
            "status": "error",
        },
    )
    assert [path.read_bytes() for path in files] == before


def _add(
    client: FlaskClient, subject: URIRef, values: dict[URIRef, str]
) -> tuple[int, dict]:
    response = client.post(
        "/api/configuration/apply_changes",
        json=[
            {
                "action": "create",
                "subject": str(subject),
                "data": {
                    "properties": {
                        str(predicate): [value] for predicate, value in values.items()
                    }
                },
                "primary_source": "",
            }
        ],
    )
    return response.status_code, response.get_json()


def _numeric_property(client: FlaskClient, app: Flask) -> URIRef:
    field = _literal_property(_data(app))
    assert (
        _update(client, field, SH.datatype, str(XSD.string), str(XSD.decimal))[0] == 200
    )
    return field


def test_a_field_takes_a_description_and_value_bounds(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    field = _numeric_property(admin_client, config_app)

    status, _ = _add(
        admin_client,
        field,
        {
            SH.description: "Shown under the field",
            SH.minInclusive: "1",
            SH.maxInclusive: "2.5",
            SH.minExclusive: "0",
            SH.maxExclusive: "3",
        },
    )

    data = _data(config_app)
    assert status == 200
    assert set(data.objects(field, SH.description)) == {
        Literal("Shown under the field")
    }
    assert set(data.objects(field, SH.minInclusive)) == {
        Literal("1", datatype=XSD.integer)
    }
    assert set(data.objects(field, SH.maxInclusive)) == {
        Literal("2.5", datatype=XSD.decimal)
    }
    assert set(data.objects(field, SH.minExclusive)) == {
        Literal("0", datatype=XSD.integer)
    }
    assert set(data.objects(field, SH.maxExclusive)) == {
        Literal("3", datatype=XSD.integer)
    }


def test_a_minimum_value_above_the_maximum_is_not_saved(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    field = _numeric_property(admin_client, config_app)

    assert _add(admin_client, field, {SH.minInclusive: "5", SH.maxInclusive: "1"}) == (
        422,
        {
            "errors": [
                "shapes.4.properties.2.maxInclusive:"
                " The maximum is lower than the minimum"
            ],
            "status": "error",
        },
    )


def test_bounds_on_a_text_field_are_not_saved(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    field = _literal_property(_data(config_app))

    assert _add(admin_client, field, {SH.minInclusive: "1"}) == (
        422,
        {
            "errors": [
                "shapes.4.properties.2.minInclusive: Bounds need a numeric datatype"
            ],
            "status": "error",
        },
    )


def test_a_negative_number_of_values_is_rejected(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    field = _literal_property(_data(config_app))

    assert _update(admin_client, field, SH.minCount, "1", "-1") == (
        400,
        {
            "error_type": "validation",
            "message": "'-1' is not a valid value. The 'Minimum number of values'"
            " property requires a value of at least 0",
            "status": "error",
        },
    )


def test_entity_types_can_be_created_without_any_shapes(
    empty_config_app: Flask,
) -> None:
    client = _signed_in(empty_config_app)
    assert client.get("/api/me").get_json()["config"]["shacl"] is False

    response = client.post(
        "/api/configuration/apply_changes",
        json=[
            {
                "action": "create",
                "subject": str(ROOT),
                "data": {
                    "entity_type": str(SH.ShapesGraph),
                    "properties": {
                        str(DCTERMS.hasPart): [
                            {
                                "entity_type": str(SH.NodeShape),
                                "entity_shape": "https://w3id.org/heritrace/meta/NodeShapeShape",
                                "properties": {
                                    str(SH.name): ["Person"],
                                    str(SH.targetClass): [str(FOAF.Person)],
                                },
                            }
                        ]
                    },
                },
            }
        ],
    )

    assert response.status_code == 200
    shape = _data(empty_config_app).value(predicate=SH.targetClass, object=FOAF.Person)
    assert str(shape).startswith(SHAPE_NAMESPACE)
    assert client.get("/api/me").get_json()["config"]["shacl"] is True


def test_configuration_routes_are_for_admins_but_preflights_pass(
    client: FlaskClient,
) -> None:
    assert client.post("/api/configuration/check-lock").status_code == 401
    assert client.options("/api/configuration/check-lock").status_code == 200


def test_a_new_prefix_is_declared(admin_client: FlaskClient, config_app: Flask) -> None:
    status, _ = _add(
        admin_client,
        ROOT,
        {
            SH.declare: {
                "entity_type": str(SH.PrefixDeclaration),
                "entity_shape": str(META.PrefixDeclarationShape),
                "properties": {
                    str(SH.prefix): ["ex"],
                    str(SH.namespace): ["http://example.org/"],
                },
            }
        },
    )

    assert status == 200
    shapes = read_shapes(read_shacl(config_app.config["CONFIG_DIR"]))
    assert shapes.prefixes["ex"] == "http://example.org/"


def test_the_first_start_leaves_the_shapes_file_as_written(config_app: Flask) -> None:
    config_dir = config_app.config["CONFIG_DIR"]

    assert (config_dir / "shacl.ttl").read_bytes() == EDITOR_SHAPES.read_bytes()
    assert (config_dir / EDITOR_FILE).exists()


def test_a_saved_configuration_is_plain_shacl(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    field = _literal_property(_data(config_app))

    assert _update(admin_client, field, SH.name, "Literal Value", "Value")[0] == 200

    text = (config_app.config["CONFIG_DIR"] / "shacl.ttl").read_text()
    saved = Graph().parse(data=text, format="turtle")
    assert isomorphic(saved, canonical(_data(config_app)))
    assert GENID not in text
    assert str(META) not in text
    for predicate in (SH["in"], OWL.hasKey):
        heads = set(saved.objects(None, predicate))
        assert heads
        assert all((head, RDF.first, None) in saved for head in heads)


def _snapshot_agents(config_dir: Path, entity: URIRef) -> list[str]:
    provenance = Dataset(default_union=True).parse(
        config_dir / PROVENANCE_FILE, format="trig"
    )
    return [
        str(provenance.value(snapshot, PROV.wasAttributedTo))
        for snapshot in provenance.subjects(PROV.specializationOf, entity)
    ]


def test_a_restart_without_changes_adds_no_version(config_app: Flask) -> None:
    config_dir = config_app.config["CONFIG_DIR"]
    before = (config_dir / PROVENANCE_FILE).read_bytes()

    ensure_configuration_entity(config_dir)

    assert (config_dir / PROVENANCE_FILE).read_bytes() == before


def test_a_restart_adds_no_version_when_shapes_share_a_blank_node(
    tmp_path: Path,
) -> None:
    (tmp_path / "shacl.ttl").write_text(
        EDITOR_SHAPES.read_text()
        + """
schema:JournalShape sh:property _:abstract .
schema:ThesisShape sh:property _:abstract .
_:abstract sh:path dcterms:abstract ; sh:name "Abstract" ; sh:datatype xsd:string .
"""
    )
    ensure_configuration_entity(tmp_path)
    before = (tmp_path / PROVENANCE_FILE).read_bytes()

    ensure_configuration_entity(tmp_path)

    assert (tmp_path / PROVENANCE_FILE).read_bytes() == before


def test_a_shapes_file_edited_by_hand_becomes_a_new_version(
    config_app: Flask,
) -> None:
    config_dir = config_app.config["CONFIG_DIR"]
    shacl_path = config_dir / "shacl.ttl"
    edited = Graph().parse(shacl_path, format="turtle")
    field = next(
        prop
        for prop in edited.objects(IDENTIFIER_SHAPE, SH.property)
        if (prop, SH.path, LITERAL_VALUE) in edited
    )
    edited.set((field, SH.name, Literal("Written by hand")))
    edited.serialize(shacl_path, format="turtle")

    ensure_configuration_entity(config_dir)

    view = _data(config_app)
    assert Literal("Written by hand") in {
        view.value(prop, SH.name)
        for prop in view.objects(IDENTIFIER_SHAPE, SH.property)
    }
    assert _snapshot_agents(config_dir, IDENTIFIER_SHAPE) == [
        str(SYSTEM_AGENT),
        str(SYSTEM_AGENT),
    ]


def _edit_by_hand(config_dir: Path) -> None:
    shacl_path = config_dir / "shacl.ttl"
    edited = Graph().parse(shacl_path, format="turtle")
    edited.add((IDENTIFIER_SHAPE, SH.description, Literal("Written by hand")))
    edited.serialize(shacl_path, format="turtle")


def test_a_hand_edit_reloads_heritrace(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    _edit_by_hand(config_app.config["CONFIG_DIR"])

    with patch("heritrace.extensions.request_reload", return_value=True) as reload:
        admin_client.get("/api/me")
        admin_client.get("/api/me")

    reload.assert_called_once_with()


def test_a_save_does_not_overwrite_a_hand_edit(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    config_dir = config_app.config["CONFIG_DIR"]
    _edit_by_hand(config_dir)
    files = [config_dir / name for name in ("shacl.ttl", EDITOR_FILE, PROVENANCE_FILE)]
    before = [path.read_bytes() for path in files]
    field = _literal_property(_data(config_app))

    assert _update(admin_client, field, SH.name, "Literal Value", "Value") == (
        422,
        {
            "errors": ["shacl.ttl changed on disk. Reload the page to see its content"],
            "status": "error",
        },
    )
    assert [path.read_bytes() for path in files] == before


def test_removing_a_prefix_removes_its_declaration(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    data = _data(config_app)
    declaration = next(data.objects(ROOT, SH.declare))
    prefix = str(data.value(declaration, SH.prefix))
    deletion = {
        "action": "delete",
        "subject": str(ROOT),
        "predicate": str(SH.declare),
        "object": str(declaration),
    }
    check = admin_client.post(
        "/api/configuration/check_orphans",
        json={"changes": [deletion], "entity_type": str(SH.ShapesGraph)},
    ).get_json()
    assert check["should_delete"] is True

    response = admin_client.post(
        "/api/configuration/apply_changes",
        json=[
            {
                **deletion,
                "affected_entities": check["affected_entities"],
                "delete_affected": True,
                "primary_source": "",
            }
        ],
    )

    assert response.status_code == 200
    assert (declaration, None, None) not in _data(config_app)
    shapes = read_shapes(read_shacl(config_app.config["CONFIG_DIR"]))
    assert prefix not in shapes.prefixes


def _entity_types(client: FlaskClient, language: str) -> set[str]:
    response = client.get(
        "/api/configuration/entity-types", headers={"Accept-Language": language}
    )
    return {entity_type["label"] for entity_type in response.get_json()["types"]}


def test_names_follow_the_language_of_the_interface(admin_client: FlaskClient) -> None:
    english = {"Field", "Prefix", "Resource type", "Resource types"}
    assert _entity_types(admin_client, "en") == english
    assert _entity_types(admin_client, "it") == {
        "Campo",
        "Prefisso",
        "Tipi di risorsa",
        "Tipo di risorsa",
    }
    assert _entity_types(admin_client, "fr") == english


def _add_name(client: FlaskClient, subject: URIRef, name: str, language: str) -> int:
    response = client.post(
        "/api/configuration/apply_changes",
        json=[
            {
                "action": "create",
                "subject": str(subject),
                "data": {
                    "properties": {
                        str(SH.name): [{"value": name, "language": language}]
                    }
                },
                "primary_source": "",
            }
        ],
    )
    return response.status_code


def _label(client: FlaskClient, entity: URIRef, language: str) -> str:
    response = client.get(
        f"/api/configuration/entity/{quote(str(entity), safe='')}",
        headers={"Accept-Language": language},
    )
    return response.get_json()["label"]


def test_a_name_is_saved_once_for_each_language(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    assert _add_name(admin_client, JOURNAL_ARTICLE_SHAPE, "Articolo", "it") == 200
    assert _add_name(admin_client, JOURNAL_ARTICLE_SHAPE, "Saggio", "it") == 400

    names = {Literal("Journal Article"), Literal("Articolo", lang="it")}
    assert set(_data(config_app).objects(JOURNAL_ARTICLE_SHAPE, SH.name)) == names
    shacl = read_shacl(config_app.config["CONFIG_DIR"])
    assert set(shacl.objects(JOURNAL_ARTICLE_SHAPE, SH.name)) == names
    assert _label(admin_client, JOURNAL_ARTICLE_SHAPE, "it") == "Articolo"
    assert _label(admin_client, JOURNAL_ARTICLE_SHAPE, "en") == "Journal Article"


def _edit_name(
    client: FlaskClient, old: Literal, new: str, new_language: str | None = None
) -> int:
    change = {
        "subject": str(IDENTIFIER_SHAPE),
        "action": "update",
        "predicate": str(SH.name),
        "object": str(old),
        "newObject": new,
        "language": old.language,
        "primary_source": "",
    }
    if new_language is not None:
        change["newLanguage"] = new_language
    response = client.post("/api/configuration/apply_changes", json=[change])
    return response.status_code


def _identifier_names(app: Flask) -> set[Node]:
    return set(_data(app).objects(IDENTIFIER_SHAPE, SH.name))


def test_an_edited_name_keeps_its_language(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    assert _add_name(admin_client, IDENTIFIER_SHAPE, "Identifier", "it") == 200

    assert (
        _edit_name(admin_client, Literal("Identifier", lang="it"), "Identificatore")
        == 200
    )
    assert _identifier_names(config_app) == {
        Literal("Identifier"),
        Literal("Identificatore", lang="it"),
    }


def test_an_edited_name_takes_the_language_it_is_given(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    assert _edit_name(admin_client, Literal("Identifier"), "Identifiant", "fr") == 200
    assert _identifier_names(config_app) == {Literal("Identifiant", lang="fr")}

    assert (
        _edit_name(admin_client, Literal("Identifiant", lang="fr"), "Identifier", "")
        == 200
    )
    assert _identifier_names(config_app) == {Literal("Identifier")}

    assert _add_name(admin_client, IDENTIFIER_SHAPE, "Identificatore", "it") == 200
    assert _edit_name(admin_client, Literal("Identifier"), "Codice", "it") == 400
    assert _identifier_names(config_app) == {
        Literal("Identifier"),
        Literal("Identificatore", lang="it"),
    }


@pytest.mark.parametrize(
    ("names", "unsupported"),
    [
        ('"Book"@en, "Libro"@it, "Volume"', []),
        ('"Libro"@it, "Volume"@it', ["http://example.org/BookShape: sh:name (1)"]),
    ],
)
def test_shapes_written_by_hand_have_one_name_for_each_language(
    names: str, unsupported: list[str]
) -> None:
    graph = Graph().parse(
        data=f"""
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .

        ex:BookShape a sh:NodeShape ;
          sh:targetClass ex:Book ;
          sh:name {names} .
        """,
        format="turtle",
    )

    assert unsupported_parts(graph, read_shapes(graph)) == unsupported


def test_named_values_keep_their_names_and_descriptions() -> None:
    graph = Graph().parse(
        data="""
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <http://example.org/> .

        ex:BookShape a sh:NodeShape ;
          sh:targetClass ex:Book ;
          sh:property [ sh:path ex:cover ; sh:in ( ex:hardcover ex:paperback ) ] .
        ex:hardcover rdfs:label "Hardcover"@en, "Copertina rigida"@it ;
          rdfs:comment "A cover made of board."@en .
        ex:paperback a ex:Cover .
        """,
        format="turtle",
    )
    shapes = read_shapes(graph)
    hardcover = URIRef("http://example.org/hardcover")

    assert unsupported_parts(graph, shapes) == ["1 triples outside any shape"]
    assert set(shapes_to_graph(shapes).triples((hardcover, None, None))) == set(
        graph.triples((hardcover, None, None))
    )
