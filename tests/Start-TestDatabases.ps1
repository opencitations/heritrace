# PowerShell script to start test databases for HERITRACE

# Get the absolute path of the current directory
$CURRENT_DIR = (Get-Location).Path

# Create test database directories if they don't exist
$datasetDbPath = Join-Path -Path $CURRENT_DIR -ChildPath "tests\test_dataset_db"
$provDbPath = Join-Path -Path $CURRENT_DIR -ChildPath "tests\test_provenance_db"

if (-not (Test-Path -Path $datasetDbPath)) {
    Write-Host "Creating dataset database directory..."
    New-Item -Path $datasetDbPath -ItemType Directory -Force | Out-Null
}

if (-not (Test-Path -Path $provDbPath)) {
    Write-Host "Creating provenance database directory..."
    New-Item -Path $provDbPath -ItemType Directory -Force | Out-Null
}

# Check if containers already exist and remove them if they do
if (docker ps -a --format "{{.Names}}" | Select-String -Pattern "^test-dataset-db$") {
    Write-Host "Removing existing test-dataset-db container..."
    docker rm -f test-dataset-db
}

if (docker ps -a --format "{{.Names}}" | Select-String -Pattern "^test-provenance-db$") {
    Write-Host "Removing existing test-provenance-db container..."
    docker rm -f test-provenance-db
}

# Start Virtuoso for dataset database on port 9999 (different from dev port 8999)
Write-Host "Starting test-dataset-db container..."
docker run -d --name test-dataset-db `
  -p 9999:8890 `
  -e DBA_PASSWORD=dba `
  -e SPARQL_UPDATE=true `
  -v "${datasetDbPath}:/database" `
  openlink/virtuoso-opensource-7:latest

# Start Virtuoso for provenance database on port 9998 (different from dev port 8998)
Write-Host "Starting test-provenance-db container..."
docker run -d --name test-provenance-db `
  -p 9998:8890 `
  -e DBA_PASSWORD=dba `
  -e SPARQL_UPDATE=true `
  -v "${provDbPath}:/database" `
  openlink/virtuoso-opensource-7:latest

# Wait for databases to be ready
Write-Host "Waiting for test databases to start..."
Start-Sleep -Seconds 30
Write-Host "Test databases should be ready now."

# Set permissions for the 'nobody' user in both databases
Write-Host "Setting permissions for the 'nobody' user in the dataset database..."
docker exec test-dataset-db /opt/virtuoso-opensource/bin/isql -U dba -P dba exec="DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('nobody', 7);"

Write-Host "Setting permissions for the 'nobody' user in the provenance database..."
docker exec test-provenance-db /opt/virtuoso-opensource/bin/isql -U dba -P dba exec="DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('nobody', 7);"

# Assign SPARQL_UPDATE role to the SPARQL account
Write-Host "Assigning SPARQL_UPDATE role to the SPARQL account in the dataset database..."
docker exec test-dataset-db /opt/virtuoso-opensource/bin/isql -U dba -P dba exec="DB.DBA.USER_GRANT_ROLE ('SPARQL', 'SPARQL_UPDATE');"

Write-Host "Assigning SPARQL_UPDATE role to the SPARQL account in the provenance database..."
docker exec test-provenance-db /opt/virtuoso-opensource/bin/isql -U dba -P dba exec="DB.DBA.USER_GRANT_ROLE ('SPARQL', 'SPARQL_UPDATE');"

Write-Host "Permissions set successfully."
Write-Host "Dataset DB: http://localhost:9999/sparql"
Write-Host "Provenance DB: http://localhost:9998/sparql" 