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

DATASET_CONTAINER=$(docker ps --filter "name=heritrace-dataset" --format "{{.Names}}" | head -n 1)
PROVENANCE_CONTAINER=$(docker ps --filter "name=heritrace-provenance" --format "{{.Names}}" | head -n 1)

if [ -z "$DATASET_CONTAINER" ]; then
    echo "❌ Error: Dataset container not found or not running."
    echo "   Please start the application with ./start.sh and try again."
    exit 1
fi

if [ -z "$PROVENANCE_CONTAINER" ]; then
    echo "❌ Error: Provenance container not found or not running."
    echo "   Please start the application with ./start.sh and try again."
    exit 1
fi

export_virtuoso_data() {
    local container=$1
    local output_file=$2
    local db_type=$3

    echo "   Exporting $db_type data from $container..."
    
    local sparql_query="CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } FILTER(?g NOT IN (<http://localhost:8890/DAV/>, <http://www.openlinksw.com/schemas/virtrdf#>, <http://www.w3.org/2002/07/owl#>, <http://www.w3.org/ns/ldp#>, <urn:activitystreams-owl:map>, <urn:core:services:sparql>)) }"

    docker exec "$container" curl -s -X POST http://localhost:8890/sparql \
        -H "Content-Type: application/sparql-query" \
        -H "Accept: text/turtle" \
        --data "$sparql_query" > "$output_file"
    
    echo "✅ $db_type data exported successfully"
}

export_virtuoso_data "$DATASET_CONTAINER" "${DATA_DIR}/data.ttl" "dataset"
export_virtuoso_data "$PROVENANCE_CONTAINER" "${PROVENANCE_DIR}/data.ttl" "provenance"

echo "📋 Including testing questionnaires and responses..."
if [ -f "sus_questionnaire.md" ]; then
    cp "sus_questionnaire.md" "$EXPORT_DIR/"
    echo "   ✅ SUS questionnaire included"
fi

if [ -f "written_responses_template.md" ]; then
    cp "written_responses_template.md" "$EXPORT_DIR/"
    echo "   ✅ Written responses template included"
fi

echo ""
echo "✅ All data exported successfully!"
echo ""

echo "🔄 Creating zip archive..."

if command -v zip >/dev/null 2>&1; then
    (cd "$EXPORT_DIR" && zip -r "$ZIP_FILE" ./* >/dev/null)
elif command -v python3 >/dev/null 2>&1; then
    python3 -c "
import zipfile
import os
import sys

export_dir = '$EXPORT_DIR'
zip_file = '$ZIP_FILE'

with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(export_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arc_name = os.path.relpath(file_path, export_dir)
            zf.write(file_path, arc_name)
"
elif command -v python >/dev/null 2>&1; then
    python -c "
import zipfile
import os
import sys

export_dir = '$EXPORT_DIR'
zip_file = '$ZIP_FILE'

with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(export_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arc_name = os.path.relpath(file_path, export_dir)
            zf.write(file_path, arc_name)
"
else
    echo "❌ Error: No archiving tool available (zip, python3, or python required)"
    echo "   Please install one of these tools and try again."
    rm -rf "$EXPORT_DIR"
    exit 1
fi
rm -rf "$EXPORT_DIR"
echo "📦 Complete export archive: $ZIP_FILE"
