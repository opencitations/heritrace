# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import os
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

import pytest
from filelock import Timeout
from flask import Flask
from flask.testing import FlaskClient
from rdflib import DCTERMS, FOAF, XSD, Graph, Literal, URIRef
from rdflib_ocdm.counter_handler.in_memory_counter_handler import InMemoryCounterHandler

from heritrace import create_app, extensions
from heritrace.configuration.entity import (
    PROVENANCE_FILE,
    ROOT,
    SHAPE_NAMESPACE,
    configuration_lock,
)
from heritrace.configuration.shapes import read_duplicate_keys
from heritrace.configuration.vocabulary import DASH, SH
from heritrace.scripts.seed_config import seed_config
from tests.test_config import TestConfig, test_example_dir

ADMIN = "0000-0000-0000-0000"
IDENTIFIER_SHAPE = URIRef("http://schema.org/IdentifierShape")
JOURNAL_ARTICLE_SHAPE = URIRef("http://schema.org/JournalArticleShape")
HAS_IDENTIFIER = URIRef("http://purl.org/spar/datacite/hasIdentifier")
LITERAL_VALUE = URIRef(
    "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
)


@pytest.fixture
def config_app(tmp_path: Path) -> Generator[Flask, None, None]:
    seed_config(tmp_path, test_example_dir)
    an_hour_ago = time.time() - 3600
    os.utime(tmp_path / "shacl.ttl", (an_hour_ago, an_hour_ago))

    class Config(TestConfig):
        CONFIG_DIR = tmp_path
        DISPLAY_RULES_PATH = tmp_path / "display_rules.yaml"

    app = create_app(Config)
    with app.app_context():
        yield app


@pytest.fixture
def empty_config_app(tmp_path: Path) -> Generator[Flask, None, None]:
    seed_config(tmp_path, test_example_dir)
    (tmp_path / "shacl.ttl").unlink()
    (tmp_path / "display_rules.yaml").unlink()

    class Config(TestConfig):
        CONFIG_DIR = tmp_path
        DISPLAY_RULES_PATH = tmp_path / "display_rules.yaml"

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
    return Graph().parse(app.config["CONFIG_DIR"] / "shacl.ttl", format="turtle")


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
    files = [config_dir / "shacl.ttl", config_dir / PROVENANCE_FILE]
    before = [path.read_bytes() for path in files]
    field = _literal_property(_data(config_app))

    assert _update(admin_client, field, SH.minCount, "1", "5") == (
        422,
        {
            "errors": [
                "shapes.10.properties.2.maxCount: The maximum is lower than the minimum"
            ],
            "status": "error",
        },
    )
    assert [path.read_bytes() for path in files] == before


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
