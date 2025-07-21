#!/bin/bash

# HERITRACE Test Database Builder
# This script creates packages for building and pushing test databases to Docker Hub
# The test databases contain a subset of OpenCitations Meta data for testing purposes

set -e

echo "🔨 Building HERITRACE Test Database Packages"
echo "============================================="

BUILD_DIR="build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "📁 Preparing build environment..."

prepare_test_databases_package() {
    local build_package_dir="$BUILD_DIR/heritrace-test-databases"
    
    echo "🎁 Building test databases package..."
    
    mkdir -p "$build_package_dir"
    
    echo "   Copying Docker files for test databases..."
    cp "common/dockerfiles/Dockerfile.virtuoso" "$build_package_dir/"
    cp "common/dockerfiles/Dockerfile.provenance" "$build_package_dir/"
    
    echo "   Copying test data..."
    mkdir -p "$build_package_dir/data"
    cp -r "common/data"/* "$build_package_dir/data/"
    
    echo "   Setting up Virtuoso configuration files..."
    mkdir -p "$build_package_dir/dataset_database"
    mkdir -p "$build_package_dir/prov_database"
    cp "common/templates/virtuoso_dataset.ini" "$build_package_dir/dataset_database/virtuoso.ini"
    cp "common/templates/virtuoso_provenance.ini" "$build_package_dir/prov_database/virtuoso.ini"
    
    echo "   Copying database scripts..."
    mkdir -p "$build_package_dir/scripts"
    cp "common/scripts/virtuoso_utils.py" "$build_package_dir/scripts/"
    cp "common/scripts/load_data.py" "$build_package_dir/scripts/"
    cp "common/scripts/setup_provenance.py" "$build_package_dir/scripts/"
    cp "common/scripts/virtuoso_entrypoint.sh" "$build_package_dir/scripts/"
    cp "common/scripts/provenance_entrypoint.sh" "$build_package_dir/scripts/"
    
    echo "   Copying Docker Hub push scripts..."
    cp "common/scripts/push-to-dockerhub.sh" "$build_package_dir/"
    cp "common/scripts/push-to-dockerhub.cmd" "$build_package_dir/"
    chmod +x "$build_package_dir/push-to-dockerhub.sh"
    
    echo "   Creating docker-compose-test.yml for local testing..."
    cat > "$build_package_dir/docker-compose-test.yml" << 'EOF'
services:
  heritrace-dataset:
    build:
      context: .
      dockerfile: Dockerfile.virtuoso
    container_name: heritrace-dataset
    environment:
      - DBA_PASSWORD=dba
      - DAV_PASSWORD=dba
      - CONTAINER_TYPE=dataset
    ports:
      - "8890:8890"
    volumes:
      - ./dataset_database:/database
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8890/sparql"]
      interval: 30s
      timeout: 10s
      retries: 5
    networks:
      - heritrace-network

  heritrace-provenance:
    build:
      context: .
      dockerfile: Dockerfile.provenance
    container_name: heritrace-provenance
    environment:
      - DBA_PASSWORD=dba
      - DAV_PASSWORD=dba
      - CONTAINER_TYPE=provenance
    ports:
      - "8891:8890"
    volumes:
      - ./prov_database:/database
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8890/sparql"]
      interval: 30s
      timeout: 10s
      retries: 5
    networks:
      - heritrace-network

networks:
  heritrace-network:
    driver: bridge
EOF
    
    echo "   Creating README for database building..."
    cat > "$build_package_dir/README.md" << 'EOF'
# HERITRACE Test Databases

This package contains Docker files and scripts to build and push test database images to Docker Hub.

## Contents
- Dockerfile.virtuoso: Docker file for dataset database
- Dockerfile.provenance: Docker file for provenance database  
- data/: Test data subset from OpenCitations Meta
- scripts/: Database initialization scripts

## Testing Locally

To test the database images locally before pushing to Docker Hub, simply run:

```bash
docker compose -f docker-compose-test.yml up
```

This will build and start both databases. Visit:
- Dataset DB: http://localhost:8890/sparql 
- Provenance DB: http://localhost:8891/sparql

To stop the test databases:
```bash
docker compose -f docker-compose-test.yml down
```

## Push to Docker Hub

To build and push the test database images to Docker Hub:

**Linux/macOS:**
```bash
./push-to-dockerhub.sh [version] [docker_username]
```

**Windows:**
```cmd
push-to-dockerhub.cmd [version] [docker_username]
```

This will create and push:
- arcangelo7/heritrace-testing-virtuoso-dataset:[version]
- arcangelo7/heritrace-testing-virtuoso-provenance:[version]

EOF
        
    find "$build_package_dir" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_package_dir" -name "*.pyc" -delete 2>/dev/null || true
    
    chmod +x "$build_package_dir"/*.sh 2>/dev/null || true
    chmod +x "$build_package_dir"/scripts/*.sh 2>/dev/null || true
    
    echo "   ✅ Test databases package prepared"
}

prepare_test_databases_package

echo "📁 Moving test databases folder to final location..."
mv "$BUILD_DIR/heritrace-test-databases" ./

PACKAGE_SIZE=$(du -sh heritrace-test-databases | cut -f1)

echo ""
echo "🎉 Test databases folder created!"
echo "================================="
echo "📁 Created folder:"
echo "   🗄️ heritrace-test-databases/ ($PACKAGE_SIZE)"
echo ""
echo "💡 The folder contains ONLY what's needed to build test database images:"
echo "   - Docker files for Virtuoso test databases (dataset and provenance)"
echo "   - Test data subset from OpenCitations Meta"
echo "   - Scripts to push the test database images to Docker Hub"
echo "   - docker-compose-test.yml for local testing"
echo "   - README with building instructions"

echo ""
echo "🧹 Cleaning up build directory..."
rm -rf "$BUILD_DIR"

echo ""
echo "✅ Ready to use! To test locally:"
echo "   cd heritrace-test-databases"
echo "   docker compose -f docker-compose-test.yml up"

echo "✅ Build complete!" 