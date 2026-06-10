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

### 1. What was the main goal of Week 16 Day 1-2?

The goal was to move from a local Dockerized ML API mindset to a cloud-runtime architecture mindset. The key question was not “can the model run locally?” but “what cloud runtime should operate this container, and what architecture explains deployment, health checks, logs, revisions, and cost?”

### 2. Which cloud runtime did you choose as the primary target?

I chose **Google Cloud Run** as the primary target.

The Week 14-15 project is already a FastAPI service packaged in Docker, so Cloud Run is a clean fit: it runs containers directly, provides an HTTPS service URL, supports autoscaling to zero, captures logs, and manages revisions without requiring Kubernetes or manual VM operations.

### 3. Why Cloud Run instead of AWS ECS/Fargate?

ECS/Fargate is production-grade and very useful in AWS environments, but it requires more surrounding infrastructure: task definitions, clusters, networking, load balancer choices, IAM roles, and service configuration.

For this project, I wanted the simplest credible deployment path that still demonstrates real production concepts. Cloud Run lets me focus on container image, registry, runtime service, endpoint, logs, revisions, and rollback instead of spending most of the time on infrastructure plumbing.

### 4. Why not deploy on a VM?

A VM would work, but it is less attractive for this portfolio project because I would need to manage more operations myself: process supervision, TLS, firewall rules, patching, restart behavior, and scaling.

A managed container runtime like Cloud Run better matches modern ML service deployment patterns.

### 5. What is the difference between a container registry and a runtime service?

A **container registry** stores versioned container images. In this project, that would be Google Artifact Registry.

A **runtime service** runs the container and exposes it to users or clients. In this project, that would be Google Cloud Run.

The deployment flow is:

```text
Docker build → Artifact Registry push → Cloud Run deploy → HTTPS endpoint smoke test
```

### 6. What is the Day 1-2 architecture?

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

The client calls the Cloud Run HTTPS URL. Cloud Run routes the request into the FastAPI container. The container loads the model artifact and metadata, validates inputs, returns predictions, and writes structured logs that Cloud Run forwards to Cloud Logging.

### 7. What environment variables matter for this first architecture step?

The first version uses simple runtime configuration:

```bash
APP_ENV=local
MODEL_VERSION=0.1.0
MLOPS_PREDICTION_LOG_CSV=logs/predictions.csv
PORT=8000
```

The point is to avoid hard-coded machine-specific assumptions. Local and cloud deployments should be configured through environment variables.

### 8. What is the health-check strategy?

The service uses `GET /health` to confirm that the API is reachable and the model is loaded. For Day 1-2, this endpoint is the basic readiness signal. A deployment is not considered healthy just because the container starts; it must also load the model successfully.

### 9. What logs or metrics are important at this stage?

At the architecture stage, I would track:

- request count
- error rate
- p50/p95 latency
- model version
- request id
- prediction latency
- validation failures

The important idea is that an ML service needs both infrastructure observability and model-serving observability.

### 10. What cost feature makes Cloud Run attractive for this project?

Cloud Run can scale to zero when the service is idle. For a portfolio/demo ML API that may receive occasional traffic, scale-to-zero is valuable because it limits idle cost while preserving a real cloud deployment path.

### 11. What security choice would you make for the first cloud design?

The safe default is to keep the Cloud Run service authenticated, especially for non-demo deployments. If I make a temporary public portfolio endpoint later, I would first verify that the image contains no secrets, no private data, no trading credentials, and no action-taking capability.

### 12. What files did Day 1-2 produce?

The Day 1-2 deliverables are:

- `README.md` — project overview, architecture, quick start, Cloud Run plan.
- `configs/local.env.example` — local runtime environment example.
- `infra/architecture_diagram.md` — ASCII architecture diagram and component responsibilities.
- `infra/gcp_cloud_run.md` — Cloud Run resource/deployment design notes.

### 13. How would you summarize Day 1-2 in an interview?

I took an existing Dockerized FastAPI ML service and designed a cloud deployment architecture around it. I selected Google Cloud Run as the primary runtime because it gives a simple managed path from container image to HTTPS service, with built-in logging, revisions, and scale-to-zero. I documented the registry/runtime split, environment variables, health check, logging path, and tradeoffs against ECS/Fargate and VM deployment.
