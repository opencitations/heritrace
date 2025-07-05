"""
Virtual properties utilities for display rules.

This module contains functions for processing virtual properties which allow
entities to display computed or derived relationships that don't exist directly
in the knowledge graph.
"""

from typing import Dict, List, Optional, Tuple, Union

from heritrace.extensions import get_sparql
from rdflib import Graph, Literal, URIRef
from SPARQLWrapper import JSON


def process_virtual_properties(subject: str, rule: Dict, historical_snapshot: Optional[Graph] = None) -> List[Tuple[URIRef, URIRef, Union[URIRef, Literal]]]:
    """
    Process virtual properties for an entity based on display rules.
    
    Args:
        subject: URI of the entity
        rule: Display rule configuration for the entity
        historical_snapshot: Optional historical snapshot graph
        
    Returns:
        List of virtual property triples as (URIRef, URIRef, URIRef|Literal)
    """
    virtual_triples = []
    
    if not rule:
        return virtual_triples
    
    for prop_config in rule["displayProperties"]:
        if "virtual_property" in prop_config and "implementedVia" in prop_config:
            virtual_prop_uri = prop_config["virtual_property"]
            implementation = prop_config["implementedVia"]
            
            values = fetch_virtual_property_values(
                subject, 
                implementation, 
                historical_snapshot
            )
            
            for value in values:
                virtual_triples.append((URIRef(subject), URIRef(virtual_prop_uri), value))
    
    return virtual_triples


def fetch_virtual_property_values(subject: str, implementation: Dict, historical_snapshot: Optional[Graph] = None) -> List[Union[URIRef, Literal]]:
    """
    Fetch values for a virtual property based on its implementation.
    
    Args:
        subject: URI of the entity
        implementation: Implementation configuration from display rules
        historical_snapshot: Optional historical snapshot graph
        
    Returns:
        List of target entities (URIRef, Literal, etc.)
    """
    intermediate_class = implementation["class"]
    source_property = implementation["sourceProperty"]
    target_property = implementation["targetProperty"]
    
    if historical_snapshot:
        return fetch_virtual_property_values_from_graph(
            subject, intermediate_class, source_property, target_property, historical_snapshot
        )
    else:
        return fetch_virtual_property_values_from_sparql(
            subject, intermediate_class, source_property, target_property
        )


def fetch_virtual_property_values_from_sparql(subject: str, intermediate_class: str, source_property: str, target_property: str) -> List[Union[URIRef, Literal]]:
    """
    Fetch virtual property values using SPARQL query.
    
    Args:
        subject: URI of the entity
        intermediate_class: Class of the intermediate entity
        source_property: Property linking intermediate entity to source
        target_property: Property linking intermediate entity to target
        
    Returns:
        List of target entities (URIRef, Literal, etc.)
    """
    sparql = get_sparql()
    
    query = f"""
    SELECT DISTINCT ?target WHERE {{
        ?intermediate a <{intermediate_class}> .
        ?intermediate <{source_property}> <{subject}> .
        ?intermediate <{target_property}> ?target .
    }}
    """
    
    try:
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        
        values = []
        for binding in results["results"]["bindings"]:
            target = binding["target"]
            if target["type"] == "uri":
                values.append(URIRef(target["value"]))
            elif target["type"] in {"literal", "typed-literal"}:
                if "datatype" in target:
                    values.append(Literal(target["value"], datatype=URIRef(target["datatype"])))
                elif "xml:lang" in target:
                    values.append(Literal(target["value"], lang=target["xml:lang"]))
                else:
                    values.append(Literal(target["value"]))
        
        return values
    except Exception as e:
        print(f"Error fetching virtual property values: {e}")
        return []


def fetch_virtual_property_values_from_graph(subject: str, intermediate_class: str, source_property: str, target_property: str, graph: Graph) -> List[Union[URIRef, Literal]]:
    """
    Fetch virtual property values from a historical graph snapshot.
    
    Args:
        subject: URI of the entity
        intermediate_class: Class of the intermediate entity
        source_property: Property linking intermediate entity to source
        target_property: Property linking intermediate entity to target
        graph: Historical graph snapshot
        
    Returns:
        List of target entities (URIRef, Literal, etc.)
    """
    targets = []
    
    for intermediate in graph.subjects(URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef(intermediate_class), unique=True):
        if (intermediate, URIRef(source_property), URIRef(subject)) in graph:
            for target in graph.objects(intermediate, URIRef(target_property), unique=True):
                targets.append(target)
    
    return targets
