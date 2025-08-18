Write-Host "Stopping databases..." -ForegroundColor Blue
docker stop database prov_database

Write-Host "Removing containers..." -ForegroundColor Blue
docker rm database prov_database

Write-Host "Cleanup complete." -ForegroundColor Green