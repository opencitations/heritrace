# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import re
from functools import lru_cache
from http import HTTPStatus
from typing import cast
from urllib.parse import urlparse

import requests
from flask import current_app
from rdflib import URIRef

from heritrace.utils.references import AgentRef, url_agent

_ORCID_ID_LENGTH = 19
_ORCID_HYPHEN_COUNT = 3
_ORCID_ID = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
_CHECK_DIGIT_TEN = 10


class OrcidNotFoundError(Exception):
    pass


def is_orcid_url(url: str) -> bool:
    """Check if a URL is an ORCID URL."""
    if not isinstance(url, str):
        return False
    return urlparse(url).netloc == "orcid.org"


def extract_orcid_id(url: str) -> str | None:
    """Extract ORCID ID from URL."""
    if not isinstance(url, str):
        return None
    path = urlparse(url).path.strip("/")
    return path.removeprefix("https://orcid.org/")


def normalize_orcid(value: str) -> str:
    return cast("str", extract_orcid_id(value)) if is_orcid_url(value) else value


def is_valid_orcid_id(orcid_id: str) -> bool:
    if not _ORCID_ID.match(orcid_id):
        return False
    # ISO 7064 MOD 11-2, as described at
    # https://support.orcid.org/hc/en-us/articles/360006897674
    digits = orcid_id.replace("-", "")
    total = 0
    for digit in digits[:-1]:
        total = (total + int(digit)) * 2
    check = (12 - total % 11) % 11
    return digits[-1] == ("X" if check == _CHECK_DIGIT_TEN else str(check))


def _person_name(person: dict) -> str | None:
    # ORCID sends null for the parts of a name its owner keeps private.
    name = person["name"]
    if name is None:
        return None
    parts = [
        part["value"]
        for part in (name["given-names"], name["family-name"])
        if part is not None
    ]
    return " ".join(parts) or None


def fetch_orcid_name(orcid_id: str) -> str | None:
    response = requests.get(
        f"https://pub.orcid.org/v3.0/{orcid_id}/person",
        headers={"Accept": "application/json"},
        timeout=5,
    )
    if response.status_code == HTTPStatus.NOT_FOUND:
        raise OrcidNotFoundError(orcid_id)
    response.raise_for_status()
    return _person_name(response.json())


@lru_cache(maxsize=1000)
def get_orcid_data(orcid_id: str) -> dict | None:
    """
    Fetch researcher data from ORCID API with caching.

    In demo mode, this function returns synthetic data without calling the external API.

    Args:
        orcid_id (str): The ORCID identifier

    Returns:
        dict: Researcher data including name and other details
    """
    if current_app.config.get("ENV") == "demo":
        return {
            "name": f"Demo User ({orcid_id})",
            "other_names": [],
            "biography": "This is a synthetic user account for demo purposes.",
            "orcid": orcid_id,
        }

    headers = {"Accept": "application/json"}

    try:
        response = requests.get(
            f"https://pub.orcid.org/v3.0/{orcid_id}/person", headers=headers, timeout=5
        )

        if response.status_code == HTTPStatus.OK:
            data = response.json()

            # Extract relevant information
            result = {
                "name": None,
                "other_names": [],
                "biography": None,
                "orcid": orcid_id,
            }

            result["name"] = _person_name(data)

            # Get other names
            if "other-names" in data and "other-name" in data["other-names"]:
                result["other_names"] = [
                    name.get("content", "")
                    for name in data["other-names"]["other-name"]
                    if "content" in name
                ]

            # Get biography
            if data.get("biography"):
                result["biography"] = data["biography"].get("content", "")

            return result

    except requests.RequestException:
        return None

    return None


def get_responsible_agent_uri(user_identifier: str) -> URIRef:
    if user_identifier.startswith(("http://", "https://")):
        return URIRef(user_identifier)

    if (
        len(user_identifier) == _ORCID_ID_LENGTH
        and user_identifier.count("-") == _ORCID_HYPHEN_COUNT
    ):
        return URIRef(f"https://orcid.org/{user_identifier}")

    return URIRef(user_identifier)


def orcid_agent(url: str) -> AgentRef:
    orcid_id = extract_orcid_id(url)
    if not orcid_id:
        return url_agent(url)

    researcher_data = get_orcid_data(orcid_id)
    if not researcher_data:
        return url_agent(url)

    return {
        "kind": "orcid",
        "url": url,
        "label": researcher_data["name"] or url,
        "orcid_id": orcid_id,
    }
