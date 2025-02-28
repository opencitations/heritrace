# PowerShell script to start test databases for HERITRACE

# Create test database directories if they don't exist
New-Item -Path "tests/test_dataset_db" -ItemType Directory -Force | Out-Null
New-Item -Path "tests/test_provenance_db" -ItemType Directory -Force | Out-Null

# Start Virtuoso for dataset database on port 9999 (different from dev port 8999)
docker run -d --name test-dataset-db `
  -p 9999:8890 `
  -e DBA_PASSWORD=dba `
  -e SPARQL_UPDATE=true `
  -v "${PWD}/tests/test_dataset_db:/database" `
  openlink/virtuoso-opensource-7:latest

# Start Virtuoso for provenance database on port 9998 (different from dev port 8998)
docker run -d --name test-provenance-db `
  -p 9998:8890 `
  -e DBA_PASSWORD=dba `
  -e SPARQL_UPDATE=true `
  -v "${PWD}/tests/test_provenance_db:/database" `
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