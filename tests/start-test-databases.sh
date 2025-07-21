#!/bin/bash
# Script to start test databases for HERITRACE using virtuoso-launch

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

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

install_pipx() {
    print_info "Installing pipx..."
    
    if command_exists python3; then
        python3 -m pip install --user pipx
        if [ $? -eq 0 ]; then
            python3 -m pipx ensurepath
            export PATH="$HOME/.local/bin:$PATH"
            print_success "pipx installed successfully via python3 -m pip"
            return 0
        fi
    fi
    
    if command_exists pip; then
        pip install --user pipx
        if [ $? -eq 0 ]; then
            pipx ensurepath
            export PATH="$HOME/.local/bin:$PATH"
            print_success "pipx installed successfully via pip"
            return 0
        fi
    fi
    
    if command_exists pip3; then
        pip3 install --user pipx
        if [ $? -eq 0 ]; then
            pipx ensurepath
            export PATH="$HOME/.local/bin:$PATH"
            print_success "pipx installed successfully via pip3"
            return 0
        fi
    fi
    
    print_error "Failed to install pipx. Please install it manually:"
    print_error "  - On Ubuntu/Debian: sudo apt install pipx"
    print_error "  - On macOS with Homebrew: brew install pipx"
    print_error "  - Or via pip: pip install --user pipx"
    return 1
}

setup_virtuoso_utilities() {
    if ! command_exists pipx; then
        print_warning "pipx not found. Attempting to install..."
        install_pipx
        if [ $? -ne 0 ]; then
            return 1
        fi
    fi
    
    if ! command_exists virtuoso-launch; then
        print_info "virtuoso-utilities not found. Installing..."
        pipx install virtuoso-utilities
        if [ $? -ne 0 ]; then
            print_error "Failed to install virtuoso-utilities"
            return 1
        fi
        print_success "virtuoso-utilities installed successfully"
    else
        print_info "virtuoso-utilities already installed"
    fi
    
    return 0
}

launch_virtuoso_db() {
    local name=$1
    local http_port=$2
    local isql_port=$3
    local data_dir=$4
    
    print_info "Launching Virtuoso test database: $name"
    print_info "  HTTP Port: $http_port"
    print_info "  ISQL Port: $isql_port"
    print_info "  Data Directory: $data_dir"
    
    mkdir -p "$data_dir"
    
    virtuoso-launch \
        --name "$name" \
        --http-port "$http_port" \
        --isql-port "$isql_port" \
        --data-dir "$data_dir" \
        --dba-password "dba" \
        --detach \
        --force-remove \
        --wait-ready \
        --enable-write-permissions \
        --memory "1g"
    
    if [ $? -eq 0 ]; then
        print_success "Test database $name started successfully"
        return 0
    else
        print_error "Failed to start test database $name"
        return 1
    fi
}

# Get the absolute path of the current directory
CURRENT_DIR="$(pwd)"

# Setup virtuoso-utilities
setup_virtuoso_utilities
if [ $? -ne 0 ]; then
    print_error "Failed to setup virtuoso-utilities. Exiting."
    exit 1
fi

# Start Virtuoso for dataset database
print_info "Starting test-dataset-db container..."
launch_virtuoso_db "test-dataset-db" 9999 10099 "${CURRENT_DIR}/tests/test_dataset_db"
if [ $? -ne 0 ]; then
    print_error "Failed to start test-dataset-db"
    exit 1
fi

# Start Virtuoso for provenance database
print_info "Starting test-provenance-db container..."
launch_virtuoso_db "test-provenance-db" 9998 10098 "${CURRENT_DIR}/tests/test_provenance_db"
if [ $? -ne 0 ]; then
    print_error "Failed to start test-provenance-db"
    exit 1
fi

# Start Redis for resource locking on port 6379 (same as production)
if [ "$(docker ps -a -q -f name=test-redis)" ]; then
    print_info "Removing existing test-redis container..."
    docker rm -f test-redis
fi

print_info "Starting test-redis container..."
docker run -d --name test-redis \
  -p 6379:6379 \
  redis:7-alpine

if [ $? -ne 0 ]; then
    print_error "Failed to start test-redis"
    exit 1
fi

print_success "All test databases started successfully."
print_info "Dataset DB: http://localhost:9999/sparql"
print_info "Provenance DB: http://localhost:9998/sparql"
print_info "Redis: localhost:6379" 