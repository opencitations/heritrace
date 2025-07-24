# HERITRACE Test Database Packages

This directory contains scripts specifically for building and managing test databases for HERITRACE user testing.

**PURPOSE**: These scripts create Docker packages containing a subset of OpenCitations Meta data for testing purposes. The main HERITRACE application uses the official Docker Hub image `arcangelo7/heritrace`.

## Build Test Database Packages

To create packages containing test database Docker files and scripts:

**Linux/macOS:**
Run from terminal:
```bash
./build-test-databases.sh
```

**Windows:**
Double-click `build-test-databases.cmd` or run from command prompt:
```cmd
build-test-databases.cmd
```

This will create `heritrace-enduser-local.zip` containing:
- Docker files for building Virtuoso test databases (dataset and provenance)
- Test data subset from OpenCitations Meta
- Scripts to push test database images to Docker Hub
- Complete testing environment using official HERITRACE image

## Online Testing Packages

For lightweight packages that only pull from Docker Hub (no local building):

**Linux/macOS:**
Run from terminal:
```bash
./build-online-packages.sh
```

**Windows:**
Double-click `build-online-packages.cmd` or run from command prompt:
```cmd
build-online-packages.cmd
```

This creates minimal packages using published Docker images:
- **Main app**: `arcangelo7/heritrace` (official image)
- **Dataset DB**: `arcangelo7/heritrace-testing-virtuoso-dataset:1.0.0` (test database)
- **Provenance DB**: `arcangelo7/heritrace-testing-virtuoso-provenance:1.0.0` (test database)

## Push Test Databases to Docker Hub

To build and push the test database images to Docker Hub:

**Linux/macOS:**
Run from terminal:
```bash
cd common/scripts
./push-to-dockerhub.sh [version] [docker_username]
```

**Windows:**
```cmd
cd common\scripts
push-to-dockerhub.cmd [version] [docker_username]
```