#!/bin/bash

# HERITRACE Testing - Resources Export Script
# This script exports the modified resources (Shacl and Display Rules) from Docker volumes

set -e

echo "📦 HERITRACE Resources Export"
echo "==============================================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/"

EXPORT_DIR="${ROOT_DIR}export"
ZIP_FILE="$(pwd)/export.zip"

SOURCE_DIR="./resources"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Error: 'resources' directory not found in the current location."
    exit 1
fi

SHACL_FILE="${SOURCE_DIR}/shacl.ttl"
DISPLAY_RULES_FILE="${SOURCE_DIR}/display_rules.yaml"

if [ ! -f "$SHACL_FILE" ] && [ ! -f "$DISPLAY_RULES_FILE" ]; then
    echo "❌ Error: Neither 'shacl.ttl' nor 'display_rules.yaml' found in the 'resources' directory."
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

echo "🔄 Creating zip archive..."
(cd "$EXPORT_DIR" && zip -r "$ZIP_FILE" ./* >/dev/null)

echo "🧹 Cleaning up temporary directory..."
rm -rf "$EXPORT_DIR"

echo "✅ Successfully exported resources to: $ZIP_FILE"