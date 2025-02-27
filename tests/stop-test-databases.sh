#!/bin/bash
# Script to stop test databases for HERITRACE

echo "Stopping test databases..."

# Stop and remove dataset database container
docker stop test-dataset-db || true
docker rm test-dataset-db || true

# Stop and remove provenance database container
docker stop test-provenance-db || true
docker rm test-provenance-db || true

echo "Test databases stopped and containers removed." 