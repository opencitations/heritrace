@echo off
setlocal enabledelayedexpansion

REM HERITRACE Test Database Builder
REM This script creates packages for building and pushing test databases to Docker Hub
REM The test databases contain a subset of OpenCitations Meta data for testing purposes

echo [BUILD] Building HERITRACE Test Database Packages
echo =====================================================

if not exist "..\..\app.py" (
    echo [ERROR] Error: This script must be run from user_testing\packages\
    echo    Current directory: %CD%
    pause
    exit /b 1
)

set BUILD_DIR=build
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%"

echo [FILES] Preparing build environment...

call :prepare_test_databases_package

echo [FOLDER] Moving test databases folder to final location...
move "%BUILD_DIR%\heritrace-test-databases" ".\"

for /f %%i in ('powershell -command "(Get-ChildItem -Path 'heritrace-test-databases' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set PACKAGE_SIZE_MB=%%i

echo.
echo [SUCCESS] Test databases folder created!
echo =================================
echo [FOLDER] Created folder:
echo    [DB] heritrace-test-databases/ (!PACKAGE_SIZE_MB! MB)
echo.
echo [INFO] The folder contains ONLY what's needed to build test database images:
echo    - Docker files for Virtuoso test databases (dataset and provenance)
echo    - Test data subset from OpenCitations Meta
echo    - Scripts to push the test database images to Docker Hub
echo    - docker-compose-test.yml for local testing
echo    - README with building instructions

echo.
echo [CLEAN] Cleaning up build directory...
rmdir /s /q "%BUILD_DIR%"

echo.
echo [READY] Ready to use! To test locally:
echo    cd heritrace-test-databases
echo    docker compose -f docker-compose-test.yml up

echo [DONE] Build complete!
pause
goto :eof

:prepare_test_databases_package
set build_package_dir=%BUILD_DIR%\heritrace-test-databases

echo [PKG] Building test databases package...

mkdir "%build_package_dir%"

echo    Copying Docker files for test databases...
copy "common\dockerfiles\Dockerfile.virtuoso" "%build_package_dir%\"
copy "common\dockerfiles\Dockerfile.provenance" "%build_package_dir%\"

echo    Copying test data...
mkdir "%build_package_dir%\data"
xcopy "common\data\*" "%build_package_dir%\data\" /E /I /Q

echo    Setting up Virtuoso configuration files...
mkdir "%build_package_dir%\dataset_database"
mkdir "%build_package_dir%\prov_database"
copy "common\templates\virtuoso_dataset.ini" "%build_package_dir%\dataset_database\virtuoso.ini"
copy "common\templates\virtuoso_provenance.ini" "%build_package_dir%\prov_database\virtuoso.ini"

echo    Copying database scripts...
mkdir "%build_package_dir%\scripts"
copy "common\scripts\virtuoso_utils.py" "%build_package_dir%\scripts\"
copy "common\scripts\load_data.py" "%build_package_dir%\scripts\"
copy "common\scripts\setup_provenance.py" "%build_package_dir%\scripts\"
copy "common\scripts\virtuoso_entrypoint.sh" "%build_package_dir%\scripts\"
copy "common\scripts\provenance_entrypoint.sh" "%build_package_dir%\scripts\"

echo    Copying Docker Hub push scripts...
copy "common\scripts\push-to-dockerhub.sh" "%build_package_dir%\"
copy "common\scripts\push-to-dockerhub.cmd" "%build_package_dir%\"

echo    Creating docker-compose-test.yml for local testing...
(
echo services:
echo   heritrace-dataset:
echo     build:
echo       context: .
echo       dockerfile: Dockerfile.virtuoso
echo     container_name: heritrace-dataset
echo     environment:
echo       - DBA_PASSWORD=dba
echo       - DAV_PASSWORD=dba
echo       - CONTAINER_TYPE=dataset
echo     ports:
echo       - "8890:8890"
echo     volumes:
echo       - ./dataset_database:/database
echo     healthcheck:
echo       test: ["CMD", "wget", "-q", "--spider", "http://localhost:8890/sparql"]
echo       interval: 30s
echo       timeout: 10s
echo       retries: 5
echo     networks:
echo       - heritrace-network
echo.
echo   heritrace-provenance:
echo     build:
echo       context: .
echo       dockerfile: Dockerfile.provenance
echo     container_name: heritrace-provenance
echo     environment:
echo       - DBA_PASSWORD=dba
echo       - DAV_PASSWORD=dba
echo       - CONTAINER_TYPE=provenance
echo     ports:
echo       - "8891:8890"
echo     volumes:
echo       - ./prov_database:/database
echo     healthcheck:
echo       test: ["CMD", "wget", "-q", "--spider", "http://localhost:8890/sparql"]
echo       interval: 30s
echo       timeout: 10s
echo       retries: 5
echo     networks:
echo       - heritrace-network
echo.
echo networks:
echo   heritrace-network:
echo     driver: bridge
) > "%build_package_dir%\docker-compose-test.yml"

echo    Creating README for database building...
(
echo # HERITRACE Test Databases
echo.
echo This package contains Docker files and scripts to build and push test database images to Docker Hub.
echo.
echo ## Contents
echo - Dockerfile.virtuoso: Docker file for dataset database
echo - Dockerfile.provenance: Docker file for provenance database  
echo - data/: Test data subset from OpenCitations Meta
echo - scripts/: Database initialization scripts
echo.
echo ## Testing Locally
echo.
echo To test the database images locally before pushing to Docker Hub, simply run:
echo.
echo ```bash
echo docker compose -f docker-compose-test.yml up
echo ```
echo.
echo This will build and start both databases. Visit:
echo - Dataset DB: http://localhost:8890/sparql 
echo - Provenance DB: http://localhost:8891/sparql
echo.
echo To stop the test databases:
echo ```bash
echo docker compose -f docker-compose-test.yml down
echo ```
echo.
echo ## Push to Docker Hub
echo.
echo To build and push the test database images to Docker Hub:
echo.
echo **Linux/macOS:**
echo ```bash
echo ./push-to-dockerhub.sh [version] [docker_username]
echo ```
echo.
echo **Windows:**
echo ```cmd
echo push-to-dockerhub.cmd [version] [docker_username]
echo ```
echo.
echo This will create and push:
echo - arcangelo7/heritrace-testing-virtuoso-dataset:[version]
echo - arcangelo7/heritrace-testing-virtuoso-provenance:[version]
echo.
) > "%build_package_dir%\README.md"

REM Clean up Python cache files
for /d /r "%build_package_dir%" %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
del /s /q "%build_package_dir%\*.pyc" 2>nul

echo    [DONE] Test databases package prepared
goto :eof