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

## Week 16 Day 1-2 Study Plan Answers

This section directly answers the Week 16 Day 1-2 topics from `Phase3_Week16-17_Cloud_Deployment.md`.

### 1. Cloud Run vs ECS/Fargate vs VM deployment

**Google Cloud Run** is the primary deployment target for this project.

Cloud Run is best for this Week 16-17 project because the Week 14-15 model service is already packaged as a Dockerized FastAPI app. Cloud Run can run that container directly, expose an HTTPS endpoint, autoscale, capture logs, create service revisions, and scale to zero when idle.

**AWS ECS/Fargate** is a strong alternative for AWS production environments, but it requires more setup: cluster/service configuration, task definitions, IAM roles, networking, and often a load balancer.

**VM deployment** is the fallback option. It is simple conceptually, but weaker operationally because I would need to manage process restarts, TLS, patching, firewall rules, monitoring, and scaling myself.

Decision: **use Cloud Run as the primary path**, keep ECS/Fargate as a comparison point, and use local Docker/architecture docs as fallback if cloud credentials or billing become a blocker.

### 2. Container registry vs runtime service

A **container registry** stores Docker images. For the Cloud Run path, the registry would be **Google Artifact Registry**.

A **runtime service** runs the container image and exposes the application. For this project, the runtime service would be **Google Cloud Run**.

Deployment flow:

```text
Build Docker image
        ↓
Push image to Artifact Registry
        ↓
Deploy image to Cloud Run
        ↓
Smoke test the service URL
```

Artifact Registry answers: “Where is the image stored?”

Cloud Run answers: “Where is the image running?”

### 3. Public endpoint vs internal endpoint

A **public endpoint** is reachable from the internet. It is useful for demos and portfolio screenshots, but it creates more security and cost risk.

An **internal or authenticated endpoint** restricts access through IAM or private networking. This is safer for real ML services, especially if the service touches private data, credentials, or business logic.

For this project, the safe default is an authenticated Cloud Run service. A public endpoint is acceptable only as a temporary demo if:

- the container has no secrets
- the model is educational only
- there is no trading/execution capability
- max instances are limited
- usage is monitored

### 4. Environment variables

Environment variables keep runtime configuration separate from code. The same Docker image can run locally or in Cloud Run with different environment settings.

Local example in `configs/local.env.example`:

```bash
APP_ENV=local
MODEL_VERSION=0.1.0
MLOPS_PREDICTION_LOG_CSV=logs/predictions.csv
PORT=8000
```

For Cloud Run, the equivalent values can be passed during deployment:

```bash
--set-env-vars APP_ENV=cloud,MODEL_VERSION=0.1.0,MLOPS_PREDICTION_LOG_CSV=/tmp/predictions.csv
```

No secrets should be hard-coded into the image. If secrets are needed later, they should come from Secret Manager or another runtime secret store.

### 5. Service revisions

A **service revision** is a versioned Cloud Run deployment. Cloud Run creates a new revision when the deployed image or service configuration changes.

Revisions matter because they make deployments safer:

- each release has a traceable version
- traffic can be shifted between revisions
- a bad deployment can be rolled back to a previous revision
- canary releases are possible by splitting traffic

For this project, revisions connect naturally to `MODEL_VERSION` and Docker image tags.

### 6. Health checks

The service should use `GET /health` as the basic health-check endpoint.

For this ML API, a good health check should confirm:

- the API process is running
- the model artifact loaded successfully
- the active model version is available

A container that starts but cannot load the model is not actually healthy for prediction serving.

Current expected health response shape:

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_name": "spy_direction_baseline",
  "model_version": "0.1.0"
}
```

### 7. Logs and metrics

Cloud Run forwards container stdout/stderr to Cloud Logging, so the app should write structured logs.

Important logs for this ML service:

- request id
- endpoint
- model version
- latency
- prediction result
- probability summary
- validation errors
- feature-count/basic feature statistics

Important metrics:

- request count
- 4xx/5xx error rate
- p50/p95 latency
- CPU and memory usage
- instance count
- cold-start behavior

The key idea is that an ML service needs both infrastructure observability and model-serving observability.

### 8. Cost and scale-to-zero

Cloud Run is cost-efficient for this project because it can **scale to zero** when idle. That fits a portfolio ML API, where traffic may be occasional rather than continuous.

Cost controls for this project:

- set `--min-instances 0`
- set a conservative `--max-instances`
- use modest CPU and memory
- avoid excessive logging
- monitor request volume
- keep public demo windows temporary

Scale-to-zero gives a realistic cloud deployment path without paying for an always-on VM.
