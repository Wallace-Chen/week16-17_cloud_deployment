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
├── DEPLOYMENT.md
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
│   ├── collect_logs.sh
│   ├── deploy_cloud_run.sh
│   ├── rollback_cloud_run.sh
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

Detailed commands and design notes are in [`infra/gcp_cloud_run.md`](infra/gcp_cloud_run.md). Day 3-4 deployment commands, log collection, rollback, and smoke-test workflow are in [`DEPLOYMENT.md`](DEPLOYMENT.md).

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

## Interview Talking Points — Week 16 Day 1-2

These answers correspond directly to the **Interview Talking Points** under Day 1-2 in `Phase3_Week16-17_Cloud_Deployment.md`.

### 1. Why choose Cloud Run over a VM or Kubernetes for this project?

Cloud Run is the best fit because this project already has a Dockerized FastAPI model-serving app, and Cloud Run can run that container directly as a managed HTTPS service.

Compared with a **VM**, Cloud Run removes a lot of manual operations work: server patching, process supervision, TLS setup, restart policies, firewall management, and manual scaling. A VM would work, but it would make the project more about server administration than ML service deployment.

Compared with **Kubernetes**, Cloud Run is much simpler. Kubernetes is powerful for complex multi-service platforms, but it is unnecessary for a small portfolio ML API. For this project, I mainly need container deployment, service URL, logs, revisions, traffic control, and scale-to-zero. Cloud Run provides those without cluster management.

So the decision is: use Cloud Run because it demonstrates a real cloud deployment path while keeping the infrastructure simple enough to explain clearly.

### 2. What is the difference between a container registry and a container runtime?

A **container registry** stores container images. It is where the built Docker artifact lives before deployment. In the Google Cloud path, this would be **Artifact Registry**.

A **container runtime** runs the image as a live service. In this project, the runtime is **Cloud Run**.

The flow is:

```text
docker build
    ↓
push image to Artifact Registry
    ↓
deploy image to Cloud Run
    ↓
Cloud Run runs the FastAPI service behind HTTPS
```

Short version:

- Registry = stores the image.
- Runtime = runs the image.

### 3. What should be configurable through environment variables?

Anything that changes between local, staging, and cloud environments should be configurable through environment variables instead of hard-coded in source code.

For this project, the important variables are:

```bash
APP_ENV=local
MODEL_VERSION=0.1.0
MLOPS_PREDICTION_LOG_CSV=logs/predictions.csv
PORT=8000
```

Examples:

- `APP_ENV` distinguishes local vs cloud runtime behavior.
- `MODEL_VERSION` makes logs and responses traceable to a model release.
- `MLOPS_PREDICTION_LOG_CSV` controls where local prediction audit logs are written.
- `PORT` lets the service adapt to local Docker or cloud runtime expectations.

In a real deployment, secrets should also be injected through a secret manager or secure runtime environment, not committed to the repo or baked into the Docker image.

### 4. Why does a deployment need both health checks and smoke tests?

A **health check** is a lightweight service-readiness signal. For this app, `GET /health` confirms that the API is running and the model artifact loaded successfully. It answers: “Is the service alive and ready?”

A **smoke test** verifies the deployed system from the outside like a real client. It should call `/health`, `/metadata`, and `/predict` with a sample request. It answers: “Can the deployed endpoint actually serve the expected workflow?”

Both are needed because they catch different problems. A health check may pass even if prediction input/output behavior is broken. A smoke test may catch issues with routing, endpoint URL, request validation, model metadata, or prediction response format.

For this project, the smoke test command is:

```bash
python scripts/smoke_test_endpoint.py --url http://localhost:8000
```

Later, the same script can test a Cloud Run URL.
