# Google Cloud Run Deployment Plan

## Decision

Primary deployment target: **Google Cloud Run**.

Cloud Run is preferred over ECS/Fargate or a VM because it keeps the deployment focused on the production concepts that matter for this portfolio project:

- container image as deployable artifact
- managed HTTPS endpoint
- revision history
- traffic splitting and rollback
- logs and metrics without operating servers
- scale-to-zero cost control

ECS/Fargate is a strong alternative for AWS-heavy teams, but it requires more surrounding infrastructure: task definitions, clusters, networking, load balancer decisions, IAM roles, and service configuration. A VM is easiest conceptually but weakest as a modern ML platform story because too much operational work moves back to the user.

## Required cloud resources

| Resource | Purpose |
| --- | --- |
| Google Cloud project | Billing, IAM, APIs, and resource ownership. |
| Artifact Registry Docker repository | Stores `financial-mlops-api` container images. |
| Cloud Run service | Runs the FastAPI container behind HTTPS. |
| Cloud Logging | Receives container logs automatically. |
| Cloud Monitoring | Tracks request count, latency, error rate, container CPU/memory. |
| IAM service account | Runtime identity for the Cloud Run service. |

Required APIs:

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com logging.googleapis.com monitoring.googleapis.com
```

## Deployment flow

Assumed variables:

```bash
PROJECT_ID="your-gcp-project"
REGION="us-central1"
REPOSITORY="mlops-demos"
IMAGE="financial-mlops-api"
TAG="0.1.0"
SERVICE="financial-mlops-api"
```

High-level flow:

```bash
# 1. Build local container image
docker build -t ${IMAGE}:${TAG} .

# 2. Create Artifact Registry repo once, if missing
gcloud artifacts repositories create ${REPOSITORY} \
  --repository-format=docker \
  --location=${REGION} \
  --description="Financial MLOps demo images"

# 3. Authenticate Docker to Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# 4. Tag and push image
docker tag ${IMAGE}:${TAG} ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE}:${TAG}
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE}:${TAG}

# 5. Deploy to Cloud Run
gcloud run deploy ${SERVICE} \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE}:${TAG} \
  --region ${REGION} \
  --platform managed \
  --port 8000 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --set-env-vars APP_ENV=cloud,MODEL_VERSION=${TAG},MLOPS_PREDICTION_LOG_CSV=/tmp/predictions.csv \
  --no-allow-unauthenticated
```

For a temporary public portfolio demo, replace `--no-allow-unauthenticated` with `--allow-unauthenticated`, but only after confirming there are no secrets, trading credentials, or private data in the image or environment.

## Environment variables

| Variable | Local value | Cloud Run value | Purpose |
| --- | --- | --- | --- |
| `APP_ENV` | `local` | `cloud` | Runtime environment label for logs/config branching. |
| `MODEL_VERSION` | `0.1.0` | image tag or model version | Makes responses/logs traceable to deployed model. |
| `MLOPS_PREDICTION_LOG_CSV` | `logs/predictions.csv` | `/tmp/predictions.csv` | Local CSV audit path. Cloud Run filesystem is ephemeral, so durable monitoring should use logs. |
| `PORT` | `8000` | provided by Cloud Run / set to `8000` | HTTP port used by Uvicorn container. |

## Health check endpoint

The service exposes:

```text
GET /health
```

Expected behavior:

- returns HTTP 200
- confirms application status is `ok`
- includes loaded model/version information
- fails quickly if the model artifact cannot load

Cloud Run does not require a separate Kubernetes-style readiness probe for this simple service, but the Dockerfile includes a local `HEALTHCHECK` and the smoke test should call `/health` immediately after deployment.

## Logging path

Application logs should go to stdout/stderr so Cloud Run forwards them automatically to Cloud Logging.

Recommended log fields:

- `timestamp`
- `request_id`
- `endpoint`
- `model_version`
- `latency_ms`
- `status_code`
- prediction/probability summary for `/predict`
- validation error category if request validation fails

Local CSV prediction logs are useful for Week 14-15 development, but for Cloud Run they should be treated as ephemeral. The production path is Cloud Logging plus an optional BigQuery/Cloud Storage sink later.

## Monitoring plan

Minimum Cloud Monitoring dashboard:

1. Cloud Run request count.
2. 4xx/5xx error rate.
3. p50/p95 request latency.
4. Container CPU and memory utilization.
5. Instance count / cold-start pattern.
6. Prediction volume by model version from structured logs.

Portfolio explanation:

> I monitor both infrastructure health and model-serving behavior. Infra metrics tell me whether the service is reachable and performant; structured prediction logs tell me whether the model contract and outputs are behaving as expected.

## Rollback strategy

Cloud Run keeps revisions. Rollback is a traffic-routing operation, not a rebuild.

Commands:

```bash
# List revisions
gcloud run revisions list --service ${SERVICE} --region ${REGION}

# Send all traffic back to a known-good revision
gcloud run services update-traffic ${SERVICE} \
  --region ${REGION} \
  --to-revisions ${KNOWN_GOOD_REVISION}=100
```

Recommended release strategy:

1. Deploy new image tag.
2. Smoke test the new revision.
3. If stable, send 100% traffic to latest.
4. If risky, split traffic 90/10 or 95/5 first.
5. If errors rise, route traffic back to the previous revision.

## Security notes for Day 1-2

- Do not bake secrets into the Docker image.
- Prefer Cloud Run IAM authentication for non-demo deployments.
- Keep public demo endpoints read-only and rate-limited.
- Use a dedicated service account with minimal permissions.
- Store future secrets in Secret Manager, mounted as env vars only at runtime.
- Keep model artifact and metadata versioned so rollback is auditable.
