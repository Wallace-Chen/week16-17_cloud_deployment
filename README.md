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

## Interview Talking Points — Week 16 Day 1-2 Only

These questions are based directly on the **Topics** list for Day 1-2 in the study plan.

### 1. How would you compare Cloud Run, ECS/Fargate, and VM deployment for this project?

Cloud Run is the best primary target here because the Week 14-15 service is already a Dockerized FastAPI app. Cloud Run provides a managed HTTPS endpoint, autoscaling, revisions, logging, and scale-to-zero with minimal infrastructure setup.

ECS/Fargate is also production-grade, especially in AWS environments, but it requires more setup around clusters, task definitions, networking, IAM, and often a load balancer.

A VM is the simplest mental model, but it pushes too much operational work onto me: process management, TLS, patching, firewall rules, restarts, and scaling.

### 2. What is the difference between a container registry and a runtime service?

A container registry stores built Docker images. For this project, the planned registry is Google Artifact Registry.

A runtime service runs the container and exposes it as an application. For this project, the planned runtime is Google Cloud Run.

The basic flow is:

```text
docker build → push image to Artifact Registry → deploy image to Cloud Run
```

### 3. What is the difference between a public endpoint and an internal endpoint?

A public endpoint can be reached from the internet. It is convenient for demos, portfolios, and smoke tests, but it increases security and cost risk.

An internal or authenticated endpoint is safer for real systems because access is restricted through IAM, service-to-service identity, or private networking.

For this project, the safe default is authenticated Cloud Run. A public endpoint should only be used temporarily for demo purposes after confirming the image contains no secrets, private data, or trading credentials.

### 4. Why are environment variables important in cloud deployment?

Environment variables keep runtime configuration separate from code. The same container image can run locally or in Cloud Run with different settings.

For this project, the Day 1-2 local example is:

```bash
APP_ENV=local
MODEL_VERSION=0.1.0
MLOPS_PREDICTION_LOG_CSV=logs/predictions.csv
PORT=8000
```

In Cloud Run, these values can be set at deployment time instead of hard-coded into the app.

### 5. What are service revisions, and why do they matter?

A service revision is a versioned deployment of the Cloud Run service. Each time a new container image or service configuration is deployed, Cloud Run creates a new revision.

Revisions matter because they make deployment history visible and support safer releases. If a new revision has problems, traffic can be routed back to an older known-good revision.

### 6. What health check should this service expose?

The service should expose `GET /health`.

For this ML API, a useful health check should confirm not only that the web server is running, but also that the model artifact loaded correctly. A container that starts but cannot load the model is not actually ready to serve predictions.

### 7. What logs and metrics matter for this service?

Important infrastructure metrics include request count, error rate, latency, CPU, memory, and instance count.

Important model-serving logs include request id, endpoint, model version, latency, validation failures, prediction output, and probability summary.

The key point is that ML services need both system observability and model-serving observability.

### 8. Why is cost and scale-to-zero relevant here?

Cloud Run can scale to zero when no requests are coming in. That is useful for a portfolio ML service because the endpoint may only receive occasional traffic.

Scale-to-zero keeps idle cost low while still giving a real cloud deployment path. For demos, I would also set conservative CPU, memory, and max-instance limits to reduce the risk of unexpected cost.
