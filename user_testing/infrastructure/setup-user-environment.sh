#!/bin/bash

# HERITRACE User Testing Environment Setup
# Usage: ./setup-user-environment.sh <user_id> <user_type>
# user_type: "technician" or "enduser"

set -e

USER_ID=$1
USER_TYPE=$2

if [ -z "$USER_ID" ] || [ -z "$USER_TYPE" ]; then
    echo "Usage: $0 <user_id> <user_type>"
    echo "e.g., $0 user001 technician"
    exit 1
fi

if [ "$USER_TYPE" != "technician" ] && [ "$USER_TYPE" != "enduser" ]; then
    echo "Error: user_type must be 'technician' or 'enduser'"
    exit 1
fi

# Calculate ports for this user (starting from 5100)
USER_NUM=$(echo $USER_ID | sed 's/user//')
BASE_PORT=$((5100 + USER_NUM * 10))
USER_PORT=$BASE_PORT
REDIS_PORT=$((BASE_PORT + 1))
DATASET_PORT=$((BASE_PORT + 2))
PROV_PORT=$((BASE_PORT + 3))
NETWORK_NAME="heritrace-test-$USER_ID"

USER_DIR="users/$USER_ID"
mkdir -p "$USER_DIR"
mkdir -p "$USER_DIR/data"

echo "Setting up environment for $USER_ID ($USER_TYPE) on port $USER_PORT"

# Create user-specific environment file
cat > "$USER_DIR/.env" << EOF
USER_ID=$USER_ID
USER_PORT=$USER_PORT
REDIS_PORT=$REDIS_PORT
DATASET_PORT=$DATASET_PORT
PROV_PORT=$PROV_PORT
USER_TYPE=$USER_TYPE
DATASET_DB_NAME=virtuoso-dataset-$USER_ID
PROV_DB_NAME=virtuoso-prov-$USER_ID
NETWORK_NAME=$NETWORK_NAME
EOF

# Create user-specific docker-compose file
cat > "$USER_DIR/docker-compose.yml" << EOF
services:
  heritrace-$USER_ID:
    build: ../../../../
    ports:
      - "$USER_PORT:5000"
    environment:
      - FLASK_ENV=demo
      - USER_ID=$USER_ID
      - REDIS_HOST=redis-$USER_ID
    volumes:
      - ../../../../heritrace:/app/heritrace
      - ../../../../app.py:/app/app.py
      - ./config.py:/app/config.py
      - ../../../../pyproject.toml:/app/pyproject.toml
      - ../../../../poetry.lock:/app/poetry.lock
      - ../../../../babel:/app/babel
      - ../../../../webpack.config.js:/app/webpack.config.js
      # Mount individual resources files
      - ../../../../resources/context.json:/app/resources/context.json:ro
      - ../../../../resources/datatypes.py:/app/resources/datatypes.py:ro
      - ../../../../resources/datatypes_validation.py:/app/resources/datatypes_validation.py:ro
      - ./resources/shacl.ttl:/app/resources/shacl.ttl:ro
      - ./resources/display_rules.yaml:/app/resources/display_rules.yaml:ro
      - ./resources/__init__.py:/app/resources/__init__.py:ro
      - "user-$USER_ID-venv:/app/.venv"
      - "user-$USER_ID-node-modules:/app/node_modules"
    depends_on:
      redis-$USER_ID:
        condition: service_healthy
    command: npm run start

  redis-$USER_ID:
    image: redis:7-alpine
    container_name: redis-$USER_ID
    ports:
      - "$REDIS_PORT:6379"
    volumes:
      - "user-$USER_ID-redis:/data"
      - ../../../../redis.conf:/etc/redis/redis.conf:ro
    command: redis-server /etc/redis/redis.conf
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3

volumes:
  user-$USER_ID-redis:
  user-$USER_ID-venv:
  user-$USER_ID-node-modules:

networks:
  default:
    name: $NETWORK_NAME
    external: true
EOF

# Define orphan strategy based on user type
if [ "$USER_TYPE" == "technician" ]; then
    ORPHAN_STRATEGY="OrphanHandlingStrategy.DELETE"
else
    ORPHAN_STRATEGY="OrphanHandlingStrategy.ASK"
fi

# Create user-specific config
cat > "$USER_DIR/config.py" << EOF
import os
from heritrace.meta_counter_handler import MetaCounterHandler
from heritrace.uri_generator import MetaURIGenerator
from heritrace.utils.strategies import OrphanHandlingStrategy, ProxyHandlingStrategy

BASE_HERITRACE_DIR = os.path.abspath(os.path.dirname(__file__))

# Redis for this user
REDIS_HOST = 'redis-$USER_ID'
REDIS_PORT = 6379
REDIS_DB = 0

counter_handler = MetaCounterHandler(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB
)

meta_uri_generator = MetaURIGenerator(
    "https://w3id.org/oc/meta", "$USER_ID", counter_handler
)

class Config:
    SECRET_KEY = "test-key-$USER_ID"
    APP_TITLE = "HERITRACE Test - $USER_ID"
    APP_SUBTITLE = "User Testing Environment"

    # User-specific databases (connecting to host ports)
    DATASET_DB_URL = f"http://localhost:$DATASET_PORT/sparql"
    PROVENANCE_DB_URL = f"http://localhost:$PROV_PORT/sparql"
    
    DATASET_DB_TRIPLESTORE = "virtuoso"
    PROVENANCE_DB_TRIPLESTORE = "virtuoso"
    DATASET_IS_QUADSTORE = True
    PROVENANCE_IS_QUADSTORE = True
    DATASET_DB_TEXT_INDEX_ENABLED = True
    
    REDIS_URL = f"redis://redis-$USER_ID:6379/0"
    
    URI_GENERATOR = meta_uri_generator
    COUNTER_HANDLER = counter_handler
    
    # Test-specific paths
    SHACL_PATH = "/app/resources/shacl.ttl"
    DISPLAY_RULES_PATH = "/app/resources/display_rules.yaml"
    CHANGE_TRACKING_CONFIG = "/app/change_tracking.json"
    CACHE_FILE = "/app/cache.json"
    CACHE_VALIDITY_DAYS = 7
    
    # ORCID is disabled in demo mode, but dummy keys are provided for resilience
    ORCID_CLIENT_ID = "DEMO_CLIENT_ID"
    ORCID_CLIENT_SECRET = "DEMO_CLIENT_SECRET"
    ORCID_AUTHORIZE_URL = "https://sandbox.orcid.org/oauth/authorize"
    ORCID_TOKEN_URL = "https://sandbox.orcid.org/oauth/token"
    ORCID_SCOPE = "/authenticate"
    ORCID_WHITELIST = []
    
    LANGUAGES = ["en"]
    BABEL_TRANSLATION_DIRECTORIES = "/app/babel/translations"
    PRIMARY_SOURCE = "https://test.example.com/$USER_ID"
    DATASET_GENERATION_TIME = "2024-01-01T00:00:00+00:00"
    
    ORPHAN_HANDLING_STRATEGY = $ORPHAN_STRATEGY
    PROXY_HANDLING_STRATEGY = ProxyHandlingStrategy.DELETE
EOF

# Copy test data for bulk loading
cp "../test_materials/test_data.nq.gz" "$USER_DIR/data/"

# Use only files needed by the application (in resources/)
mkdir -p "$USER_DIR/resources"
cp "../test_materials/test_shacl.ttl" "$USER_DIR/resources/shacl.ttl"
cp "../test_materials/test_display_rules.yaml" "$USER_DIR/resources/display_rules.yaml"

# Create __init__.py for Python module (datatypes.py and datatypes_validation.py are mounted from source)
touch "$USER_DIR/resources/__init__.py"

# Create user access info
cat > "$USER_DIR/ACCESS_INFO.txt" << EOF
HERITRACE Testing Environment - User $USER_ID

Access URL: https://127.0.0.1:$USER_PORT
User Type: $USER_TYPE

Login Instructions:
Login is automatic in this demo environment. You have been automatically signed in
as a demo user with a synthetic ORCID iD to protect your privacy.

Your synthetic user for this session is:
- User: Demo User ($USER_ID)

**IMPORTANT: SSL Certificate Warning**
This test environment uses a self-signed SSL certificate. Your browser will show a security warning ("Your connection is not private"). You must accept this warning to proceed.
- In Chrome/Edge: Click "Advanced", then "Proceed to 127.0.0.1 (unsafe)".
- In Firefox: Click "Advanced", then "Accept the Risk and Continue".

Test Session ID: $USER_ID
Generated: $(date)

Technical Details:
- HERITRACE Port: $USER_PORT
- Dataset DB Port: $DATASET_PORT  
- Provenance DB Port: $PROV_PORT
- Redis Port: $REDIS_PORT
- Dataset DB Container: virtuoso-dataset-$USER_ID
- Provenance DB Container: virtuoso-prov-$USER_ID
EOF

echo "Environment for $USER_ID created successfully in $USER_DIR"
echo "Run './manage-environments.sh start $USER_ID' to launch it."
echo "Login will be automatic (DEMO MODE)." 