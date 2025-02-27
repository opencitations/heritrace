# PowerShell script to stop test databases for HERITRACE

Write-Host "Stopping test databases..."

# Stop and remove dataset database container
docker stop test-dataset-db 2>$null
docker rm test-dataset-db 2>$null

# Stop and remove provenance database container
docker stop test-provenance-db 2>$null
docker rm test-provenance-db 2>$null

Write-Host "Test databases stopped and containers removed." 