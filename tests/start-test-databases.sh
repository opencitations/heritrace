#!/bin/bash
# Script to start test databases for HERITRACE

# Create test database directories if they don't exist
mkdir -p tests/test_dataset_db
mkdir -p tests/test_provenance_db

# Start Virtuoso for dataset database on port 9999 (different from dev port 8999)
docker run -d --name test-dataset-db \
  -p 9999:8890 \
  -e DBA_PASSWORD=dba \
  -e SPARQL_UPDATE=true \
  -v "$(pwd)/tests/test_dataset_db:/database" \
  openlink/virtuoso-opensource-7:latest

# Start Virtuoso for provenance database on port 9998 (different from dev port 8998)
docker run -d --name test-provenance-db \
  -p 9998:8890 \
  -e DBA_PASSWORD=dba \
  -e SPARQL_UPDATE=true \
  -v "$(pwd)/tests/test_provenance_db:/database" \
  openlink/virtuoso-opensource-7:latest

# Wait for databases to be ready
echo "Waiting for test databases to start..."
sleep 30
echo "Test databases should be ready now."
echo "Dataset DB: http://localhost:9999/sparql"
echo "Provenance DB: http://localhost:9998/sparql" 