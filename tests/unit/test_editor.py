# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import pytest
from unittest.mock import MagicMock
from rdflib import URIRef, Literal
from datetime import datetime

from heritrace.editor import Editor

@pytest.fixture
def mock_editor_deps():
    return {
        "dataset_endpoint": "http://localhost:9999/blazegraph/sparql",
        "provenance_endpoint": "http://localhost:9998/blazegraph/sparql",
        "counter_handler": MagicMock(),
        "resp_agent": URIRef("http://example.com/agent"),
        "source": URIRef("http://initial.source"), # Initial source
        "c_time": datetime.now()
    }

def test_set_primary_source(mock_editor_deps):
    editor = Editor(**mock_editor_deps)
    new_source = URIRef("http://new.source")

    editor.set_primary_source(new_source)

    assert editor.source == new_source

