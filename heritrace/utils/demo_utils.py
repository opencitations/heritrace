#!/usr/bin/python
# -*-
"""This module provides utility functions for operating HERITRACE in a demo mode.

It includes functions for generating synthetic, valid ORCID iDs for test users,
which is crucial for ensuring privacy and reproducibility in user testing environments.
"""

import hashlib


def _calculate_orcid_checksum(base_digits: str) -> str:
    """Calculate the checksum for an ORCID iD.

    The checksum is calculated using the ISO 7064 MOD 11,2 algorithm.

    Args:
        base_digits (str): The first 15 digits of the ORCID iD.

    Returns:
        str: The calculated checksum character ('0'-'9' or 'X').
    """
    total = 0
    for digit in base_digits:
        total = (total + int(digit)) * 2
    remainder = total % 11
    result = (11 - remainder) % 11
    return "X" if result == 10 else str(result)


def generate_synthetic_orcid(user_id: str) -> str:
    """Generate a deterministic, valid, synthetic ORCID iD for a given user ID.

    The generated ORCID is based on a hash of the user_id, ensuring that the same
    user_id will always produce the same ORCID iD for reproducibility. The ORCID
    starts with a "0009-" prefix to identify it as a test identifier.

    Args:
        user_id (str): A unique identifier for the user (e.g., 'user001').

    Returns:
        str: A valid, synthetic ORCID iD in the format 'XXXX-XXXX-XXXX-XXXX'.
    """
    # Use a part of the SHA256 hash to ensure a unique but deterministic number
    hash_object = hashlib.sha256(user_id.encode())
    hex_dig = hash_object.hexdigest()
    # Take 11 characters to form the middle part of the ORCID
    numeric_string = "".join(filter(str.isdigit, hex_dig))[:11]

    # Pad with zeros if it's shorter than 11 digits
    numeric_string = numeric_string.ljust(11, "0")

    # The prefix "0009" identifies this as a non-real, test ORCID.
    base_digits = "0009" + numeric_string
    checksum = _calculate_orcid_checksum(base_digits)

    # Format the ORCID iD with hyphens
    p1 = base_digits[0:4]
    p2 = base_digits[4:8]
    p3 = base_digits[8:12]
    p4 = base_digits[12:15] + checksum

    return f"{p1}-{p2}-{p3}-{p4}" 