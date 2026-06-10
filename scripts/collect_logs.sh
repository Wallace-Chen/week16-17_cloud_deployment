#!/usr/bin/env bash
set -euo pipefail

# Collect recent Cloud Run logs for the Financial MLOps API.
#
# Usage:
#   PROJECT_ID=my-gcp-project ./scripts/collect_logs.sh
#   PROJECT_ID=my-gcp-project SERVICE_NAME=financial-mlops-api REGION=us-central1 LIMIT=50 ./scripts/collect_logs.sh
#   PROJECT_ID=my-gcp-project DRY_RUN=true ./scripts/collect_logs.sh

# Homebrew on Apple Silicon may install gcloud outside the default non-login SSH PATH.
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:/opt/homebrew/bin:${PATH}"
export CLOUDSDK_PYTHON=${CLOUDSDK_PYTHON:-/opt/homebrew/opt/python@3.13/libexec/bin/python}

PROJECT_ID=${PROJECT_ID:?Set PROJECT_ID}
REGION=${REGION:-us-central1}
SERVICE_NAME=${SERVICE_NAME:-financial-mlops-api}
LIMIT=${LIMIT:-50}
FRESHNESS=${FRESHNESS:-1h}
FORMAT=${FORMAT:-json}
DRY_RUN=${DRY_RUN:-false}

if ! command -v gcloud >/dev/null 2>&1; then
  echo "ERROR: gcloud CLI is required." >&2
  exit 127
fi

FILTER="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND resource.labels.location=\"${REGION}\""

CMD=(gcloud logging read "${FILTER}" \
  --project "${PROJECT_ID}" \
  --freshness "${FRESHNESS}" \
  --limit "${LIMIT}" \
  --format "${FORMAT}")

echo "Cloud Run log query:"
printf "+ %q " "${CMD[@]}"
echo

if [[ "${DRY_RUN}" != "true" ]]; then
  "${CMD[@]}"
fi
