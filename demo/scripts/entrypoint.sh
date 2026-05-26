#!/bin/bash

# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

set -e

echo "Container type: ${CONTAINER_TYPE:-unknown}"

if [ ! -f /database/virtuoso.ini ]; then
    echo "First run: initializing database..."
    if [[ "${CONTAINER_TYPE}" == "dataset" ]]; then
        cp /config/virtuoso_dataset.ini /database/virtuoso.ini
    elif [[ "${CONTAINER_TYPE}" == "provenance" ]]; then
        cp /config/virtuoso_provenance.ini /database/virtuoso.ini
    else
        echo "Error: CONTAINER_TYPE must be 'dataset' or 'provenance'" >&2
        exit 1
    fi
fi

DB_PASSWORD=${DBA_PASSWORD:-dba}

echo "Starting Virtuoso daemon for setup..."
/opt/virtuoso-opensource/bin/virtuoso-t +wait +configfile /database/virtuoso.ini

if [[ "${CONTAINER_TYPE}" == "dataset" ]]; then
    echo "Loading data..."
    python3 /scripts/load_data.py -d /data -H localhost -P 1111 -u dba -k "$DB_PASSWORD" -g https://w3id.org/oc/meta/br/
elif [[ "${CONTAINER_TYPE}" == "provenance" ]]; then
    echo "Setting up provenance database..."
    python3 /scripts/setup_provenance.py -H localhost -P 1111 -u dba -k "$DB_PASSWORD"
fi

echo "Stopping Virtuoso daemon..."
/opt/virtuoso-opensource/bin/isql localhost:1111 dba "$DB_PASSWORD" "EXEC=shutdown();" || true
sleep 2

echo "Restarting Virtuoso as foreground process..."
exec /opt/virtuoso-opensource/bin/virtuoso-t +foreground +configfile /database/virtuoso.ini
