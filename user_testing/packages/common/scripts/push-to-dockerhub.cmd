@echo off
setlocal enabledelayedexpansion

REM Script to tag and push Docker images to Docker Hub
REM Usage: push-to-dockerhub.cmd [version] [docker_username]

set VERSION=%1
set DOCKER_USERNAME=%2

if "%VERSION%"=="" set VERSION=1.0.0
if "%DOCKER_USERNAME%"=="" set DOCKER_USERNAME=arcangelo7

echo [DOCKER] Tagging and pushing Docker images to Docker Hub
echo ==================================================
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

echo [BUILD] Building Docker images...
set DOCKER_METADATA_AUTHOR=Arcangelo Massari
set DOCKER_METADATA_DESCRIPTION=Heritrace User Testing Environment - A comprehensive testing suite for HERITRACE, the semantic data editor for galleries, libraries, archives, and museums (GLAM) professionals. This environment enables usability testing of metadata editing workflows, provenance management, and semantic data integration features.
set DOCKER_METADATA_VERSION=%VERSION%

docker compose build --build-arg DOCKER_METADATA_AUTHOR="%DOCKER_METADATA_AUTHOR%" --build-arg DOCKER_METADATA_DESCRIPTION="%DOCKER_METADATA_DESCRIPTION%" --build-arg DOCKER_METADATA_VERSION="%DOCKER_METADATA_VERSION%"
if %errorlevel% neq 0 (
    echo [ERROR] Docker build failed
    pause
    exit /b 1
)

for %%i in ("%CD%") do set PROJECT_NAME=%%~nxi
set HERITRACE_IMAGE=%PROJECT_NAME%-heritrace
set DATASET_IMAGE=%PROJECT_NAME%-heritrace-dataset
set PROVENANCE_IMAGE=%PROJECT_NAME%-heritrace-provenance

echo [TAG] Tagging images...
docker tag %HERITRACE_IMAGE% %DOCKER_USERNAME%/heritrace-testing:%VERSION%
docker tag %DATASET_IMAGE% %DOCKER_USERNAME%/heritrace-testing-virtuoso-dataset:%VERSION%
docker tag %PROVENANCE_IMAGE% %DOCKER_USERNAME%/heritrace-testing-virtuoso-provenance:%VERSION%

echo [PUSH] Pushing images to Docker Hub...
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

docker push %DOCKER_USERNAME%/heritrace-testing:%VERSION%
if %errorlevel% neq 0 (
    echo [ERROR] Failed to push heritrace image
    pause
    exit /b 1
)

echo [SUCCESS] All images pushed to Docker Hub!
pause