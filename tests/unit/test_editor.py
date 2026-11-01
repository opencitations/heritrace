# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from unittest.mock import MagicMock

from rdflib import XSD, Literal, URIRef
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler

from heritrace.editor import Editor, EndpointConfig

SUBJECT = URIRef("http://example.org/entity")
TITLE = URIRef("http://purl.org/dc/terms/title")
AGENT = URIRef("http://example.org/agent")


def _editor() -> Editor:
    return Editor(
        EndpointConfig(
            dataset="http://localhost:9999/sparql",
            provenance="http://localhost:9998/sparql",
            is_quadstore=False,
        ),
        MagicMock(spec=CounterHandler),
        AGENT,
    )


def test_create_writes_xsd_string_as_plain_literal() -> None:
    editor = _editor()

    editor.create(SUBJECT, TITLE, Literal("Title", datatype=XSD.string))

    assert set(editor.g_set.objects(SUBJECT, TITLE)) == {Literal("Title")}


def test_update_writes_xsd_string_as_plain_literal() -> None:
    editor = _editor()
    editor.g_set.add((SUBJECT, TITLE, Literal("Old")), resp_agent=AGENT)

    editor.update(SUBJECT, TITLE, Literal("Old"), Literal("New", datatype=XSD.string))

    assert set(editor.g_set.objects(SUBJECT, TITLE)) == {Literal("New")}


def test_create_keeps_other_datatypes() -> None:
    editor = _editor()
    year = Literal("2004", datatype=XSD.gYear)

    editor.create(SUBJECT, URIRef("http://example.org/year"), year)

    assert set(editor.g_set.objects(SUBJECT, URIRef("http://example.org/year"))) == {
        year
    }
