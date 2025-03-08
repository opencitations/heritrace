#!/bin/bash

# Create network if it doesn't exist
docker network create virtuoso-net 2>/dev/null || true

# Function to start or restart a container
start_container() {
    local name=$1
    local port=$2
    local conductor_port=$3

    # Check if container exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${name}$"; then
        echo "Container ${name} exists."
        
        # Check if it's running
        if docker ps --format '{{.Names}}' | grep -q "^${name}$"; then
            echo "${name} is already running."
            return 0
        else
            echo "Starting existing ${name}..."
            docker start ${name}
            return 0
        fi
    fi

    # Start new container if it doesn't exist
    echo "Starting new ${name}..."
    docker run -d \
        --name ${name} \
        --network virtuoso-net \
        -p ${port}:8890 \
        -p ${conductor_port}:1111 \
        -e DBA_PASSWORD=dba \
        -e SPARQL_UPDATE=true \
        -v "$(pwd)/${name}":/database \
        openlink/virtuoso-opensource-7@sha256:c08d54120b8085234f8244951232553428e235543412e41d75705736a3026f1b
}

# Start both databases
echo "Starting dataset database..."
start_container "database" 8999 1119

echo "Starting provenance database..."
start_container "prov_database" 8998 1118

echo "Waiting for databases to initialize..."
sleep 5

echo "Databases started. You can check their status with:"
echo "docker ps | grep virtuoso"