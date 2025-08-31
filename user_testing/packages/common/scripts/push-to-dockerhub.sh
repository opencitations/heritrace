#!/bin/bash

# Script to build and push auxiliary Docker images to Docker Hub
# Usage: ./push-to-dockerhub.sh [version] [docker_username]

set -e

VERSION=${1:-"1.0.1"}
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

echo "🔧 Setting up Docker buildx for multi-platform support..."
if ! docker buildx ls | grep -q "heritrace-builder"; then
    docker buildx create --name heritrace-builder --use
else
    docker buildx use heritrace-builder
fi
docker buildx inspect --bootstrap

echo "🔨 Building auxiliary Docker images for multiple platforms (amd64, arm64)..."
DOCKER_METADATA_AUTHOR="Arcangelo Massari"
DOCKER_METADATA_DESCRIPTION="Heritrace User Testing Environment - Auxiliary services (Virtuoso dataset and provenance databases) for HERITRACE testing"
DOCKER_METADATA_VERSION=$VERSION

echo "⬆️ Building and pushing dataset image for multiple platforms..."
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -f Dockerfile.virtuoso \
    -t $DOCKER_USERNAME/heritrace-testing-virtuoso-dataset:$VERSION \
    --build-arg DOCKER_METADATA_AUTHOR="$DOCKER_METADATA_AUTHOR" \
    --build-arg DOCKER_METADATA_DESCRIPTION="$DOCKER_METADATA_DESCRIPTION" \
    --build-arg DOCKER_METADATA_VERSION="$DOCKER_METADATA_VERSION" \
    --push .

echo "⬆️ Building and pushing provenance image for multiple platforms..."
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -f Dockerfile.provenance \
    -t $DOCKER_USERNAME/heritrace-testing-virtuoso-provenance:$VERSION \
    --build-arg DOCKER_METADATA_AUTHOR="$DOCKER_METADATA_AUTHOR" \
    --build-arg DOCKER_METADATA_DESCRIPTION="$DOCKER_METADATA_DESCRIPTION" \
    --build-arg DOCKER_METADATA_VERSION="$DOCKER_METADATA_VERSION" \
    --push .

echo "✅ Auxiliary images pushed to Docker Hub!"
echo ""
echo "🔧 To use the complete setup:"
echo "   - Dataset DB: $DOCKER_USERNAME/heritrace-testing-virtuoso-dataset:$VERSION"
echo "   - Provenance DB: $DOCKER_USERNAME/heritrace-testing-virtuoso-provenance:$VERSION"