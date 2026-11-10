# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from heritrace.apis.orcid import is_valid_orcid_id, normalize_orcid
from heritrace.configuration.settings import STRATEGIES, Settings
from heritrace.configuration.shapes import (
    EDITORS,
    VIEWERS,
    NodeShape,
    PropertyShape,
    Shapes,
)

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


def _validate_property(issues: list[Issue], location: str, prop: PropertyShape) -> None:
    _check_iri(issues, f"{location}.path", prop.path)
    for key, count in (("minCount", prop.min_count), ("maxCount", prop.max_count)):
        if count is not None and count < 0:
            issues.append(Issue(f"{location}.{key}", "The value cannot be negative"))
    if (
        prop.min_count is not None
        and prop.max_count is not None
        and prop.min_count > prop.max_count
    ):
        issues.append(
            Issue(f"{location}.maxCount", "The maximum is lower than the minimum")
        )
    if prop.editor is not None and prop.editor not in EDITORS:
        issues.append(Issue(f"{location}.editor", "Unknown editor"))
    if prop.viewer is not None and prop.viewer not in VIEWERS:
        issues.append(Issue(f"{location}.viewer", "Unknown viewer"))
    if prop.kind != "any" and not prop.values:
        issues.append(Issue(f"{location}.values", "Add at least one value"))
    for value in prop.values:
        _check_iri(issues, f"{location}.values", value)
    for detail_path in prop.details:
        _check_iri(issues, f"{location}.details", detail_path)


def _validate_shape(issues: list[Issue], location: str, shape: NodeShape) -> None:
    _check_iri(issues, f"{location}.iri", shape.iri)
    _check_iri(issues, f"{location}.targetClass", shape.target_class)
    for index, prop in enumerate(shape.properties):
        _validate_property(issues, f"{location}.properties.{index}", prop)
    for index, rule in enumerate(shape.patterns):
        rule_location = f"{location}.patterns.{index}"
        _check_iri(issues, f"{rule_location}.conditionPath", rule.condition_path)
        _check_iri(issues, f"{rule_location}.conditionValue", rule.condition_value)
        _check_iri(issues, f"{rule_location}.path", rule.path)
        try:
            re.compile(rule.pattern)
        except re.error:
            issues.append(
                Issue(f"{rule_location}.pattern", "This regular expression is invalid")
            )


def validate_shapes(shapes: Shapes) -> list[Issue]:
    issues: list[Issue] = []
    for index, prefix in enumerate(shapes.prefixes):
        if not _PREFIX.match(prefix):
            issues.append(Issue(f"prefixes.{index}.prefix", "Invalid prefix name"))
        _check_iri(issues, f"prefixes.{index}.namespace", shapes.prefixes[prefix])
    shape_iris = [shape.iri for shape in shapes.shapes]
    for index, shape in enumerate(shapes.shapes):
        if shape_iris.count(shape.iri) > 1:
            issues.append(
                Issue(f"shapes.{index}.iri", "Another entity type uses this IRI")
            )
        _validate_shape(issues, f"shapes.{index}", shape)
    return issues
