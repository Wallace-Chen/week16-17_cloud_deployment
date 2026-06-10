# Week 16 Day 1-2 Architecture Diagram

## Primary target

**Google Cloud Run** is the primary deployment target for this project.

Reason: the Week 14-15 service is already a Dockerized FastAPI application. Cloud Run is the shortest credible path from container to production-style HTTPS service: push image to Artifact Registry, deploy a managed service, inspect revisions/logs, and optionally split traffic for rollback/canary releases.

## Runtime architecture

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

## Expanded deployment view

```text
Developer laptop / CI
        │
        │ docker build
        ▼
financial-mlops-api container image
        │
        │ docker tag + docker push
        ▼
Google Artifact Registry
        │
        │ gcloud run deploy --image ...
        ▼
Cloud Run managed service
        │
        ├── GET /health       readiness + model-version check
        ├── GET /metadata     model contract and training metadata
        └── POST /predict     validated financial-ML prediction request
        │
        ▼
Structured application logs
        │
        ├── request id
        ├── latency
        ├── model version
        ├── prediction/probability summary
        └── errors / validation failures
        │
        ▼
Cloud Logging + Monitoring dashboard
```

## Component responsibilities

| Component | Responsibility |
| --- | --- |
| FastAPI app | Defines API contract, validates features, serves predictions. |
| Docker image | Immutable runtime package containing source, dependencies, model, metadata, and config. |
| Artifact Registry | Stores versioned container images before deployment. |
| Cloud Run | Runs the container behind HTTPS, handles autoscaling, revisions, traffic, and service URL. |
| Cloud Logging | Captures stdout/stderr and structured logs for debugging and monitoring. |
| Smoke test | Verifies `/health`, `/metadata`, and `/predict` after local or cloud deployment. |

## Endpoint choice

For portfolio/demo use, the service can be public with unauthenticated access disabled or enabled depending on demo needs:

- **Private/internal or authenticated endpoint:** safer default for real ML systems.
- **Public demo endpoint:** acceptable only with no secrets, no trading action, rate limits, and clear demo disclaimers.

This project should treat the model as an educational financial-ML demo, not an investment signal.
