# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast
from zipfile import ZipFile

from rdflib import RDF, XSD, Dataset, Graph, Literal, URIRef
from rdflib_ocdm.counter_handler.in_memory_counter_handler import (
    InMemoryCounterHandler,
)
from rdflib_ocdm.ocdm_graph import OCDMDataset

from default_components.meta_rdf_file_writer import MetaRDFFileWriter

BASE_IRI = "https://w3id.org/oc/meta/"
GRAPH_IRI = URIRef(f"{BASE_IRI}br/")
GRAPH = Graph(identifier=GRAPH_IRI)
ENTITY_TYPE = URIRef("http://purl.org/spar/fabio/Expression")
TITLE = URIRef("http://purl.org/dc/terms/title")
RESP_AGENT = URIRef("https://orcid.org/0000-0002-8420-0696")
PRIMARY_SOURCE = URIRef("https://example.org/source")
PROV_INVALIDATED_AT_TIME = "http://www.w3.org/ns/prov#invalidatedAtTime"

JsonObject = dict[str, object]
JsonLdDocument = list[JsonObject]


def _add_entity(graph: OCDMDataset, subject: URIRef, title: str) -> None:
    graph.add(
        (subject, RDF.type, ENTITY_TYPE, GRAPH),
        resp_agent=RESP_AGENT,
        primary_source=PRIMARY_SOURCE,
    )
    graph.add(
        (
            subject,
            TITLE,
            Literal(title, datatype=XSD.string),
            GRAPH,
        ),
        resp_agent=RESP_AGENT,
        primary_source=PRIMARY_SOURCE,
    )


def _new_entities(
    counter: InMemoryCounterHandler,
    entities: list[tuple[URIRef, str]],
    timestamp: float,
) -> OCDMDataset:
    graph = OCDMDataset(counter)
    graph.preexisting_finished()
    for subject, title in entities:
        _add_entity(graph, subject, title)
    graph.generate_provenance(c_time=timestamp)
    return graph


def _existing_entity(
    counter: InMemoryCounterHandler, subject: URIRef, title: str
) -> OCDMDataset:
    graph = OCDMDataset(counter)
    _add_entity(graph, subject, title)
    graph.preexisting_finished(RESP_AGENT, PRIMARY_SOURCE)
    return graph


def _read_archive(path: Path, member_name: str) -> JsonLdDocument:
    with ZipFile(path) as archive:
        return cast("JsonLdDocument", json.loads(archive.read(member_name)))


def _entities(document: JsonLdDocument) -> dict[str, JsonObject]:
    return {
        cast("str", entity["@id"]): entity
        for graph in document
        for entity in cast("list[JsonObject]", graph["@graph"])
    }


def _serialized_provenance(graph: Dataset) -> dict[str, JsonObject]:
    serialized = cast("JsonLdDocument", json.loads(graph.serialize(format="json-ld")))
    return _entities(serialized)


def _apply_provenance_changes(
    existing: dict[str, JsonObject], graph: OCDMDataset
) -> dict[str, JsonObject]:
    expected = {entity_uri: entity.copy() for entity_uri, entity in existing.items()}
    changes = _serialized_provenance(graph.get_provenance_graphs())
    for snapshot_uri in graph.provenance.all_entities:
        changes[str(snapshot_uri)]["@type"] = ["http://www.w3.org/ns/prov#Entity"]
    for entity_uri, change in changes.items():
        if entity_uri in expected:
            expected[entity_uri].update(change)
        else:
            expected[entity_uri] = change
    return expected


def test_writes_new_data_and_provenance_archives(tmp_path: Path) -> None:
    subject = URIRef(f"{BASE_IRI}br/091101")
    graph = _new_entities(InMemoryCounterHandler(), [(subject, "Initial title")], 1000)

    MetaRDFFileWriter(str(tmp_path)).persist(graph)

    data_path = tmp_path / "br" / "09110" / "10000" / "1000.zip"
    provenance_path = tmp_path / "br" / "09110" / "10000" / "1000" / "prov" / "se.zip"
    assert _read_archive(data_path, "1000.json") == [
        {
            "@id": f"{BASE_IRI}br/",
            "@graph": [
                {
                    "@id": str(subject),
                    "@type": [str(ENTITY_TYPE)],
                    str(TITLE): [
                        {
                            "@type": str(XSD.string),
                            "@value": "Initial title",
                        }
                    ],
                }
            ],
        }
    ]
    assert _read_archive(provenance_path, "se.json") == [
        {
            "@id": f"{subject}/prov/",
            "@graph": [
                {
                    "@id": f"{subject}/prov/se/1",
                    "@type": ["http://www.w3.org/ns/prov#Entity"],
                    "http://purl.org/dc/terms/description": [
                        {
                            "@type": str(XSD.string),
                            "@value": f"The entity '{subject}' has been created.",
                        }
                    ],
                    "http://www.w3.org/ns/prov#generatedAtTime": [
                        {
                            "@type": str(XSD.dateTime),
                            "@value": "1970-01-01T00:16:40+00:00",
                        }
                    ],
                    "http://www.w3.org/ns/prov#hadPrimarySource": [
                        {"@id": str(PRIMARY_SOURCE)}
                    ],
                    "http://www.w3.org/ns/prov#specializationOf": [
                        {"@id": str(subject)}
                    ],
                    "http://www.w3.org/ns/prov#wasAttributedTo": [
                        {"@id": str(RESP_AGENT)}
                    ],
                }
            ],
        }
    ]
    assert data_path.stat().st_mode & 0o777 == 0o644
    assert data_path.stat().st_uid == tmp_path.stat().st_uid
    assert data_path.stat().st_gid == tmp_path.stat().st_gid
    data_lock_path = Path(f"{data_path}.lock")
    assert data_lock_path.stat().st_mode & 0o777 == 0o644
    assert data_lock_path.stat().st_uid == tmp_path.stat().st_uid
    assert data_lock_path.stat().st_gid == tmp_path.stat().st_gid


def test_updates_and_deletes_without_losing_shared_archive_content(
    tmp_path: Path,
) -> None:
    counter = InMemoryCounterHandler()
    subject = URIRef(f"{BASE_IRI}br/091101")
    unrelated = URIRef(f"{BASE_IRI}br/091102")
    writer = MetaRDFFileWriter(str(tmp_path))
    initial = _new_entities(
        counter,
        [(subject, "Initial title"), (unrelated, "Unrelated title")],
        1000,
    )
    writer.persist(initial)

    data_path = tmp_path / "br" / "09110" / "10000" / "1000.zip"
    provenance_path = tmp_path / "br" / "09110" / "10000" / "1000" / "prov" / "se.zip"
    initial_provenance = _entities(_read_archive(provenance_path, "se.json"))
    data_path.chmod(0o640)

    updated = _existing_entity(counter, subject, "Initial title")
    updated.remove(
        (
            subject,
            TITLE,
            Literal("Initial title", datatype=XSD.string),
            GRAPH,
        )
    )
    updated.add(
        (
            subject,
            TITLE,
            Literal("Updated title", datatype=XSD.string),
            GRAPH,
        )
    )
    updated.generate_provenance(c_time=2000)
    writer.persist(updated)

    assert _entities(_read_archive(data_path, "1000.json")) == {
        str(subject): {
            "@id": str(subject),
            "@type": [str(ENTITY_TYPE)],
            str(TITLE): [{"@type": str(XSD.string), "@value": "Updated title"}],
        },
        str(unrelated): {
            "@id": str(unrelated),
            "@type": [str(ENTITY_TYPE)],
            str(TITLE): [{"@type": str(XSD.string), "@value": "Unrelated title"}],
        },
    }
    expected_after_update = _apply_provenance_changes(initial_provenance, updated)
    assert _entities(_read_archive(provenance_path, "se.json")) == (
        expected_after_update
    )
    assert expected_after_update[f"{subject}/prov/se/1"][PROV_INVALIDATED_AT_TIME] == [
        {
            "@type": str(XSD.dateTime),
            "@value": "1970-01-01T00:33:20+00:00",
        }
    ]
    assert data_path.stat().st_mode & 0o777 == 0o640

    deleted = _existing_entity(counter, subject, "Updated title")
    for quad_subject, predicate, value, context in list(
        deleted.quads((subject, None, None, None))
    ):
        deleted.remove(
            (
                quad_subject,
                predicate,
                value,
                deleted.graph(context),
            )
        )
    deleted.mark_as_deleted(subject)
    deleted.generate_provenance(c_time=3000)
    writer.persist(deleted)

    assert _entities(_read_archive(data_path, "1000.json")) == {
        str(unrelated): {
            "@id": str(unrelated),
            "@type": [str(ENTITY_TYPE)],
            str(TITLE): [{"@type": str(XSD.string), "@value": "Unrelated title"}],
        }
    }
    assert _entities(_read_archive(provenance_path, "se.json")) == (
        _apply_provenance_changes(expected_after_update, deleted)
    )


def test_concurrent_writes_to_the_same_archives_preserve_both_entities(
    tmp_path: Path,
) -> None:
    first = URIRef(f"{BASE_IRI}br/091101")
    second = URIRef(f"{BASE_IRI}br/091102")
    graphs = [
        _new_entities(InMemoryCounterHandler(), [(first, "First")], 1000),
        _new_entities(InMemoryCounterHandler(), [(second, "Second")], 1000),
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(
            executor.map(
                MetaRDFFileWriter(str(tmp_path)).persist,
                graphs,
            )
        )

    data_path = tmp_path / "br" / "09110" / "10000" / "1000.zip"
    provenance_path = tmp_path / "br" / "09110" / "10000" / "1000" / "prov" / "se.zip"
    assert _entities(_read_archive(data_path, "1000.json")) == {
        str(first): {
            "@id": str(first),
            "@type": [str(ENTITY_TYPE)],
            str(TITLE): [{"@type": str(XSD.string), "@value": "First"}],
        },
        str(second): {
            "@id": str(second),
            "@type": [str(ENTITY_TYPE)],
            str(TITLE): [{"@type": str(XSD.string), "@value": "Second"}],
        },
    }
    assert set(_entities(_read_archive(provenance_path, "se.json"))) == {
        f"{first}/prov/se/1",
        f"{second}/prov/se/1",
    }
