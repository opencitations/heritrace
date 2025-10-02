#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info "Starting Virtuoso databases using Docker..."

if docker network ls | grep -q "heritrace_heritrace-network"; then
    NETWORK_NAME="heritrace_heritrace-network"
    print_info "Using existing Docker network: $NETWORK_NAME"
elif docker network ls | grep -q "heritrace-network"; then
    NETWORK_NAME="heritrace-network"
    print_info "Using existing Docker network: $NETWORK_NAME"
else
    NETWORK_NAME="heritrace-network"
    print_info "Creating Docker network: $NETWORK_NAME"
    docker network create $NETWORK_NAME
    if [ $? -eq 0 ]; then
        print_success "Docker network created successfully"
    else
        print_error "Failed to create Docker network"
        exit 1
    fi
fi

# Stop and remove existing containers if they exist
print_info "Cleaning up existing containers..."
docker stop heritrace-dataset heritrace-provenance 2>/dev/null
docker rm heritrace-dataset heritrace-provenance 2>/dev/null

# Create data directories
mkdir -p ./dataset_database
mkdir -p ./prov_database

print_info "Starting dataset database..."
docker run -d \
    --name heritrace-dataset \
    --network $NETWORK_NAME \
    -p 8890:8890 \
    -v "$(pwd)/dataset_database:/database" \
    -e DBA_PASSWORD=dba \
    -e DAV_PASSWORD=dba \
    -e CONTAINER_TYPE=dataset \
    arcangelo7/heritrace-testing-virtuoso-dataset:1.0.2

if [ $? -eq 0 ]; then
    print_success "Dataset database started successfully"
else
    print_error "Failed to start dataset database"
    exit 1
fi

print_info "Starting provenance database..."
docker run -d \
    --name heritrace-provenance \
    --network $NETWORK_NAME \
    -p 8891:8890 \
    -v "$(pwd)/prov_database:/database" \
    -e DBA_PASSWORD=dba \
    -e DAV_PASSWORD=dba \
    -e CONTAINER_TYPE=provenance \
    arcangelo7/heritrace-testing-virtuoso-provenance:1.0.2

if [ $? -eq 0 ]; then
    print_success "Provenance database started successfully"
else
    print_error "Failed to start provenance database"
    exit 1
fi

print_info "Waiting for databases to be ready..."
sleep 5

print_success "All databases started successfully!"
print_info ""
print_info "You can check their status with:"
print_info "  docker ps | grep heritrace"
print_info ""
print_info "Access the databases at:"
print_info "  Dataset DB - HTTP: http://localhost:8890/sparql"
print_info "  Provenance DB - HTTP: http://localhost:8891/sparql"
