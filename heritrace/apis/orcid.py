# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from functools import lru_cache
from http import HTTPStatus
from urllib.parse import urlparse

import requests
from flask import current_app
from rdflib import URIRef

from heritrace.utils.references import AgentRef, url_agent

_ORCID_ID_LENGTH = 19
_ORCID_HYPHEN_COUNT = 3


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

            # Get main name
            if "name" in data:
                given_name = data["name"].get("given-names", {}).get("value", "")
                family_name = data["name"].get("family-name", {}).get("value", "")
                if given_name or family_name:
                    result["name"] = f"{given_name} {family_name}".strip()

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
