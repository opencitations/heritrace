#!/bin/bash

# HERITRACE User Testing Online Package Builder
# This script creates two standalone ZIP packages for user testing with pre-built online images

set -e

echo "🔨 Building HERITRACE Online Testing Packages"
echo "==============================================="

BUILD_DIR="online-build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "📁 Preparing build environment..."

generate_script_from_template() {
    local template_file=$1
    local output_file=$2
    local package_type=$3
    local package_type_title=$4

    local export_message
    if [ "$package_type" = "enduser" ]; then
        export_message="echo \"   - Export all modified data: ./export-data.sh\""
    else
        export_message="echo \"   - Export the modified resources (Shacl and Display Rules): ./export-resources.sh\""
    fi

    local export_command
    if [ "$package_type" = "enduser" ]; then
        export_command="   - Export all modified data: ./export-data.sh"
    else
        export_command="   - Export the modified resources (Shacl and Display Rules): ./export-resources.sh"
    fi

    sed -e "s/{{PACKAGE_TYPE}}/$package_type/g" \
        -e "s/{{PACKAGE_TYPE_TITLE}}/$package_type_title/g" \
        -e "s|{{EXPORT_MESSAGE}}|$export_message|g" \
        -e "s|{{EXPORT_COMMAND}}|$export_command|g" \
        "$template_file" > "$output_file"

    if [[ "$output_file" == *.sh ]]; then
        chmod +x "$output_file"
    fi
}

echo "🎁 Building enduser online package..."
ENDUSER_DIR="$BUILD_DIR/heritrace-enduser-testing"
mkdir -p "$ENDUSER_DIR"

cp "common/templates/docker-compose-dockerhub-enduser.yml" "$ENDUSER_DIR/docker-compose.yml"

generate_script_from_template "common/templates/scripts/start.sh.template" "$ENDUSER_DIR/start.sh" "enduser" "End User"
generate_script_from_template "common/templates/scripts/stop.sh.template" "$ENDUSER_DIR/stop.sh" "enduser" "End User"
generate_script_from_template "common/templates/scripts/start.cmd.template" "$ENDUSER_DIR/start.cmd" "enduser" "End User"
generate_script_from_template "common/templates/scripts/stop.cmd.template" "$ENDUSER_DIR/stop.cmd" "enduser" "End User"

cp "enduser/README.md" "$ENDUSER_DIR/README.md"
cp "../sus_questionnaire.md" "$ENDUSER_DIR/sus_questionnaire.md"
cp "../written_responses_template.md" "$ENDUSER_DIR/written_responses_template.md"

mkdir -p "$ENDUSER_DIR/dataset_database"
mkdir -p "$ENDUSER_DIR/prov_database"
cp "common/templates/virtuoso_dataset.ini" "$ENDUSER_DIR/dataset_database/virtuoso.ini"
cp "common/templates/virtuoso_provenance.ini" "$ENDUSER_DIR/prov_database/virtuoso.ini"

cp "common/scripts/export-data.sh" "$ENDUSER_DIR/"
cp "common/scripts/export-data.cmd" "$ENDUSER_DIR/"
chmod +x "$ENDUSER_DIR/export-data.sh"

echo "🎁 Building technician online package..."
TECHNICIAN_DIR="$BUILD_DIR/heritrace-technician-testing"
mkdir -p "$TECHNICIAN_DIR"
mkdir -p "$TECHNICIAN_DIR/resources"

cp "common/templates/docker-compose-dockerhub-technician.yml" "$TECHNICIAN_DIR/docker-compose.yml"

generate_script_from_template "common/templates/scripts/start.sh.template" "$TECHNICIAN_DIR/start.sh" "technician" "Configurator"
generate_script_from_template "common/templates/scripts/stop.sh.template" "$TECHNICIAN_DIR/stop.sh" "technician" "Configurator"
generate_script_from_template "common/templates/scripts/start.cmd.template" "$TECHNICIAN_DIR/start.cmd" "technician" "Configurator"
generate_script_from_template "common/templates/scripts/stop.cmd.template" "$TECHNICIAN_DIR/stop.cmd" "technician" "Configurator"

cp "technician/README.md" "$TECHNICIAN_DIR/README.md"
cp "../sus_questionnaire.md" "$TECHNICIAN_DIR/sus_questionnaire.md"
cp "../written_responses_template.md" "$TECHNICIAN_DIR/written_responses_template.md"

mkdir -p "$TECHNICIAN_DIR/dataset_database"
mkdir -p "$TECHNICIAN_DIR/prov_database"
cp "common/templates/virtuoso_dataset.ini" "$TECHNICIAN_DIR/dataset_database/virtuoso.ini"
cp "common/templates/virtuoso_provenance.ini" "$TECHNICIAN_DIR/prov_database/virtuoso.ini"

cp "technician/resources/display_rules.yaml" "$TECHNICIAN_DIR/resources/"
cp "technician/resources/shacl.ttl" "$TECHNICIAN_DIR/resources/"

cp "common/scripts/export-resources.sh" "$TECHNICIAN_DIR/"
cp "common/scripts/export-resources.cmd" "$TECHNICIAN_DIR/"
chmod +x "$TECHNICIAN_DIR/export-resources.sh"

echo "📦 Creating ZIP packages..."
cd "$BUILD_DIR"

echo "   Creating heritrace-enduser-testing.zip..."
zip -r heritrace-enduser-testing.zip heritrace-enduser-testing/ > /dev/null
mv heritrace-enduser-testing.zip ../

echo "   Creating heritrace-technician-testing.zip..."
zip -r heritrace-technician-testing.zip heritrace-technician-testing/ > /dev/null
mv heritrace-technician-testing.zip ../

cd ..

print_summary() {
    ENDUSER_SIZE=$(du -h heritrace-enduser-testing.zip | cut -f1)
    TECHNICIAN_SIZE=$(du -h heritrace-technician-testing.zip | cut -f1)

    echo ""
    echo "🎉 Online Package build completed!"
    echo "=================================="
    echo "📦 Created packages:"
    echo "   📚 heritrace-enduser-testing.zip ($ENDUSER_SIZE)"
    echo "   🔧 heritrace-technician-testing.zip ($TECHNICIAN_SIZE)"
    echo ""
    echo "💡 Each package contains:"
    echo "   - docker-compose.yml - Pre-configured Docker setup"
    echo "   - start.sh / start.cmd - One-click startup scripts"
    echo "   - stop.sh / stop.cmd - Clean shutdown scripts"
    echo "   - README.md - Complete user instructions"
    echo "   - sus_questionnaire.md - SUS usability questionnaire"
    echo "   - written_responses_template.md - Written reflection questions template"

    if [ -f "heritrace-enduser-testing.zip" ]; then
        echo "   - export-data.sh/cmd - Script to export all data"
    fi
    if [ -f "heritrace-technician-testing.zip" ]; then
        echo "   - export-resources.sh/cmd - Script to export SHACL and display rules"
    fi

    echo ""
    echo "🧹 Cleaning up build directory..."
    rm -rf "$BUILD_DIR"

    echo "✅ Build complete!"
}

print_summary