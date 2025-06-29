#!/bin/bash

echo "Stopping databases..."
docker stop database prov_database

echo "Removing containers..."
docker rm database prov_database

echo "Cleanup complete."