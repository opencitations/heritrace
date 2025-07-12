#!/bin/bash

# Provenance database entrypoint script for Heritrace
# This script runs the standard Virtuoso startup and sets up the provenance database

set -e
set -x

echo "🖥️ Container type: ${CONTAINER_TYPE:-unknown}"

echo "🚀 Starting Virtuoso..."
/opt/virtuoso-opensource/bin/virtuoso-t +wait +configfile /database/virtuoso.ini

if [[ "${CONTAINER_TYPE}" == "provenance" ]]; then
    echo "⚙️ This is the provenance container. Running setup script..."
    
    DB_PASSWORD=${DBA_PASSWORD:-dba}
    
    python3 /scripts/setup_provenance.py -H localhost -P 1111 -u dba -k "$DB_PASSWORD"
else
    echo "ℹ️ This is not the provenance container. Skipping setup."
fi

echo "✅ Virtuoso is now running. Container will stay alive."
exec tail -f /database/virtuoso.log
