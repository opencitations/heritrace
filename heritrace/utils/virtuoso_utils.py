# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

VIRTUOSO_EXCLUDED_GRAPHS = [
    "http://localhost:8890/DAV/",
    "http://www.openlinksw.com/schemas/virtrdf#",
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/ns/ldp#",
    "urn:activitystreams-owl:map",
    "urn:core:services:sparql",
]


def is_virtuoso() -> bool:
    from heritrace.extensions import get_app_state  # noqa: PLC0415

    return get_app_state().is_virtuoso
