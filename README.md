# Week 16-17 Cloud Deployment for Financial MLOps

## Overview

This project extends the Week 14-15 Financial MLOps FastAPI service into a cloud-deployment-ready ML system.

The Week 14-15 project proved the model could be packaged, tested, served locally, and containerized. Week 16-17 focuses on the next production question:

> How does this Dockerized ML API become a cloud service that can be deployed, verified, monitored, and rolled back?

Primary deployment target: **Google Cloud Run**.

Why Cloud Run:

- natural fit for a Dockerized FastAPI service
- managed HTTPS endpoint
- autoscaling to zero for cost control
- built-in logs, metrics, revisions, and traffic splitting
- simpler portfolio story than Kubernetes or full ECS infrastructure

This is an educational financial-ML deployment demo, not investment advice.

## Project structure

```text
.
├── README.md
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
├── configs/
│   ├── local.env.example
│   └── serving.yaml
├── data/
│   └── sample_request.json
├── infra/
│   ├── architecture_diagram.md
│   └── gcp_cloud_run.md
├── models/
│   ├── metadata.json
│   └── model.pkl
├── reports/
│   ├── api_examples.md
│   ├── ml_monitoring_plan.md
│   └── mlops_system_design.md
├── scripts/
│   ├── build_docker.sh
│   ├── run_local_api.py
│   ├── smoke_test_api.py
│   ├── smoke_test_endpoint.py
│   └── train_baseline_model.py
├── src/financial_mlops/
└── tests/
```

## Architecture

```text
client / smoke test
        ↓ HTTPS
Cloud Run service
        ↓
FastAPI app container
        ↓
model artifact + metadata
        ↓
structured logs
        ↓
Cloud Logging / monitoring dashboard
```

Detailed architecture notes are in [`infra/architecture_diagram.md`](infra/architecture_diagram.md).

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Readiness check and loaded model/version status. |
| `GET` | `/metadata` | Model metadata, feature contract, and training information. |
| `POST` | `/predict` | Validated financial-ML prediction request. |

## Quick start: local Python

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pytest -q
```

Run the service:

```bash
PYTHONPATH=src uvicorn financial_mlops.service:app --host 0.0.0.0 --port 8000
```

In another terminal:

```bash
python scripts/smoke_test_endpoint.py --url http://localhost:8000
```

## Local Docker run

Build:

```bash
docker build -t financial-mlops-api:cloud-demo .
```

Run:

```bash
docker run --rm -p 8000:8000 financial-mlops-api:cloud-demo
```

Smoke test:

```bash
python scripts/smoke_test_endpoint.py --url http://localhost:8000
```

Expected smoke-test checks:

1. `GET /health` returns HTTP 200 and `status=ok`.
2. `GET /metadata` returns model metadata and feature contract.
3. `POST /predict` accepts `data/sample_request.json` and returns prediction, probability, model version, latency, and request id.

## Planned Cloud Run deployment

The planned cloud flow is:

1. Build the Docker image.
2. Push the image to Google Artifact Registry.
3. Deploy the image to Cloud Run.
4. Configure environment variables.
5. Smoke test the Cloud Run service URL.
6. Inspect Cloud Logging and Cloud Monitoring.
7. Use Cloud Run revisions for rollback.

Detailed commands and design notes are in [`infra/gcp_cloud_run.md`](infra/gcp_cloud_run.md).

Core deployment command shape:

```bash
gcloud run deploy financial-mlops-api \
  --image us-central1-docker.pkg.dev/${PROJECT_ID}/mlops-demos/financial-mlops-api:0.1.0 \
  --region us-central1 \
  --platform managed \
  --port 8000 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --set-env-vars APP_ENV=cloud,MODEL_VERSION=0.1.0,MLOPS_PREDICTION_LOG_CSV=/tmp/predictions.csv \
  --no-allow-unauthenticated
```

## Environment configuration

Local example file: [`configs/local.env.example`](configs/local.env.example)

```bash
APP_ENV=local
MODEL_VERSION=0.1.0
MLOPS_PREDICTION_LOG_CSV=logs/predictions.csv
PORT=8000
```

Cloud Run should use environment variables rather than hard-coded secrets or machine-specific paths. The current model artifact is bundled in the image for simplicity; future versions could pull artifacts from a registry or object storage.

## Runtime comparison

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Cloud Run | Simple managed container runtime, HTTPS, revisions, logs, scale-to-zero. | Less control than Kubernetes/ECS for complex networking. | **Primary target.** |
| AWS ECS/Fargate | Strong AWS production pattern, flexible networking/IAM. | More setup: cluster, task definition, service, load balancer. | Comparison only for this block. |
| VM | Easy mental model and full control. | Manual ops, patching, weaker portfolio story. | Fallback only. |

## Portfolio talking points

- I can move a research model into a tested API service.
- I can package that service as a Docker image.
- I understand the difference between a container registry and a runtime service.
- I can explain Cloud Run revisions, traffic splitting, logs, health checks, and rollback.
- I can reason about cost/security tradeoffs for a public ML demo endpoint.

## Interview Talking Points — Questions and Answers

### 1. Why did you choose Google Cloud Run for this ML deployment?

I chose Cloud Run because the service is already packaged as a Dockerized FastAPI application. Cloud Run lets me deploy that container directly behind a managed HTTPS endpoint without operating servers, Kubernetes clusters, or load balancers. For this project, the goal is to demonstrate production deployment fundamentals: container image, registry, service runtime, health checks, logs, revisions, traffic routing, and rollback. Cloud Run covers those concepts with less infrastructure overhead than ECS/Fargate or a VM.

### 2. What is the difference between Artifact Registry and Cloud Run?

Artifact Registry stores the container image. Cloud Run executes the container image as a managed HTTP service. In other words, Artifact Registry is the artifact storage layer, while Cloud Run is the runtime layer. The deployment flow is: build image, push image to Artifact Registry, deploy that image to Cloud Run, then verify the Cloud Run URL.

### 3. How would you explain the deployment architecture end to end?

A client or smoke-test script sends HTTPS requests to a Cloud Run service. Cloud Run routes the request into a FastAPI container. The container loads a versioned model artifact and metadata at startup, validates incoming features, returns predictions, and emits structured logs. Cloud Run forwards stdout/stderr logs to Cloud Logging, and Cloud Monitoring tracks request count, latency, errors, CPU, memory, and instance behavior.

### 4. What endpoints does the service expose, and why?

The service exposes three main endpoints:

- `/health`: readiness check confirming the app is running and the model is loaded.
- `/metadata`: model metadata and feature-contract inspection.
- `/predict`: validated prediction endpoint for the financial-ML model.

This separates operational health, model transparency, and prediction behavior. In production, that separation helps debugging because a failed prediction does not necessarily mean the service is down.

### 5. How do you validate a deployment after release?

I use a smoke-test script against the deployed base URL. The script checks `/health`, `/metadata`, and `/predict` using a known sample request. A successful smoke test proves the service is reachable, the model loads, the metadata endpoint works, request validation passes, and the prediction response has the expected fields.

For this project, the same smoke test works locally and for a future Cloud Run URL:

```bash
python scripts/smoke_test_endpoint.py --url http://localhost:8000
python scripts/smoke_test_endpoint.py --url https://your-cloud-run-service-url
```

### 6. How would you handle rollback in Cloud Run?

Cloud Run creates a revision for each deployment. If a new revision has elevated errors or fails smoke tests, I do not need to rebuild immediately. I can route traffic back to a previous known-good revision:

```bash
gcloud run revisions list --service financial-mlops-api --region us-central1
gcloud run services update-traffic financial-mlops-api \
  --region us-central1 \
  --to-revisions KNOWN_GOOD_REVISION=100
```

That makes rollback a traffic-management action rather than an emergency code change.

### 7. What logs and metrics would you monitor?

I would monitor both infrastructure metrics and model-serving behavior.

Infrastructure metrics:

- request count
- 4xx/5xx error rate
- p50/p95 latency
- CPU and memory utilization
- instance count and cold-start pattern

Model-serving logs:

- request id
- model version
- endpoint
- latency
- validation failures
- prediction/probability summary
- feature count and basic feature statistics

The important idea is that API uptime is not enough. For ML systems, I also want to know whether the model contract and output distribution are behaving normally.

### 8. How do you manage environment-specific configuration?

I use environment variables for runtime configuration instead of hard-coded machine paths. The local example is in `configs/local.env.example`:

```bash
APP_ENV=local
MODEL_VERSION=0.1.0
MLOPS_PREDICTION_LOG_CSV=logs/predictions.csv
PORT=8000
```

For Cloud Run, these values can be set with `--set-env-vars`. Secrets should not be baked into the Docker image; future secrets should come from Secret Manager or a similar runtime secret store.

### 9. What security choices would you make for a public ML demo?

For a real internal service, I would keep Cloud Run authenticated with IAM. For a temporary public demo, I would only allow unauthenticated access if the container has no secrets, no private data, no trading credentials, and no ability to execute trades. I would also keep the model educational, apply rate limits or low max instances, and monitor usage.

The safe default is authenticated access. Public access is a portfolio/demo exception, not the default production posture.

### 10. How do you control cost?

Cloud Run helps because it can scale to zero when idle. I would also set conservative limits such as:

- `--min-instances 0`
- low `--max-instances` for demos
- modest CPU/memory allocation
- alerting on request volume or billing spikes

For this project, the service is lightweight and the model is bundled in the image, so the main cost risks are unexpected public traffic and excessive logging.

### 11. Why not deploy this on a VM?

A VM would work, but it shifts too much operational responsibility to me: patching, process management, TLS, restart policies, firewall rules, and manual scaling. For a modern ML service portfolio project, a managed container runtime is more relevant because it shows I understand production deployment patterns without turning the project into sysadmin work.

### 12. How is this different from the Week 14-15 MLOps project?

Week 14-15 focused on model serving foundations: FastAPI, tests, Docker packaging, model metadata, and local monitoring logs. Week 16-17 focuses on operating that service as a deployable cloud system: container registry, runtime choice, endpoint strategy, environment configuration, logs/metrics, revision-based rollback, security, and cost awareness.

A concise interview summary would be:

> Week 14-15 made the model service reliable locally. Week 16-17 makes it deployable and operable in the cloud.

### 13. What would you improve next?

Next improvements would be:

1. Add Cloud Run deployment and rollback scripts.
2. Add a `cloudrun.service.yaml` config file.
3. Create a monitoring dashboard plan with specific Cloud Logging queries.
4. Add a production runbook covering deploy, verify, rollback, and troubleshooting.
5. Optionally move model artifacts to cloud storage or a model registry instead of bundling them in the image.

These map directly to the remaining Week 16-17 tasks.
