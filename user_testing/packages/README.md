# User Testing Packages

This directory contains scripts to package the application for user testing.

## Local Package

To generate a complete local package for testing, run the following script:

**Linux/macOS:**
```bash
./build-local-packages.sh
```

**Windows:**
Double-click `build-local-packages.cmd` or run from command prompt:
```cmd
build-local-packages.cmd
```

This will create a self-contained package with all the necessary files for local testing.

## Online Package (Docker-based)

This approach provides a minimal package for testers, with most of the application services running in Docker containers.

### 1. Generate and Prepare the Local Package

First, you need to generate a local package, which contains the necessary scripts to push the Docker images.

**Linux/macOS:**
```bash
./build-local-packages.sh
```

**Windows:**
Double-click `build-local-packages.cmd` or run from command prompt:
```cmd
build-local-packages.cmd
```

This will create `heritrace-technician-local.zip` and `heritrace-enduser-local.zip`.

### 2. Push to Docker Hub

Next, unzip one of the generated packages (e.g., the technician package) and run the script to push the Docker images to Docker Hub.

```bash
unzip heritrace-technician-local.zip
cd heritrace-technician-local
./push-to-dockerhub.sh
cd ..
```

### 3. Build Online Package

Once the images are on Docker Hub, you can generate the lightweight online package:

**Linux/macOS:**
```bash
./build-online-packages.sh
```

**Windows:**
Double-click `build-online-packages.cmd` or run from command prompt:
```cmd
build-online-packages.cmd
```

This creates a minimal set of files for the end-user, who will pull the required Docker images to run the application.
