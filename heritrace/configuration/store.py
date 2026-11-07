# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from pathlib import Path

from rdflib import Graph

from heritrace.configuration.shapes import read_shapes
from heritrace.configuration.vocabulary import SH, SHUI

SHACL_FILE = "shacl.ttl"
SETTINGS_FILE = "settings.db"
DISPLAY_RULES_FILE = "display_rules.yaml"


def shacl_turtle(graph: Graph) -> str:
    graph.bind("sh", SH)
    graph.bind("shui", SHUI)
    for prefix, namespace in read_shapes(graph).prefixes.items():
        graph.bind(prefix, namespace)
    return graph.serialize(format="turtle")


def write_shacl(config_dir: Path, graph: Graph) -> None:
    path = config_dir / SHACL_FILE
    draft = path.with_name(f".{path.name}.tmp")
    draft.write_text(shacl_turtle(graph))
    draft.replace(path)
