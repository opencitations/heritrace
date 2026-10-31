# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import pytest
from flask.testing import FlaskClient

SHELL_TITLE = b"<title>HERITRACE test shell</title>"


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/catalogue",
        "/time-vault",
        "/create-entity",
        "/about/https://w3id.org/oc/meta/br/0601",
        "/entity-history/https://w3id.org/oc/meta/br/0601",
        "/entity-version/https://w3id.org/oc/meta/br/0601/2024-01-01T00:00:00+00:00",
        "/merge/compare-and-merge?subject=a&other_subject=b",
    ],
)
def test_spa_paths_serve_the_shell(client: FlaskClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-cache"
    assert SHELL_TITLE in response.data


def test_unknown_path_returns_json_404(client: FlaskClient) -> None:
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert response.get_json() == {"status": "error", "message": "Not found"}


def test_anonymous_api_call_returns_json_401(client: FlaskClient) -> None:
    response = client.get("/api/catalogue")
    assert response.status_code == 401
    assert response.get_json() == {
        "status": "error",
        "message": "Authentication required",
    }
