Write-Host "Stopping databases..."
docker stop dataset_db provenance_db

Write-Host "Removing containers..."
docker rm dataset_db provenance_db

Write-Host "Cleaning up network..."
docker network rm virtuoso-net

Write-Host "Cleanup complete."