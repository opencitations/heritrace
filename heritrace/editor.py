# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from dataclasses import dataclass
from datetime import datetime, timezone

from flask import current_app
from rdflib import Literal, URIRef
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from rdflib_ocdm.ocdm_graph import OCDMDataset, OCDMGraph
from rdflib_ocdm.reader import Reader
from rdflib_ocdm.storer import Storer
from SPARQLWrapper import JSON

from heritrace.sparql import SPARQLWrapperWithRetry, get_sparql_bindings


@dataclass(frozen=True, slots=True)
class EndpointConfig:
    dataset: str
    provenance: str
    is_quadstore: bool = True


class EditorError(Exception):
    pass


class Editor:
    def __init__(
        self,
        endpoints: EndpointConfig,
        counter_handler: CounterHandler,
        resp_agent: URIRef,
        source: URIRef | None = None,
        c_time: datetime | None = None,
    ) -> None:
        self.dataset_endpoint = endpoints.dataset
        self.provenance_endpoint = endpoints.provenance
        self.counter_handler = counter_handler
        self.resp_agent = resp_agent
        self.source = source
        self.c_time = self.to_posix_timestamp(c_time)
        self.dataset_is_quadstore = endpoints.is_quadstore
        self.g_set = (
            OCDMDataset(self.counter_handler)
            if self.dataset_is_quadstore
            else OCDMGraph(self.counter_handler)
        )

    def create(
        self,
        subject: URIRef,
        predicate: URIRef,
        value: Literal | URIRef,
        graph: URIRef | None = None,
    ) -> None:
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
        Reader.import_entities_from_triplestore(
            self.g_set,
            self.dataset_endpoint,
            [subject],  # type: ignore[arg-type]
        )

    def merge(self, keep_entity_uri: URIRef, delete_entity_uri: URIRef) -> None:
        if keep_entity_uri == delete_entity_uri:
            msg = "Cannot merge an entity with itself."
            raise ValueError(msg)

        merge_sparql = SPARQLWrapperWithRetry(self.dataset_endpoint)
        entities_to_import: set[URIRef] = {keep_entity_uri, delete_entity_uri}
        incoming_triples_to_update: list[tuple[URIRef, URIRef]] = []
        outgoing_triples_to_move: list[tuple[URIRef, Literal | URIRef]] = []

        query_incoming = (
            "SELECT DISTINCT ?s ?p WHERE {"
            f" ?s ?p <{delete_entity_uri}> ."
            f" FILTER (?s != <{keep_entity_uri}>) }}"
        )
        merge_sparql.setQuery(query_incoming)
        merge_sparql.setReturnFormat(JSON)
        for binding in get_sparql_bindings(merge_sparql.query().convert()):
            s_uri = URIRef(binding["s"]["value"])
            p_uri = URIRef(binding["p"]["value"])
            incoming_triples_to_update.append((s_uri, p_uri))
            entities_to_import.add(s_uri)

        query_outgoing = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT DISTINCT ?p ?o WHERE {{
                <{delete_entity_uri}> ?p ?o .
                FILTER (?p != rdf:type)
            }}
        """
        merge_sparql.setQuery(query_outgoing)
        merge_sparql.setReturnFormat(JSON)
        for binding in get_sparql_bindings(merge_sparql.query().convert()):
            p_uri = URIRef(binding["p"]["value"])
            o_node = binding["o"]
            o_val: Literal | URIRef | None = None
            if o_node["type"] == "uri":
                o_val = URIRef(o_node["value"])
                entities_to_import.add(o_val)
            elif o_node["type"] in {"literal", "typed-literal"}:
                o_val = Literal(
                    o_node["value"],
                    lang=o_node.get("xml:lang"),
                    datatype=URIRef(o_node["datatype"])
                    if o_node.get("datatype")
                    else None,
                )
            else:
                current_app.logger.warning(
                    "Skipping non-URI/Literal object type '%s' from %s via %s",
                    o_node["type"],
                    delete_entity_uri,
                    p_uri,
                )
                continue
            if o_val:
                outgoing_triples_to_move.append((p_uri, o_val))

        if entities_to_import:
            Reader.import_entities_from_triplestore(
                self.g_set,
                self.dataset_endpoint,
                list(entities_to_import),  # type: ignore[arg-type]
            )
        self.g_set.preexisting_finished(self.resp_agent, self.source, self.c_time)  # type: ignore[arg-type]

        self.g_set.merge(keep_entity_uri, delete_entity_uri)  # type: ignore[arg-type]

        self.save()

    def preexisting_finished(self) -> None:
        self.g_set.preexisting_finished(self.resp_agent, self.source, self.c_time)  # type: ignore[arg-type]

    def save(self) -> None:
        self.g_set.generate_provenance()  # type: ignore[arg-type]
        dataset_storer = Storer(self.g_set)  # type: ignore[arg-type]
        prov_storer = Storer(self.g_set.provenance)  # type: ignore[attr-defined]
        dataset_storer.upload_all(self.dataset_endpoint)  # type: ignore[arg-type]
        prov_storer.upload_all(self.provenance_endpoint)  # type: ignore[arg-type]
        self.g_set.commit_changes()  # type: ignore[arg-type]

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

    def set_primary_source(self, source: URIRef) -> None:
        self.source = source
