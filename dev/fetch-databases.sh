#!/bin/bash

# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

set -euo pipefail

DATASET="$1"
FILES_URL="https://zenodo.org/api/records/23063958/files"
ARCHIVE="oc_meta_data_2026_09_22.7z"
IMAGE="adfreiburg/qlever:0.6.0@sha256:37d5ede193f1bffb6aebf734d15d2a4c2a3228ee102858b0c6c2e65c149a78ec"
DEV_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$DEV_DIR/data/$DATASET"
DOWNLOAD_DIR="$DATA_DIR/download"

build_index() {
    local dir="$1"
    shift
    docker run --rm -i -u "$(id -u):$(id -g)" \
        -v "$dir:/index" -w /index \
        --entrypoint qlever-index "$IMAGE" "$@"
}

fetch_big() {
    mkdir -p "$DOWNLOAD_DIR"
    while read -r md5 part; do
        file="$DOWNLOAD_DIR/$ARCHIVE.$part"
        if [ -f "$file" ] && echo "$md5  $file" | md5sum -c --status -; then
            continue
        fi
        curl -fL -C - -o "$file" "$FILES_URL/$ARCHIVE.$part/content"
        echo "$md5  $file" | md5sum -c -
    done <<EOF
afd7c8d15c55ce42b4e6e9acf67e839c 001
7ce8b4e217c24b7149b2aae4b9c09a63 002
d7d6b1458d6b3f21b16a1e205b835628 003
b53f2484df37a3f5c78279762a461d99 004
86f9527d314faf3c19a1cfac809d4a5d 005
1d70583e59b9bc4296e75eae450adb71 006
EOF
    rm -rf "$DOWNLOAD_DIR/extracted"
    7z x -o"$DOWNLOAD_DIR/extracted" "$DOWNLOAD_DIR/$ARCHIVE.001"
    index_file=$(find "$DOWNLOAD_DIR/extracted" -name '*.meta-data.json' | head -n 1)
    mv "$(dirname "$index_file")" "$DATA_DIR/meta"
    rm -rf "$DOWNLOAD_DIR"
}

build_small() {
    mkdir -p "$DATA_DIR/meta"
    build_index "$DATA_DIR/meta" -i meta-small -F nq -f - --add-has-word-triples \
        < "$DEV_DIR/../demo/iswc2026/data/dataset.nq"
}

mkdir -p "$DATA_DIR/meta-updates" "$DATA_DIR/provenance" "$DATA_DIR/redis"

if ! compgen -G "$DATA_DIR/meta/*.meta-data.json" > /dev/null; then
    case "$DATASET" in
        big) fetch_big ;;
        small) build_small ;;
    esac
fi

if [ ! -f "$DATA_DIR/provenance/meta-provenance.meta-data.json" ]; then
    build_index "$DATA_DIR/provenance" -i meta-provenance -F nq -f - < /dev/null
fi
