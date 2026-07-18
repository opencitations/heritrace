# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import cast
from zipfile import ZIP_DEFLATED, ZipFile

from filelock import FileLock
from oc_ocdm.support import find_paths
from rdflib import Dataset, URIRef
from rdflib_ocdm.ocdm_graph import OCDMGraphCommons
from rdflib_ocdm.query_utils import get_update_query
from rdflib_ocdm.support import get_entity_subgraph

JsonObject = dict[str, object]
JsonLdDocument = list[JsonObject]


@dataclass(frozen=True, slots=True)
class _EntityChange:
    graph_iri: str
    entity_uri: str
    entity: JsonObject | None
    merge: bool = False


class MetaRDFFileWriter:
    def __init__(
        self,
        rdf_dir: str,
        base_iri: str = "https://w3id.org/oc/meta/",
        dir_split_number: int = 10000,
        items_per_file: int = 1000,
    ) -> None:
        self.rdf_dir = Path(rdf_dir)
        self.base_iri = f"{base_iri.rstrip('/')}/"
        self.dir_split_number = dir_split_number
        self.items_per_file = items_per_file

    def persist(self, graph_set: OCDMGraphCommons) -> None:
        if not isinstance(graph_set, Dataset):
            msg = "MetaRDFFileWriter requires an RDF dataset"
            raise TypeError(msg)

        archive_changes: defaultdict[tuple[Path, str], list[_EntityChange]] = (
            defaultdict(list)
        )
        self._collect_data_changes(graph_set, archive_changes)
        self._collect_provenance_changes(graph_set, archive_changes)

        for (archive_path, member_name), changes in sorted(
            archive_changes.items(), key=lambda item: str(item[0][0])
        ):
            self._update_archive(archive_path, member_name, changes)

    def _collect_data_changes(
        self,
        graph_set: OCDMGraphCommons,
        archive_changes: defaultdict[tuple[Path, str], list[_EntityChange]],
    ) -> None:
        for entity_uri in sorted(graph_set.all_entities, key=str):
            update_query, _, _ = get_update_query(graph_set, entity_uri)
            if not update_query:
                continue

            metadata = graph_set.entity_index[entity_uri]
            archive = self._archive_location(entity_uri)
            if metadata["to_be_deleted"]:
                graph_iri = str(metadata["graph_iri"])
                entity = None
            else:
                graph_iri, entity = self._serialize_entity(
                    cast("Dataset", graph_set), entity_uri
                )

            archive_changes[archive].append(
                _EntityChange(
                    graph_iri=graph_iri,
                    entity_uri=str(entity_uri),
                    entity=entity,
                )
            )

    def _collect_provenance_changes(
        self,
        graph_set: OCDMGraphCommons,
        archive_changes: defaultdict[tuple[Path, str], list[_EntityChange]],
    ) -> None:
        provenance = graph_set.provenance
        for snapshot_uri in sorted(provenance.all_entities, key=str):
            graph_iri, entity = self._serialize_provenance_entity(
                provenance, snapshot_uri
            )
            archive_changes[self._archive_location(snapshot_uri)].append(
                _EntityChange(
                    graph_iri=graph_iri,
                    entity_uri=str(snapshot_uri),
                    entity=entity,
                    merge=True,
                )
            )

    def _archive_location(self, entity_uri: URIRef) -> tuple[Path, str]:
        base_dir = f"{self.rdf_dir}{os.sep}"
        _, json_path = find_paths(
            str(entity_uri),
            base_dir,
            self.base_iri,
            "_",
            self.dir_split_number,
            self.items_per_file,
        )
        path = Path(json_path)
        return path.with_suffix(".zip"), path.name

    @staticmethod
    def _serialize_entity(graph: Dataset, entity_uri: URIRef) -> tuple[str, JsonObject]:
        subgraph = get_entity_subgraph(graph, entity_uri)
        serialized = json.loads(subgraph.serialize(format="json-ld"))
        documents = cast("JsonLdDocument", serialized)
        document = documents[0]
        entities = cast("list[JsonObject]", document["@graph"])
        return cast("str", document["@id"]), entities[0]

    @classmethod
    def _serialize_provenance_entity(
        cls, provenance: Dataset, snapshot_uri: URIRef
    ) -> tuple[str, JsonObject]:
        graph_iri = URIRef(f"{str(snapshot_uri).split('/prov/se/', 1)[0]}/prov/")
        subgraph = Dataset()
        for subject, predicate, value, _ in provenance.quads(
            (snapshot_uri, None, None, None)
        ):
            subgraph.add((subject, predicate, value, graph_iri))  # type: ignore[arg-type]
        return cls._serialize_entity(subgraph, snapshot_uri)

    def _update_archive(
        self,
        archive_path: Path,
        member_name: str,
        changes: list[_EntityChange],
    ) -> None:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(f"{archive_path}.lock"):
            document = self._read_archive(archive_path, member_name)
            for change in changes:
                self._apply_change(document, change)
            self._write_archive(archive_path, member_name, document)

    @staticmethod
    def _read_archive(archive_path: Path, member_name: str) -> JsonLdDocument:
        if not archive_path.exists():
            return []
        with (
            ZipFile(archive_path) as archive,
            archive.open(member_name) as member,
        ):
            return cast("JsonLdDocument", json.load(member))

    @staticmethod
    def _apply_change(document: JsonLdDocument, change: _EntityChange) -> None:
        target_graph = next(
            (
                graph
                for graph in document
                if cast("str", graph["@id"]) == change.graph_iri
            ),
            None,
        )
        if target_graph is None:
            if change.entity is not None:
                document.append({"@id": change.graph_iri, "@graph": [change.entity]})
            return

        entities = cast("list[JsonObject]", target_graph["@graph"])
        entity_index = next(
            (
                index
                for index, entity in enumerate(entities)
                if cast("str", entity["@id"]) == change.entity_uri
            ),
            None,
        )
        if entity_index is None:
            if change.entity is not None:
                entities.append(change.entity)
            return

        if change.entity is None:
            del entities[entity_index]
        elif change.merge:
            entities[entity_index].update(change.entity)
        else:
            entities[entity_index] = change.entity

        if not entities:
            document.remove(target_graph)

    @staticmethod
    def _write_archive(
        archive_path: Path, member_name: str, document: JsonLdDocument
    ) -> None:
        with NamedTemporaryFile(
            dir=archive_path.parent,
            prefix=f".{archive_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

        try:
            with ZipFile(
                temporary_path,
                mode="w",
                compression=ZIP_DEFLATED,
                allowZip64=True,
            ) as archive:
                archive.writestr(
                    member_name,
                    json.dumps(
                        document,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode(),
                )
            with temporary_path.open("rb") as temporary_file:
                os.fsync(temporary_file.fileno())
            temporary_path.replace(archive_path)
        finally:
            temporary_path.unlink(missing_ok=True)
