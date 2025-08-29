#!/bin/bash

# Container-based Apify Actor Deployment Script
# This script builds a container that handles the entire deployment process internally

set -e

echo "=== Container-based Apify Actor Deployment ==="
echo

# Check if APIFY_TOKEN is set
if [ -z "$APIFY_TOKEN" ]; then
    echo "Error: APIFY_TOKEN environment variable is required"
    echo "Please set it with: export APIFY_TOKEN=your_token_here"
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found. Please install Docker first."
    exit 1
fi

echo "Found Docker: $(docker --version)"
echo "APIFY_TOKEN is set"
echo

# Check if we're in the right directory
if [ ! -d "actors" ] || [ ! -d "shared" ]; then
    echo "Error: actors or shared directory not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

if [ ! -f "Dockerfile.deploy" ]; then
    echo "Error: Dockerfile.deploy not found"
    exit 1
fi

echo "Building deployment container..."
docker build -f Dockerfile.deploy -t apify-deployer .

if [ $? -ne 0 ]; then
    echo "Failed to build deployment container"
    exit 1
fi

echo "Successfully built deployment container"
echo

echo "Running deployment inside container..."
docker run --rm -e APIFY_TOKEN="$APIFY_TOKEN" apify-deployer

echo
echo "Container deployment completed!"