#!/bin/bash

# HERITRACE Testing Environment Manager
# Usage: ./manage-environments.sh <action> <user_id>
# Actions: start, stop, reset, delete, status, export, cleanup

set -e

ACTION=$1
USER_ID=$2

show_usage() {
    echo "HERITRACE Testing Environment Manager"
    echo ""
    echo "Usage: $0 <action> [user_id]"
    echo ""
    echo "Actions:"
    echo "  start <user_id>     - Start user environment"
    echo "  stop <user_id>      - Stop user environment"
    echo "  restart <user_id>   - Restart user environment (stop + start)"
    echo "  reset <user_id>     - Reset user environment to initial state"
    echo "  delete <user_id>    - Completely delete a user environment"
    echo "  status [user_id]    - Show status of environments"
    echo "  export <user_id>    - Export user modifications for analysis"
    echo "  cleanup             - Clean up all stopped environments"
    echo "  list                - List all created environments"
    echo ""
    echo "Examples:"
    echo "  $0 start user001"
    echo "  $0 restart user001"
    echo "  $0 status"
    echo "  $0 export user001"
}

if [ -z "$ACTION" ]; then
    show_usage
    exit 1
fi

start_environment() {
    local user_id=$1
    local user_dir="users/$user_id"
    
    if [ ! -d "$user_dir" ]; then
        echo "Error: Environment for $user_id not found. Create it first with setup-user-environment.sh"
        exit 1
    fi
    
    source "$user_dir/.env"
    
    echo "Starting environment for $user_id..."
    
    echo "Starting Dataset Virtuoso container..."
    virtuoso-launch \
        --name "$DATASET_DB_NAME" \
        --http-port "$DATASET_PORT" \
        --isql-port $((DATASET_PORT + 100)) \
        --network "$NETWORK_NAME" \
        --data-dir "$PWD/$user_dir/dataset-data" \
        --mount-volume "$PWD/$user_dir/data:/data" \
        --dba-password "dba" \
        --memory "2g" \
        --detach \
        --force-remove \
        --wait-ready \
        --enable-write-permissions
    
    echo "Starting Provenance Virtuoso container..."
    virtuoso-launch \
        --name "$PROV_DB_NAME" \
        --http-port "$PROV_PORT" \
        --isql-port $((PROV_PORT + 100)) \
        --network "$NETWORK_NAME" \
        --data-dir "$PWD/$user_dir/prov-data" \
        --dba-password "dba" \
        --memory "1g" \
        --detach \
        --force-remove \
        --wait-ready \
        --enable-write-permissions
    
    echo "Loading test data into dataset..."
    virtuoso-bulk-load \
        --data-directory "/data" \
        --password "dba" \
        --port 1111 \
        --docker-container "$DATASET_DB_NAME" \

    # echo "Rebuilding full-text index for dataset..."
    # virtuoso-rebuild-index \
    #     --password "dba" \
    #     --port 1111 \
    #     --docker-container "$DATASET_DB_NAME" \

    echo "Restarting dataset container for index changes to take effect..."
    docker restart "$DATASET_DB_NAME"

    echo "Waiting for dataset container to be ready after restart..."
    for i in {1..30}; do
        if curl -s --fail "http://localhost:$DATASET_PORT/sparql" > /dev/null; then
            echo "✓ Dataset DB is ready."
            break
        fi
        sleep 2
        if [ $i -eq 30 ]; then
            echo "Error: Timed out waiting for dataset DB to restart."
            exit 1
        fi
    done
    
    echo "Starting HERITRACE application..."
    cd "$user_dir"
    docker compose up -d
    cd - > /dev/null
    
    echo "Waiting for HERITRACE to start..."
    for i in {1..30}; do
        if curl -s --fail --insecure "https://localhost:$USER_PORT" > /dev/null; then
            echo "✓ HERITRACE is ready at https://localhost:$USER_PORT"
            break
        fi
        echo "  Attempt $i/30 - waiting for HERITRACE to respond..."
        sleep 2
        if [ $i -eq 30 ]; then
            echo "Error: Timed out waiting for HERITRACE to start at https://localhost:$USER_PORT"
            echo "Check the logs with: cd $user_dir && docker compose logs"
            exit 1
        fi
    done
    
    echo ""
    echo "Environment started for $user_id"
    cat "$user_dir/ACCESS_INFO.txt"
}

stop_environment() {
    local user_id=$1
    local user_dir="users/$user_id"
    
    if [ ! -d "$user_dir" ]; then
        echo "Error: Environment for $user_id not found"
        exit 1
    fi
    
    source "$user_dir/.env"
    
    echo "Stopping environment for $user_id..."
    
    # Stop HERITRACE application
    cd "$user_dir"
    docker compose down
    cd - > /dev/null
    
    # Stop Virtuoso containers
    echo "Stopping Virtuoso containers..."
    docker stop "$DATASET_DB_NAME" 2>/dev/null || true
    docker stop "$PROV_DB_NAME" 2>/dev/null || true
    
    echo "Environment stopped for $user_id"
}

restart_environment() {
    local user_id=$1
    local user_dir="users/$user_id"
    
    if [ ! -d "$user_dir" ]; then
        echo "Error: Environment for $user_id not found"
        exit 1
    fi
    
    echo "Restarting environment for $user_id..."
    
    echo "Stopping environment..."
    stop_environment "$user_id"
    
    echo "Starting environment..."
    start_environment "$user_id"
    
    echo "Restart completed for $user_id"
}

reset_environment() {
    local user_id=$1
    local user_dir="users/$user_id"
    
    if [ ! -d "$user_dir" ]; then
        echo "Error: Environment for $user_id not found"
        exit 1
    fi
    
    source "$user_dir/.env"
    
    echo "Resetting environment for $user_id..."
    
    # Stop and remove HERITRACE containers/volumes
    cd "$user_dir"
    docker compose down -v
    cd - > /dev/null
    
    # Stop and remove Virtuoso containers
    echo "Removing Virtuoso containers..."
    docker stop "$DATASET_DB_NAME" 2>/dev/null || true
    docker stop "$PROV_DB_NAME" 2>/dev/null || true
    docker rm "$DATASET_DB_NAME" 2>/dev/null || true
    docker rm "$PROV_DB_NAME" 2>/dev/null || true
    
    # Remove Virtuoso data directories
    rm -rf "$user_dir/dataset-data" 2>/dev/null || true
    rm -rf "$user_dir/prov-data" 2>/dev/null || true
    
    # Remove user-specific volumes
    docker volume rm -f "${user_id}_user-${user_id}-cache" 2>/dev/null || true
    docker volume rm -f "${user_id}_user-${user_id}-redis" 2>/dev/null || true
    docker volume rm -f "${user_id}_user-${user_id}-venv" 2>/dev/null || true
    docker volume rm -f "${user_id}_user-${user_id}-node-modules" 2>/dev/null || true
    
    echo "Environment reset for $user_id. Use 'start' to restart with fresh data."
}

delete_environment() {
    local user_id=$1
    local user_dir="users/$user_id"
    
    if [ ! -d "$user_dir" ]; then
        echo "Error: Environment for $user_id not found"
        exit 1
    fi
    
    source "$user_dir/.env"
    
    echo "Deleting environment for $user_id..."
    
    # Stop and remove HERITRACE containers/volumes
    cd "$user_dir"
    docker compose down -v --remove-orphans >/dev/null 2>&1
    cd - > /dev/null
    
    # Stop and remove Virtuoso containers
    echo "Removing Docker containers..."
    docker stop "$DATASET_DB_NAME" >/dev/null 2>&1 || true
    docker stop "$PROV_DB_NAME" >/dev/null 2>&1 || true
    docker rm "$DATASET_DB_NAME" >/dev/null 2>&1 || true
    docker rm "$PROV_DB_NAME" >/dev/null 2>&1 || true
    
    # Remove user-specific volumes
    echo "Removing Docker volumes..."
    docker volume rm -f "${user_id}_user-${user_id}-redis" >/dev/null 2>&1 || true
    docker volume rm -f "${user_id}_user-${user_id}-venv" >/dev/null 2>&1 || true
    docker volume rm -f "${user_id}_user-${user_id}-node-modules" >/dev/null 2>&1 || true
    
    # Remove the user directory
    echo "Removing user directory $user_dir..."
    rm -rf "$user_dir"
    
    echo "Environment for $user_id completely deleted."
}

show_status() {
    local user_id=$1
    
    if [ -n "$user_id" ]; then
        # Status for specific user
        local user_dir="users/$user_id"
        if [ ! -d "$user_dir" ]; then
            echo "Environment for $user_id: NOT CREATED"
            return
        fi
        
        source "$user_dir/.env"
        local heritrace_running=false
        local dataset_running=false
        local prov_running=false
        
        if docker ps --format "{{.Names}}" | grep -q "heritrace-$user_id"; then
            heritrace_running=true
        fi
        
        if docker ps --format "{{.Names}}" | grep -q "$DATASET_DB_NAME"; then
            dataset_running=true
        fi
        
        if docker ps --format "{{.Names}}" | grep -q "$PROV_DB_NAME"; then
            prov_running=true
        fi
        
        if $heritrace_running && $dataset_running && $prov_running; then
            echo "Environment for $user_id: RUNNING"
            echo "URL: https://localhost:$USER_PORT"
            echo "Dataset DB: https://localhost:$DATASET_PORT"
            echo "Provenance DB: https://localhost:$PROV_PORT"
        elif $heritrace_running || $dataset_running || $prov_running; then
            echo "Environment for $user_id: PARTIALLY RUNNING"
            echo "HERITRACE: $heritrace_running"
            echo "Dataset DB: $dataset_running"
            echo "Provenance DB: $prov_running"
        else
            echo "Environment for $user_id: STOPPED"
        fi
    else
        # Status for all users
        echo "HERITRACE Testing Environments Status:"
        echo "======================================"
        
        if [ ! -d "users" ]; then
            echo "No environments created yet."
            return
        fi
        
        for user_dir in users/*/; do
            if [ -d "$user_dir" ]; then
                local user_id=$(basename "$user_dir")
                source "$user_dir/.env"
                
                local heritrace_running=false
                local dataset_running=false
                local prov_running=false
                
                if docker ps --format "{{.Names}}" | grep -q "heritrace-$user_id"; then
                    heritrace_running=true
                fi
                
                if docker ps --format "{{.Names}}" | grep -q "$DATASET_DB_NAME"; then
                    dataset_running=true
                fi
                
                if docker ps --format "{{.Names}}" | grep -q "$PROV_DB_NAME"; then
                    prov_running=true
                fi
                
                if $heritrace_running && $dataset_running && $prov_running; then
                    echo "$user_id: RUNNING (https://localhost:$USER_PORT)"
                elif $heritrace_running || $dataset_running || $prov_running; then
                    echo "$user_id: PARTIALLY RUNNING"
                else
                    echo "$user_id: STOPPED"
                fi
            fi
        done
    fi
}

export_modifications() {
    local user_id=$1
    local user_dir="users/$user_id"
    local export_dir="exports/$user_id-$(date +%Y%m%d-%H%M%S)"
    
    if [ ! -d "$user_dir" ]; then
        echo "Error: Environment for $user_id not found"
        exit 1
    fi
    
    source "$user_dir/.env"
    
    # Check if environment is running
    if ! docker ps --format "{{.Names}}" | grep -q "heritrace-$user_id"; then
        echo "Error: Environment for $user_id is not running"
        exit 1
    fi
    
    mkdir -p "$export_dir"
    
    echo "Exporting modifications for $user_id..."
    
    # Export dataset changes
    curl -s "http://localhost:$DATASET_PORT/sparql" \
        --data-urlencode "query=CONSTRUCT { ?s ?p ?o } WHERE { GRAPH <https://w3id.org/oc/meta> { ?s ?p ?o } }" \
        -H "Accept: text/turtle" > "$export_dir/final_dataset.ttl"
    
    # Export provenance
    curl -s "http://localhost:$PROV_PORT/sparql" \
        --data-urlencode "query=CONSTRUCT { ?s ?p ?o } WHERE { GRAPH <https://w3id.org/oc/meta/prov> { ?s ?p ?o } }" \
        -H "Accept: text/turtle" > "$export_dir/provenance.ttl"
    
    # Copy modified configuration files
    cp "$user_dir/resources/"* "$export_dir/" 2>/dev/null || true
    
    # Create export summary
    cat > "$export_dir/export_summary.txt" << EOF
HERITRACE Test Export - User $user_id
=====================================

Export Date: $(date)
User Type: $USER_TYPE
Original URL: https://localhost:$USER_PORT

Files Exported:
- final_dataset.ttl: Complete dataset after user modifications
- provenance.ttl: Provenance/change tracking data
- shacl.ttl: Final SHACL configuration (if modified)
- display_rules.yaml: Final display rules (if modified)

Analysis Notes:
- Compare final_dataset.ttl with test_materials/test_data.nq.gz for changes
- Check provenance.ttl for user interaction patterns
- Validate SHACL modifications against test requirements
EOF
    
    echo "Export completed: $export_dir"
    echo "Files: $(ls -la $export_dir | wc -l) items exported"
}

cleanup_environments() {
    echo "Cleaning up stopped environments..."
    
    # Remove unused containers
    docker container prune -f
    
    # Remove unused volumes
    docker volume prune -f
    
    # Remove unused networks
    docker network prune -f
    
    echo "Cleanup completed"
}

list_environments() {
    echo "Created Testing Environments:"
    echo "============================="
    
    if [ ! -d "users" ]; then
        echo "No environments created yet."
        return
    fi
    
    for user_dir in users/*/; do
        if [ -d "$user_dir" ]; then
            local user_id=$(basename "$user_dir")
            source "$user_dir/.env"
            
            local status="STOPPED"
            if docker ps --format "{{.Names}}" | grep -q "heritrace-$user_id"; then
                status="RUNNING"
            fi
            
            echo "$user_id ($USER_TYPE): $status - Port $USER_PORT"
        fi
    done
}

case $ACTION in
    start)
        if [ -z "$USER_ID" ]; then
            echo "Error: user_id required for start action"
            show_usage
            exit 1
        fi
        start_environment "$USER_ID"
        ;;
    stop)
        if [ -z "$USER_ID" ]; then
            echo "Error: user_id required for stop action"
            show_usage
            exit 1
        fi
        stop_environment "$USER_ID"
        ;;
    restart)
        if [ -z "$USER_ID" ]; then
            echo "Error: user_id required for restart action"
            show_usage
            exit 1
        fi
        restart_environment "$USER_ID"
        ;;
    reset)
        if [ -z "$USER_ID" ]; then
            echo "Error: user_id required for reset action"
            show_usage
            exit 1
        fi
        echo "WARNING: This will delete all data for $USER_ID!"
        read -p "Are you sure? (y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            reset_environment "$USER_ID"
        else
            echo "Reset cancelled"
        fi
        ;;
    delete)
        if [ -z "$USER_ID" ]; then
            echo "Error: user_id required for delete action"
            show_usage
            exit 1
        fi
        echo "WARNING: This will PERMANENTLY delete all data and the directory for $USER_ID!"
        read -p "Are you sure? (y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            delete_environment "$USER_ID"
        else
            echo "Delete cancelled"
        fi
        ;;
    status)
        show_status "$USER_ID"
        ;;
    export)
        if [ -z "$USER_ID" ]; then
            echo "Error: user_id required for export action"
            show_usage
            exit 1
        fi
        export_modifications "$USER_ID"
        ;;
    cleanup)
        cleanup_environments
        ;;
    list)
        list_environments
        ;;
    *)
        echo "Error: Unknown action '$ACTION'"
        show_usage
        exit 1
        ;;
esac 