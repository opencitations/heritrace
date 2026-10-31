# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from typing import Literal, TypedDict


class AgentRef(TypedDict):
    kind: Literal["orcid", "url", "text", "unknown"]
    url: str | None
    label: str
    orcid_id: str | None


class SourceRef(TypedDict):
    kind: Literal["zenodo", "version", "url", "text", "unknown"]
    url: str | None
    label: str
    extra: str | None
    entity_uri: str | None
    timestamp: str | None


def unknown_agent() -> AgentRef:
    return {"kind": "unknown", "url": None, "label": "Unknown", "orcid_id": None}


def url_agent(url: str) -> AgentRef:
    return {"kind": "url", "url": url, "label": url, "orcid_id": None}


def text_agent(text: str) -> AgentRef:
    return {"kind": "text", "url": None, "label": text, "orcid_id": None}


def unknown_source() -> SourceRef:
    return {
        "kind": "unknown",
        "url": None,
        "label": "Unknown",
        "extra": None,
        "entity_uri": None,
        "timestamp": None,
    }


def url_source(url: str) -> SourceRef:
    return {
        "kind": "url",
        "url": url,
        "label": url,
        "extra": None,
        "entity_uri": None,
        "timestamp": None,
    }


def text_source(text: str) -> SourceRef:
    return {
        "kind": "text",
        "url": None,
        "label": text,
        "extra": None,
        "entity_uri": None,
        "timestamp": None,
    }
