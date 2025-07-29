#!/bin/bash

# HERITRACE Testing - Resources Export Script
# This script exports the modified resources (Shacl and Display Rules) from Docker volumes

set -e

echo "📦 HERITRACE Resources Export"
echo "==============================================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/"

EXPORT_DIR="${ROOT_DIR}export"
ZIP_FILE="$(pwd)/export.zip"

SOURCE_DIR="./config"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Error: 'config' directory not found in the current location."
    exit 1
fi

SHACL_FILE="${SOURCE_DIR}/shacl.ttl"
DISPLAY_RULES_FILE="${SOURCE_DIR}/display_rules.yaml"

if [ ! -f "$SHACL_FILE" ] && [ ! -f "$DISPLAY_RULES_FILE" ]; then
    echo "❌ Error: Neither 'shacl.ttl' nor 'display_rules.yaml' found in the 'config' directory."
    exit 1
fi

rm -rf "$EXPORT_DIR"
mkdir -p "$EXPORT_DIR"

echo "🔄 Copying resources to export directory..."

if [ -f "$SHACL_FILE" ]; then
    cp "$SHACL_FILE" "$EXPORT_DIR/"
    echo "   - Found shacl.ttl"
fi

if [ -f "$DISPLAY_RULES_FILE" ]; then
    cp "$DISPLAY_RULES_FILE" "$EXPORT_DIR/"
    echo "   - Found display_rules.yaml"
fi

echo "📋 Including testing questionnaires and responses..."
if [ -f "sus_questionnaire.md" ]; then
    cp "sus_questionnaire.md" "$EXPORT_DIR/"
    echo "   - Found SUS questionnaire"
fi

if [ -f "written_responses_template.md" ]; then
    cp "written_responses_template.md" "$EXPORT_DIR/"
    echo "   - Found written responses template"
fi

echo "🔄 Creating zip archive..."
# Cross-platform archive creation
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

echo "🧹 Cleaning up temporary directory..."
rm -rf "$EXPORT_DIR"

echo "✅ Successfully exported resources to: $ZIP_FILE"