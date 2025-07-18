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
    
    print_info "Launching Virtuoso database: $name"
    print_info "  HTTP Port: $http_port"
    print_info "  ISQL Port: $isql_port"
    print_info "  Data Directory: $data_dir"
    print_info "  Memory Limit: 1g"
    
    mkdir -p "$data_dir"
    
    virtuoso-launch \
        --name "$name" \
        --http-port "$http_port" \
        --isql-port "$isql_port" \
        --data-dir "$data_dir" \
        --memory "1g" \
        --dba-password "dba" \
        --detach \
        --force-remove \
        --wait-ready \
        --enable-write-permissions \
        --network heritrace-network
    
    if [ $? -eq 0 ]; then
        print_success "Database $name started successfully"
        return 0
    else
        print_error "Failed to start database $name"
        return 1
    fi
}

print_info "Setting up Virtuoso databases using launch_virtuoso..."

if ! docker network ls | grep -q heritrace-network; then
    print_info "Creating Docker network: heritrace-network"
    docker network create heritrace-network
    if [ $? -eq 0 ]; then
        print_success "Docker network created successfully"
    else
        print_error "Failed to create Docker network"
        exit 1
    fi
else
    print_info "Docker network heritrace-network already exists"
fi

setup_virtuoso_utilities
if [ $? -ne 0 ]; then
    print_error "Failed to setup virtuoso-utilities. Exiting."
    exit 1
fi

print_info "Starting dataset database..."
launch_virtuoso_db "database" 8999 1119 "./database"

if [ $? -ne 0 ]; then
    print_error "Failed to start dataset database"
    exit 1
fi

print_info "Starting provenance database..."
launch_virtuoso_db "prov_database" 8998 1118 "./prov_database"

if [ $? -ne 0 ]; then
    print_error "Failed to start provenance database"
    exit 1
fi

print_success "All databases started successfully!"
print_info ""
print_info "You can check their status with:"
print_info "  docker ps | grep virtuoso"
print_info ""
print_info "Access the databases at:"
print_info "  Dataset DB - HTTP: http://localhost:8999 | ISQL: localhost:1119"
print_info "  Provenance DB - HTTP: http://localhost:8998 | ISQL: localhost:1118"