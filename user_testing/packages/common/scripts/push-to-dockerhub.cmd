@echo off
setlocal enabledelayedexpansion

REM Script to build and push auxiliary Docker images to Docker Hub
REM Usage: push-to-dockerhub.cmd [version] [docker_username]

set VERSION=%1
set DOCKER_USERNAME=%2

if "%VERSION%"=="" set VERSION=1.0.1
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

echo [BUILDX] Setting up Docker buildx for multi-platform support...
docker buildx ls | findstr heritrace-builder >nul 2>&1
if %errorlevel% neq 0 (
    docker buildx create --name heritrace-builder --use
) else (
    docker buildx use heritrace-builder
)
docker buildx inspect --bootstrap

echo [BUILD] Building auxiliary Docker images for multiple platforms (amd64, arm64)...
set DOCKER_METADATA_AUTHOR=Arcangelo Massari
set DOCKER_METADATA_DESCRIPTION=Heritrace User Testing Environment - Auxiliary services (Virtuoso dataset and provenance databases) for HERITRACE testing
set DOCKER_METADATA_VERSION=%VERSION%

echo [PUSH] Building and pushing dataset image for multiple platforms...
docker buildx build ^
    --platform linux/amd64,linux/arm64 ^
    -f Dockerfile.virtuoso ^
    -t %DOCKER_USERNAME%/heritrace-testing-virtuoso-dataset:%VERSION% ^
    --build-arg DOCKER_METADATA_AUTHOR="%DOCKER_METADATA_AUTHOR%" ^
    --build-arg DOCKER_METADATA_DESCRIPTION="%DOCKER_METADATA_DESCRIPTION%" ^
    --build-arg DOCKER_METADATA_VERSION="%DOCKER_METADATA_VERSION%" ^
    --push .
if %errorlevel% neq 0 (
    echo [ERROR] Failed to build and push dataset Docker image
    pause
    exit /b 1
)

echo [PUSH] Building and pushing provenance image for multiple platforms...
docker buildx build ^
    --platform linux/amd64,linux/arm64 ^
    -f Dockerfile.provenance ^
    -t %DOCKER_USERNAME%/heritrace-testing-virtuoso-provenance:%VERSION% ^
    --build-arg DOCKER_METADATA_AUTHOR="%DOCKER_METADATA_AUTHOR%" ^
    --build-arg DOCKER_METADATA_DESCRIPTION="%DOCKER_METADATA_DESCRIPTION%" ^
    --build-arg DOCKER_METADATA_VERSION="%DOCKER_METADATA_VERSION%" ^
    --push .
if %errorlevel% neq 0 (
    echo [ERROR] Failed to build and push provenance Docker image
    pause
    exit /b 1
)

echo [SUCCESS] Auxiliary images pushed to Docker Hub!
echo.
echo [USAGE] To use the complete setup:
echo   - Dataset DB: %DOCKER_USERNAME%/heritrace-testing-virtuoso-dataset:%VERSION%
echo   - Provenance DB: %DOCKER_USERNAME%/heritrace-testing-virtuoso-provenance:%VERSION%
pause