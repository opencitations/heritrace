#!/bin/bash
# Script to stop test databases for HERITRACE

# Stop and remove the test database containers
if [ "$(docker ps -a -q -f name=test-dataset-db)" ]; then
    echo "Stopping and removing test-dataset-db container..."
    docker stop test-dataset-db
    docker rm test-dataset-db
fi

if [ "$(docker ps -a -q -f name=test-provenance-db)" ]; then
    echo "Stopping and removing test-provenance-db container..."
    docker stop test-provenance-db
    docker rm test-provenance-db
fi

if [ "$(docker ps -a -q -f name=test-redis)" ]; then
    echo "Stopping and removing test-redis container..."
    docker stop test-redis
    docker rm test-redis
fi

echo "Test databases stopped and removed." 