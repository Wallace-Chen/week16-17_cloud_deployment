#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-financial-mlops-api:latest}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"
docker build -t "$IMAGE_NAME" .

echo "Built $IMAGE_NAME"
echo "Run with: docker run --rm -p 8000:8000 $IMAGE_NAME"
