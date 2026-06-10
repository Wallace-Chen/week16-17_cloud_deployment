#!/usr/bin/env bash
set -euo pipefail

# Roll back a Cloud Run service by sending traffic to a known-good revision.
#
# Usage:
#   PROJECT_ID=my-gcp-project REVISION=financial-mlops-api-00003-abc ./scripts/rollback_cloud_run.sh
#
# To inspect revisions first:
#   PROJECT_ID=my-gcp-project ./scripts/rollback_cloud_run.sh --list

PROJECT_ID=${PROJECT_ID:?Set PROJECT_ID}
REGION=${REGION:-us-central1}
SERVICE_NAME=${SERVICE_NAME:-financial-mlops-api}
REVISION=${REVISION:-}
DRY_RUN=${DRY_RUN:-false}

if ! command -v gcloud >/dev/null 2>&1; then
  echo "ERROR: gcloud CLI is required." >&2
  exit 127
fi

run() {
  echo "+ $*"
  if [[ "${DRY_RUN}" != "true" ]]; then
    "$@"
  fi
}

if [[ "${1:-}" == "--list" ]]; then
  run gcloud run revisions list \
    --project "${PROJECT_ID}" \
    --service "${SERVICE_NAME}" \
    --region "${REGION}"
  exit 0
fi

if [[ -z "${REVISION}" ]]; then
  echo "ERROR: Set REVISION to the known-good Cloud Run revision." >&2
  echo "List revisions with: PROJECT_ID=${PROJECT_ID} ./scripts/rollback_cloud_run.sh --list" >&2
  exit 2
fi

run gcloud run services update-traffic "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --to-revisions "${REVISION}=100"

echo "ROLLBACK_OK service=${SERVICE_NAME} revision=${REVISION} region=${REGION}"
