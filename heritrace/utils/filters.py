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
from SPARQLWrapper import JSON, SPARQLWrapper


class Filter:
    def __init__(self, context: dict, display_rules: dict, sparql_endpoint: str):
        self.context = context
        self.display_rules = display_rules
        self.sparql = SPARQLWrapper(sparql_endpoint)
        self.sparql.setReturnFormat(JSON)
        self._query_lock = threading.Lock()

    def human_readable_predicate(
        self, url: str, entity_classes: list, is_link: bool = True
    ):
        subject_classes = [str(subject_class) for subject_class in entity_classes]
        if self.display_rules:
            for display_rule in self.display_rules:
                # Check if the rule has the expected structure
                if "target" in display_rule and "class" in display_rule["target"]:
                    rule_class = display_rule["target"]["class"]
                    for subject_class in subject_classes:
                        if subject_class == rule_class:
                            if url == subject_class:
                                return display_rule["displayName"]
                            
                            # Check if displayProperties exists before iterating
                            if "displayProperties" in display_rule:
                                for display_property in display_rule["displayProperties"]:
                                    if display_property["property"] == str(url):
                                        if "displayRules" in display_property:
                                            # Se ci sono displayRules, restituisci il primo displayName trovato
                                            return display_property["displayRules"][0][
                                                "displayName"
                                            ]
                                        elif "displayName" in display_property:
                                            # Se non ci sono displayRules ma c'è un displayName, restituiscilo
                                            return display_property["displayName"]
                            # If displayProperties is missing or property not found within it, 
                            # the loop continues to the next rule or falls through to default logic.

        # Se non è stato trovato un displayName nelle regole di visualizzazione,
        # procedi con la logica originale
        first_part, last_part = self.split_ns(url)
        if first_part in self.context:
            if last_part.islower():
                return last_part
            else:
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
        elif validators.url(url) and is_link:
            return f"<a href='{url_for('entity.about', subject=quote(url))}' alt='{gettext('Link to the entity %(entity)s', entity=url)}'>{url}</a>"
        else:
            return url

    def human_readable_entity(
        self, uri: str, entity_classes: list, graph: Graph | ConjunctiveGraph = None
    ) -> str:
        subject_classes = [str(subject_class) for subject_class in entity_classes]

        # Cerca prima una configurazione fetchUriDisplay
        uri_display = self.get_fetch_uri_display(uri, subject_classes, graph)
        if uri_display:
            return uri_display

        # Se non trova nulla, restituisce l'URI originale
        return uri

    def get_fetch_uri_display(
        self, uri: str, entity_classes: list, graph: Graph | ConjunctiveGraph = None
    ) -> str | None:
        for entity_class in entity_classes:
            for rule in self.display_rules:
                # Check if the rule has the expected structure
                if "target" in rule and "class" in rule["target"] and rule["target"]["class"] == entity_class and "fetchUriDisplay" in rule:
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
                                # Prendi il primo binding e il primo (e unico) valore
                                first_binding = results["results"]["bindings"][0]
                                first_key = list(first_binding.keys())[0]
                                return first_binding[first_key]["value"]
                        except Exception as e:
                            print(f"Error executing fetchUriDisplay query: {e}")
        return None

    def human_readable_datetime(self, dt_str):
        dt = dateutil.parser.parse(dt_str)
        return format_datetime(dt, format="long")

    def split_ns(self, ns: str) -> Tuple[str, str]:
        parsed = urlparse(ns)
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
