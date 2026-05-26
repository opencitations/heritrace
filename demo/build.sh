#!/bin/bash

# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

set -e

VERSION=${1:-"1.0.0"}
DOCKER_USERNAME=${2:-"arcangelo7"}
IMAGE="$DOCKER_USERNAME/heritrace-demo-dataset:$VERSION"

echo "Building and pushing demo Virtuoso image"
echo "Version: $VERSION"
echo "Image: $IMAGE"

if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running" >&2
    exit 1
fi

echo "Logging in to Docker Hub..."
docker login

if ! docker buildx ls | grep -q "heritrace-builder"; then
    docker buildx create --name heritrace-builder --use
else
    docker buildx use heritrace-builder
fi
docker buildx inspect --bootstrap

echo "Building image..."
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t "$IMAGE" \
    --push .

echo "Done: $IMAGE"
