# PowerShell script to launch Virtuoso databases using launch_virtuoso

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
    
    Write-Info "Launching Virtuoso database: $Name"
    Write-Info "  HTTP Port: $HttpPort"
    Write-Info "  ISQL Port: $IsqlPort"
    Write-Info "  Data Directory: $DataDir"
    Write-Info "  Memory Limit: 4g"
    
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
            --memory "4g" `
            --dba-password "dba" `
            --detach `
            --force-remove `
            --wait-ready `
            --enable-write-permissions
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Database $Name started successfully"
            return $true
        }
        else {
            Write-Error "Failed to start database $Name (exit code: $LASTEXITCODE)"
            return $false
        }
    }
    catch {
        Write-Error "Failed to start database $Name: $_"
        return $false
    }
}

Write-Info "Setting up Virtuoso databases using launch_virtuoso..."

if (-not (Setup-VirtuosoUtilities)) {
    Write-Error "Failed to setup virtuoso-utilities. Exiting."
    exit 1
}

Write-Info "Creating Docker network (if needed)..."
docker network create virtuoso-net 2>$null
$CURRENT_DIR = (Get-Location).Path

$datasetDbPath = Join-Path -Path $CURRENT_DIR -ChildPath "database"
$provDbPath = Join-Path -Path $CURRENT_DIR -ChildPath "prov_database"

Write-Info "Starting dataset database..."
if (-not (Launch-VirtuosoDatabase -Name "database" -HttpPort 8999 -IsqlPort 1119 -DataDir $datasetDbPath)) {
    Write-Error "Failed to start dataset database"
    exit 1
}

Write-Info "Starting provenance database..."
if (-not (Launch-VirtuosoDatabase -Name "prov_database" -HttpPort 8998 -IsqlPort 1118 -DataDir $provDbPath)) {
    Write-Error "Failed to start provenance database"
    exit 1
}

Write-Success "All databases started successfully!"
Write-Info ""
Write-Info "You can check their status with:"
Write-Info "  docker ps | findstr virtuoso"
Write-Info ""
Write-Info "Access the databases at:"
Write-Info "  Dataset DB - HTTP: http://localhost:8999 | ISQL: localhost:1119"
Write-Info "  Provenance DB - HTTP: http://localhost:8998 | ISQL: localhost:1118"