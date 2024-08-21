import os

from rdflib import URIRef
from rdflib_ocdm.counter_handler.sqlite_counter_handler import \
    SqliteCounterHandler

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = 'adoiugwoad7y78agdlauwvdliu'
    DATASET_ENDPOINT = 'http://localhost:9999/blazegraph/sparql'
    PROVENANCE_ENDPOINT = 'http://localhost:19999/blazegraph/sparql'
    DATASET_GENERATION_TIME = '2024-03-30T10:23:11+02:00'
    COUNTER_HANDLER = SqliteCounterHandler(os.path.join(BASE_DIR, 'meta_counter_handler.db'))
    LANGUAGES = ['en', 'it']
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(BASE_DIR, 'babel', 'translations')
    CHANGE_TRACKING_CONFIG = os.path.join(BASE_DIR, 'change_tracking.json')
    RESPONSIBLE_AGENT = URIRef('https://orcid.org/0000-0002-8420-0696')
    PRIMARY_SOURCE = None
    SHACL_PATH = None
    DISPLAY_RULES_PATH = None