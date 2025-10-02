#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_info "Stopping databases..."
docker stop heritrace-dataset heritrace-provenance 2>/dev/null

print_info "Removing containers..."
docker rm heritrace-dataset heritrace-provenance 2>/dev/null

print_success "Cleanup complete."
