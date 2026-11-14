# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from rdflib import Dataset, Graph, Literal, URIRef

from heritrace.configuration.vocabulary import SH
from heritrace.sparql import get_sparql_bindings, select_results
from heritrace.utils.filters import Filter

_PREFIXES = (
    "SELECT ?prefix ?namespace WHERE {"
    f" ?declaration {SH.prefix.n3()} ?prefix ; {SH.namespace.n3()} ?namespace }}"
)


def compact_iri(iri: str, prefixes: dict[str, str]) -> str:
    namespace = max(
        (namespace for namespace in prefixes if iri.startswith(namespace)),
        key=len,
        default=None,
    )
    if namespace is None:
        return iri
    return f"{prefixes[namespace]}:{iri.removeprefix(namespace)}"


# The configuration editor works with IRIs: it shows each one in the compact
# form that the declared prefixes give, unless the meta-shapes name it.
class ConfigurationFilter(Filter):
    def _iri_labels(
        self, values: list[URIRef], graph: Graph | Dataset | None
    ) -> dict[URIRef | Literal, str]:
        prefixes = self._prefixes(graph)
        return {
            value: self.presentation.value_name(str(value))
            or compact_iri(str(value), prefixes)
            for value in values
        }

    def _prefixes(self, graph: Graph | Dataset | None) -> dict[str, str]:
        if graph is not None:
            with self._query_lock:
                results = graph.query(_PREFIXES)
            return {
                str(namespace): str(prefix)
                for prefix, namespace in select_results(results)
            }
        sparql = self._get_sparql()
        sparql.setQuery(_PREFIXES)
        return {
            binding["namespace"]["value"]: binding["prefix"]["value"]
            for binding in get_sparql_bindings(sparql.query().convert())
        }
