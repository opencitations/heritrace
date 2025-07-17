#!/bin/bash

# HERITRACE User Testing Package Builder
# This script creates a standalone ZIP package for end user testing

set -e

echo "🔨 Building HERITRACE User Testing Packages"
echo "============================================"

if [ ! -f "../../app.py" ]; then
    echo "❌ Error: This script must be run from user_testing/packages/"
    echo "   Current directory: $(pwd)"
    exit 1
fi

BUILD_DIR="build"
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

prepare_package() {
    local package_type=$1
    local build_package_dir="$BUILD_DIR/heritrace-$package_type-local"
    
    local package_type_title
    if [ "$package_type" = "enduser" ]; then
        package_type_title="End User"
    else
        package_type_title="Configurator"
    fi
    
    echo "🎁 Building $package_type package..."
    
    mkdir -p "$build_package_dir"
    
    echo "   Copying $package_type-specific files..."
    cp -r "$package_type"/* "$build_package_dir/"
    cp "../sus_questionnaire.md" "$build_package_dir/sus_questionnaire.md"
    cp "../written_responses_template.md" "$build_package_dir/written_responses_template.md"
    
    echo "   Generating scripts from templates..."
    generate_script_from_template "common/templates/scripts/start.sh.template" "$build_package_dir/start.sh" "$package_type" "$package_type_title"
    generate_script_from_template "common/templates/scripts/stop.sh.template" "$build_package_dir/stop.sh" "$package_type" "$package_type_title"
    generate_script_from_template "common/templates/scripts/start.cmd.template" "$build_package_dir/start.cmd" "$package_type" "$package_type_title"
    generate_script_from_template "common/templates/scripts/stop.cmd.template" "$build_package_dir/stop.cmd" "$package_type" "$package_type_title"
    
    echo "   Copying common Docker files and data..."
    cp "common/dockerfiles/Dockerfile.virtuoso" "$build_package_dir/"
    cp "common/dockerfiles/Dockerfile.provenance" "$build_package_dir/"
    cp "common/dockerfiles/Dockerfile.heritrace" "$build_package_dir/"
    
    if [ "$package_type" = "enduser" ]; then
        cp "common/templates/docker-compose-enduser.yml" "$build_package_dir/docker-compose.yml"
    else
        cp "common/templates/docker-compose-technician.yml" "$build_package_dir/docker-compose.yml"
    fi
    
    echo "   Copying common data directory..."
    mkdir -p "$build_package_dir/data"
    cp -r "common/data"/* "$build_package_dir/data/"
    
    echo "   Generating config.py from template..."
    generate_script_from_template "common/templates/config.py.template" "$build_package_dir/config.py" "$package_type" "$package_type_title"
    
    echo "   Copying HERITRACE application files..."
    cp ../../app.py "$build_package_dir/"
    cp ../../pyproject.toml "$build_package_dir/"
    cp ../../poetry.lock "$build_package_dir/"
    cp ../../package*.json "$build_package_dir/"
    cp ../../webpack.config.js "$build_package_dir/"
    
    cp -r ../../heritrace "$build_package_dir/"
    cp -r ../../babel "$build_package_dir/"
    
    mkdir -p "$build_package_dir/resources"
    cp ../../resources/context.json "$build_package_dir/resources/"
    cp ../../resources/datatypes.py "$build_package_dir/resources/"
    cp ../../resources/datatypes_validation.py "$build_package_dir/resources/"
    touch "$build_package_dir/resources/__init__.py"
    
    echo "   Setting up Virtuoso database directories..."
    mkdir -p "$build_package_dir/dataset_database"
    mkdir -p "$build_package_dir/prov_database"
    
    echo "   Creating Virtuoso configuration files..."
    
    cp "common/templates/virtuoso_dataset.ini" "$build_package_dir/dataset_database/virtuoso.ini"
    cp "common/templates/virtuoso_provenance.ini" "$build_package_dir/prov_database/virtuoso.ini"
    
    echo "   Setting up scripts directory..."
    mkdir -p "$build_package_dir/scripts"
    cp "common/scripts/virtuoso_utils.py" "$build_package_dir/scripts/"
    cp "common/scripts/load_data.py" "$build_package_dir/scripts/"
    cp "common/scripts/setup_provenance.py" "$build_package_dir/scripts/"
    cp "common/scripts/virtuoso_entrypoint.sh" "$build_package_dir/scripts/"
    cp "common/scripts/provenance_entrypoint.sh" "$build_package_dir/scripts/"
    
    if [ "$package_type" = "enduser" ]; then
        cp "common/scripts/export-data.sh" "$build_package_dir/"
        cp "common/scripts/export-data.cmd" "$build_package_dir/"
        chmod +x "$build_package_dir/export-data.sh"
    else
        cp "common/scripts/export-resources.sh" "$build_package_dir/"
        cp "common/scripts/export-resources.cmd" "$build_package_dir/"
        chmod +x "$build_package_dir/export-resources.sh"
    fi
    
    echo "   Adding Docker Hub scripts and compose files..."
    cp "common/scripts/push-to-dockerhub.sh" "$build_package_dir/"
    cp "common/scripts/push-to-dockerhub.cmd" "$build_package_dir/"
    chmod +x "$build_package_dir/push-to-dockerhub.sh"
    
    if [ "$package_type" = "enduser" ]; then
        cp "common/templates/docker-compose-dockerhub-enduser.yml" "$build_package_dir/docker-compose-dockerhub.yml"
    else
        cp "common/templates/docker-compose-dockerhub-technician.yml" "$build_package_dir/docker-compose-dockerhub.yml"
    fi
    
    find "$build_package_dir" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_package_dir" -name "*.pyc" -delete 2>/dev/null || true
    
    chmod +x "$build_package_dir"/*.sh 2>/dev/null || true
    chmod +x "$build_package_dir"/scripts/*.sh 2>/dev/null || true
    
    echo "   ✅ $package_type package prepared"
}

prepare_package "enduser"

echo "📦 Creating ZIP packages..."

cd "$BUILD_DIR"

echo "   Creating heritrace-enduser-local.zip..."
zip -r heritrace-enduser-local.zip heritrace-enduser-local/ >/dev/null
mv heritrace-enduser-local.zip ../

cd ..

ENDUSER_SIZE=$(du -h heritrace-enduser-local.zip | cut -f1)

echo ""
echo "🎉 Package build completed!"
echo "=========================="
echo "📦 Created package:"
echo "   📚 heritrace-enduser-local.zip ($ENDUSER_SIZE)"
echo ""
echo "💡 The package contains:"
echo "   - start.sh / start.cmd - One-click startup"
echo "   - stop.sh / stop.cmd - Clean shutdown"
echo "   - README.md - Complete user instructions"
echo "   - sus_questionnaire.md - SUS usability questionnaire"
echo "   - written_responses_template.md - Written reflection questions template"
echo "   - A standalone Docker setup with all dependencies"

echo ""
echo "🧹 Cleaning up build directory..."
rm -rf "$BUILD_DIR"

echo "✅ Build complete!" 