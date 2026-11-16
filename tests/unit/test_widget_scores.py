# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from typing import cast

from flask import Flask
from rdflib import Graph

from heritrace.configuration.vocabulary import HT, SHUI
from heritrace.utils.shacl_display import extract_shacl_form_fields
from heritrace.utils.shacl_presentation import read_presentation

PREFIXES = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix shui: <http://www.w3.org/ns/shacl-ui/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix ex: <http://example.org/> .

ex:PersonShape a sh:NodeShape ; sh:targetClass ex:Person .
"""
SHAPE = ("http://example.org/Record", "http://example.org/RecordShape")


def _fields(shapes: str) -> dict[str, list[dict[str, object]]]:
    app = Flask(__name__)
    app.config["DATASET_DB_URL"] = "http://example.org/sparql"
    shacl = Graph().parse(data=PREFIXES + shapes, format="turtle")
    return extract_shacl_form_fields(shacl, read_presentation(shacl), app)[SHAPE]


def _editors(fields: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    return {
        predicate.removeprefix("http://example.org/"): definitions[0]["editor"]
        for predicate, definitions in fields.items()
    }


def test_the_highest_score_picks_the_editor_of_each_field() -> None:
    fields = _fields("""
        ex:RecordShape a sh:NodeShape ;
          sh:targetClass ex:Record ;
          sh:property [ sh:path ex:title ; sh:datatype xsd:string ] ;
          sh:property [
            sh:path ex:abstract ; sh:datatype xsd:string ;
            shui:editor shui:TextAreaEditor ;
          ] ;
          sh:property [ sh:path ex:label ; sh:datatype rdf:langString ] ;
          sh:property [ sh:path ex:open ; sh:datatype xsd:boolean ] ;
          sh:property [ sh:path ex:pages ; sh:datatype xsd:integer ] ;
          sh:property [ sh:path ex:issued ; sh:datatype xsd:date ] ;
          sh:property [
            sh:path ex:year ;
            sh:or ( [ sh:datatype xsd:date ] [ sh:datatype xsd:gYear ] ) ;
          ] ;
          sh:property [ sh:path ex:status ; sh:in ( "draft" "final" ) ] ;
          sh:property [
            sh:path ex:kind ;
            sh:or ( [ sh:hasValue ex:Book ] [ sh:hasValue ex:Article ] ) ;
          ] ;
          sh:property [ sh:path ex:note ] ;
          sh:property [ sh:path ex:author ; sh:node ex:PersonShape ] ;
          sh:property [
            sh:path ex:editor ; sh:node ex:PersonShape ;
            shui:editor shui:DetailsEditor ;
          ] ;
          sh:property [
            sh:path ex:translator ; sh:node ex:PersonShape ;
            shui:editor shui:AutoCompleteEditor ;
          ] ;
          sh:property [ sh:path ex:owner ; sh:class ex:Person ; sh:nodeKind sh:IRI ] .
    """)

    assert _editors(fields) == {
        "title": str(SHUI.TextFieldEditor),
        "abstract": str(SHUI.TextAreaEditor),
        "label": str(SHUI.TextFieldWithLangEditor),
        "open": str(SHUI.BooleanEditor),
        "pages": str(SHUI.NumberFieldEditor),
        "issued": str(SHUI.DatePickerEditor),
        "year": str(SHUI.DatePickerEditor),
        "status": str(SHUI.EnumSelectEditor),
        "kind": str(SHUI.EnumSelectEditor),
        "note": str(SHUI.TextFieldEditor),
        "author": str(HT.ResourceDialogEditor),
        "editor": str(SHUI.DetailsEditor),
        "translator": str(SHUI.AutoCompleteEditor),
        "owner": str(SHUI.AutoCompleteEditor),
    }
    owner = fields["http://example.org/owner"][0]
    assert (owner["nodeShape"], owner["objectClass"], owner["nestedShape"]) == (
        "http://example.org/PersonShape",
        "http://example.org/Person",
        [],
    )


def test_an_alternative_takes_the_editor_of_its_property() -> None:
    fields = _fields("""
        ex:RecordShape a sh:NodeShape ;
          sh:targetClass ex:Record ;
          sh:property [
            sh:path ex:contributor ;
            shui:editor shui:DetailsEditor ;
            sh:or ( [ sh:node ex:PersonShape ] [ sh:node ex:OrganisationShape ] ) ;
          ] ;
          sh:property [
            sh:path ex:publisher ;
            shui:editor shui:AutoCompleteEditor ;
            sh:or ( [ sh:class ex:Person ] [ sh:nodeKind sh:IRI ] ) ;
          ] .
        ex:OrganisationShape a sh:NodeShape ; sh:targetClass ex:Organisation .
    """)

    assert {
        predicate.removeprefix("http://example.org/"): [
            (alternative.get("nodeShape"), alternative["editor"])
            for alternative in cast("list[dict[str, object]]", definitions[0]["or"])
        ]
        for predicate, definitions in fields.items()
    } == {
        "contributor": [
            ("http://example.org/PersonShape", str(SHUI.DetailsEditor)),
            ("http://example.org/OrganisationShape", str(SHUI.DetailsEditor)),
        ],
        "publisher": [
            (None, str(SHUI.IRIEditor)),
            ("http://example.org/PersonShape", str(SHUI.AutoCompleteEditor)),
        ],
    }
