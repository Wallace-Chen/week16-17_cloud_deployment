#!/usr/bin/env bash
set -euo pipefail

# Deploy the Financial MLOps FastAPI container to Google Cloud Run.
#
# Required:
#   PROJECT_ID=my-gcp-project ./scripts/deploy_cloud_run.sh
#
# Optional environment variables:
#   REGION=us-central1
#   REPOSITORY=mlops
#   SERVICE_NAME=financial-mlops-api
#   IMAGE_TAG=0.1.0-$(git rev-parse --short HEAD)
#   APP_ENV=production
#   MODEL_VERSION=0.1.0
#   ALLOW_UNAUTHENTICATED=false   # set true for temporary public demo only
#   MIN_INSTANCES=0
#   MAX_INSTANCES=3
#   MEMORY=1Gi
#   CPU=1
#   DRY_RUN=false                 # set true to print commands without executing

# Homebrew on Apple Silicon may install gcloud outside the default non-login SSH PATH.
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:/opt/homebrew/bin:${PATH}"
export CLOUDSDK_PYTHON=${CLOUDSDK_PYTHON:-/opt/homebrew/opt/python@3.13/libexec/bin/python}

PROJECT_ID=${PROJECT_ID:?Set PROJECT_ID, e.g. PROJECT_ID=my-gcp-project}
REGION=${REGION:-us-central1}
REPOSITORY=${REPOSITORY:-mlops}
SERVICE_NAME=${SERVICE_NAME:-financial-mlops-api}
APP_ENV=${APP_ENV:-production}
MODEL_VERSION=${MODEL_VERSION:-0.1.0}
IMAGE_TAG=${IMAGE_TAG:-${MODEL_VERSION}-$(git rev-parse --short HEAD 2>/dev/null || echo manual)}
ALLOW_UNAUTHENTICATED=${ALLOW_UNAUTHENTICATED:-false}
MIN_INSTANCES=${MIN_INSTANCES:-0}
MAX_INSTANCES=${MAX_INSTANCES:-3}
MEMORY=${MEMORY:-1Gi}
CPU=${CPU:-1}
DRY_RUN=${DRY_RUN:-false}

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:${IMAGE_TAG}"
LATEST_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:latest"

run() {
  echo "+ $*"
  if [[ "${DRY_RUN}" != "true" ]]; then
    "$@"
  fi
}

if ! command -v gcloud >/dev/null 2>&1; then
  echo "ERROR: gcloud CLI is required. Install Google Cloud SDK first." >&2
  exit 127
fi

if ! command -v docker >/dev/null 2>&1 && [[ "${DRY_RUN}" != "true" ]]; then
  echo "WARNING: docker is not available locally. This script uses gcloud builds submit, so local Docker is optional." >&2
fi

AUTH_FLAG="--no-allow-unauthenticated"
if [[ "${ALLOW_UNAUTHENTICATED}" == "true" ]]; then
  AUTH_FLAG="--allow-unauthenticated"
  echo "WARNING: deploying public unauthenticated service. Use only for a temporary demo."
fi

run gcloud config set project "${PROJECT_ID}"

run gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com

run gcloud artifacts repositories create "${REPOSITORY}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="MLOps demo images" || true

# Cloud Build builds from the current directory and pushes the versioned tag.
run gcloud builds submit --tag "${IMAGE}" .

# Also tag latest for convenience. This keeps the versioned image as the deploy source of truth.
run gcloud artifacts docker tags add "${IMAGE}" "${LATEST_IMAGE}" || true

run gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  ${AUTH_FLAG} \
  --port 8000 \
  --memory "${MEMORY}" \
  --cpu "${CPU}" \
  --min-instances "${MIN_INSTANCES}" \
  --max-instances "${MAX_INSTANCES}" \
  --set-env-vars "APP_ENV=${APP_ENV},MODEL_VERSION=${MODEL_VERSION},MLOPS_PREDICTION_LOG_CSV=/tmp/predictions.csv"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format "value(status.url)" 2>/dev/null || true)

echo
if [[ -n "${SERVICE_URL}" ]]; then
  echo "DEPLOYMENT_OK"
  echo "Service URL: ${SERVICE_URL}"
  echo "Smoke test: python scripts/smoke_test_endpoint.py --url ${SERVICE_URL}"
else
  echo "Deployment command finished, but service URL was not available. Check: gcloud run services describe ${SERVICE_NAME} --region ${REGION}"
fi
