# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from rdflib import XSD, Graph, Literal, URIRef
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from rdflib_ocdm.ocdm_graph import OCDMDataset, OCDMGraph
from rdflib_ocdm.reader import Reader
from rdflib_ocdm.storer import Storer
from SPARQLWrapper import JSON

from heritrace.counter_handler import TransactionalCounterHandler
from heritrace.rdf_files import load_rdf_file
from heritrace.sparql import (
    LocalSparql,
    SparqlEndpoint,
    SPARQLWrapperWithRetry,
    get_sparql_bindings,
)

if TYPE_CHECKING:
    from heritrace.save_plugin import SavePlugin


class EditorError(Exception):
    pass


class Backend(Protocol):
    @property
    def is_quadstore(self) -> bool: ...

    def sparql(self) -> SparqlEndpoint: ...

    def import_entities(
        self, g_set: OCDMGraph | OCDMDataset, subjects: list[URIRef]
    ) -> None: ...

    def store(self, g_set: OCDMGraph | OCDMDataset) -> None: ...


@dataclass(frozen=True, slots=True)
class TriplestoreBackend:
    dataset: str
    provenance: str
    is_quadstore: bool = True

    def sparql(self) -> SparqlEndpoint:
        return SPARQLWrapperWithRetry(self.dataset)

    def import_entities(
        self, g_set: OCDMGraph | OCDMDataset, subjects: list[URIRef]
    ) -> None:
        Reader.import_entities_from_triplestore(g_set, self.dataset, subjects)

    def store(self, g_set: OCDMGraph | OCDMDataset) -> None:
        if not Storer(g_set).upload_all(self.dataset):
            msg = "Failed to update the dataset triplestore"
            raise EditorError(msg)
        if not Storer(g_set.provenance).upload_all(self.provenance):
            msg = "Failed to update the provenance triplestore"
            raise EditorError(msg)


# Keeps the data in a Turtle file and its provenance in a TriG file. Before
# writing, check receives the data as it will be after the change and raises to
# reject it, and export receives it once accepted. The caller holds a lock on
# the files for the whole change, from reading the counters to storing.
@dataclass(frozen=True, slots=True)
class FileBackend:
    data_path: Path
    provenance_path: Path
    check: Callable[[Graph], None]
    export: Callable[[Graph], None]
    after_store: Callable[[], object]
    is_quadstore: bool = False

    def sparql(self) -> SparqlEndpoint:
        return LocalSparql(lambda: load_rdf_file(self.data_path))

    def import_entities(
        self, g_set: OCDMGraph | OCDMDataset, subjects: list[URIRef]
    ) -> None:
        Reader.import_entities_from_graph(
            g_set, load_rdf_file(self.data_path), subjects
        )

    def store(self, g_set: OCDMGraph | OCDMDataset) -> None:
        candidate = Graph()
        for triple in load_rdf_file(self.data_path):
            candidate.add(triple)
        Storer(g_set).apply(candidate)
        self.check(candidate)
        draft = self.data_path.with_name(f".{self.data_path.name}.tmp")
        candidate.serialize(draft, format="turtle")
        self.export(candidate)
        Storer(g_set.provenance).store_file(self.provenance_path)
        draft.replace(self.data_path)
        self.after_store()


def _as_stored(value: Literal | URIRef) -> Literal | URIRef:
    if isinstance(value, Literal) and value.datatype == XSD.string:
        return Literal(str(value))
    return value


class Editor:
    def __init__(  # noqa: PLR0913
        self,
        backend: Backend,
        counter_handler: CounterHandler,
        resp_agent: URIRef,
        source: URIRef | None = None,
        c_time: datetime | None = None,
        save_plugin: "SavePlugin | None" = None,
    ) -> None:
        self.backend = backend
        self.counter_handler = counter_handler
        self.resp_agent = resp_agent
        self.source = source
        self.c_time = self.to_posix_timestamp(c_time)
        self.save_plugin = save_plugin
        self.dataset_is_quadstore = backend.is_quadstore
        self.transactional_counter_handler: TransactionalCounterHandler | None = (
            counter_handler
            if isinstance(counter_handler, TransactionalCounterHandler)
            else None
        )
        self._counter_transaction_started = False
        self.g_set = (
            OCDMDataset(self.counter_handler)
            if self.dataset_is_quadstore
            else OCDMGraph(self.counter_handler)
        )
        self.begin_counter_transaction()

    def create(
        self,
        subject: URIRef,
        predicate: URIRef,
        value: Literal | URIRef,
        graph: URIRef | None = None,
    ) -> None:
        value = _as_stored(value)
        if self.dataset_is_quadstore and graph:
            self.g_set.add(  # type: ignore[arg-type]
                (subject, predicate, value, graph),  # type: ignore[arg-type]
                resp_agent=self.resp_agent,
                primary_source=self.source,
            )
        else:
            self.g_set.add(  # type: ignore[arg-type]
                (subject, predicate, value),
                resp_agent=self.resp_agent,
                primary_source=self.source,
            )

    def update(
        self,
        subject: URIRef,
        predicate: URIRef,
        old_value: Literal | URIRef,
        new_value: Literal | URIRef,
        graph: URIRef | None = None,
    ) -> None:
        new_value = _as_stored(new_value)
        if self.dataset_is_quadstore and graph:
            if (subject, predicate, old_value, graph) not in self.g_set:  # type: ignore[operator]
                msg = (
                    f"Triple ({subject}, {predicate},"
                    f" {old_value}, {graph}) does not exist"
                )
                raise EditorError(msg)
            self.g_set.remove((subject, predicate, old_value, graph))  # type: ignore[arg-type]
            self.g_set.add(  # type: ignore[arg-type]
                (subject, predicate, new_value, graph),  # type: ignore[arg-type]
                resp_agent=self.resp_agent,
                primary_source=self.source,
            )
        else:
            if (subject, predicate, old_value) not in self.g_set:  # type: ignore[operator]
                msg = f"Triple ({subject}, {predicate}, {old_value}) does not exist"
                raise EditorError(msg)
            self.g_set.remove((subject, predicate, old_value))  # type: ignore[arg-type]
            self.g_set.add(  # type: ignore[arg-type]
                (subject, predicate, new_value),
                resp_agent=self.resp_agent,
                primary_source=self.source,
            )

    def _delete_full_entity(self, subject: URIRef) -> None:
        if self.dataset_is_quadstore:
            quads = list(self.g_set.quads((subject, None, None, None)))  # type: ignore[arg-type]
            if not quads:
                msg = f"Entity {subject} does not exist"
                raise EditorError(msg)
            for quad in quads:
                self.g_set.remove(quad)  # type: ignore[arg-type]

            object_quads = list(self.g_set.quads((None, None, subject, None)))  # type: ignore[arg-type]
            for quad in object_quads:
                self.g_set.remove(quad)  # type: ignore[arg-type]
        else:
            triples = list(self.g_set.triples((subject, None, None)))  # type: ignore[arg-type]
            if not triples:
                msg = f"Entity {subject} does not exist"
                raise EditorError(msg)
            for triple in triples:
                self.g_set.remove(triple)  # type: ignore[arg-type]

            object_triples = list(self.g_set.triples((None, None, subject)))  # type: ignore[arg-type]
            for triple in object_triples:
                self.g_set.remove(triple)  # type: ignore[arg-type]
        self.g_set.mark_as_deleted(subject)  # type: ignore[arg-type]

    def _delete_specific_triple(
        self,
        subject: URIRef,
        predicate: URIRef,
        value: Literal | URIRef,
        graph: URIRef | None,
    ) -> None:
        if self.dataset_is_quadstore and graph:
            if (subject, predicate, value, graph) not in self.g_set:  # type: ignore[operator]
                msg = (
                    f"Triple ({subject}, {predicate}, {value}, {graph}) does not exist"
                )
                raise EditorError(msg)
            self.g_set.remove((subject, predicate, value, graph))  # type: ignore[arg-type]
        else:
            if (subject, predicate, value) not in self.g_set:  # type: ignore[operator]
                msg = f"Triple ({subject}, {predicate}, {value}) does not exist"
                raise EditorError(msg)
            self.g_set.remove((subject, predicate, value))  # type: ignore[arg-type]

    def _delete_all_for_predicate(
        self,
        subject: URIRef,
        predicate: URIRef,
        graph: URIRef | None,
    ) -> None:
        if self.dataset_is_quadstore and graph:
            quads = list(self.g_set.quads((subject, predicate, None, graph)))  # type: ignore[arg-type]
            if not quads:
                msg = (
                    f"No triples found with subject"
                    f" {subject} and predicate"
                    f" {predicate} in graph {graph}"
                )
                raise EditorError(msg)
            for quad in quads:
                self.g_set.remove(quad)  # type: ignore[arg-type]
        else:
            triples = list(self.g_set.triples((subject, predicate, None)))  # type: ignore[arg-type]
            if not triples:
                msg = (
                    f"No triples found with subject {subject} and predicate {predicate}"
                )
                raise EditorError(msg)
            for triple in triples:
                self.g_set.remove(triple)  # type: ignore[arg-type]

    def delete(
        self,
        subject: URIRef,
        predicate: URIRef | None = None,
        value: Literal | URIRef | None = None,
        graph: URIRef | None = None,
    ) -> None:
        if predicate is None:
            self._delete_full_entity(subject)
        elif value:
            self._delete_specific_triple(subject, predicate, value, graph)
        else:
            self._delete_all_for_predicate(subject, predicate, graph)

        from heritrace.utils.sparql_utils import get_triples_from_graph  # noqa: PLC0415

        if len(list(get_triples_from_graph(self.g_set, (subject, None, None)))) == 0:
            self.g_set.mark_as_deleted(subject)  # type: ignore[arg-type]

    def import_entity(self, subject: URIRef) -> None:
        self.backend.import_entities(self.g_set, [subject])

    def merge(
        self,
        keep_entity_uri: URIRef,
        delete_entity_uri: URIRef,
        primary_source: URIRef | None = None,
    ) -> None:
        if keep_entity_uri == delete_entity_uri:
            msg = "Cannot merge an entity with itself."
            raise ValueError(msg)

        merge_sparql = self.backend.sparql()
        entities_to_import: set[URIRef] = {keep_entity_uri, delete_entity_uri}

        query_incoming = (
            "SELECT DISTINCT ?s WHERE {"
            f" ?s ?p <{delete_entity_uri}> ."
            f" FILTER (?s != <{keep_entity_uri}>) }}"
        )
        merge_sparql.setQuery(query_incoming)
        merge_sparql.setReturnFormat(JSON)
        for binding in get_sparql_bindings(merge_sparql.query().convert()):
            s_uri = URIRef(binding["s"]["value"])
            entities_to_import.add(s_uri)

        self.backend.import_entities(self.g_set, list(entities_to_import))
        self.begin_counter_transaction()
        self.g_set.preexisting_finished(self.resp_agent, self.source, self.c_time)  # type: ignore[arg-type]
        self.set_primary_source(primary_source)
        self.g_set.merge(keep_entity_uri, delete_entity_uri)  # type: ignore[arg-type]

        self.save()

    def preexisting_finished(self) -> None:
        self.begin_counter_transaction()
        self.g_set.preexisting_finished(self.resp_agent, self.source, self.c_time)  # type: ignore[arg-type]

    def save(self) -> None:
        self.begin_counter_transaction()
        try:
            self.g_set.generate_provenance()  # type: ignore[arg-type]
            self.backend.store(self.g_set)
            if self.save_plugin is not None:
                self.save_plugin.persist(self.g_set)
            self.g_set.commit_changes()  # type: ignore[arg-type]
            self._commit_counter_transaction()
        finally:
            if self._counter_transaction_started:
                self._rollback_counter_transaction()

    def begin_counter_transaction(self) -> None:
        if (
            self._counter_transaction_started
            or self.transactional_counter_handler is None
        ):
            return
        self.transactional_counter_handler.begin_counter_transaction()
        self._counter_transaction_started = True

    def _commit_counter_transaction(self) -> None:
        if (
            not self._counter_transaction_started
            or self.transactional_counter_handler is None
        ):
            return
        self.transactional_counter_handler.commit_counter_transaction()
        self._counter_transaction_started = False

    def _rollback_counter_transaction(self) -> None:
        if (
            not self._counter_transaction_started
            or self.transactional_counter_handler is None
        ):
            return
        self.transactional_counter_handler.rollback_counter_transaction()
        self._counter_transaction_started = False

    def to_posix_timestamp(self, value: str | datetime | None) -> float | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.timestamp()
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        return None

    def set_primary_source(self, source: URIRef | None) -> None:
        self.source = source
        for metadata in self.g_set.entity_index.values():  # type: ignore[union-attr]
            metadata["source"] = source
