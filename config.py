import os

from rdflib import URIRef
from edit_sphere.meta_counter_handler import MetaCounterHandler

from edit_sphere.uri_generator import DefaultURIGenerator, MetaURIGenerator

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

counter_handler = MetaCounterHandler(os.path.join(BASE_DIR, 'meta_counter_handler.db'))

default_uri_generator = DefaultURIGenerator("https://example.com")
meta_uri_generator = MetaURIGenerator("https://w3id.org/oc/meta", "060", counter_handler)

shacl_path = os.path.join(BASE_DIR, 'resources', 'shacl.ttl')
display_rules_path = os.path.join(BASE_DIR, 'display_rules.yaml')

class Config(object):
    SECRET_KEY = 'adoiugwoad7y78agdlauwvdliu'
    CACHE_FILE = 'cache.json'
    CACHE_VALIDITY_DAYS = 7

    # Database configuration
    DATASET_DB_TYPE = 'docker'  # 'endpoint' or 'docker'
    DATASET_DB_TRIPLESTORE = 'virtuoso' # virtuoso or blazegraph
    DATASET_DB_URL = 'http://127.0.0.1:8892/sparql'
    DATASET_DB_DOCKER_IMAGE = 'openlink/virtuoso-opensource-7@sha256:c08d54120b8085234f8244951232553428e235543412e41d75705736a3026f1b'
    DATASET_DB_DOCKER_PORT = 8892
    DATASET_DB_DOCKER_ISQL_PORT = 1112
    DATASET_DB_VOLUME_PATH = os.path.join(BASE_DIR, 'db_volumes', 'data')

    PROVENANCE_DB_TYPE = 'docker'  # 'endpoint' or 'docker'
    PROVENANCE_DB_TRIPLESTORE = 'virtuoso' # virtuoso or blazegraph
    PROVENANCE_DB_URL = 'http://127.0.0.1:8893/sparql'
    PROVENANCE_DB_DOCKER_IMAGE = 'openlink/virtuoso-opensource-7@sha256:c08d54120b8085234f8244951232553428e235543412e41d75705736a3026f1b'
    PROVENANCE_DB_DOCKER_PORT = 8893
    PROVENANCE_DB_DOCKER_ISQL_PORT = 1113
    PROVENANCE_DB_VOLUME_PATH = os.path.join(BASE_DIR, 'db_volumes', 'prov')

    DATASET_IS_QUADSTORE = True  # Set to True if using a quadstore for dataset, False for triplestore
    PROVENANCE_IS_QUADSTORE = True  # Set to True if using a quadstore for provenance, False for triplestore

    DATASET_GENERATION_TIME = '2024-03-30T10:23:11+02:00'
    URI_GENERATOR = meta_uri_generator
    COUNTER_HANDLER = counter_handler
    LANGUAGES = ['en', 'it']
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(BASE_DIR, 'babel', 'translations')
    CHANGE_TRACKING_CONFIG = os.path.join(BASE_DIR, 'change_tracking.json')
    RESPONSIBLE_AGENT = URIRef('https://orcid.org/0000-0002-8420-0696')
    PRIMARY_SOURCE = None
    SHACL_PATH = shacl_path
    DISPLAY_RULES_PATH = display_rules_path