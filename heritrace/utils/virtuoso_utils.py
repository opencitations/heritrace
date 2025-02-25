from flask import current_app


VIRTUOSO_EXCLUDED_GRAPHS = [
    "http://localhost:8890/DAV/",
    "http://www.openlinksw.com/schemas/virtrdf#",
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/ns/ldp#",
    "urn:activitystreams-owl:map",
    "urn:core:services:sparql",
]


def is_virtuoso(app=None):
    """
    Check if the triplestore is Virtuoso.

    Args:
        app: Flask application object (optional)

    Returns:
        bool: True if triplestore is Virtuoso, False otherwise
    """
    if app is None:
        from flask import current_app

        app = current_app
    return app.config["DATASET_DB_TRIPLESTORE"].lower() == "virtuoso"
