# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import pytest

from heritrace.component_options import load_component_options


def test_load_component_options(monkeypatch) -> None:
    monkeypatch.setenv(
        "COMPONENT_OPTIONS",
        '{"directory":"/app/info_dir","supplier_prefix":"09110","enabled":true}',
    )

    assert load_component_options("COMPONENT_OPTIONS") == {
        "directory": "/app/info_dir",
        "supplier_prefix": "09110",
        "enabled": True,
    }


def test_load_component_options_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("COMPONENT_OPTIONS", raising=False)

    assert load_component_options("COMPONENT_OPTIONS") == {}


def test_load_component_options_rejects_invalid_json(monkeypatch) -> None:
    monkeypatch.setenv("COMPONENT_OPTIONS", "{")

    with pytest.raises(
        ValueError, match="COMPONENT_OPTIONS must contain a valid JSON object"
    ):
        load_component_options("COMPONENT_OPTIONS")


def test_load_component_options_rejects_non_object(monkeypatch) -> None:
    monkeypatch.setenv("COMPONENT_OPTIONS", '["value"]')

    with pytest.raises(TypeError, match="COMPONENT_OPTIONS must contain a JSON object"):
        load_component_options("COMPONENT_OPTIONS")
