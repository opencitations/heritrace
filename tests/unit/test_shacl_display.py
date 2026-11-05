# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from rdflib import Graph

from heritrace.utils.shacl_display import order_form_fields
from heritrace.utils.shacl_presentation import read_presentation

EX = "http://example.org/"

SHAPES = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .

ex:PersonShape a sh:NodeShape ;
  sh:targetClass ex:Person ;
  sh:property [ sh:path ex:name ; sh:order 2 ] ;
  sh:property [ sh:path ex:role ; sh:node ex:EditorShape ; sh:order 3 ] ;
  sh:property [ sh:path ex:role ; sh:node ex:AuthorShape ; sh:order 1 ] ;
  sh:property [ sh:path ex:unordered ] .
"""


def test_form_fields_follow_sh_order() -> None:
    entity_key = (EX + "Person", EX + "PersonShape")
    editor = {"nodeShape": EX + "EditorShape"}
    author = {"nodeShape": EX + "AuthorShape"}
    form_fields = {
        entity_key: {
            EX + "unordered": [{"uri": EX + "unordered"}],
            EX + "virtual": [{"uri": "Virtual"}],
            EX + "name": [{"uri": EX + "name"}],
            EX + "role": [editor, author],
        }
    }
    presentation = read_presentation(Graph().parse(data=SHAPES, format="turtle"))

    result = order_form_fields(form_fields, presentation)

    assert list(result[entity_key].items()) == [
        (EX + "role", [author, editor]),
        (EX + "name", [{"uri": EX + "name"}]),
        (EX + "unordered", [{"uri": EX + "unordered"}]),
        (EX + "virtual", [{"uri": "Virtual"}]),
    ]
