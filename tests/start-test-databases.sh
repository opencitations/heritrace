#!/bin/bash
# Script to start test databases for HERITRACE

# Get the absolute path of the current directory
CURRENT_DIR="$(pwd)"

# Create test database directories if they don't exist
mkdir -p "${CURRENT_DIR}/tests/test_dataset_db"
mkdir -p "${CURRENT_DIR}/tests/test_provenance_db"

# Check if containers already exist and remove them if they do
if [ "$(docker ps -a -q -f name=test-dataset-db)" ]; then
    echo "Removing existing test-dataset-db container..."
    docker rm -f test-dataset-db
fi

if [ "$(docker ps -a -q -f name=test-provenance-db)" ]; then
    echo "Removing existing test-provenance-db container..."
    docker rm -f test-provenance-db
fi

if [ "$(docker ps -a -q -f name=test-redis)" ]; then
    echo "Removing existing test-redis container..."
    docker rm -f test-redis
fi

# Start Virtuoso for dataset database on port 9999 (different from dev port 8999)
echo "Starting test-dataset-db container..."
docker run -d --name test-dataset-db \
  -p 9999:8890 \
  -e DBA_PASSWORD=dba \
  -e SPARQL_UPDATE=true \
  -v "${CURRENT_DIR}/tests/test_dataset_db:/database" \
  openlink/virtuoso-opensource-7:latest

# Start Virtuoso for provenance database on port 9998 (different from dev port 8998)
echo "Starting test-provenance-db container..."
docker run -d --name test-provenance-db \
  -p 9998:8890 \
  -e DBA_PASSWORD=dba \
  -e SPARQL_UPDATE=true \
  -v "${CURRENT_DIR}/tests/test_provenance_db:/database" \
  openlink/virtuoso-opensource-7:latest

# Start Redis for resource locking on port 6380
echo "Starting test-redis container..."
docker run -d --name test-redis \
  -p 6380:6379 \
  redis:7-alpine

# Wait for databases to be ready
echo "Waiting for test databases to start..."
sleep 30
echo "Test databases should be ready now."

# Set permissions for the 'nobody' user in both databases
echo "Setting permissions for the 'nobody' user in the dataset database..."
docker exec test-dataset-db /opt/virtuoso-opensource/bin/isql -U dba -P dba exec="DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('nobody', 7);"

echo "Setting permissions for the 'nobody' user in the provenance database..."
docker exec test-provenance-db /opt/virtuoso-opensource/bin/isql -U dba -P dba exec="DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('nobody', 7);"

# Assign SPARQL_UPDATE role to the SPARQL account
echo "Assigning SPARQL_UPDATE role to the SPARQL account in the dataset database..."
docker exec test-dataset-db /opt/virtuoso-opensource/bin/isql -U dba -P dba exec="DB.DBA.USER_GRANT_ROLE ('SPARQL', 'SPARQL_UPDATE');"

echo "Assigning SPARQL_UPDATE role to the SPARQL account in the provenance database..."
docker exec test-provenance-db /opt/virtuoso-opensource/bin/isql -U dba -P dba exec="DB.DBA.USER_GRANT_ROLE ('SPARQL', 'SPARQL_UPDATE');"

echo "Permissions set successfully."
echo "Dataset DB: http://localhost:9999/sparql"
echo "Provenance DB: http://localhost:9998/sparql"
echo "Redis: localhost:6380" 