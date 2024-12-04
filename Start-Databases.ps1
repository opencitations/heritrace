# Create network if it doesn't exist
docker network create virtuoso-net 2>$null

# Start dataset database
Write-Host "Starting dataset database..."
docker run -d `
  --name dataset_db `
  --network virtuoso-net `
  -p 8999:8890 `
  -p 1119:1111 `
  -e DBA_PASSWORD=dba `
  -e SPARQL_UPDATE=true `
  -v "${PWD}/database:/database" `
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
  -v "${PWD}/prov_database:/database" `
  openlink/virtuoso-opensource-7@sha256:c08d54120b8085234f8244951232553428e235543412e41d75705736a3026f1b

Write-Host "Waiting for databases to initialize..."
Start-Sleep -Seconds 5

Write-Host "Databases started. You can check their status with:"
Write-Host "docker ps | findstr virtuoso"