# PowerShell script to stop Virtuoso databases

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

Write-Info "Stopping databases..."
docker stop heritrace-dataset heritrace-provenance 2>$null

Write-Info "Removing containers..."
docker rm heritrace-dataset heritrace-provenance 2>$null

Write-Success "Cleanup complete."
