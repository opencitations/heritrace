import os

from rdflib import URIRef
from heritrace.meta_counter_handler import MetaCounterHandler

from heritrace.uri_generator import DefaultURIGenerator, MetaURIGenerator

BASE_DIR = '/home/tech/francesca_virtuoso'
BASE_HERITRACE_DIR = os.path.abspath(os.path.dirname(__file__))

counter_handler = MetaCounterHandler(os.path.join(BASE_DIR, '09110_counter_handler.db'))

default_uri_generator = DefaultURIGenerator("https://example.com")
meta_uri_generator = MetaURIGenerator("https://w3id.org/oc/meta", "09110", counter_handler)

shacl_path = os.path.join(BASE_HERITRACE_DIR, 'resources', 'shacl.ttl')

display_rules_path = os.path.join(BASE_HERITRACE_DIR, 'display_rules.yaml')

class Config(object):
    SECRET_KEY = 'adoiugwoad7y78agdlauwvdliu'
    CACHE_FILE = 'cache.json'
    CACHE_VALIDITY_DAYS = 7

    # Database configuration
    DATASET_DB_TYPE = 'docker'  # 'endpoint' or 'docker'
    DATASET_DB_TRIPLESTORE = 'virtuoso' # virtuoso or blazegraph
    DATASET_DB_URL = 'http://127.0.0.1:8999/sparql'
    DATASET_DB_DOCKER_IMAGE = 'openlink/virtuoso-opensource-7@sha256:c08d54120b8085234f8244951232553428e235543412e41d75705736a3026f1b'
    DATASET_DB_DOCKER_PORT = 8999
    DATASET_DB_DOCKER_ISQL_PORT = 1119
    DATASET_DB_VOLUME_PATH = os.path.join(BASE_DIR, 'database')

    PROVENANCE_DB_TYPE = 'docker'  # 'endpoint' or 'docker'
    PROVENANCE_DB_TRIPLESTORE = 'virtuoso' # virtuoso or blazegraph
    PROVENANCE_DB_URL = 'http://127.0.0.1:8998/sparql'
    PROVENANCE_DB_DOCKER_IMAGE = 'openlink/virtuoso-opensource-7@sha256:c08d54120b8085234f8244951232553428e235543412e41d75705736a3026f1b'
    PROVENANCE_DB_DOCKER_PORT = 8998
    PROVENANCE_DB_DOCKER_ISQL_PORT = 1118
    PROVENANCE_DB_VOLUME_PATH = os.path.join(BASE_DIR, 'prov_database')

    DATASET_IS_QUADSTORE = True  # Set to True if using a quadstore for dataset, False for triplestore
    PROVENANCE_IS_QUADSTORE = True  # Set to True if using a quadstore for provenance, False for triplestore

    DATASET_GENERATION_TIME = '2024-09-16T00:00:00+02:00'
    URI_GENERATOR = meta_uri_generator
    COUNTER_HANDLER = counter_handler
    LANGUAGES = ['en', 'it']
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(BASE_DIR, 'babel', 'translations')
    CHANGE_TRACKING_CONFIG = os.path.join(BASE_DIR, 'change_tracking.json')
    RESPONSIBLE_AGENT = URIRef('https://orcid.org/0009-0002-5790-4804')
    PRIMARY_SOURCE = 'https://doi.org/10.5281/zenodo.13768531'
    SHACL_PATH = shacl_path
    DISPLAY_RULES_PATH = display_rules_path