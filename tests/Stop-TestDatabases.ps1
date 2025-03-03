# PowerShell script to stop test databases for HERITRACE

# Stop and remove the test database containers
if (docker ps -a --format "{{.Names}}" | Select-String -Pattern "^test-dataset-db$") {
    Write-Host "Stopping and removing test-dataset-db container..."
    docker stop test-dataset-db
    docker rm test-dataset-db
}

if (docker ps -a --format "{{.Names}}" | Select-String -Pattern "^test-provenance-db$") {
    Write-Host "Stopping and removing test-provenance-db container..."
    docker stop test-provenance-db
    docker rm test-provenance-db
}

if (docker ps -a --format "{{.Names}}" | Select-String -Pattern "^test-redis$") {
    Write-Host "Stopping and removing test-redis container..."
    docker stop test-redis
    docker rm test-redis
}

Write-Host "Test databases stopped and removed." 