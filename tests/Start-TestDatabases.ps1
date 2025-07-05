# PowerShell script to start test databases for HERITRACE using virtuoso-launch

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

function Test-Command {
    param([string]$CommandName)
    
    try {
        Get-Command $CommandName -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Install-Pipx {
    Write-Info "Installing pipx..."
    
    if (Test-Command "python") {
        try {
            python -m pip install --user pipx
            if ($LASTEXITCODE -eq 0) {
                python -m pipx ensurepath
                $userBinPath = [System.IO.Path]::Combine($env:APPDATA, "Python", "Scripts")
                if (Test-Path $userBinPath) {
                    $env:PATH += ";$userBinPath"
                }
                Write-Success "pipx installed successfully via python -m pip"
                return $true
            }
        }
        catch {
            Write-Warning "Failed to install pipx via python -m pip"
        }
    }
    
    if (Test-Command "python3") {
        try {
            python3 -m pip install --user pipx
            if ($LASTEXITCODE -eq 0) {
                python3 -m pipx ensurepath
                Write-Success "pipx installed successfully via python3 -m pip"
                return $true
            }
        }
        catch {
            Write-Warning "Failed to install pipx via python3 -m pip"
        }
    }
    
    if (Test-Command "pip") {
        try {
            pip install --user pipx
            if ($LASTEXITCODE -eq 0) {
                pipx ensurepath
                Write-Success "pipx installed successfully via pip"
                return $true
            }
        }
        catch {
            Write-Warning "Failed to install pipx via pip"
        }
    }
    
    Write-Error "Failed to install pipx. Please install it manually:"
    Write-Error "  - Via pip: pip install --user pipx"
    Write-Error "  - Via Scoop: scoop install pipx"
    Write-Error "  - Via Chocolatey: choco install pipx"
    return $false
}

function Setup-VirtuosoUtilities {
    if (-not (Test-Command "pipx")) {
        Write-Warning "pipx not found. Attempting to install..."
        if (-not (Install-Pipx)) {
            return $false
        }
    }
    
    if (-not (Test-Command "virtuoso-launch")) {
        Write-Info "virtuoso-utilities not found. Installing..."
        try {
            pipx install virtuoso-utilities
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to install virtuoso-utilities"
                return $false
            }
            Write-Success "virtuoso-utilities installed successfully"
        }
        catch {
            Write-Error "Failed to install virtuoso-utilities: $_"
            return $false
        }
    }
    else {
        Write-Info "virtuoso-utilities already installed"
    }
    
    return $true
}

function Launch-VirtuosoDatabase {
    param(
        [string]$Name,
        [int]$HttpPort,
        [int]$IsqlPort,
        [string]$DataDir
    )
    
    Write-Info "Launching Virtuoso test database: $Name"
    Write-Info "  HTTP Port: $HttpPort"
    Write-Info "  ISQL Port: $IsqlPort"
    Write-Info "  Data Directory: $DataDir"
    
    if (-not (Test-Path -Path $DataDir)) {
        Write-Info "Creating data directory: $DataDir"
        New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    }
    
    try {
        virtuoso-launch `
            --name $Name `
            --http-port $HttpPort `
            --isql-port $IsqlPort `
            --data-dir $DataDir `
            --dba-password "dba" `
            --detach `
            --force-remove `
            --wait-ready `
            --enable-write-permissions
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Test database $Name started successfully"
            return $true
        }
        else {
            Write-Error "Failed to start test database $Name (exit code: $LASTEXITCODE)"
            return $false
        }
    }
    catch {
        Write-Error "Failed to start test database $Name: $_"
        return $false
    }
}

# Get the absolute path of the current directory
$CURRENT_DIR = (Get-Location).Path

# Setup virtuoso-utilities
if (-not (Setup-VirtuosoUtilities)) {
    Write-Error "Failed to setup virtuoso-utilities. Exiting."
    exit 1
}

# Start Virtuoso for dataset database
$datasetDbPath = Join-Path -Path $CURRENT_DIR -ChildPath "tests\test_dataset_db"
Write-Info "Starting test-dataset-db container..."
if (-not (Launch-VirtuosoDatabase -Name "test-dataset-db" -HttpPort 9999 -IsqlPort 10099 -DataDir $datasetDbPath)) {
    Write-Error "Failed to start test-dataset-db"
    exit 1
}

# Start Virtuoso for provenance database
$provDbPath = Join-Path -Path $CURRENT_DIR -ChildPath "tests\test_provenance_db"
Write-Info "Starting test-provenance-db container..."
if (-not (Launch-VirtuosoDatabase -Name "test-provenance-db" -HttpPort 9998 -IsqlPort 10098 -DataDir $provDbPath)) {
    Write-Error "Failed to start test-provenance-db"
    exit 1
}

# Start Redis for resource locking on port 6380
if (docker ps -a --format "{{.Names}}" | Select-String -Pattern "^test-redis$") {
    Write-Info "Removing existing test-redis container..."
    docker rm -f test-redis
}

Write-Info "Starting test-redis container..."
docker run -d --name test-redis `
  -p 6380:6379 `
  redis:7-alpine

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to start test-redis"
    exit 1
}

Write-Success "All test databases started successfully."
Write-Info "Dataset DB: http://localhost:9999/sparql"
Write-Info "Provenance DB: http://localhost:9998/sparql"
Write-Info "Redis: localhost:6380" 