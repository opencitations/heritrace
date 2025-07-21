#!/bin/bash

# Script to build and push auxiliary Docker images to Docker Hub
# Usage: ./push-to-dockerhub.sh [version] [docker_username]

set -e

VERSION=${1:-"1.0.0"}
DOCKER_USERNAME=${2:-"arcangelo7"}

echo "🐳 Building and pushing auxiliary Docker images to Docker Hub"
echo "============================================================="
echo "Version: $VERSION"
echo "Docker Username: $DOCKER_USERNAME"
echo ""

if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running or not accessible"
    exit 1
fi

echo "🔐 Ensuring you are logged in to Docker Hub..."
docker login

echo "🔨 Building auxiliary Docker images (Virtuoso dataset and provenance)..."
DOCKER_METADATA_AUTHOR="Arcangelo Massari"
DOCKER_METADATA_DESCRIPTION="Heritrace User Testing Environment - Auxiliary services (Virtuoso dataset and provenance databases) for HERITRACE testing"
DOCKER_METADATA_VERSION=$VERSION

docker build -f Dockerfile.virtuoso -t temp-dataset --build-arg DOCKER_METADATA_AUTHOR="$DOCKER_METADATA_AUTHOR" --build-arg DOCKER_METADATA_DESCRIPTION="$DOCKER_METADATA_DESCRIPTION" --build-arg DOCKER_METADATA_VERSION="$DOCKER_METADATA_VERSION" .
docker build -f Dockerfile.provenance -t temp-provenance --build-arg DOCKER_METADATA_AUTHOR="$DOCKER_METADATA_AUTHOR" --build-arg DOCKER_METADATA_DESCRIPTION="$DOCKER_METADATA_DESCRIPTION" --build-arg DOCKER_METADATA_VERSION="$DOCKER_METADATA_VERSION" .

echo "🏷️ Tagging auxiliary images..."
docker tag temp-dataset $DOCKER_USERNAME/heritrace-testing-virtuoso-dataset:$VERSION
docker tag temp-provenance $DOCKER_USERNAME/heritrace-testing-virtuoso-provenance:$VERSION

echo "⬆️ Pushing auxiliary images to Docker Hub..."
docker push $DOCKER_USERNAME/heritrace-testing-virtuoso-dataset:$VERSION
docker push $DOCKER_USERNAME/heritrace-testing-virtuoso-provenance:$VERSION

echo "🧹 Cleaning up temporary images..."
docker rmi temp-dataset temp-provenance

echo "✅ Auxiliary images pushed to Docker Hub!"
echo ""
echo "🔧 To use the complete setup:"
echo "   - Dataset DB: $DOCKER_USERNAME/heritrace-testing-virtuoso-dataset:$VERSION"
echo "   - Provenance DB: $DOCKER_USERNAME/heritrace-testing-virtuoso-provenance:$VERSION"