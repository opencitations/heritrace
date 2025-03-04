from datetime import datetime

from rdflib import Graph, Literal, URIRef
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from rdflib_ocdm.ocdm_graph import OCDMConjunctiveGraph, OCDMGraph
from rdflib_ocdm.reader import Reader
from rdflib_ocdm.storer import Storer


class Editor:
    def __init__(
        self,
        dataset_endpoint: str,
        provenance_endpoint: str,
        counter_handler: CounterHandler,
        resp_agent: URIRef,
        source: URIRef = None,
        c_time: datetime | None = None,
        dataset_is_quadstore: bool = True,
    ):
        self.dataset_endpoint = dataset_endpoint
        self.provenance_endpoint = provenance_endpoint
        self.counter_handler = counter_handler
        self.resp_agent = resp_agent
        self.source = source
        self.c_time = self.to_posix_timestamp(c_time)
        self.dataset_is_quadstore = dataset_is_quadstore
        self.g_set = (
            OCDMConjunctiveGraph(self.counter_handler)
            if self.dataset_is_quadstore
            else OCDMGraph(self.counter_handler)
        )

    def create(
        self,
        subject: URIRef,
        predicate: URIRef,
        value: Literal | URIRef,
        graph: URIRef | Graph | str = None,
    ) -> None:
        subject = URIRef(subject) if not isinstance(subject, URIRef) else subject
        predicate = URIRef(predicate) if not isinstance(predicate, URIRef) else predicate
        graph = (
            graph.identifier
            if graph and isinstance(graph, Graph)
            else URIRef(graph) if graph else None
        )

        if self.dataset_is_quadstore and graph:
            self.g_set.add(
                (subject, predicate, value, graph),
                resp_agent=self.resp_agent,
                primary_source=self.source,
            )
        else:
            self.g_set.add(
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
        graph: URIRef | Graph | str = None,
    ) -> None:
        subject = URIRef(subject) if not isinstance(subject, URIRef) else subject
        predicate = URIRef(predicate) if not isinstance(predicate, URIRef) else predicate
        graph = (
            graph.identifier
            if graph and isinstance(graph, Graph)
            else URIRef(graph) if graph else None
        )

        # Check if the triple exists before updating
        if self.dataset_is_quadstore and graph:
            if not (subject, predicate, old_value, graph) in self.g_set:
                raise Exception(
                    f"Triple ({subject}, {predicate}, {old_value}, {graph}) does not exist"
                )
            self.g_set.remove((subject, predicate, old_value, graph))
            self.g_set.add(
                (subject, predicate, new_value, graph),
                resp_agent=self.resp_agent,
                primary_source=self.source,
            )
        else:
            if not (subject, predicate, old_value) in self.g_set:
                raise Exception(
                    f"Triple ({subject}, {predicate}, {old_value}) does not exist"
                )
            self.g_set.remove((subject, predicate, old_value))
            self.g_set.add(
                (subject, predicate, new_value),
                resp_agent=self.resp_agent,
                primary_source=self.source,
            )

    def delete(
        self,
        subject: URIRef,
        predicate: URIRef = None,
        value=None,
        graph: URIRef | Graph | str = None,
    ) -> None:
        graph = (
            graph.identifier
            if isinstance(graph, Graph)
            else URIRef(graph) if graph else None
        )
        subject = URIRef(subject) if not isinstance(subject, URIRef) else subject
        predicate = (
            URIRef(predicate)
            if predicate and not isinstance(predicate, URIRef)
            else predicate
        )
        graph = (
            graph.identifier
            if graph and isinstance(graph, Graph)
            else URIRef(graph) if graph else None
        )

        if predicate is None:
            # Delete the entire entity
            # Check if the entity exists
            if self.dataset_is_quadstore:
                quads = list(self.g_set.quads((subject, None, None, None)))
                if not quads:
                    raise Exception(f"Entity {subject} does not exist")
                for quad in quads:
                    self.g_set.remove(quad)

                # Also remove any triples where this entity is the object
                object_quads = list(self.g_set.quads((None, None, subject, None)))
                for quad in object_quads:
                    self.g_set.remove(quad)
            else:
                triples = list(self.g_set.triples((subject, None, None)))
                if not triples:
                    raise Exception(f"Entity {subject} does not exist")
                for triple in triples:
                    self.g_set.remove(triple)

                # Also remove any triples where this entity is the object
                object_triples = list(self.g_set.triples((None, None, subject)))
                for triple in object_triples:
                    self.g_set.remove(triple)
            self.g_set.mark_as_deleted(subject)
        else:
            if value:
                # Check if the specific triple/quad exists before removing it
                if self.dataset_is_quadstore and graph:
                    if not (subject, predicate, value, graph) in self.g_set:
                        raise Exception(
                            f"Triple ({subject}, {predicate}, {value}, {graph}) does not exist"
                        )
                    self.g_set.remove((subject, predicate, value, graph))
                else:
                    if not (subject, predicate, value) in self.g_set:
                        raise Exception(
                            f"Triple ({subject}, {predicate}, {value}) does not exist"
                        )
                    self.g_set.remove((subject, predicate, value))
            else:
                # Check if any triples with the given subject and predicate exist
                if self.dataset_is_quadstore and graph:
                    quads = list(self.g_set.quads((subject, predicate, None, graph)))
                    if not quads:
                        raise Exception(
                            f"No triples found with subject {subject} and predicate {predicate} in graph {graph}"
                        )
                    for quad in quads:
                        self.g_set.remove(quad)
                else:
                    triples = list(self.g_set.triples((subject, predicate, None)))
                    if not triples:
                        raise Exception(
                            f"No triples found with subject {subject} and predicate {predicate}"
                        )
                    for triple in triples:
                        self.g_set.remove(triple)

        # Check if the entity is now empty and mark it as deleted if so
        if len(list(self.g_set.triples((subject, None, None)))) == 0:
            self.g_set.mark_as_deleted(subject)

    def import_entity(self, subject):
        Reader.import_entities_from_triplestore(
            self.g_set, self.dataset_endpoint, [subject]
        )

    def preexisting_finished(self):
        self.g_set.preexisting_finished(self.resp_agent, self.source, self.c_time)

    def save(self):
        self.g_set.generate_provenance()
        dataset_storer = Storer(self.g_set)
        prov_storer = Storer(self.g_set.provenance)
        dataset_storer.upload_all(self.dataset_endpoint)
        prov_storer.upload_all(self.provenance_endpoint)
        self.g_set.commit_changes()

    def to_posix_timestamp(self, value: str | datetime | None) -> float | None:
        if value is None:
            return None
        elif isinstance(value, datetime):
            return value.timestamp()
        elif isinstance(value, str):
            dt = datetime.fromisoformat(value)
            return dt.timestamp()
