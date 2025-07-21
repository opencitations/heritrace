@echo off
setlocal enabledelayedexpansion

REM Script to build and push auxiliary Docker images to Docker Hub
REM Usage: push-to-dockerhub.cmd [version] [docker_username]

set VERSION=%1
set DOCKER_USERNAME=%2

if "%VERSION%"=="" set VERSION=1.0.0
if "%DOCKER_USERNAME%"=="" set DOCKER_USERNAME=arcangelo7

echo [DOCKER] Building and pushing auxiliary Docker images to Docker Hub
echo =============================================================
echo Version: %VERSION%
echo Docker Username: %DOCKER_USERNAME%
echo.

docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running or not accessible
    pause
    exit /b 1
)

echo [LOGIN] Ensuring you are logged in to Docker Hub...
docker login
if %errorlevel% neq 0 (
    echo [ERROR] Docker login failed
    pause
    exit /b 1
)

echo [BUILD] Building auxiliary Docker images (Virtuoso dataset and provenance)...
set DOCKER_METADATA_AUTHOR=Arcangelo Massari
set DOCKER_METADATA_DESCRIPTION=Heritrace User Testing Environment - Auxiliary services (Virtuoso dataset and provenance databases) for HERITRACE testing
set DOCKER_METADATA_VERSION=%VERSION%

REM Build only the auxiliary services (dataset and provenance databases)
docker build -f Dockerfile.virtuoso -t temp-dataset --build-arg DOCKER_METADATA_AUTHOR="%DOCKER_METADATA_AUTHOR%" --build-arg DOCKER_METADATA_DESCRIPTION="%DOCKER_METADATA_DESCRIPTION%" --build-arg DOCKER_METADATA_VERSION="%DOCKER_METADATA_VERSION%" .
if %errorlevel% neq 0 (
    echo [ERROR] Failed to build dataset Docker image
    pause
    exit /b 1
)

docker build -f Dockerfile.provenance -t temp-provenance --build-arg DOCKER_METADATA_AUTHOR="%DOCKER_METADATA_AUTHOR%" --build-arg DOCKER_METADATA_DESCRIPTION="%DOCKER_METADATA_DESCRIPTION%" --build-arg DOCKER_METADATA_VERSION="%DOCKER_METADATA_VERSION%" .
if %errorlevel% neq 0 (
    echo [ERROR] Failed to build provenance Docker image
    pause
    exit /b 1
)

echo [TAG] Tagging auxiliary images...
docker tag temp-dataset %DOCKER_USERNAME%/heritrace-testing-virtuoso-dataset:%VERSION%
docker tag temp-provenance %DOCKER_USERNAME%/heritrace-testing-virtuoso-provenance:%VERSION%

echo [PUSH] Pushing auxiliary images to Docker Hub...
docker push %DOCKER_USERNAME%/heritrace-testing-virtuoso-dataset:%VERSION%
if %errorlevel% neq 0 (
    echo [ERROR] Failed to push dataset image
    pause
    exit /b 1
)

docker push %DOCKER_USERNAME%/heritrace-testing-virtuoso-provenance:%VERSION%
if %errorlevel% neq 0 (
    echo [ERROR] Failed to push provenance image
    pause
    exit /b 1
)

echo [CLEANUP] Cleaning up temporary images...
docker rmi temp-dataset temp-provenance

echo [SUCCESS] Auxiliary images pushed to Docker Hub!
echo.
echo [USAGE] To use the complete setup:
echo   - Dataset DB: %DOCKER_USERNAME%/heritrace-testing-virtuoso-dataset:%VERSION%
echo   - Provenance DB: %DOCKER_USERNAME%/heritrace-testing-virtuoso-provenance:%VERSION%
pause