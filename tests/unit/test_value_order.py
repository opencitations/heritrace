# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from collections import OrderedDict
from unittest.mock import MagicMock, patch

from flask import Flask
from rdflib import SH, Graph, Literal, URIRef

from heritrace.configuration.entity import META_SHAPES
from heritrace.rdf_files import load_rdf_file
from heritrace.routes.api import ChangeOperation, index_logic
from heritrace.routes.entity._creation import (
    CreationContext,
    process_ordered_properties,
)
from heritrace.utils.display_rules_utils import GroupingContext, process_index_ordering
from heritrace.utils.shacl_display import extract_shacl_form_fields
from heritrace.utils.shacl_presentation import read_presentation
from heritrace.utils.shacl_utils import get_entity_index_position, index_order

EX = "http://example.org/"
META = "https://w3id.org/heritrace/meta/"

SHAPES = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ht: <https://w3id.org/heritrace#> .
@prefix ex: <http://example.org/> .

ex:AlbumShape a sh:NodeShape ;
  sh:targetClass ex:Album ;
  sh:property [ sh:path ex:hasTrack ; sh:node ex:TrackShape ] ;
  sh:property [ sh:path ex:hasAuthor ; ht:orderedBy ex:next ] ;
  sh:property [ sh:path ex:hasNote ] .

ex:TrackShape a sh:NodeShape ;
  sh:targetClass ex:Track ;
  sh:property [ sh:path sh:order ] .
"""


def _property(presentation, shape: str, path: str):
    return next(p for p in presentation.shape_properties(shape) if p.path == path)


def test_values_whose_shape_declares_sh_order_are_ordered_by_it() -> None:
    presentation = read_presentation(Graph().parse(data=SHAPES, format="turtle"))

    track = _property(presentation, EX + "AlbumShape", EX + "hasTrack")
    author = _property(presentation, EX + "AlbumShape", EX + "hasAuthor")
    note = _property(presentation, EX + "AlbumShape", EX + "hasNote")

    assert (track.ordered_by, track.indexed) == (str(SH.order), True)
    assert (author.ordered_by, author.indexed) == (EX + "next", False)
    assert (note.ordered_by, note.indexed) == (None, False)


def test_property_shapes_are_ordered_by_sh_order() -> None:
    presentation = read_presentation(load_rdf_file(META_SHAPES))

    fields = _property(presentation, META + "NodeShapeShape", str(SH.property))
    details = _property(presentation, META + "PropertyShapeShape", str(SH.property))

    assert (fields.ordered_by, fields.indexed) == (str(SH.order), True)
    assert details.ordered_by is None


def test_form_fields_expose_sh_order_as_ordering() -> None:
    shapes = Graph().parse(data=SHAPES, format="turtle")
    form_fields = extract_shacl_form_fields(
        shapes, read_presentation(shapes), Flask(__name__)
    )

    album = form_fields[(EX + "Album", EX + "AlbumShape")]

    assert [field.get("orderedBy") for field in album[EX + "hasTrack"]] == [
        str(SH.order)
    ]
    assert [field.get("orderedBy") for field in album[EX + "hasAuthor"]] == [
        EX + "next"
    ]
    assert [field.get("orderedBy") for field in album[EX + "hasNote"]] == [None]


def _album() -> Graph:
    graph = Graph()
    album = URIRef(EX + "album")
    has_track = URIRef(EX + "hasTrack")
    for name, position in (("b", 2), ("a", 10), ("c", None), ("d", None)):
        track = URIRef(EX + name)
        graph.add((album, has_track, track))
        if position is not None:
            graph.add((track, SH.order, Literal(position)))
    return graph


def test_index_order_sorts_numerically_and_skips_unpositioned() -> None:
    order = index_order(EX + "album", EX + "hasTrack", str(SH.order), _album())

    assert order == [EX + "b", EX + "a"]
    assert (
        get_entity_index_position(
            EX + "a", EX + "album", EX + "hasTrack", str(SH.order), _album()
        )
        == 2
    )


def test_unpositioned_values_follow_in_lexicographic_order() -> None:
    triples = [
        {"triple": (EX + "album", EX + "hasTrack", label)}
        for label in ("Delta", "Alpha", "Ten", "Two")
    ]
    ctx = GroupingContext(
        subject=URIRef(EX + "album"),
        triples=[],
        grouped_triples=OrderedDict(tracks={"triples": triples}),
        fetched_values_map={
            "Alpha": EX + "c",
            "Delta": EX + "d",
            "Ten": EX + "a",
            "Two": EX + "b",
        },
        relevant_properties=set(),
        historical_snapshot=_album(),
        highest_priority_class=None,
        highest_priority_shape=None,
        value_shapes={},
        value_triples={},
    )

    process_index_ordering(ctx, EX + "hasTrack", str(SH.order), "tracks")

    assert [t["triple"][2] for t in ctx.grouped_triples["tracks"]["triples"]] == [
        "Two",
        "Ten",
        "Alpha",
        "Delta",
    ]


def test_index_logic_renumbers_values_and_keeps_their_iris() -> None:
    editor = MagicMock()
    graph = _album()
    editor.g_set = graph
    op = ChangeOperation(editor=editor, subject=URIRef(EX + "album"))

    with patch(
        "heritrace.routes.api.get_triples_from_graph",
        side_effect=lambda g, pattern: g.triples(pattern),
    ):
        index_logic(
            op,
            URIRef(EX + "hasTrack"),
            [EX + "c", EX + "a", "temp-1"],
            SH.order,
            {"temp-1": EX + "e"},
        )

    editor.delete.assert_called_once_with(URIRef(EX + "a"), SH.order, Literal(10), None)
    assert [call.args for call in editor.create.call_args_list] == [
        (URIRef(EX + "c"), SH.order, Literal(1), None),
        (URIRef(EX + "a"), SH.order, Literal(2), None),
        (URIRef(EX + "e"), SH.order, Literal(3), None),
    ]


@patch("heritrace.routes.entity._creation._process_ordered_entity_value")
def test_new_values_receive_their_position(mock_process) -> None:
    mock_process.side_effect = [URIRef(EX + "x"), URIRef(EX + "y")]
    editor = MagicMock()
    ctx = CreationContext(
        editor=editor,
        entity_uri=URIRef(EX + "album"),
        predicate=URIRef(EX + "hasTrack"),
        default_graph_uri=None,
    )

    process_ordered_properties(ctx, [{}, {}], SH.order, indexed=True)

    assert [call.args for call in editor.create.call_args_list] == [
        (URIRef(EX + "x"), SH.order, Literal(1), None),
        (URIRef(EX + "y"), SH.order, Literal(2), None),
    ]
