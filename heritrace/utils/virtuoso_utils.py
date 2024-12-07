from flask import current_app


VIRTUOSO_EXCLUDED_GRAPHS = [
    "http://localhost:8890/DAV/",
    "http://www.openlinksw.com/schemas/virtrdf#",
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/ns/ldp#",
    "urn:activitystreams-owl:map",
    "urn:core:services:sparql"
]

def is_virtuoso():
    """Check if the current triplestore is Virtuoso."""
    return current_app.config['DATASET_DB_TRIPLESTORE'].lower() == 'virtuoso'