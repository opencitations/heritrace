from datetime import datetime
import argparse
import concurrent.futures
import csv
import os
import traceback
from typing import Dict, List, Set

from rdflib import Graph, Literal, URIRef
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from rdflib_ocdm.ocdm_graph import OCDMConjunctiveGraph, OCDMGraph
from rdflib_ocdm.reader import Reader
from rdflib_ocdm.storer import Storer
from SPARQLWrapper import SPARQLWrapper, JSON
from tqdm import tqdm


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

    def _normalize_params(self, subject, predicate=None, graph=None) -> tuple[URIRef, URIRef | None, URIRef | Graph | str | None]:
        """Normalizza i parametri comuni per le operazioni sui grafi."""
        # Normalizza il soggetto
        if not isinstance(subject, URIRef):
            subject = URIRef(subject)
            
        # Normalizza il predicato se fornito
        if predicate is not None and not isinstance(predicate, URIRef):
            predicate = URIRef(predicate)
            
        # Normalizza il grafo se fornito
        if graph is not None:
            if isinstance(graph, Graph):
                graph = graph.identifier
            elif isinstance(graph, str):
                graph = URIRef(graph)
                
        return subject, predicate, graph

    def create(
        self,
        subject: URIRef,
        predicate: URIRef,
        value: Literal | URIRef,
        graph: URIRef | Graph | str = None,
    ) -> None:
        # Normalizza i parametri
        subject, predicate, graph = self._normalize_params(subject, predicate, graph)
        
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
        # Normalizza i parametri
        subject, predicate, graph = self._normalize_params(subject, predicate, graph)

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
        # Normalizza i parametri
        subject, predicate, graph = self._normalize_params(subject, predicate, graph)
                
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

    def merge(self, keep_entity_uri: str, delete_entity_uri: str) -> None:
        """
        Merges one entity into another within the dataset.

        The delete_entity_uri will be removed, and its properties and
        incoming references will be transferred to keep_entity_uri.
        All operations are performed within the local graph set managed by
        this Editor instance and then saved, ensuring provenance capture.

        Args:
            keep_entity_uri: The URI of the entity to keep.
            delete_entity_uri: The URI of the entity to delete and merge from.

        Raises:
            ValueError: If keep_entity_uri and delete_entity_uri are the same.
            Exception: If errors occur during SPARQL queries or graph operations.
        """
        keep_uri, _, _ = self._normalize_params(keep_entity_uri)
        delete_uri, _, _ = self._normalize_params(delete_entity_uri)

        if keep_uri == delete_uri:
            raise ValueError("Cannot merge an entity with itself.")

        sparql = SPARQLWrapper(self.dataset_endpoint)
        entities_to_import: Set[URIRef] = {keep_uri, delete_uri}
        incoming_triples_to_update: List[tuple[URIRef, URIRef]] = []
        outgoing_triples_to_move: List[tuple[URIRef, Literal | URIRef]] = []

        try:
            # 1. Find incoming references to delete_uri
            # We fetch subjects and predicates pointing to the entity to be deleted.
            query_incoming = f"SELECT DISTINCT ?s ?p WHERE {{ ?s ?p <{delete_uri}> . FILTER (?s != <{keep_uri}>) }}"
            sparql.setQuery(query_incoming)
            sparql.setReturnFormat(JSON)
            results_incoming = sparql.query().convert()
            for result in results_incoming["results"]["bindings"]:
                s_uri = URIRef(result["s"]["value"])
                p_uri = URIRef(result["p"]["value"])
                incoming_triples_to_update.append((s_uri, p_uri))
                entities_to_import.add(s_uri) # Ensure referencing entities are loaded

            # 2. Find outgoing properties from delete_uri (excluding rdf:type)
            # We fetch predicates and objects of the entity to be deleted.
            query_outgoing = f"""
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                SELECT DISTINCT ?p ?o WHERE {{
                    <{delete_uri}> ?p ?o .
                    FILTER (?p != rdf:type)
                }}
            """
            sparql.setQuery(query_outgoing)
            sparql.setReturnFormat(JSON)
            results_outgoing = sparql.query().convert()
            for result in results_outgoing["results"]["bindings"]:
                p_uri = URIRef(result["p"]["value"])
                o_node = result["o"]
                o_val: Literal | URIRef | None = None
                if o_node["type"] == "uri":
                    o_val = URIRef(o_node["value"])
                    entities_to_import.add(o_val) # Ensure referenced entities are loaded
                elif o_node["type"] in {"literal", "typed-literal"}:
                     o_val = Literal(o_node["value"], lang=o_node.get("xml:lang"), datatype=URIRef(o_node["datatype"]) if o_node.get("datatype") else None)
                else: # bnode? Skip for now or handle if necessary
                    print(f"Warning: Skipping non-URI/Literal object type '{o_node['type']}' from {delete_uri} via {p_uri}")
                    continue
                if o_val:
                    outgoing_triples_to_move.append((p_uri, o_val))

            # 3. Import all involved entities into the local graph set
            # This brings the current state of these entities from the triplestore
            # into the Editor's context for modification.
            if entities_to_import:
                Reader.import_entities_from_triplestore(
                    self.g_set, self.dataset_endpoint, list(entities_to_import)
                )
            # Mark the start of modifications if using preexisting_finished pattern
            self.g_set.preexisting_finished(self.resp_agent, self.source, self.c_time)


            # 4. Process changes in the local graph set
            # The graph context handling here is simplified. It assumes operations
            # apply to the default graph or that OCDM handles context.
            # Refinement might be needed for multi-graph scenarios.
            graph_context = self.g_set.identifier if self.dataset_is_quadstore else None

            # Process incoming triples: delete old, create new pointing to keep_uri
            for s_uri, p_uri in incoming_triples_to_update:
                 try:
                     # Check if the triple to delete actually exists locally first
                     if self.dataset_is_quadstore:
                         if (s_uri, p_uri, delete_uri, graph_context) in self.g_set.quads((s_uri, p_uri, delete_uri, graph_context)):
                             self.delete(s_uri, p_uri, delete_uri, graph=graph_context)
                             self.create(s_uri, p_uri, keep_uri, graph=graph_context)
                     else:
                          if (s_uri, p_uri, delete_uri) in self.g_set.triples((s_uri, p_uri, delete_uri)):
                             self.delete(s_uri, p_uri, delete_uri)
                             self.create(s_uri, p_uri, keep_uri)
                 except Exception as e:
                     print(f"Warning: Could not replace incoming triple ({s_uri}, {p_uri}, {delete_uri}): {e}. Skipping this triple.")

            # Process outgoing triples: delete old, create new from keep_uri
            for p_uri, o_val in outgoing_triples_to_move:
                 try:
                      # Check if the triple to delete actually exists locally first
                     if self.dataset_is_quadstore:
                         if (delete_uri, p_uri, o_val, graph_context) in self.g_set.quads((delete_uri, p_uri, o_val, graph_context)):
                             self.delete(delete_uri, p_uri, o_val, graph=graph_context)
                             # Avoid creating duplicate outgoing triples
                             if (keep_uri, p_uri, o_val, graph_context) not in self.g_set.quads((keep_uri, p_uri, o_val, graph_context)):
                                 self.create(keep_uri, p_uri, o_val, graph=graph_context)
                     else:
                         if (delete_uri, p_uri, o_val) in self.g_set.triples((delete_uri, p_uri, o_val)):
                             self.delete(delete_uri, p_uri, o_val)
                             # Avoid creating duplicate outgoing triples
                             if (keep_uri, p_uri, o_val) not in self.g_set.triples((keep_uri, p_uri, o_val)):
                                 self.create(keep_uri, p_uri, o_val)
                 except Exception as e:
                     print(f"Warning: Could not move outgoing triple ({delete_uri}, {p_uri}, {o_val}): {e}. Skipping this triple.")


            # 5. Delete the merged entity entirely
            # This removes any remaining triples associated with delete_uri (like rdf:type)
            # and marks it as deleted in the provenance.
            try:
                 # Need to ensure the entity actually exists locally before deleting
                 # Check if triples exist for the subject before calling delete
                 if self.dataset_is_quadstore:
                     if list(self.g_set.quads((delete_uri, None, None, None))):
                        self.delete(delete_uri, graph=graph_context) # Pass graph context if applicable
                 else:
                     if list(self.g_set.triples((delete_uri, None, None))):
                        self.delete(delete_uri)
            except Exception as e:
                 # This might happen if the entity was already gone or import failed
                 print(f"Info: Entity {delete_uri} likely already deleted or did not exist locally. Merge continuing. ({e})")


            # 6. Save changes and provenance
            # This uploads the modified local graph and the generated provenance graph.
            self.save()

        except Exception as e:
            print(f"Error during merge operation for {keep_uri} and {delete_uri}: {e}")
            print(traceback.format_exc())
            # Avoid committing partial changes by not calling save()
            raise # Re-raise the exception to signal failure

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
