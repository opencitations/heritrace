#!/bin/bash

set -e

echo "📦 HERITRACE Data Export"
echo "==============================================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/"
EXPORT_DIR="${ROOT_DIR}export"
DATA_DIR="${EXPORT_DIR}/data"
PROVENANCE_DIR="${EXPORT_DIR}/provenance"
ZIP_FILE="$(pwd)/export.zip"

if ! docker info >/dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "   Please start Docker Desktop and try again."
    exit 1
fi

rm -rf "$EXPORT_DIR"
mkdir -p "$DATA_DIR" "$PROVENANCE_DIR"

echo "🔄 Exporting database data..."

DATASET_CONTAINER=$(docker ps --filter "name=dataset" --format "{{.Names}}" | head -n 1)
PROVENANCE_CONTAINER=$(docker ps --filter "name=provenance" --format "{{.Names}}" | head -n 1)

if [ -z "$DATASET_CONTAINER" ] || [ -z "$PROVENANCE_CONTAINER" ]; then
    echo "❌ Error: Virtuoso containers not found. Make sure the application is running."
    exit 1
fi

export_virtuoso_data() {
    local container=$1
    local output_file=$2
    local db_type=$3

    echo "   Exporting $db_type data from $container..."
    
    local sparql_query="CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"

    docker exec "$container" curl -s -X POST http://localhost:8890/sparql \
        -H "Content-Type: application/sparql-query" \
        -H "Accept: text/turtle" \
        --data "$sparql_query" > "$output_file"
    
    echo "✅ $db_type data exported successfully"
}

export_virtuoso_data "$DATASET_CONTAINER" "${DATA_DIR}/data.ttl" "dataset"
export_virtuoso_data "$PROVENANCE_CONTAINER" "${PROVENANCE_DIR}/data.ttl" "provenance"

echo ""
echo "✅ All data exported successfully!"
echo ""

echo "🔄 Creating zip archive..."
(cd "$EXPORT_DIR" && zip -r "$ZIP_FILE" ./* >/dev/null)
rm -rf "$EXPORT_DIR"
echo "📦 Complete export archive: $ZIP_FILE"
