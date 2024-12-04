#!/bin/bash

echo "Stopping databases..."
docker stop dataset_db provenance_db

echo "Removing containers..."
docker rm dataset_db provenance_db

echo "Cleaning up network..."
docker network rm virtuoso-net

echo "Cleanup complete."