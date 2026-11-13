# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import shutil
import signal
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
import responses
from flask.testing import FlaskClient
from rdflib import Graph, Literal
from rdflib.compare import isomorphic

from heritrace import create_app
from heritrace.configuration.components import ComponentError
from heritrace.configuration.entity import ensure_configuration_entity, read_shacl
from heritrace.configuration.settings import (
    Settings,
    StoredSettings,
    read_settings,
    write_settings,
)
from heritrace.configuration.store import SETTINGS_FILE, SHACL_FILE
from heritrace.configuration.vocabulary import SH
from heritrace.language import LANGUAGES
from heritrace.scripts.seed_config import seed_config
from tests.conftest import write_test_configuration
from tests.test_config import BASE_DIR, TestConfig, test_example_dir

EXAMPLES = [
    BASE_DIR / "example_configurations" / "opencitations_meta" / "shacl.ttl",
    BASE_DIR / "example_configurations" / "paratext" / "shacl.ttl",
    BASE_DIR / "demo" / "iswc2026" / "config" / "shacl.ttl",
]


@pytest.fixture
def restore_store() -> Generator[None, None, None]:
    yield
    write_test_configuration()


@pytest.fixture
def visitor_client(client: FlaskClient) -> FlaskClient:
    with client.session_transaction() as sess:
        sess["_user_id"] = "0000-0000-0000-0009"
        sess["_fresh"] = True
    return client


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.parent.name)
def test_example_becomes_the_configuration_without_losses(
    tmp_path: Path, example: Path
) -> None:
    shutil.copyfile(example, tmp_path / SHACL_FILE)

    ensure_configuration_entity(tmp_path)

    assert isomorphic(
        read_shacl(tmp_path),
        Graph().parse(example, format="turtle"),
    )


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.parent.name)
def test_example_texts_come_in_every_interface_language(example: Path) -> None:
    graph = Graph().parse(example, format="turtle")
    untranslated = [
        (subject, predicate)
        for predicate in (SH.name, SH.message)
        for subject in set(graph.subjects(predicate, None))
        if sorted(
            (
                literal.language
                for literal in graph.objects(subject, predicate)
                if isinstance(literal, Literal)
            ),
            key=str,
        )
        != sorted(LANGUAGES)
    ]

    assert untranslated == []


def test_settings_list_the_strategies(logged_in_client: FlaskClient) -> None:
    payload = logged_in_client.get("/api/configuration").get_json()

    assert payload["settings"]["appTitle"] == "ParaText Test"
    assert payload["options"] == {
        "strategies": ["ASK", "DELETE", "KEEP"],
        "defaultCountLimit": 10000,
    }


def test_save_reports_every_invalid_field(logged_in_client: FlaskClient) -> None:
    settings = logged_in_client.get("/api/configuration").get_json()["settings"]
    settings.update(appTitle=" ", countLimit=0)

    response = logged_in_client.put("/api/configuration", json=settings)

    assert response.status_code == 422
    assert response.get_json()["issues"] == [
        {"location": "settings.appTitle", "message": "The title cannot be empty"},
        {"location": "settings.countLimit", "message": "The value must be at least 1"},
    ]


def test_save_rejects_malformed_payload(logged_in_client: FlaskClient) -> None:
    response = logged_in_client.put("/api/configuration", json={"appTitle": None})
    assert response.status_code == 400


@pytest.mark.usefixtures("restore_store")
def test_save_under_gunicorn_reloads_the_workers(
    logged_in_client: FlaskClient,
) -> None:
    settings = logged_in_client.get("/api/configuration").get_json()["settings"]
    settings["appTitle"] = "Renamed"

    with (
        patch("heritrace.configuration.runtime.os.kill") as kill,
        patch("heritrace.configuration.runtime.os.getppid", return_value=42),
    ):
        response = logged_in_client.put(
            "/api/configuration",
            json=settings,
            environ_base={"SERVER_SOFTWARE": "gunicorn/26.0.0"},
        )

    payload = response.get_json()
    assert payload["reloading"] is True
    kill.assert_called_once_with(42, signal.SIGHUP)
    stored = read_settings(TestConfig.CONFIG_DIR / SETTINGS_FILE)
    assert stored is not None
    assert stored.settings.app_title == "Renamed"
    assert stored.revision == payload["revision"]


def test_configuration_is_for_admins_only(visitor_client: FlaskClient) -> None:
    assert visitor_client.get("/api/configuration").status_code == 403
    assert visitor_client.get(f"/api/configuration/orcid/{_ORCID}").status_code == 403
    assert visitor_client.get("/api/me").get_json()["is_admin"] is False


def _admin(client: FlaskClient, orcid: str, name: str) -> FlaskClient:
    with client.session_transaction() as sess:
        sess["_user_id"] = orcid
        sess["user_name"] = name
        sess["_fresh"] = True
    return client


def test_an_admin_editing_the_settings_keeps_the_others_out() -> None:
    config = type(
        "TwoAdminsConfig",
        (TestConfig,),
        {"ADMIN_ORCIDS": ["0000-0000-0000-0000", "0000-0000-0000-0001"]},
    )
    app = create_app(config)
    first = _admin(app.test_client(), "0000-0000-0000-0000", "First Admin")
    second = _admin(app.test_client(), "0000-0000-0000-0001", "Second Admin")
    settings = first.get("/api/configuration").get_json()["settings"]

    assert first.post("/api/configuration/lock").get_json() == {"status": "success"}
    locked = {
        "status": "locked",
        "user_name": "First Admin",
        "user_id": "0000-0000-0000-0000",
    }
    assert second.post("/api/configuration/lock").get_json() == locked
    rejected = second.put("/api/configuration", json=settings)
    assert (rejected.status_code, rejected.get_json()) == (423, locked)

    first.delete("/api/configuration/lock")

    assert second.post("/api/configuration/lock").get_json() == {"status": "success"}
    second.delete("/api/configuration/lock")


_ORCID = "0000-0002-1825-0097"
_PERSON_URL = f"https://pub.orcid.org/v3.0/{_ORCID}/person"


def test_save_reports_each_invalid_orcid(logged_in_client: FlaskClient) -> None:
    settings = logged_in_client.get("/api/configuration").get_json()["settings"]
    settings["orcidSafelist"] = [
        f"https://orcid.org/{_ORCID}",
        "0000-0002-1825-0098",
        "",
    ]

    response = logged_in_client.put("/api/configuration", json=settings)

    message = "Enter an ORCID iD, such as 0000-0002-1825-0097"
    assert response.status_code == 422
    assert response.get_json()["issues"] == [
        {"location": "settings.orcidSafelist.1", "message": message},
        {"location": "settings.orcidSafelist.2", "message": message},
    ]


@responses.activate
def test_orcid_lookup_gives_the_public_name(logged_in_client: FlaskClient) -> None:
    responses.add(
        responses.GET,
        _PERSON_URL,
        json={
            "name": {
                "given-names": {"value": "Josiah"},
                "family-name": {"value": "Carberry"},
            }
        },
    )

    response = logged_in_client.get(f"/api/configuration/orcid/{_ORCID}")

    assert response.status_code == 200
    assert response.get_json() == {"name": "Josiah Carberry"}


@responses.activate
def test_orcid_lookup_of_a_private_name(logged_in_client: FlaskClient) -> None:
    responses.add(responses.GET, _PERSON_URL, json={"name": None})

    response = logged_in_client.get(f"/api/configuration/orcid/{_ORCID}")

    assert response.get_json() == {"name": None}


@responses.activate
def test_orcid_lookup_tells_missing_from_unreachable(
    logged_in_client: FlaskClient,
) -> None:
    responses.add(responses.GET, _PERSON_URL, status=404)
    assert logged_in_client.get(f"/api/configuration/orcid/{_ORCID}").status_code == 404

    responses.replace(
        responses.GET, _PERSON_URL, body=requests.ConnectionError("offline")
    )
    assert logged_in_client.get(f"/api/configuration/orcid/{_ORCID}").status_code == 502

    responses.replace(responses.GET, _PERSON_URL, status=500)
    assert logged_in_client.get(f"/api/configuration/orcid/{_ORCID}").status_code == 502


def test_orcid_lookup_rejects_an_invalid_id(logged_in_client: FlaskClient) -> None:
    response = logged_in_client.get("/api/configuration/orcid/0000-0002-1825-0098")

    assert response.status_code == 400


def _admin_client_for(config_dir: Path) -> FlaskClient:
    config = type("MissingConfig", (TestConfig,), {"CONFIG_DIR": config_dir})
    client = create_app(config).test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "0000-0000-0000-0000"
        sess["_fresh"] = True
    return client


def test_missing_settings_start_in_setup_mode_with_defaults(tmp_path: Path) -> None:
    client = _admin_client_for(tmp_path)

    me = client.get("/api/me").get_json()
    assert me["setup_required"] is True
    assert me["setup_error"] == "The configuration has no system settings"
    assert me["config"] is None
    assert client.get("/api/catalogue").status_code == 503
    assert client.post("/api/merge", json={}).status_code == 503
    assert client.post("/api/configuration/lock").get_json() == {"status": "success"}
    client.delete("/api/configuration/lock")
    settings = client.get("/api/configuration").get_json()["settings"]
    assert settings["appTitle"] == "HERITRACE"
    assert settings["appSubtitle"] == "Edit your knowledge graph with provenance"
    assert settings["primarySource"] == ""
    assert settings["datasetGenerationTime"] is None


def test_invalid_turtle_starts_in_setup_mode(tmp_path: Path) -> None:
    seed_config(tmp_path, test_example_dir)
    (tmp_path / SHACL_FILE).write_text("this is not turtle")

    me = _admin_client_for(tmp_path).get("/api/me").get_json()
    assert me["setup_required"] is True
    assert me["setup_error"]


def test_a_component_that_cannot_be_imported_stops_the_start() -> None:
    config = type(
        "BrokenConfig", (TestConfig,), {"SAVE_PLUGIN_CLASS": "missing.module.Plugin"}
    )

    with pytest.raises(ComponentError) as error:
        create_app(config)

    assert str(error.value) == (
        "SAVE_PLUGIN_CLASS: no Python class exists at missing.module.Plugin"
    )


def test_settings_keep_every_value_in_sqlite(tmp_path: Path) -> None:
    path = tmp_path / SETTINGS_FILE
    settings = Settings(
        primary_source="https://example.org",
        orcid_safelist=["0000-0002-9079-593X", "0000-0002-1825-0097"],
        orphan_handling="DELETE",
    )

    write_settings(path, settings, "r1")
    write_settings(path, settings, "r2")

    assert read_settings(path) == StoredSettings(settings, "r2")
