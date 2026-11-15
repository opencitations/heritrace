# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import os
import shutil
import time
from collections.abc import Generator
from pathlib import Path
from typing import cast
from unittest.mock import patch
from urllib.parse import quote

import pytest
from filelock import Timeout
from flask import Flask
from flask.testing import FlaskClient
from rdflib import (
    DCTERMS,
    FOAF,
    OWL,
    PROV,
    RDF,
    RDFS,
    XSD,
    Dataset,
    Graph,
    Literal,
    URIRef,
)
from rdflib.collection import Collection
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
    ConfigurationRejectedError,
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
from heritrace.configuration.vocabulary import DASH, HT, META, SH, SHUI
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
        "Journal",
        "Number",
        "Type (fabio:Expression)",
        "Type (fabio:JournalVolume)",
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

    saved = read_shacl(config_app.config["CONFIG_DIR"])
    assert status == 200
    shown = Literal("false", datatype=XSD.boolean)
    assert set(saved.objects(IDENTIFIER_SHAPE, DASH.hidden)) == {shown}
    assert read_duplicate_keys(saved, IDENTIFIER_SHAPE) == [
        ["http://purl.org/spar/datacite/usesIdentifierScheme", str(LITERAL_VALUE)]
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
    client: FlaskClient, subject: URIRef, values: dict[URIRef, object]
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


def test_a_field_reads_its_property_backwards(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    status, _ = _add(
        admin_client,
        URIRef("http://schema.org/VolumeShape"),
        {
            SH.property: {
                "entity_type": str(SH.PropertyShape),
                "entity_shape": str(META.PropertyShapeShape),
                "properties": {
                    str(SH.name): ["Issues"],
                    str(SH.path): [
                        {
                            "entity_type": str(HT.InversePath),
                            "entity_shape": str(META.InversePathShape),
                            "properties": {
                                str(SH.inversePath): [str(DCTERMS.isPartOf)]
                            },
                        }
                    ],
                },
            }
        },
    )

    assert status == 200
    saved = read_shacl(config_app.config["CONFIG_DIR"])
    assert (None, RDF.type, HT.InversePath) not in saved
    volume = next(
        shape
        for shape in read_shapes(saved).shapes
        if shape.iri == "http://schema.org/VolumeShape"
    )
    assert [prop.path for prop in volume.properties if prop.inverse] == [
        str(DCTERMS.isPartOf)
    ]


def _replace_path(
    client: FlaskClient, field: URIRef, old: URIRef, new: URIRef | None
) -> tuple[int, dict]:
    deletion = {
        "action": "delete",
        "subject": str(field),
        "predicate": str(SH.path),
        "object": str(old),
    }
    addition = {
        "action": "create",
        "subject": str(field),
        "data": {"properties": {str(SH.path): [str(new)]}},
    }
    response = client.post(
        "/api/configuration/apply_changes",
        json=[deletion, addition] if new is not None else [deletion],
    )
    return response.status_code, response.get_json()


def test_a_required_value_is_replaced_within_one_save(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    field = _literal_property(_data(config_app))

    status, _ = _replace_path(admin_client, field, LITERAL_VALUE, DCTERMS.title)

    assert status == 200
    assert set(_data(config_app).objects(field, SH.path)) == {DCTERMS.title}


def test_a_required_value_is_not_removed_without_a_replacement(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    field = _literal_property(_data(config_app))

    status, body = _replace_path(admin_client, field, LITERAL_VALUE, None)

    assert (status, body["message"]) == (
        400,
        "The property Property requires at least 1 value",
    )
    assert set(_data(config_app).objects(field, SH.path)) == {LITERAL_VALUE}


def _app_with(tmp_path: Path, volume_field: str) -> Generator[Flask, None, None]:
    (tmp_path / "shacl.ttl").write_text(
        EDITOR_SHAPES.read_text() + f"schema:VolumeShape sh:property {volume_field} .\n"
    )
    seed_config(tmp_path, test_example_dir)

    class Config(TestConfig):
        CONFIG_DIR = tmp_path

    app = create_app(Config)
    with app.app_context():
        yield app


@pytest.fixture
def inverse_path_app(tmp_path: Path) -> Generator[Flask, None, None]:
    yield from _app_with(tmp_path, "[ sh:path [ sh:inversePath dcterms:isPartOf ] ]")


def _inverse_path_field(app: Flask) -> tuple[URIRef, URIRef]:
    data = _data(app)
    return next(
        (URIRef(str(property_shape)), URIRef(str(path)))
        for property_shape, path in data.subject_objects(SH.path)
        if (path, SH.inversePath, DCTERMS.isPartOf) in data
    )


def test_an_inverse_path_is_replaced_by_a_property(inverse_path_app: Flask) -> None:
    client = _signed_in(inverse_path_app)
    field, path = _inverse_path_field(inverse_path_app)
    deletion = {
        "action": "delete",
        "subject": str(field),
        "predicate": str(SH.path),
        "object": str(path),
    }
    orphans = client.post(
        "/api/configuration/check_orphans",
        json={"changes": [deletion], "entity_type": str(SH.PropertyShape)},
    ).get_json()

    response = client.post(
        "/api/configuration/apply_changes",
        json=[
            {
                **deletion,
                "affected_entities": orphans["affected_entities"],
                "delete_affected": orphans["should_delete"],
            },
            {
                "action": "create",
                "subject": str(field),
                "data": {"properties": {str(SH.path): [str(DCTERMS.isPartOf)]}},
            },
        ],
    )

    assert response.status_code == 200
    saved = read_shacl(inverse_path_app.config["CONFIG_DIR"])
    assert set(saved.subjects(SH.inversePath)) == set()
    assert (None, SH.path, DCTERMS.isPartOf) in saved


def test_an_inverse_path_is_shown_in_place(inverse_path_app: Flask) -> None:
    client = _signed_in(inverse_path_app)
    field, _ = _inverse_path_field(inverse_path_app)
    groups = client.get(
        f"/api/configuration/entity/{quote(str(field), safe='')}",
        headers={"Accept-Language": "en"},
    ).get_json()["groups"]
    label = _label(client, field, "en")

    path = next(group for group in groups if group["property"] == str(SH.path))
    assert label == "^dcterms:isPartOf"
    assert [
        (triple["alternative"], triple["details"]) for triple in path["triples"]
    ] == [
        (
            "Inverse path",
            [
                {
                    "name": "Property",
                    "property": str(SH.inversePath),
                    "values": [
                        {
                            "label": "dcterms:isPartOf",
                            "uri": None,
                            "value": str(DCTERMS.isPartOf),
                            "language": None,
                        }
                    ],
                }
            ],
        )
    ]


FABIO = "http://purl.org/spar/fabio/"


@pytest.fixture
def qualified_app(tmp_path: Path) -> Generator[Flask, None, None]:
    yield from _app_with(
        tmp_path,
        f"""[
  sh:path rdf:type ;
  sh:name "Kind" ;
  sh:qualifiedValueShape [ sh:hasValue <{FABIO}Expression> ] ;
  sh:qualifiedMinCount 1 ;
  sh:qualifiedMaxCount 1
] , [
  sh:path dcterms:type ;
  sh:name "Genre" ;
  sh:qualifiedValueShape [
    sh:or ( [ sh:hasValue <{FABIO}Book> ] [ sh:hasValue <{FABIO}Thesis> ] )
  ] ;
  sh:qualifiedMaxCount 1
]""",
    )


def _volume_field(app: Flask, name: str) -> tuple[URIRef, URIRef]:
    data = _data(app)
    return next(
        (URIRef(str(field)), URIRef(str(qualified)))
        for field, qualified in data.subject_objects(SH.qualifiedValueShape)
        if (field, SH.name, Literal(name)) in data
    )


def test_qualified_values_are_shown_in_place(qualified_app: Flask) -> None:
    client = _signed_in(qualified_app)
    field, qualified = _volume_field(qualified_app, "Kind")
    genre, _ = _volume_field(qualified_app, "Genre")
    groups, genre_groups = (
        client.get(
            f"/api/configuration/entity/{quote(str(entity), safe='')}",
            headers={"Accept-Language": "en"},
        ).get_json()["groups"]
        for entity in (field, genre)
    )

    shown = {
        group["display_name"]: [triple["value"] for triple in group["triples"]]
        for group in groups
    }
    details = next(
        triple["details"]
        for group in groups
        for triple in group["triples"]
        if group["property"] == str(SH.qualifiedValueShape)
    )
    assert _label(client, field, "en") == "Kind (fabio:Expression)"
    assert {
        name: shown[name]
        for name in (
            "Minimum occurrences",
            "Maximum occurrences",
        )
    } == {
        "Minimum occurrences": ["1"],
        "Maximum occurrences": ["1"],
    }
    assert details == [
        {
            "name": "Value",
            "property": str(SH.hasValue),
            "values": [
                {
                    "label": "fabio:Expression",
                    "uri": None,
                    "value": f"{FABIO}Expression",
                    "language": None,
                }
            ],
        }
    ]
    assert _label(client, qualified, "en") == "fabio:Expression"
    assert [
        (triple["value"], triple["details"])
        for group in genre_groups
        if group["property"] == str(SH.qualifiedValueShape)
        for triple in group["triples"]
    ] == [("fabio:Book, fabio:Thesis", None)]


def _add_qualified_field(
    client: FlaskClient, counts: dict[URIRef, list[str]]
) -> tuple[int, dict]:
    return _add(
        client,
        URIRef("http://schema.org/VolumeShape"),
        {
            SH.property: {
                "entity_type": str(SH.PropertyShape),
                "entity_shape": str(META.PropertyShapeShape),
                "properties": {
                    str(SH.path): [str(DCTERMS.type)],
                    str(SH.qualifiedValueShape): [
                        {
                            "entity_type": str(HT.QualifiedValueShape),
                            "entity_shape": str(META.QualifiedValueShapeShape),
                            "properties": {str(SH.hasValue): [f"{FABIO}Book"]},
                        }
                    ],
                    **{str(predicate): value for predicate, value in counts.items()},
                },
            }
        },
    )


def test_a_field_counts_only_its_qualified_values(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    status, _ = _add_qualified_field(admin_client, {SH.qualifiedMaxCount: ["1"]})

    assert status == 200
    saved = read_shacl(config_app.config["CONFIG_DIR"])
    assert (None, RDF.type, HT.QualifiedValueShape) not in saved
    volume = next(
        shape
        for shape in read_shapes(saved).shapes
        if shape.iri == "http://schema.org/VolumeShape"
    )
    assert [
        (prop.kind, prop.values, prop.min_count, prop.max_count)
        for prop in volume.properties
        if prop.qualified
    ] == [("value", [f"{FABIO}Book"], None, 1)]


def test_qualified_values_need_a_number_to_count(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    before = read_shacl(config_app.config["CONFIG_DIR"])

    status, body = _add_qualified_field(admin_client, {})

    assert (status, [error.split(": ", 1)[1] for error in body["errors"]]) == (
        422,
        ["Add the minimum or maximum occurrences of the value to count"],
    )
    assert isomorphic(read_shacl(config_app.config["CONFIG_DIR"]), before)


DATACITE = "http://purl.org/spar/datacite/"
USES_SCHEME = URIRef(f"{DATACITE}usesIdentifierScheme")


def _allowed_values(graph: Graph, path: URIRef) -> list[list[str]]:
    return sorted(
        [str(value) for value in Collection(graph, head)]
        for field in graph.subjects(SH.path, path)
        for head in graph.objects(field, SH["in"])
    )


def _allowed_value_group(client: FlaskClient, field: URIRef) -> dict:
    groups = client.get(
        f"/api/configuration/entity/{quote(str(field), safe='')}",
        headers={"Accept-Language": "en"},
    ).get_json()["groups"]
    return next(group for group in groups if group["property"] == str(SH["in"]))


def _allowed_value(value: str, temp_id: str) -> dict:
    return {
        "entity_type": str(HT.AllowedValue),
        "entity_shape": str(META.AllowedValueShape),
        "properties": {str(RDF.first): [value]},
        "tempId": temp_id,
    }


def _scheme_field(app: Flask) -> URIRef:
    data = _data(app)
    return next(
        URIRef(str(field))
        for field in data.objects(IDENTIFIER_SHAPE, SH.property)
        if (field, SH.path, USES_SCHEME) in data
    )


def test_allowed_values_are_shown_in_their_order(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    group = _allowed_value_group(admin_client, _scheme_field(config_app))

    assert (
        group["is_draggable"],
        [triple["details"] for triple in group["triples"]],
    ) == (
        True,
        [
            [
                {
                    "name": "Value",
                    "property": str(RDF.first),
                    "values": [
                        {
                            "label": f"datacite:{scheme}",
                            "uri": None,
                            "value": f"{DATACITE}{scheme}",
                            "language": None,
                        }
                    ],
                }
            ]
            for scheme in ("doi", "pmid")
        ],
    )


def test_a_new_field_keeps_the_order_of_its_allowed_values(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    status, _ = _add(
        admin_client,
        URIRef("http://schema.org/VolumeShape"),
        {
            SH.property: {
                "entity_type": str(SH.PropertyShape),
                "entity_shape": str(META.PropertyShapeShape),
                "properties": {
                    str(SH.path): [str(DCTERMS.format)],
                    str(SH["in"]): [
                        _allowed_value(f"{DATACITE}{scheme}", scheme)
                        for scheme in ("pmid", "isbn", "doi")
                    ],
                },
            }
        },
    )

    assert status == 200
    saved = read_shacl(config_app.config["CONFIG_DIR"])
    assert (
        _allowed_values(saved, DCTERMS.format),
        set(saved.subjects(RDF.type, HT.AllowedValue)),
    ) == (
        [[f"{DATACITE}pmid", f"{DATACITE}isbn", f"{DATACITE}doi"]],
        set(),
    )


def test_allowed_values_exclude_a_datatype(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    before = read_shacl(config_app.config["CONFIG_DIR"])

    status, body = _add(
        admin_client,
        URIRef("http://schema.org/VolumeShape"),
        {
            SH.property: {
                "entity_type": str(SH.PropertyShape),
                "entity_shape": str(META.PropertyShapeShape),
                "properties": {
                    str(SH.path): [str(DCTERMS.format)],
                    str(SH.datatype): [str(XSD.string)],
                    str(SH["in"]): [_allowed_value(f"{DATACITE}doi", "doi")],
                },
            }
        },
    )

    assert (status, [issue.split(": ", 1)[1] for issue in body["errors"]]) == (
        422,
        ["Datatype and Allowed values cannot be used together"],
    )
    assert isomorphic(read_shacl(config_app.config["CONFIG_DIR"]), before)


def test_allowed_values_are_removed_added_and_reordered(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    field = _scheme_field(config_app)
    doi, pmid = (
        triple["object"]
        for triple in _allowed_value_group(admin_client, field)["triples"]
    )
    base = {
        "subject": str(field),
        "predicate": str(SH["in"]),
        "shape": str(META.AllowedValueShape),
        "entity_type": str(SH.PropertyShape),
        "entity_shape": str(META.PropertyShapeShape),
    }
    deletion = {**base, "action": "delete", "object": doi}
    orphans = admin_client.post(
        "/api/configuration/check_orphans",
        json={"changes": [deletion], "entity_type": str(SH.PropertyShape)},
    ).get_json()

    response = admin_client.post(
        "/api/configuration/apply_changes",
        json=[
            {
                **deletion,
                "affected_entities": orphans["affected_entities"],
                "delete_affected": orphans["should_delete"],
            },
            {
                **base,
                "action": "order",
                "object": ["isbn", pmid],
                "newObject": str(RDF.rest),
            },
            {
                "action": "create",
                "subject": str(field),
                "data": {
                    "properties": {
                        str(SH["in"]): [_allowed_value(f"{DATACITE}isbn", "isbn")]
                    }
                },
            },
        ],
    )

    assert response.status_code == 200
    saved = read_shacl(config_app.config["CONFIG_DIR"])
    assert _allowed_values(saved, USES_SCHEME) == [
        [f"{DATACITE}doi", f"{DATACITE}isbn"],
        [f"{DATACITE}isbn", f"{DATACITE}pmid"],
    ]


SCHEMA = "http://schema.org/"


@pytest.fixture
def alternatives_app(tmp_path: Path) -> Generator[Flask, None, None]:
    yield from _app_with(
        tmp_path,
        """[
  sh:path dcterms:date ;
  sh:name "Date" ;
  sh:or (
    [ sh:datatype xsd:date ] [ sh:datatype xsd:gYearMonth ] [ sh:datatype xsd:gYear ]
  )
] , [
  sh:path frbr:partOf ;
  sh:name "Container" ;
  sh:or (
    [ sh:node schema:JournalShape ; sh:class fabio:Journal ]
    [ sh:node schema:VolumeShape ; sh:class fabio:JournalVolume ]
  )
]""",
    )


def _field_named(app: Flask, name: str) -> URIRef:
    return URIRef(str(_data(app).value(predicate=SH.name, object=Literal(name))))


def _alternative_group(client: FlaskClient, field: URIRef) -> dict:
    groups = client.get(
        f"/api/configuration/entity/{quote(str(field), safe='')}",
        headers={"Accept-Language": "en"},
    ).get_json()["groups"]
    return next(group for group in groups if group["property"] == str(SH["or"]))


def _saved_alternatives(graph: Graph, path: URIRef) -> list[dict[str, str]]:
    field = graph.value(predicate=SH.path, object=path)
    return [
        {
            str(predicate): str(value)
            for predicate, value in graph.predicate_objects(item)
        }
        for item in Collection(graph, cast("Node", graph.value(field, SH["or"])))
    ]


def _shown_value(name: str, property_iri: URIRef, value: str, label: str) -> dict:
    return {
        "name": name,
        "property": str(property_iri),
        "values": [{"label": label, "uri": None, "value": value, "language": None}],
    }


def _value_alternative(constraints: dict[URIRef, str], temp_id: str) -> dict:
    return {
        "entity_type": str(HT.ValueAlternative),
        "entity_shape": str(META.ValueAlternativeShape),
        "properties": {
            str(predicate): [value] for predicate, value in constraints.items()
        },
        "tempId": temp_id,
    }


def test_value_alternatives_are_shown_in_their_order(alternatives_app: Flask) -> None:
    client = _signed_in(alternatives_app)
    dates = _alternative_group(client, _field_named(alternatives_app, "Date"))
    containers = _alternative_group(client, _field_named(alternatives_app, "Container"))

    assert (
        dates["is_draggable"],
        [triple["details"] for triple in dates["triples"]],
        [triple["details"] for triple in containers["triples"]],
    ) == (
        True,
        [
            [_shown_value("Datatype", SH.datatype, str(XSD[name]), str(XSD[name]))]
            for name in ("date", "gYearMonth", "gYear")
        ],
        [
            [
                _shown_value("SHACL shape of the value", SH.node, shape, shape),
                _shown_value(
                    "Class of the value", SH["class"], f"{FABIO}{name}", f"fabio:{name}"
                ),
            ]
            for shape, name in (
                (f"{SCHEMA}JournalShape", "Journal"),
                (f"{SCHEMA}VolumeShape", "JournalVolume"),
            )
        ],
    )


def test_value_alternatives_are_removed_added_and_reordered(
    alternatives_app: Flask,
) -> None:
    client = _signed_in(alternatives_app)
    field = _field_named(alternatives_app, "Date")
    date, year_month, year = (
        triple["object"] for triple in _alternative_group(client, field)["triples"]
    )
    base = {
        "subject": str(field),
        "predicate": str(SH["or"]),
        "shape": str(META.ValueAlternativeShape),
        "entity_type": str(SH.PropertyShape),
        "entity_shape": str(META.PropertyShapeShape),
    }
    deletion = {**base, "action": "delete", "object": year_month}
    orphans = client.post(
        "/api/configuration/check_orphans",
        json={"changes": [deletion], "entity_type": str(SH.PropertyShape)},
    ).get_json()

    response = client.post(
        "/api/configuration/apply_changes",
        json=[
            {
                **deletion,
                "affected_entities": orphans["affected_entities"],
                "delete_affected": orphans["should_delete"],
            },
            {
                **base,
                "action": "order",
                "object": ["dateTime", year, date],
                "newObject": str(RDF.rest),
            },
            {
                "action": "create",
                "subject": str(field),
                "data": {
                    "properties": {
                        str(SH["or"]): [
                            _value_alternative(
                                {SH.datatype: str(XSD.dateTime)}, "dateTime"
                            )
                        ]
                    }
                },
            },
        ],
    )

    assert response.status_code == 200
    saved = read_shacl(alternatives_app.config["CONFIG_DIR"])
    assert _saved_alternatives(saved, DCTERMS.date) == [
        {str(SH.datatype): str(XSD[name])} for name in ("dateTime", "gYear", "date")
    ]


def test_a_new_field_takes_value_alternatives(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    pairs = [
        (f"{SCHEMA}JournalShape", "Journal"),
        (f"{SCHEMA}VolumeShape", "JournalVolume"),
    ]

    status, _ = _add(
        admin_client,
        URIRef(f"{SCHEMA}BookShape"),
        {
            SH.property: {
                "entity_type": str(SH.PropertyShape),
                "entity_shape": str(META.PropertyShapeShape),
                "properties": {
                    str(SH.path): [str(DCTERMS.isPartOf)],
                    str(SH["or"]): [
                        _value_alternative(
                            {SH.node: shape, SH["class"]: f"{FABIO}{name}"}, name
                        )
                        for shape, name in pairs
                    ],
                },
            }
        },
    )

    assert status == 200
    saved = read_shacl(config_app.config["CONFIG_DIR"])
    assert (
        _saved_alternatives(saved, DCTERMS.isPartOf),
        set(saved.subjects(RDF.type, HT.ValueAlternative)),
    ) == (
        [
            {str(SH.node): shape, str(SH["class"]): f"{FABIO}{name}"}
            for shape, name in pairs
        ],
        set(),
    )


DATE = {SH.datatype: str(XSD.date)}
YEAR = {SH.datatype: str(XSD.gYear)}


def _add_date_field(
    client: FlaskClient,
    alternatives: list[dict[URIRef, str]],
    own: dict[URIRef, list[str]],
) -> tuple[int, dict]:
    return _add(
        client,
        URIRef(f"{SCHEMA}BookShape"),
        {
            SH.property: {
                "entity_type": str(SH.PropertyShape),
                "entity_shape": str(META.PropertyShapeShape),
                "properties": {
                    str(SH.path): [str(DCTERMS.date)],
                    str(SH["or"]): [
                        _value_alternative(constraints, str(index))
                        for index, constraints in enumerate(alternatives)
                    ],
                    **{str(predicate): value for predicate, value in own.items()},
                },
            }
        },
    )


def test_a_single_value_alternative_is_saved_as_the_constraint_of_its_field(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    status, _ = _add_date_field(admin_client, [DATE], {})

    assert status == 200
    saved = read_shacl(config_app.config["CONFIG_DIR"])
    field = saved.value(predicate=SH.path, object=DCTERMS.date)
    assert (
        saved.value(field, SH.datatype),
        saved.value(field, SH["or"]),
    ) == (XSD.date, None)


@pytest.mark.parametrize(
    ("alternatives", "own", "error"),
    [
        (
            [DATE, {SH["class"]: f"{FABIO}Journal"}],
            {},
            "The value alternatives of a field use the same constraint",
        ),
        (
            [{**DATE, SH["class"]: f"{FABIO}Journal"}, YEAR],
            {},
            "Datatype and Class of the value cannot be used together",
        ),
        (
            [DATE, YEAR],
            {SH.datatype: [str(XSD.string)]},
            "Datatype and Value alternatives cannot be used together",
        ),
    ],
)
def test_value_alternatives_are_checked_when_saved(
    admin_client: FlaskClient,
    config_app: Flask,
    alternatives: list[dict[URIRef, str]],
    own: dict[URIRef, list[str]],
    error: str,
) -> None:
    before = read_shacl(config_app.config["CONFIG_DIR"])

    status, body = _add_date_field(admin_client, alternatives, own)

    assert (status, [issue.split(": ", 1)[1] for issue in body["errors"]]) == (
        422,
        [error],
    )
    assert isomorphic(read_shacl(config_app.config["CONFIG_DIR"]), before)


_DOI_PATTERN = "^10[.].+/.+$"
_PMID_PATTERN = "^[0-9]+$"


@pytest.fixture
def rules_app(tmp_path: Path) -> Generator[Flask, None, None]:
    (tmp_path / "shacl.ttl").write_text(
        EDITOR_SHAPES.read_text()
        + f"""schema:IdentifierShape sh:or (
  [
    sh:property [ sh:path datacite:usesIdentifierScheme ; sh:hasValue datacite:doi ] ;
    sh:property [
      sh:path literal:hasLiteralValue ;
      sh:pattern "{_DOI_PATTERN}" ;
      sh:message "Not a DOI"@en, "Non è un DOI"@it ;
    ] ;
  ]
  [
    sh:property [ sh:path datacite:usesIdentifierScheme ; sh:hasValue datacite:pmid ] ;
    sh:property [ sh:path literal:hasLiteralValue ; sh:pattern "{_PMID_PATTERN}" ] ;
  ]
) .
"""
    )
    seed_config(tmp_path, test_example_dir)

    class Config(TestConfig):
        CONFIG_DIR = tmp_path

    app = create_app(Config)
    with app.app_context():
        yield app


def _rule_group(client: FlaskClient) -> dict:
    groups = client.get(
        f"/api/configuration/entity/{quote(str(IDENTIFIER_SHAPE), safe='')}",
        headers={"Accept-Language": "en"},
    ).get_json()["groups"]
    return next(group for group in groups if group["property"] == str(SH["or"]))


def _saved_rules(app: Flask) -> list[tuple[str, str, str, dict[str, str]]]:
    shapes = read_shapes(read_shacl(app.config["CONFIG_DIR"]))
    shape = next(shape for shape in shapes.shapes if shape.iri == str(IDENTIFIER_SHAPE))
    return sorted(
        (rule.condition_value, rule.path, rule.pattern, rule.messages)
        for rule in shape.patterns
    )


def _pmid_rule_change(client: FlaskClient) -> dict:
    pmid = next(
        triple["object"]
        for triple in _rule_group(client)["triples"]
        if triple["value"] == "datacite:pmid"
    )
    deletion = {
        "subject": str(IDENTIFIER_SHAPE),
        "predicate": str(SH["or"]),
        "shape": str(META.PatternRuleShape),
        "entity_type": str(SH.NodeShape),
        "entity_shape": str(META.NodeShapeShape),
        "action": "delete",
        "object": pmid,
    }
    orphans = client.post(
        "/api/configuration/check_orphans",
        json={"changes": [deletion], "entity_type": str(SH.NodeShape)},
    ).get_json()
    return {
        **deletion,
        "affected_entities": orphans["affected_entities"],
        "delete_affected": orphans["should_delete"],
    }


def test_format_rules_are_shown_by_their_condition(rules_app: Flask) -> None:
    group = _rule_group(_signed_in(rules_app))

    assert (
        group["is_draggable"],
        sorted((triple["value"], triple["details"]) for triple in group["triples"]),
    ) == (False, [("datacite:doi", None), ("datacite:pmid", None)])


def test_format_rules_are_removed_and_added(rules_app: Flask) -> None:
    client = _signed_in(rules_app)
    rule = {
        "entity_type": str(HT.PatternRule),
        "entity_shape": str(META.PatternRuleShape),
        "properties": {
            str(HT.conditionPath): [str(USES_SCHEME)],
            str(HT.conditionValue): [f"{DATACITE}pmid"],
            str(HT.checkedPath): [str(LITERAL_VALUE)],
            str(SH.pattern): ["^[1-9][0-9]*$"],
            str(SH.message): [{"value": "Not a PMID", "language": "en"}],
        },
    }

    response = client.post(
        "/api/configuration/apply_changes",
        json=[
            _pmid_rule_change(client),
            {
                "action": "create",
                "subject": str(IDENTIFIER_SHAPE),
                "data": {"properties": {str(SH["or"]): [rule]}},
            },
        ],
    )

    assert response.status_code == 200
    assert _saved_rules(rules_app) == [
        (
            f"{DATACITE}doi",
            str(LITERAL_VALUE),
            _DOI_PATTERN,
            {"en": "Not a DOI", "it": "Non è un DOI"},
        ),
        (f"{DATACITE}pmid", str(LITERAL_VALUE), "^[1-9][0-9]*$", {"en": "Not a PMID"}),
    ]
    assert (
        set(
            read_shacl(rules_app.config["CONFIG_DIR"]).subjects(
                RDF.type, HT.PatternRule
            )
        )
        == set()
    )


def test_an_allowed_value_without_a_format_rule_is_rejected(rules_app: Flask) -> None:
    client = _signed_in(rules_app)
    before = read_shacl(rules_app.config["CONFIG_DIR"])

    response = client.post(
        "/api/configuration/apply_changes", json=[_pmid_rule_change(client)]
    )

    assert (
        response.status_code,
        [issue.split(": ", 1)[1] for issue in response.get_json()["errors"]],
    ) == (422, ["datacite:pmid has no format rule"])
    assert isomorphic(read_shacl(rules_app.config["CONFIG_DIR"]), before)


def _criterion_group(client: FlaskClient, shape: URIRef, language: str = "en") -> dict:
    groups = client.get(
        f"/api/configuration/entity/{quote(str(shape), safe='')}",
        headers={"Accept-Language": language},
    ).get_json()["groups"]
    return next(group for group in groups if group["property"] == str(OWL.hasKey))


@pytest.mark.parametrize(("language", "joined"), [("en", "and"), ("it", "e")])
def test_a_duplicate_criterion_is_named_after_its_properties(
    admin_client: FlaskClient, language: str, joined: str
) -> None:
    group = _criterion_group(admin_client, IDENTIFIER_SHAPE, language)

    assert (
        group["is_draggable"],
        [(triple["value"], triple["details"]) for triple in group["triples"]],
    ) == (
        False,
        [(f"datacite:usesIdentifierScheme {joined} literal:hasLiteralValue", None)],
    )


def test_duplicate_criteria_are_removed_and_added(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    title = next(
        triple["object"]
        for triple in _criterion_group(admin_client, JOURNAL_ARTICLE_SHAPE)["triples"]
        if triple["value"] == "dcterms:title"
    )
    deletion = {
        "subject": str(JOURNAL_ARTICLE_SHAPE),
        "predicate": str(OWL.hasKey),
        "shape": str(META.DuplicateCriterionShape),
        "entity_type": str(SH.NodeShape),
        "entity_shape": str(META.NodeShapeShape),
        "action": "delete",
        "object": title,
    }
    orphans = admin_client.post(
        "/api/configuration/check_orphans",
        json={"changes": [deletion], "entity_type": str(SH.NodeShape)},
    ).get_json()
    criterion = {
        "entity_type": str(HT.DuplicateCriterion),
        "entity_shape": str(META.DuplicateCriterionShape),
        "properties": {str(HT.keyProperty): [str(DCTERMS.title), str(DCTERMS.issued)]},
    }

    response = admin_client.post(
        "/api/configuration/apply_changes",
        json=[
            {
                **deletion,
                "affected_entities": orphans["affected_entities"],
                "delete_affected": orphans["should_delete"],
            },
            {
                "action": "create",
                "subject": str(JOURNAL_ARTICLE_SHAPE),
                "data": {"properties": {str(OWL.hasKey): [criterion]}},
            },
        ],
    )

    assert response.status_code == 200
    saved = read_shacl(config_app.config["CONFIG_DIR"])
    assert (
        read_duplicate_keys(saved, JOURNAL_ARTICLE_SHAPE),
        set(saved.subjects(RDF.type, HT.DuplicateCriterion)),
    ) == ([[str(DCTERMS.issued), str(DCTERMS.title)], [str(HAS_IDENTIFIER)]], set())


def _label_query(app: Flask) -> tuple[URIRef, Literal]:
    data = _data(app)
    query = cast("Node", data.value(IDENTIFIER_SHAPE, HT.labelQuery))
    return URIRef(str(query)), cast("Literal", data.value(query, SH.select))


def test_a_label_query_is_shown_on_its_resource_type(
    admin_client: FlaskClient, config_app: Flask
) -> None:
    expression, select = _label_query(config_app)
    groups = admin_client.get(
        f"/api/configuration/entity/{quote(str(IDENTIFIER_SHAPE), safe='')}",
        headers={"Accept-Language": "en"},
    ).get_json()["groups"]
    fields = next(group for group in groups if group["property"] == str(SH.property))
    query = next(group for group in groups if group["property"] == str(HT.labelQuery))

    assert sorted(triple["value"] for triple in fields["triples"]) == [
        "Identifier Scheme",
        "Literal Value",
        "Type (datacite:Identifier)",
    ]
    assert [(triple["object"], triple["details"]) for triple in query["triples"]] == [
        (
            str(expression),
            [
                {
                    "name": "SPARQL query",
                    "property": str(SH.select),
                    "values": [
                        {
                            "label": str(select),
                            "uri": None,
                            "value": str(select),
                            "language": None,
                        }
                    ],
                }
            ],
        )
    ]
    assert _label(admin_client, expression, "it") == "Query dell'etichetta"


def _saved_label_queries(saved: Graph) -> list[Node]:
    return [
        cast("Node", saved.value(query, SH.select))
        for field in saved.objects(IDENTIFIER_SHAPE, SH.property)
        if (field, SH.path, RDFS.label) in saved
        for query in saved.objects(field, SH.values)
    ]


LABEL_QUERY_ERROR = "shapes.4.properties.3.labelQuery: "


@pytest.mark.parametrize(
    ("query", "result"),
    [
        ("SELECT ?label WHERE { $this dcterms:title ?label }", (200, None)),
        (
            "SELECT ?label WHERE { $this schema:name ?label }",
            (422, "The query uses undeclared prefixes: schema"),
        ),
        (
            "SELECT ?label WHERE { $this dcterms:title ?label",
            (
                422,
                "The query is not valid SPARQL: Expected SelectQuery, found end of"
                " text  (at char 298), (line:6, col:49)",
            ),
        ),
        (
            "SELECT ?label ?title WHERE { $this dcterms:title ?label, ?title }",
            (422, "The query must be a SELECT that returns one variable"),
        ),
    ],
)
def test_a_label_query_is_checked_when_saved(
    admin_client: FlaskClient,
    config_app: Flask,
    query: str,
    result: tuple[int, str | None],
) -> None:
    expression, select = _label_query(config_app)

    status, body = _update(admin_client, expression, SH.select, str(select), query)

    if result[1] is None:
        saved = read_shacl(config_app.config["CONFIG_DIR"])
        assert (status, _saved_label_queries(saved)) == (200, [Literal(query)])
        assert (None, RDF.type, HT.SelectExpression) not in saved
    else:
        assert (status, body["errors"]) == (
            result[0],
            [LABEL_QUERY_ERROR + result[1]],
        )


def test_a_label_query_written_by_hand_needs_the_label_role(
    config_app: Flask,
) -> None:
    config_dir = config_app.config["CONFIG_DIR"]
    shacl_path = config_dir / "shacl.ttl"
    edited = Graph().parse(shacl_path, format="turtle")
    label_field = next(
        field
        for field in edited.objects(IDENTIFIER_SHAPE, SH.property)
        if (field, SH.path, RDFS.label) in edited
    )
    edited.remove((label_field, SHUI.propertyRole, SHUI.LabelRole))
    edited.serialize(shacl_path, format="turtle")

    with pytest.raises(ConfigurationRejectedError) as rejection:
        ensure_configuration_entity(config_dir)

    assert rejection.value.issues == [
        LABEL_QUERY_ERROR + "A label query needs the display label role"
    ]


def test_a_label_field_with_a_name_stays_a_field(config_app: Flask) -> None:
    config_dir = config_app.config["CONFIG_DIR"]
    shacl_path = config_dir / "shacl.ttl"
    edited = Graph().parse(shacl_path, format="turtle")
    label_field = next(
        field
        for field in edited.objects(IDENTIFIER_SHAPE, SH.property)
        if (field, SH.path, RDFS.label) in edited
    )
    edited.add((label_field, SH.name, Literal("Label")))
    edited.serialize(shacl_path, format="turtle")

    ensure_configuration_entity(config_dir)

    data = _data(config_app)
    fields_with_a_query = [
        data.value(field, SH.name)
        for field in data.objects(IDENTIFIER_SHAPE, SH.property)
        if (field, SH.values, None) in data
    ]
    assert (data.value(IDENTIFIER_SHAPE, HT.labelQuery), fields_with_a_query) == (
        None,
        [Literal("Label")],
    )


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
    prefix = "pro"
    declaration = next(data.subjects(SH.prefix, Literal(prefix)))
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
    english = {
        "Allowed value",
        "Criterion for finding duplicates",
        "Field",
        "Format rule",
        "Inverse path",
        "Label query",
        "Prefix",
        "Value alternative",
        "Value to count",
        "Resource type",
        "Resource types",
    }
    assert _entity_types(admin_client, "en") == english
    assert _entity_types(admin_client, "it") == {
        "Campo",
        "Criterio per individuare i duplicati",
        "Regola di formato",
        "Percorso inverso",
        "Prefisso",
        "Query dell'etichetta",
        "Tipi di risorsa",
        "Valore da contare",
        "Tipo di risorsa",
        "Valore ammesso",
        "Vincolo alternativo",
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
