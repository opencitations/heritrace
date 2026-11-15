# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

from pyparsing import ParseException
from rdflib import OWL, URIRef
from rdflib.plugins.sparql.algebra import translateQuery, traverse
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.term import Node

from heritrace.apis.orcid import is_valid_orcid_id, normalize_orcid
from heritrace.configuration.labels import compact_iri
from heritrace.configuration.settings import STRATEGIES, Settings
from heritrace.configuration.shapes import (
    EDITORS,
    SINGLE_VALUE_PREDICATES,
    VIEWERS,
    NodeShape,
    PropertyShape,
    Shapes,
)
from heritrace.configuration.vocabulary import HT, SH, SHUI
from heritrace.field_errors import FieldError, field_error
from heritrace.utils.value_bounds import NUMERIC_DATATYPES

_PREFIX = re.compile(r"^[A-Za-z][\w.-]*$")


@dataclass(frozen=True)
class Issue:
    location: str
    message: str


def is_iri(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme) and not any(char.isspace() for char in value)


def _check_iri(issues: list[Issue], location: str, value: str | None) -> None:
    if value is not None and not is_iri(value):
        issues.append(
            Issue(location, "Enter a full IRI, such as https://example.org/x")
        )


def validate_settings(settings: Settings) -> list[Issue]:
    issues: list[Issue] = []
    if not settings.app_title.strip():
        issues.append(Issue("settings.appTitle", "The title cannot be empty"))
    for key, value in (
        ("countLimit", settings.count_limit),
        ("catalogueDefaultPerPage", settings.catalogue_default_per_page),
    ):
        if value < 1:
            issues.append(Issue(f"settings.{key}", "The value must be at least 1"))
    _check_iri(issues, "settings.primarySource", settings.primary_source)
    for key, value in (
        ("orphanHandling", settings.orphan_handling),
        ("compositeHandling", settings.composite_handling),
    ):
        if value not in STRATEGIES:
            issues.append(Issue(f"settings.{key}", "Choose one of the strategies"))
    for index, orcid in enumerate(settings.orcid_safelist):
        if not is_valid_orcid_id(normalize_orcid(orcid)):
            issues.append(
                Issue(
                    f"settings.orcidSafelist.{index}",
                    "Enter an ORCID iD, such as 0000-0002-1825-0097",
                )
            )
    return issues


# The rules of the shapes, each reported on the editor resource and the field
# where it can be fixed. The shapes keep the nodes of the SHACL graph, which
# the caller turns into the IRIs of the editor.
@dataclass(frozen=True)
class _Report:
    errors: list[FieldError]
    editor_iri: Callable[[Node], str]
    prefixes: dict[str, str]

    def add(
        self,
        code: str,
        node: Node | None,
        predicate: URIRef | None,
        **params: str | int,
    ) -> None:
        subject = None if node is None else self.editor_iri(node)
        self.errors.append(field_error(code, subject, predicate, **params))

    def check_iri(
        self, node: Node | None, predicate: URIRef, value: str | None
    ) -> None:
        if value is not None and not is_iri(value):
            self.add("invalidIri", node, predicate)

    def compact(self, iri: str) -> str:
        namespaces = {namespace: prefix for prefix, namespace in self.prefixes.items()}
        return compact_iri(iri, namespaces)


_BOUNDS = {
    "min_inclusive": SH.minInclusive,
    "max_inclusive": SH.maxInclusive,
    "min_exclusive": SH.minExclusive,
    "max_exclusive": SH.maxExclusive,
}
_VALUE_PREDICATES = {**SINGLE_VALUE_PREDICATES, "options": SH["in"]}


def _validate_bounds(report: _Report, prop: PropertyShape) -> None:
    bounds = {key: getattr(prop, key) for key in _BOUNDS}
    numeric = prop.kind == "datatype" and all(
        datatype in NUMERIC_DATATYPES for datatype in prop.values
    )
    if not numeric:
        for key, bound in bounds.items():
            if bound is not None:
                report.add("boundsNeedNumber", prop.node, _BOUNDS[key])
        return
    lowers = [bounds["min_inclusive"], bounds["min_exclusive"]]
    for key in ("max_inclusive", "max_exclusive"):
        upper = bounds[key]
        if upper is not None and any(
            lower is not None and lower.toPython() > upper.toPython()
            for lower in lowers
        ):
            report.add("maxBelowMin", prop.node, _BOUNDS[key])


def _used_prefixes(tree: object) -> set[str]:
    used: set[str] = set()

    def visit(node: object) -> None:
        if isinstance(node, CompValue) and node.name == "pname":
            used.add(node.prefix or "")

    traverse(tree, visitPre=visit)
    return used


# HERITRACE runs a label query after the prefixes of the shapes graph, with
# $this and $language replaced by values.
def _label_query_problem(
    query: str, prefixes: dict[str, str]
) -> tuple[str, dict[str, str]] | None:
    declarations = "".join(
        f"PREFIX {prefix}: <{namespace}>\n" for prefix, namespace in prefixes.items()
    )
    try:
        tree = parseQuery(declarations + query)
    except ParseException as error:
        return "invalidSparql", {"error": str(error)}
    declared = {
        declaration.prefix or ""
        for declaration in tree[0]
        if declaration.name == "PrefixDecl"
    }
    undeclared = sorted(_used_prefixes(tree) - declared)
    if undeclared:
        return "undeclaredPrefixes", {"prefixes": ", ".join(undeclared)}
    algebra = translateQuery(tree).algebra
    if algebra.name != "SelectQuery" or len(algebra["PV"]) != 1:
        return "selectOneVariable", {}
    return None


def _validate_label_query(report: _Report, prop: PropertyShape) -> None:
    if prop.label_query is None:
        return
    if not prop.label:
        report.add("labelQueryRole", prop.node, SHUI.propertyRole)
    problem = _label_query_problem(prop.label_query, report.prefixes)
    if problem is not None:
        code, params = problem
        report.add(code, prop.label_query_node, SH.select, **params)


def _validate_counts(report: _Report, prop: PropertyShape) -> None:
    minimum, maximum = (
        (SH.qualifiedMinCount, SH.qualifiedMaxCount)
        if prop.qualified
        else (SH.minCount, SH.maxCount)
    )
    for predicate, count in ((minimum, prop.min_count), (maximum, prop.max_count)):
        if count is not None and count < 0:
            report.add("atLeast", prop.node, predicate, limit="0")
    if (
        prop.min_count is not None
        and prop.max_count is not None
        and prop.min_count > prop.max_count
    ):
        report.add("maxBelowMin", prop.node, maximum)
    if prop.qualified and prop.min_count is None and prop.max_count is None:
        report.add("countsMissing", prop.node, SH.qualifiedMinCount)


def _validate_property(report: _Report, prop: PropertyShape) -> None:
    report.check_iri(prop.node, SH.path, prop.path)
    report.check_iri(prop.node, HT.orderedBy, prop.ordered_by)
    _validate_counts(report, prop)
    _validate_bounds(report, prop)
    for predicate, value, known in (
        (SHUI.editor, prop.editor, EDITORS),
        (SHUI.viewer, prop.viewer, VIEWERS),
    ):
        if value is not None and value not in known:
            names = ", ".join(report.compact(widget) for widget in known)
            report.add("notAllowed", prop.node, predicate, values=names)
    values = (
        SH.qualifiedValueShape
        if prop.qualified or prop.kind == "any"
        else _VALUE_PREDICATES[prop.kind]
    )
    if prop.kind != "any" and not prop.values:
        report.add("tooFew", prop.node, values, count=0, min=1)
    for value in prop.values:
        report.check_iri(prop.node, values, value)
    for detail_path in prop.details:
        report.check_iri(prop.node, SH.property, detail_path)
    _validate_label_query(report, prop)


def _validate_shape(report: _Report, shape: NodeShape) -> None:
    node = URIRef(shape.iri)
    report.check_iri(node, SH.targetClass, shape.target_class)
    for prop in shape.properties:
        _validate_property(report, prop)
    for key in shape.duplicate_keys:
        if not key:
            report.add("tooFew", node, OWL.hasKey, count=0, min=1)
        for prop in key:
            report.check_iri(node, OWL.hasKey, prop)
    for rule in shape.patterns:
        report.check_iri(rule.node, HT.conditionPath, rule.condition_path)
        report.check_iri(rule.node, HT.conditionValue, rule.condition_value)
        report.check_iri(rule.node, HT.checkedPath, rule.path)
        try:
            re.compile(rule.pattern)
        except re.error:
            report.add("invalidRegex", rule.node, SH.pattern)
    _check_rule_coverage(report, shape)


# A resource matches the rules of its type only through one of them, and a value
# of the condition field that no rule names is therefore always rejected.
def _check_rule_coverage(report: _Report, shape: NodeShape) -> None:
    covered = {(rule.condition_path, rule.condition_value) for rule in shape.patterns}
    conditions = {path for path, _ in covered}
    for prop in shape.properties:
        if prop.path in conditions and not prop.inverse and prop.kind == "options":
            for value in prop.values:
                if (prop.path, value) not in covered:
                    report.add(
                        "missingFormatRule",
                        URIRef(shape.iri),
                        SH["or"],
                        value=report.compact(value),
                    )


def validate_shapes(
    shapes: Shapes, editor_iri: Callable[[Node], str]
) -> list[FieldError]:
    report = _Report([], editor_iri, shapes.prefixes)
    for prefix, namespace in shapes.prefixes.items():
        declaration = shapes.prefix_nodes[prefix]
        if not _PREFIX.match(prefix):
            report.add("invalidPrefix", declaration, SH.prefix)
        report.check_iri(declaration, SH.namespace, namespace)
    for shape in shapes.shapes:
        _validate_shape(report, shape)
    return report.errors
