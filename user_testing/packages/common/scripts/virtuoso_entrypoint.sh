#!/bin/bash

# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

# Virtuoso entrypoint script for Heritrace
# This script runs the standard Virtuoso startup and loads data if needed

set -e

set -x

echo "🖥️ Container type: ${CONTAINER_TYPE:-unknown}"

echo "🚀 Starting Virtuoso..."
/opt/virtuoso-opensource/bin/virtuoso-t +wait +configfile /database/virtuoso.ini

if [[ "${CONTAINER_TYPE}" == "dataset" ]]; then
    echo "📥 This is the dataset container. Running data loader script..."
    
    DB_PASSWORD=${DBA_PASSWORD:-dba}
    
    python3 /scripts/load_data.py -d /data -H localhost -P 1111 -u dba -k "$DB_PASSWORD" -g https://w3id.org/oc/meta/br/
else
    echo "ℹ️ This is not the dataset container. Skipping data loading."
fi

echo "✅ Virtuoso is now running. Container will stay alive."
exec tail -f /database/virtuoso.log
