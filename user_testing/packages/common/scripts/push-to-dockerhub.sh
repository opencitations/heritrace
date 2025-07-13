#!/bin/bash

# Script to tag and push Docker images to Docker Hub
# Usage: ./push-to-dockerhub.sh [version] [docker_username]

set -e

VERSION=${1:-"1.0.0"}
DOCKER_USERNAME=${2:-"arcangelo7"}

echo "🐳 Tagging and pushing Docker images to Docker Hub"
echo "=================================================="
echo "Version: $VERSION"
echo "Docker Username: $DOCKER_USERNAME"
echo ""

if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running or not accessible"
    exit 1
fi

echo "🔐 Ensuring you are logged in to Docker Hub..."
docker login

echo "🔨 Building Docker images..."
docker compose build

PROJECT_NAME=$(basename "$PWD")
HERITRACE_IMAGE="${PROJECT_NAME}-heritrace"
DATASET_IMAGE="${PROJECT_NAME}-heritrace-dataset"
PROVENANCE_IMAGE="${PROJECT_NAME}-heritrace-provenance"

echo "🏷️ Tagging images..."
docker tag $HERITRACE_IMAGE $DOCKER_USERNAME/heritrace-testing:$VERSION
docker tag $DATASET_IMAGE $DOCKER_USERNAME/heritrace-testing-virtuoso-dataset:$VERSION
docker tag $PROVENANCE_IMAGE $DOCKER_USERNAME/heritrace-testing-virtuoso-provenance:$VERSION

echo "⬆️ Pushing images to Docker Hub..."
docker push $DOCKER_USERNAME/heritrace-testing-virtuoso-dataset:$VERSION
docker push $DOCKER_USERNAME/heritrace-testing-virtuoso-provenance:$VERSION
docker push $DOCKER_USERNAME/heritrace-testing:$VERSION

echo "✅ All images pushed to Docker Hub!"