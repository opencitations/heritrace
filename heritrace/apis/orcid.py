from functools import lru_cache
from urllib.parse import urlparse

import requests
from flask import current_app


def is_orcid_url(url):
    """Check if a URL is an ORCID URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc == "orcid.org"
    except:
        return False


def extract_orcid_id(url):
    """Extract ORCID ID from URL."""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if path.startswith("https://orcid.org/"):
            path = path[len("https://orcid.org/") :]
        return path
    except:
        return None


@lru_cache(maxsize=1000)
def get_orcid_data(orcid_id):
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

        if response.status_code == 200:
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
            if "biography" in data and data["biography"]:
                result["biography"] = data["biography"].get("content", "")

            return result

    except Exception:
        return None

    return None


def format_orcid_attribution(url):
    """
    Format ORCID attribution for display.

    Args:
        url (str): The ORCID URL

    Returns:
        str: Formatted HTML for displaying ORCID attribution
    """

    orcid_id = extract_orcid_id(url)
    if not orcid_id:
        return f'<a href="{url}" target="_blank">{url}</a>'

    researcher_data = get_orcid_data(orcid_id)
    if not researcher_data:
        return f'<a href="{url}" target="_blank">{url}</a>'

    name = researcher_data["name"] or url

    html = f'<a href="{url}" target="_blank" class="orcid-attribution">'
    html += f'<img src="/static/images/orcid-logo.png" alt="ORCID iD" class="orcid-icon mx-1 mb-1" style="width: 16px; height: 16px;">'
    html += f"{name} [orcid:{orcid_id}]</a>"

    return html
