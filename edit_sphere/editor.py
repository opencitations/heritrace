from datetime import datetime

from rdflib import ConjunctiveGraph, Literal, URIRef
from rdflib.plugins.sparql.algebra import translateUpdate
from rdflib.plugins.sparql.parser import parseUpdate
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from rdflib_ocdm.ocdm_graph import OCDMGraph
from rdflib_ocdm.storer import Reader, Storer
from SPARQLWrapper import POST, XML, SPARQLWrapper


class Editor:
    def __init__(self, dataset_endpoint: str, provenance_endpoint:str, counter_handler: CounterHandler, resp_agent: URIRef, source: URIRef = None, c_time: datetime|None = None):
        self.dataset_endpoint = dataset_endpoint
        self.provenance_endpoint = provenance_endpoint
        self.counter_handler = counter_handler
        self.resp_agent = resp_agent
        self.source = source
        self.c_time = self.to_posix_timestamp(c_time)
        self.g_set = OCDMGraph(self.counter_handler)

    def create(self, subject: URIRef, predicate: URIRef, value: Literal|URIRef) -> None:
        self.g_set.add((subject, predicate, value))

    def update(self, subject: URIRef, predicate: URIRef, old_value: Literal|URIRef, new_value: Literal|URIRef) -> None:
        self.g_set.remove((subject, predicate, old_value))
        self.g_set.add((subject, predicate, new_value))

    def delete(self, subject: str, predicate: str = None, value: str = None) -> None:
        subject = URIRef(subject)
        predicate = URIRef(predicate)
        if predicate:
            if value:
                for triple in self.g_set.triples((subject, predicate, None)):
                    if str(value) == str(triple[2]):
                        self.g_set.remove(triple)
        if len(self.g_set) == 0:
            self.g_set.mark_as_deleted(subject)

    def import_entity_from_triplestore(self, res_list: list):
        sparql: SPARQLWrapper = SPARQLWrapper(self.dataset_endpoint)
        query: str = f'''
            CONSTRUCT {{?s ?p ?o}} 
            WHERE {{
                ?s ?p ?o. 
                VALUES ?s {{<{'> <'.join(res_list)}>}}
        }}'''
        sparql.setQuery(query)
        sparql.setMethod(POST)
        sparql.setReturnFormat(XML)
        result: ConjunctiveGraph = sparql.queryAndConvert()
        if result is not None:
            for triple in result.triples((None, None, None)):
                self.g_set.add(triple)

    def execute(self, sparql_query: str) -> None:
        parsed = parseUpdate(sparql_query)
        translated = translateUpdate(parsed).algebra
        entities_added = set()
        for operation in translated:
            for triple in operation.triples:
                entity = triple[0]
                if entity not in entities_added:
                    Reader.import_entities_from_triplestore(self.g_set, self.dataset_endpoint, [entity])
                    entities_added.add(entity)
        self.g_set.preexisting_finished(self.resp_agent, self.source, self.c_time)
        for operation in translated:
            if operation.name == "DeleteData":
                for triple in operation.triples:
                    self.g_set.remove(triple)
            elif operation.name == "InsertData":
                for triple in operation.triples:
                    self.g_set.add(triple)
        for subject in self.g_set.subjects(unique=True):
            if len(list(self.g_set.triples((subject, None, None)))) == 0:
                self.g_set.mark_as_deleted(subject)

    def import_entity(self, subject):
        Reader.import_entities_from_triplestore(self.g_set, self.dataset_endpoint, [subject])
    
    def preexisting_finished(self):
        self.g_set.preexisting_finished(self.resp_agent, self.source, self.c_time)
    
    def save(self):
        self.g_set.generate_provenance()
        dataset_storer = Storer(self.g_set)
        prov_storer = Storer(self.g_set.provenance)
        dataset_storer.upload_all(self.dataset_endpoint)
        prov_storer.upload_all(self.provenance_endpoint)
        self.g_set.commit_changes()

    def to_posix_timestamp(self, value: str|datetime|None) -> float|None:
        if isinstance(value, datetime):
            return value.timestamp()
        elif isinstance(value, str):
            dt = datetime.fromisoformat(value)
            return dt.timestamp()