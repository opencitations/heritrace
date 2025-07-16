@echo off

echo HERITRACE Data Export
echo ==============================================

set "ROOT_DIR=%~dp0"

set "EXPORT_DIR=%ROOT_DIR%export"
set "DATA_DIR=%EXPORT_DIR%\data"
set "PROVENANCE_DIR=%EXPORT_DIR%\provenance"
set "ZIP_FILE=%cd%\export.zip"

docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running!
    echo    Please start Docker Desktop and try again.
    pause
    exit /b 1
)

if exist "%EXPORT_DIR%" rmdir /s /q "%EXPORT_DIR%"
mkdir "%DATA_DIR%"
mkdir "%PROVENANCE_DIR%"

echo Exporting database data...

for /f "tokens=*" %%i in ('docker ps --filter "name=dataset" --format "{{.Names}}" ^| findstr "."') do set DATASET_CONTAINER=%%i
for /f "tokens=*" %%i in ('docker ps --filter "name=provenance" --format "{{.Names}}" ^| findstr "."') do set PROVENANCE_CONTAINER=%%i

if "%DATASET_CONTAINER%"=="" (
    echo Error: Dataset container not found. Make sure the application is running.
    pause
    exit /b 1
)

if "%PROVENANCE_CONTAINER%"=="" (
    echo Error: Provenance container not found. Make sure the application is running.
    pause
    exit /b 1
)

call :export_virtuoso_data "%DATASET_CONTAINER%" "%DATA_DIR%\data.ttl" "dataset"
call :export_virtuoso_data "%PROVENANCE_CONTAINER%" "%PROVENANCE_DIR%\data.ttl" "provenance"

echo Including testing questionnaires and responses...
if exist "sus_questionnaire.md" (
    copy "sus_questionnaire.md" "%EXPORT_DIR%\" > nul
    echo    SUS questionnaire included
)

if exist "written_responses_template.md" (
    copy "written_responses_template.md" "%EXPORT_DIR%\" > nul
    echo    Written responses template included
)

echo.
echo All data exported successfully!
echo.

echo Creating zip archive...
powershell -command "Compress-Archive -Path '%EXPORT_DIR%\*' -DestinationPath '%ZIP_FILE%' -Force" > nul
if exist "%EXPORT_DIR%" rmdir /s /q "%EXPORT_DIR%"
echo Complete export archive: %ZIP_FILE%

echo.
echo Press any key to continue...
pause >nul
exit /b 0

:export_virtuoso_data
set container=%~1
set output_file=%~2
set db_type=%~3

echo    Exporting %db_type% data from %container%...

set "sparql_query=CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } FILTER(?g NOT IN (<http://localhost:8890/DAV/>, <http://www.openlinksw.com/schemas/virtrdf#>, <http://www.w3.org/2002/07/owl#>, <http://www.w3.org/ns/ldp#>, <urn:activitystreams-owl:map>, <urn:core:services:sparql>)) }"

docker exec %container% curl -s -X POST -H "Content-Type: application/sparql-query" -H "Accept: text/turtle" --data "%sparql_query%" http://localhost:8890/sparql > "%output_file%"

echo %db_type% data exported successfully
exit /b 0
