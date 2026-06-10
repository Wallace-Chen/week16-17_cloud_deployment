# Deployment Guide — Week 16 Day 3-4

This document covers the Day 3-4 tasks from `Phase3_Week16-17_Cloud_Deployment.md`: deployment scripts and endpoint smoke tests for the Financial MLOps FastAPI service.

Primary target: **Google Cloud Run**.

---

## 1. Prerequisites

Local/project prerequisites:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pytest -q
```

Cloud prerequisites:

1. Google Cloud project with billing enabled.
2. Google Cloud SDK installed and authenticated.
3. Permission to enable APIs, create Artifact Registry repositories, run Cloud Build, and deploy Cloud Run services.

Check auth:

```bash
gcloud auth list
gcloud config list
```

Required APIs are enabled by `scripts/deploy_cloud_run.sh`:

```bash
run.googleapis.com
artifactregistry.googleapis.com
cloudbuild.googleapis.com
logging.googleapis.com
monitoring.googleapis.com
```

---

## 2. Build locally

If Docker is available:

```bash
docker build -t financial-mlops-api:cloud-demo .
docker run --rm -p 8000:8000 financial-mlops-api:cloud-demo
```

In another terminal:

```bash
python scripts/smoke_test_endpoint.py --url http://localhost:8000
```

Note: the current Mac Studio environment used for this project did not have Docker CLI available during validation, so local API validation was done with Uvicorn instead:

```bash
source .venv/bin/activate
PYTHONPATH=src uvicorn financial_mlops.service:app --host 127.0.0.1 --port 8000
python scripts/smoke_test_endpoint.py --url http://127.0.0.1:8000
```

---

## 3. Deploy to Cloud Run

Minimal deployment:

```bash
PROJECT_ID=your-gcp-project ./scripts/deploy_cloud_run.sh
```

Recommended explicit deployment:

```bash
PROJECT_ID=your-gcp-project \
REGION=us-central1 \
REPOSITORY=mlops \
SERVICE_NAME=financial-mlops-api \
IMAGE_TAG=0.1.0-$(git rev-parse --short HEAD) \
APP_ENV=production \
MODEL_VERSION=0.1.0 \
ALLOW_UNAUTHENTICATED=false \
MIN_INSTANCES=0 \
MAX_INSTANCES=3 \
MEMORY=1Gi \
CPU=1 \
./scripts/deploy_cloud_run.sh
```

For a temporary public demo only:

```bash
PROJECT_ID=your-gcp-project ALLOW_UNAUTHENTICATED=true ./scripts/deploy_cloud_run.sh
```

Use public access only after confirming the image contains no secrets, no private data, and no trading/execution credentials.

### What the deployment script does

`scripts/deploy_cloud_run.sh`:

1. Requires `PROJECT_ID`.
2. Sets defaults for region, repo, service, tag, CPU/memory, and scaling.
3. Enables required Google Cloud APIs.
4. Creates the Artifact Registry Docker repo if needed.
5. Builds and pushes a versioned image using Cloud Build.
6. Adds a `latest` tag for convenience.
7. Deploys the versioned image to Cloud Run.
8. Prints the service URL and smoke-test command.

The versioned image tag is the source of truth. `latest` is convenience only.

---

## 4. Smoke test

Local endpoint:

```bash
python scripts/smoke_test_endpoint.py --url http://localhost:8000
```

Cloud Run endpoint:

```bash
python scripts/smoke_test_endpoint.py --url https://YOUR-CLOUD-RUN-URL
```

The smoke test validates:

- `GET /health`
- `GET /metadata`
- `POST /predict`
- expected prediction response keys: `ticker`, `prediction`, `probability`, `model_version`, `latency_ms`, `request_id`

A passing smoke test prints:

```text
SMOKE_TEST_OK
```

---

## 5. View logs

Collect recent Cloud Run logs:

```bash
PROJECT_ID=your-gcp-project ./scripts/collect_logs.sh
```

With explicit settings:

```bash
PROJECT_ID=your-gcp-project \
REGION=us-central1 \
SERVICE_NAME=financial-mlops-api \
FRESHNESS=2h \
LIMIT=100 \
FORMAT=json \
./scripts/collect_logs.sh
```

Dry-run the query without executing it:

```bash
PROJECT_ID=your-gcp-project DRY_RUN=true ./scripts/collect_logs.sh
```

The script uses a Cloud Logging filter for:

```text
resource.type="cloud_run_revision"
resource.labels.service_name="financial-mlops-api"
resource.labels.location="us-central1"
```

---

## 6. Rollback

List revisions:

```bash
PROJECT_ID=your-gcp-project ./scripts/rollback_cloud_run.sh --list
```

Rollback 100% of traffic to a known-good revision:

```bash
PROJECT_ID=your-gcp-project \
REGION=us-central1 \
SERVICE_NAME=financial-mlops-api \
REVISION=financial-mlops-api-00003-abc \
./scripts/rollback_cloud_run.sh
```

Rollback is revision-based: Cloud Run keeps previous revisions, so a bad release can be fixed by rerouting traffic rather than immediately rebuilding code.

---

## 7. Day 3-4 Interview Talking Points

These answers correspond directly to the Day 3-4 `Interview Talking Points` in the study plan.

### What makes a deployment script safer than manual console clicks?

A deployment script is safer because it is repeatable, reviewable, and version-controlled. Manual console clicks are easy to forget, hard to audit, and difficult to reproduce exactly.

With a script, the deployment process becomes explicit: project, region, service name, image tag, environment variables, authentication mode, scaling limits, and runtime settings are all visible in one place. This reduces configuration drift and makes it easier to debug or hand off to another engineer.

### Why tag Docker images with versions instead of only `latest`?

A versioned image tag points to a specific deployable artifact. If a deployment breaks, I can identify exactly which image was released and roll back to a known-good version.

Using only `latest` is risky because it moves over time. Two deployments using `latest` may not refer to the same image. For this project, `latest` can exist as a convenience tag, but Cloud Run should deploy a versioned tag such as:

```text
financial-mlops-api:0.1.0-<git-sha>
```

### What should a smoke test verify after deployment?

A smoke test should verify that the deployed endpoint works from the outside as a client would use it.

For this service, the smoke test checks:

1. `/health` returns a healthy status and confirms the model is loaded.
2. `/metadata` returns model and feature-contract information.
3. `/predict` accepts a known sample request.
4. The prediction response includes required fields such as prediction, probability, model version, latency, and request id.

This catches problems that a container-start check alone may miss.

### How would you roll back a bad Cloud Run revision?

I would first list Cloud Run revisions, identify the previous known-good revision, then route 100% of traffic back to it.

```bash
PROJECT_ID=your-gcp-project ./scripts/rollback_cloud_run.sh --list
PROJECT_ID=your-gcp-project REVISION=known-good-revision ./scripts/rollback_cloud_run.sh
```

The key idea is that rollback is a traffic-management operation. I do not need to immediately rebuild the application if a previous revision is already healthy.
