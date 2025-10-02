# PowerShell script to launch Virtuoso databases using Docker

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

Write-Info "Starting Virtuoso databases using Docker..."

$heritrace_network = docker network ls | Select-String "heritrace_heritrace-network"
$legacy_network = docker network ls | Select-String "heritrace-network"

if ($heritrace_network) {
    $NetworkName = "heritrace_heritrace-network"
    Write-Info "Using existing Docker network: $NetworkName"
} elseif ($legacy_network) {
    $NetworkName = "heritrace-network"
    Write-Info "Using existing Docker network: $NetworkName"
} else {
    $NetworkName = "heritrace-network"
    Write-Info "Creating Docker network: $NetworkName"
    docker network create $NetworkName
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker network created successfully"
    } else {
        Write-Error "Failed to create Docker network"
        exit 1
    }
}

# Stop and remove existing containers if they exist
Write-Info "Cleaning up existing containers..."
docker stop heritrace-dataset heritrace-provenance 2>$null
docker rm heritrace-dataset heritrace-provenance 2>$null

# Get current directory
$CURRENT_DIR = (Get-Location).Path

# Create data directories
$datasetDbPath = Join-Path -Path $CURRENT_DIR -ChildPath "dataset_database"
$provDbPath = Join-Path -Path $CURRENT_DIR -ChildPath "prov_database"

if (-not (Test-Path -Path $datasetDbPath)) {
    New-Item -ItemType Directory -Path $datasetDbPath -Force | Out-Null
}
if (-not (Test-Path -Path $provDbPath)) {
    New-Item -ItemType Directory -Path $provDbPath -Force | Out-Null
}

Write-Info "Starting dataset database..."
docker run -d `
    --name heritrace-dataset `
    --network $NetworkName `
    -p 8890:8890 `
    -v "${datasetDbPath}:/database" `
    -e DBA_PASSWORD=dba `
    -e DAV_PASSWORD=dba `
    -e CONTAINER_TYPE=dataset `
    arcangelo7/heritrace-testing-virtuoso-dataset:1.0.2

if ($LASTEXITCODE -eq 0) {
    Write-Success "Dataset database started successfully"
} else {
    Write-Error "Failed to start dataset database"
    exit 1
}

Write-Info "Starting provenance database..."
docker run -d `
    --name heritrace-provenance `
    --network $NetworkName `
    -p 8891:8890 `
    -v "${provDbPath}:/database" `
    -e DBA_PASSWORD=dba `
    -e DAV_PASSWORD=dba `
    -e CONTAINER_TYPE=provenance `
    arcangelo7/heritrace-testing-virtuoso-provenance:1.0.2

if ($LASTEXITCODE -eq 0) {
    Write-Success "Provenance database started successfully"
} else {
    Write-Error "Failed to start provenance database"
    exit 1
}

Write-Info "Waiting for databases to be ready..."
Start-Sleep -Seconds 5

Write-Success "All databases started successfully!"
Write-Info ""
Write-Info "You can check their status with:"
Write-Info "  docker ps | findstr heritrace"
Write-Info ""
Write-Info "Access the databases at:"
Write-Info "  Dataset DB - HTTP: http://localhost:8890/sparql"
Write-Info "  Provenance DB - HTTP: http://localhost:8891/sparql"
