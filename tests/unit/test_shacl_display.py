# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask import Flask
from rdflib import Graph

from heritrace.utils.shacl_display import order_form_fields
from heritrace.utils.shacl_presentation import read_presentation
from heritrace.utils.shacl_utils import get_form_fields_from_shacl

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


def test_groups_and_fields_without_a_group_share_one_order() -> None:
    shapes = Graph().parse(
        data="""
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <http://example.org/> .

        ex:BookShape a sh:NodeShape ;
          sh:targetClass ex:Book ;
          sh:property [ sh:path ex:remark ] ;
          sh:property [ sh:path ex:note ; sh:group ex:Extra ; sh:order 1 ] ;
          sh:property [ sh:path ex:title ; sh:group ex:Main ; sh:order 2 ] ;
          sh:property [ sh:path ex:code ; sh:order 1.5 ] .
        ex:Main a sh:PropertyGroup ;
          rdfs:label "Main"@en, "Principale"@it ;
          sh:order 1 .
        ex:Extra a sh:PropertyGroup ; sh:order 2 .
        """,
        format="turtle",
    )

    fields = get_form_fields_from_shacl(shapes, Flask(__name__))[
        (EX + "Book", EX + "BookShape")
    ]

    assert [
        (path, field.get("section"), field.get("sectionName"))
        for path, [field] in fields.items()
    ] == [
        (EX + "title", EX + "Main", {"en": "Main", "it": "Principale"}),
        (EX + "code", None, None),
        (EX + "note", EX + "Extra", None),
        (EX + "remark", None, None),
    ]
