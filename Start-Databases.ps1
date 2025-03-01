# Get the absolute path of the current directory
$CURRENT_DIR = (Get-Location).Path

# Create database directories if they don't exist
$datasetDbPath = Join-Path -Path $CURRENT_DIR -ChildPath "database"
$provDbPath = Join-Path -Path $CURRENT_DIR -ChildPath "prov_database"

if (-not (Test-Path -Path $datasetDbPath)) {
    Write-Host "Creating dataset database directory..."
    New-Item -ItemType Directory -Path $datasetDbPath -Force | Out-Null
}

if (-not (Test-Path -Path $provDbPath)) {
    Write-Host "Creating provenance database directory..."
    New-Item -ItemType Directory -Path $provDbPath -Force | Out-Null
}

# Create network if it doesn't exist
docker network create virtuoso-net 2>$null

# Check if containers already exist and remove them if they do
if (docker ps -a --format "{{.Names}}" | Select-String -Pattern "^dataset_db$") {
    Write-Host "Removing existing dataset_db container..."
    docker rm -f dataset_db
}

if (docker ps -a --format "{{.Names}}" | Select-String -Pattern "^provenance_db$") {
    Write-Host "Removing existing provenance_db container..."
    docker rm -f provenance_db
}

# Start dataset database
Write-Host "Starting dataset database..."
docker run -d `
  --name dataset_db `
  --network virtuoso-net `
  -p 8999:8890 `
  -p 1119:1111 `
  -e DBA_PASSWORD=dba `
  -e SPARQL_UPDATE=true `
  -v "${datasetDbPath}:/database" `
  openlink/virtuoso-opensource-7@sha256:c08d54120b8085234f8244951232553428e235543412e41d75705736a3026f1b

# Start provenance database
Write-Host "Starting provenance database..."
docker run -d `
  --name provenance_db `
  --network virtuoso-net `
  -p 8998:8890 `
  -p 1118:1111 `
  -e DBA_PASSWORD=dba `
  -e SPARQL_UPDATE=true `
  -v "${provDbPath}:/database" `
  openlink/virtuoso-opensource-7@sha256:c08d54120b8085234f8244951232553428e235543412e41d75705736a3026f1b

Write-Host "Waiting for databases to initialize..."
Start-Sleep -Seconds 5

Write-Host "Databases started. You can check their status with:"
Write-Host "docker ps | findstr virtuoso"