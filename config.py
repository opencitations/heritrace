import os

from rdflib import URIRef
from rdflib_ocdm.counter_handler.sqlite_counter_handler import \
    SqliteCounterHandler
from edit_sphere.uri_generator.meta_uri_generator import MetaURIGenerator

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
counter_handler = SqliteCounterHandler(os.path.join(BASE_DIR, 'meta_counter_handler.db'))

class Config(object):
    SECRET_KEY = 'adoiugwoad7y78agdlauwvdliu'
    DATASET_ENDPOINT = 'http://localhost:9999/blazegraph/sparql'
    PROVENANCE_ENDPOINT = 'http://localhost:19999/blazegraph/sparql'
    DATASET_GENERATION_TIME = '2024-03-30T10:23:11+02:00'
    URI_GENERATOR = MetaURIGenerator("https://w3id.org/oc/meta", "060", counter_handler)
    COUNTER_HANDLER = counter_handler
    LANGUAGES = ['en', 'it']
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(BASE_DIR, 'babel', 'translations')
    CHANGE_TRACKING_CONFIG = os.path.join(BASE_DIR, 'change_tracking.json')
    RESPONSIBLE_AGENT = URIRef('https://orcid.org/0000-0002-8420-0696')
    PRIMARY_SOURCE = None
    SHACL_PATH = os.path.join(BASE_DIR, 'resources', 'shacl.ttl')
    DISPLAY_RULES_PATH = os.path.join(BASE_DIR, 'display_rules.yaml')