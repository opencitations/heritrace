from collections import defaultdict
from datetime import datetime

from config import Config
from rdflib import XSD, Graph, Literal, URIRef
from rdflib.plugins.sparql.algebra import translateUpdate
from rdflib.plugins.sparql.parser import parseUpdate
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from rdflib_ocdm.ocdm_graph import OCDMConjunctiveGraph, OCDMGraph
from rdflib_ocdm.reader import Reader
from rdflib_ocdm.storer import Storer
from SPARQLWrapper import JSON, POST, XML, SPARQLWrapper


class Editor:
    def __init__(
        self,
        dataset_endpoint: str,
        provenance_endpoint: str,
        counter_handler: CounterHandler,
        resp_agent: URIRef,
        source: URIRef = None,
        c_time: datetime | None = None,
    ):
        self.dataset_endpoint = dataset_endpoint
        self.provenance_endpoint = provenance_endpoint
        self.counter_handler = counter_handler
        self.resp_agent = resp_agent
        self.source = source
        self.c_time = self.to_posix_timestamp(c_time)
        self.dataset_is_quadstore = Config.DATASET_IS_QUADSTORE
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
        graph = (
            graph.identifier
            if isinstance(graph, Graph)
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
        graph = (
            graph.identifier
            if isinstance(graph, Graph)
            else URIRef(graph) if graph else None
        )
        if self.dataset_is_quadstore and graph:
            self.g_set.remove((subject, predicate, old_value, graph))
            self.g_set.add(
                (subject, predicate, new_value, graph),
                resp_agent=self.resp_agent,
                primary_source=self.source,
            )
        else:
            self.g_set.remove((subject, predicate, old_value))
            self.g_set.add(
                (subject, predicate, new_value),
                resp_agent=self.resp_agent,
                primary_source=self.source,
            )

    def delete(
        self,
        subject: str,
        predicate: str = None,
        value: str = None,
        graph: URIRef | Graph | str = None,
    ) -> None:
        subject = URIRef(subject)
        predicate = URIRef(predicate) if predicate else None
        graph = (
            graph.identifier
            if isinstance(graph, Graph)
            else URIRef(graph) if graph else None
        )

        if predicate is None:
            # Delete the entire entity
            if self.dataset_is_quadstore:
                for quad in list(self.g_set.quads((subject, None, None, None))):
                    self.g_set.remove(quad)
            else:
                for triple in list(self.g_set.triples((subject, None, None))):
                    self.g_set.remove(triple)
            # Mark the entity as deleted
            self.g_set.mark_as_deleted(subject)
        else:
            if value:
                # Remove the specific triple/quad directly
                if self.dataset_is_quadstore and graph:
                    self.g_set.remove((subject, predicate, value, graph))
                else:
                    self.g_set.remove((subject, predicate, value))
            else:
                # Remove all triples with the given subject and predicate
                if self.dataset_is_quadstore and graph:
                    for quad in list(
                        self.g_set.quads((subject, predicate, None, graph))
                    ):
                        self.g_set.remove(quad)
                else:
                    for triple in list(self.g_set.triples((subject, predicate, None))):
                        self.g_set.remove(triple)

        # Check if the entity is now empty and mark it as deleted if so
        if len(list(self.g_set.triples((subject, None, None)))) == 0:
            self.g_set.mark_as_deleted(subject)

    def import_entity_from_triplestore(self, res_list: list):
        sparql: SPARQLWrapper = SPARQLWrapper(self.dataset_endpoint)
        if self.dataset_is_quadstore:
            query: str = f"""
                SELECT ?g ?s ?p ?o (LANG(?o) AS ?lang)
                WHERE {{
                    GRAPH ?g {{?s ?p ?o}}.
                    VALUES ?s {{<{'> <'.join(res_list)}>}}
                }}"""
            sparql.setQuery(query)
            sparql.setMethod(POST)
            sparql.setReturnFormat(JSON)
            results = sparql.queryAndConvert()

            if (
                results is not None
                and "results" in results
                and "bindings" in results["results"]
            ):
                for result in results["results"]["bindings"]:
                    s = URIRef(result["s"]["value"])
                    p = URIRef(result["p"]["value"])
                    g = URIRef(result["g"]["value"])

                    obj_data = result["o"]
                    if obj_data["type"] == "uri":
                        o = URIRef(obj_data["value"])
                    else:
                        value = obj_data["value"]
                        lang = result.get("lang", {}).get("value")
                        datatype = obj_data.get("datatype")

                        if lang:
                            o = Literal(value, lang=lang)
                        elif datatype:
                            o = Literal(value, datatype=URIRef(datatype))
                        else:
                            o = Literal(value, datatype=XSD.string)

                    self.g_set.add(
                        (s, p, o, g),
                        resp_agent=self.resp_agent,
                        primary_source=self.source,
                    )
        else:
            query: str = f"""
                CONSTRUCT {{
                    ?s ?p ?o
                }}
                WHERE {{
                    ?s ?p ?o.
                    VALUES ?s {{<{'> <'.join(res_list)}>}}
                }}"""
            sparql.setQuery(query)
            sparql.setMethod(POST)
            sparql.setReturnFormat(XML)
            result: Graph = sparql.queryAndConvert()

            if result is not None:
                for triple in result:
                    self.g_set.add(
                        triple, resp_agent=self.resp_agent, primary_source=self.source
                    )

    def execute(self, sparql_query: str) -> None:
        parsed = parseUpdate(sparql_query)
        translated = translateUpdate(parsed).algebra
        entities_added = set()

        def extract_entities(operation):
            if hasattr(operation, "quads") and isinstance(operation.quads, defaultdict):
                for graph, triples in operation.quads.items():
                    for triple in triples:
                        yield triple[0]
            else:
                for triple in operation.triples:
                    yield triple[0]

        for operation in translated:
            for entity in extract_entities(operation):
                if entity not in entities_added:
                    Reader.import_entities_from_triplestore(
                        self.g_set, self.dataset_endpoint, [entity]
                    )
                    entities_added.add(entity)

        self.g_set.preexisting_finished(self.resp_agent, self.source, self.c_time)

        for operation in translated:
            if operation.name == "DeleteData":
                if hasattr(operation, "quads") and isinstance(
                    operation.quads, defaultdict
                ):
                    for graph, triples in operation.quads.items():
                        for triple in triples:
                            self.g_set.remove((triple[0], triple[1], triple[2], graph))
                else:
                    for triple in operation.triples:
                        self.g_set.remove(triple)
            elif operation.name == "InsertData":
                if hasattr(operation, "quads") and isinstance(
                    operation.quads, defaultdict
                ):
                    for graph, triples in operation.quads.items():
                        for triple in triples:
                            self.g_set.add((triple[0], triple[1], triple[2], graph))
                else:
                    for triple in operation.triples:
                        self.g_set.add(triple)

        if isinstance(self.g_set, OCDMConjunctiveGraph):
            for subject in self.g_set.subjects(unique=True):
                if len(list(self.g_set.quads((subject, None, None, None)))) == 0:
                    self.g_set.mark_as_deleted(subject)
        else:
            for subject in self.g_set.subjects(unique=True):
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
        if isinstance(value, datetime):
            return value.timestamp()
        elif isinstance(value, str):
            dt = datetime.fromisoformat(value)
            return dt.timestamp()
