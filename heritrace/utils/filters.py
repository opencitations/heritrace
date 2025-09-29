from __future__ import annotations

import threading
from typing import Tuple
from urllib.parse import quote, urlparse

import dateutil
import validators
from flask import url_for
from flask_babel import format_datetime, gettext, lazy_gettext
from heritrace.apis.orcid import format_orcid_attribution, is_orcid_url
from heritrace.apis.zenodo import format_zenodo_source, is_zenodo_url
from rdflib import ConjunctiveGraph, Graph
from SPARQLWrapper import JSON


class Filter:
    def __init__(self, context: dict, display_rules: dict, sparql_endpoint: str):
        from heritrace.extensions import get_sparql

        self.context = context
        self.display_rules = display_rules
        self.sparql = get_sparql()
        self.sparql.setReturnFormat(JSON)
        self._query_lock = threading.Lock()

    def human_readable_predicate(self, predicate_uri: str, entity_key: tuple[str, str], is_link=False, object_shape_uri: str = None):
        """Get human readable label for a predicate in the context of an entity.
        
        Args:
            predicate_uri: URI of the predicate to get label for
            entity_key: Tuple of (class_uri, shape_uri) for the entity context
            is_link: Whether to format as a link
            object_shape_uri: Shape URI of the object entity (for shape-specific display rules)
            
        Returns:
            str: Human readable label for the predicate
        """
        from heritrace.utils.display_rules_utils import find_matching_rule
        
        class_uri, shape_uri = entity_key
        rule = find_matching_rule(class_uri, shape_uri, self.display_rules)
        
        if rule:
            if "displayProperties" in rule:
                for display_property in rule["displayProperties"]:
                    prop_uri = display_property.get("property") or display_property.get("virtual_property")
                    if prop_uri == str(predicate_uri):
                        if "displayRules" in display_property:
                            if object_shape_uri:
                                for display_rule in display_property["displayRules"]:
                                    if display_rule.get("shape") == object_shape_uri:
                                        return display_rule["displayName"]
                            return display_property["displayRules"][0]["displayName"]
                        elif "displayName" in display_property:
                            return display_property["displayName"]

        first_part, _ = split_namespace(predicate_uri) 
        if first_part in self.context:
            return format_uri_as_readable(predicate_uri)
        elif validators.url(predicate_uri) and is_link:
            return f"<a href='{url_for('entity.about', subject=quote(predicate_uri))}' alt='{gettext('Link to the entity %(entity)s', entity=predicate_uri)}'>{predicate_uri}</a>"
        else:
            return str(predicate_uri)

    def human_readable_class(self, entity_key):
        """
        Converts a class URI to human-readable format.

        Args:
            entity_key (tuple): A tuple containing (class_uri, shape_uri)

        Returns:
            str: Human-readable representation of the class
        """
        from heritrace.utils.display_rules_utils import find_matching_rule
        from heritrace.utils.shacl_utils import determine_shape_for_classes

        class_uri, shape_uri = entity_key

        if class_uri is None and shape_uri is None:
            return "Unknown"

        if shape_uri is None:
            shape_uri = determine_shape_for_classes([class_uri])
        rule = find_matching_rule(class_uri, shape_uri, self.display_rules)

        if rule and "displayName" in rule:
            return rule["displayName"]

        return format_uri_as_readable(class_uri)

    def human_readable_entity(
        self, uri: str, entity_key: tuple[str, str | None], graph: Graph | ConjunctiveGraph = None
    ) -> str:
        """Convert an entity URI to human-readable format using display rules.
        
        Args:
            uri: The URI of the entity to format
            entity_key: A tuple containing (class_uri, shape_uri)
            graph: Optional graph to use for fetching URI display values
            
        Returns:
            str: Human-readable representation of the entity
        """
        from heritrace.utils.display_rules_utils import find_matching_rule
        
        class_uri = entity_key[0]
        shape_uri = entity_key[1]

        rule = find_matching_rule(class_uri, shape_uri, self.display_rules)
        if not rule:
            return uri
            
        if "fetchUriDisplay" in rule:
            uri_display = self.get_fetch_uri_display(uri, rule, graph)
            if uri_display:
                return uri_display
                
        if "displayName" in rule:
            return rule["displayName"]

        return uri

    def get_fetch_uri_display(
        self, uri: str, rule: dict, graph: Graph | ConjunctiveGraph = None
    ) -> str | None:
        """Get a display value for an entity URI using fetchUriDisplay rules.
        
        Args:
            uri: The URI to get a display value for
            rule: The display rule containing the fetchUriDisplay query
            graph: Optional graph to use for fetching URI display values
            
        Returns:
            str | None: The display value if found, None otherwise
        """
        if "fetchUriDisplay" in rule:
            query = rule["fetchUriDisplay"].replace("[[uri]]", f"<{uri}>")
            if graph is not None:
                try:
                    with self._query_lock:
                        results = graph.query(query)
                    for row in results:
                        return str(row[0])
                except Exception as e:
                    print(
                        f"Error executing fetchUriDisplay query: {e}. {query}"
                    )
            else:
                self.sparql.setQuery(query)
                try:
                    results = self.sparql.query().convert()
                    if results["results"]["bindings"]:
                        first_binding = results["results"]["bindings"][0]
                        first_key = list(first_binding.keys())[0]
                        return first_binding[first_key]["value"]
                except Exception as e:
                    print(f"Error executing fetchUriDisplay query: {e}")
        return None

    def human_readable_datetime(self, dt_str):
        dt = dateutil.parser.parse(dt_str)
        return format_datetime(dt, format="long")


    def human_readable_primary_source(self, primary_source: str | None) -> str:
        if primary_source is None:
            return lazy_gettext("Unknown")
        if "/prov/se" in primary_source:
            version_url = f"/entity-version/{primary_source.replace('/prov/se', '')}"
            return (
                f"<a href='{version_url}' alt='{lazy_gettext('Link to the primary source description')}'>"
                + lazy_gettext("Version")
                + " "
                + primary_source.split("/prov/se/")[-1]
                + "</a>"
            )
        else:
            if validators.url(primary_source):
                return f"<a href='{primary_source}' alt='{lazy_gettext('Link to the primary source description')} target='_blank'>{primary_source}</a>"
            else:
                return primary_source

    def format_source_reference(self, url: str) -> str:
        """
        Format a source reference for display, handling various URL types including Zenodo DOIs and generic URLs.

        Args:
            url (str): The source URL or identifier to format
            human_readable_primary_source (callable): Function to handle generic/unknown source types

        Returns:
            str: Formatted HTML string representing the source
        """
        if not url:
            return "Unknown"

        # First check if it's a Zenodo DOI since this is more specific than a generic URL
        if is_zenodo_url(url):
            return format_zenodo_source(url)

        # If not Zenodo, use the provided generic handler
        return self.human_readable_primary_source(url)

    def format_agent_reference(self, url: str) -> str:
        """
        Format an agent reference for display, handling various URL types including ORCID and others.

        Args:
            url (str): The agent URL or identifier to format

        Returns:
            str: Formatted HTML string representing the agent
        """
        if not url:
            return "Unknown"

        if is_orcid_url(url):
            return format_orcid_attribution(url)

        # For now, just return a simple linked version for other URLs
        if validators.url(url):
            return f'<a href="{url}" target="_blank">{url}</a>'

        # If it's not a URL at all, just return the raw value
        return url


def split_namespace(uri: str) -> Tuple[str, str]:
    """
    Split a URI into namespace and local part.

    Args:
        uri: The URI to split

    Returns:
        Tuple of (namespace, local_part)
    """
    parsed = urlparse(uri)
    if parsed.fragment:
        first_part = parsed.scheme + "://" + parsed.netloc + parsed.path + "#"
        last_part = parsed.fragment
    else:
        first_part = (
            parsed.scheme
            + "://"
            + parsed.netloc
            + "/".join(parsed.path.split("/")[:-1])
            + "/"
        )
        last_part = parsed.path.split("/")[-1]
    return first_part, last_part


def format_uri_as_readable(uri: str) -> str:
    """
    Format a URI as human-readable text by extracting and formatting the local part.
    
    Args:
        uri: The URI to format
        
    Returns:
        Human-readable string
    """
    _, last_part = split_namespace(uri)
    
    if last_part.islower():
        return last_part
    else:
        # Convert CamelCase to space-separated words
        words = []
        word = ""
        for char in last_part:
            if char.isupper() and word:
                words.append(word)
                word = char
            else:
                word += char
        words.append(word)
        return " ".join(words).lower()