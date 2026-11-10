# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from collections.abc import Iterator

from heritrace.utils.shacl_presentation import inverse_predicate, is_inverse_path


def without_inverse_properties(data: dict) -> dict:
    return {
        **data,
        "properties": {
            path: values
            for path, values in data["properties"].items()
            if not is_inverse_path(path)
        },
    }


def _inverse_values(data: dict) -> Iterator[tuple[str, dict]]:
    for path, values in data["properties"].items():
        predicate = inverse_predicate(path)
        if predicate is not None:
            for value in values:
                yield predicate, value


def new_inverse_entities(data: dict, subject_uri: str) -> list[dict]:
    return [
        {
            **value,
            "properties": {
                **value["properties"],
                predicate: [{"is_existing_entity": True, "entity_uri": subject_uri}],
            },
        }
        for predicate, value in _inverse_values(data)
        if "entity_type" in value
    ]


def existing_inverse_links(data: dict) -> list[tuple[str, str]]:
    return [
        (value["entity_uri"], predicate)
        for predicate, value in _inverse_values(data)
        if "is_existing_entity" in value
    ]


def _inverse_creation_changes(change: dict) -> list[dict]:
    data = change["data"]
    subject = change["subject"]
    remaining = without_inverse_properties(data)
    return [
        *([{**change, "data": remaining}] if remaining["properties"] else []),
        *(
            {"action": "create", "subject": None, "data": entity}
            for entity in new_inverse_entities(data, subject)
        ),
        *(
            {
                "action": "add_link",
                "subject": entity_uri,
                "predicate": predicate,
                "object": subject,
            }
            for entity_uri, predicate in existing_inverse_links(data)
        ),
    ]


def _inverse_deletion_change(change: dict, predicate: str) -> dict:
    return {
        "action": "delete",
        "subject": change["object"],
        "predicate": predicate,
        "object": change["subject"],
    }


def expand_inverse_changes(changes: list[dict]) -> list[dict]:
    expanded = []
    for change in changes:
        predicate = inverse_predicate(change.get("predicate", ""))
        if change["action"] == "create" and change.get("data"):
            expanded.extend(_inverse_creation_changes(change))
        elif change["action"] == "delete" and predicate is not None:
            expanded.append(_inverse_deletion_change(change, predicate))
        else:
            expanded.append(change)
    return expanded
