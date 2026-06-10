# MLOps System Design Report: Financial Model Serving API

## Abstract

This project converts a financial ML baseline model into a production-style model-serving system. The system serves a saved SPY next-day direction classifier through FastAPI, validates an explicit feature contract, packages the runtime in Docker, tests the serving path with pytest, and defines monitoring requirements for latency, errors, drift, and auditability.

The model is intentionally a baseline rather than a trading strategy. The primary design goal is to demonstrate the engineering ability to move from research artifacts to a reliable service contract: versioned artifacts, deterministic inference, CI checks, containerized execution, and production-aware monitoring.

## Problem Statement

Notebook-based financial ML experiments are useful for research but fragile in production. They often depend on hidden notebook state, implicit feature ordering, local paths, unversioned artifacts, and manual execution. A production ML service needs a stronger contract:

1. What model artifact is being served?
2. What feature schema does it expect?
3. What response schema does it return?
4. How is the service tested before deployment?
5. How is the service containerized for repeatable runtime?
6. How are predictions, failures, and drift monitored after deployment?

This project answers those questions for a compact financial model-serving API.

## Model and Data Artifact

The served model is a baseline SPY next-day direction classifier.

| Item | Value |
| --- | --- |
| Model name | `spy_direction_baseline` |
| Version | `0.1.0` |
| Target | `next_day_direction` |
| Artifact | `models/model.pkl` |
| Metadata | `models/metadata.json` |
| Model type | `sklearn.ensemble.RandomForestClassifier` |
| Feature count | 28 |
| Training rows | 951 |
| Test rows | 238 |
| Training source | `week3-4_Mar2026/data/SPY_features.csv` |

The metadata file is as important as the model artifact because it stores the serving contract: model version, target, model type, training source, metrics, and exact feature ordering. The service uses that metadata to validate requests and convert feature dictionaries into ordered numeric arrays.

### Artifact Design Choices

- **Model artifact:** Stored as `models/model.pkl` using joblib-compatible sklearn persistence.
- **Metadata artifact:** Stored as JSON so it is human-readable and easy to expose through `/metadata`.
- **Sample request:** Stored as `data/sample_request.json` for repeatable smoke tests.
- **Feature contract:** The service rejects missing or unexpected features before inference.

### Production Tradeoff

Pickle/joblib artifacts should only be loaded from trusted sources. This is acceptable for a controlled local portfolio project, but a production system should use a secured artifact store, immutable artifact versions, access controls, and potentially safer serialization formats depending on model type.

## Architecture Overview

```text
Training / artifact creation
----------------------------
SPY feature data
    ↓
scripts/train_baseline_model.py
    ↓
models/model.pkl + models/metadata.json + data/sample_request.json

Serving path
------------
Client request JSON
    ↓
FastAPI /predict endpoint
    ↓
Pydantic request validation
    ↓
feature-key validation + metadata-defined ordering
    ↓
model.predict / model.predict_proba
    ↓
PredictionResponse: ticker, prediction, probability, model_version, latency_ms, request_id
    ↓
structured prediction log event
```

The design separates the training pipeline from the serving pipeline. Training creates versioned artifacts. Serving loads approved artifacts once at startup and then handles deterministic inference requests.

## API Design

The service exposes three endpoints:

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/health` | `GET` | Reports service readiness, loaded model status, model name, and version. |
| `/metadata` | `GET` | Returns public model metadata and feature contract. |
| `/predict` | `POST` | Validates features, runs inference, returns prediction and monitoring fields. |

### Request Contract

A prediction request includes a ticker, optional request id, and feature dictionary:

```json
{
  "ticker": "SPY",
  "features": {
    "Open": 667.4472,
    "High": 670.5088,
    "Low": 659.5587
  },
  "request_id": "optional-client-request-id"
}
```

The actual request must include all 28 metadata-defined features. Missing features or unexpected features return HTTP 422.

### Response Contract

```json
{
  "ticker": "SPY",
  "prediction": 0,
  "probability": 0.359032,
  "model_version": "0.1.0",
  "latency_ms": 17.69,
  "request_id": "392def36-d314-41c4-9b04-66cb97556c40"
}
```

### Error Semantics

- Schema errors or malformed request body: HTTP 422 from Pydantic/FastAPI.
- Missing/unexpected features: HTTP 422 from service-level feature validation.
- Runtime inference failure: HTTP 500 with a generic public message and structured internal log event.

## Training Pipeline vs Serving Pipeline

### Training Pipeline

Training is responsible for:

1. Reading historical feature data.
2. Creating the target label.
3. Fitting the baseline classifier.
4. Evaluating metrics on a chronological split.
5. Saving `model.pkl`, `metadata.json`, and `sample_request.json`.

### Serving Pipeline

Serving is responsible for:

1. Loading the approved model and metadata once at startup.
2. Validating request schema and exact feature keys.
3. Preserving feature order from metadata.
4. Running deterministic inference.
5. Returning a stable response schema.
6. Emitting prediction logs for monitoring and auditability.

### Why This Separation Matters

Training code is experimental and often batch-oriented. Serving code must be stable, low-latency, and predictable. Keeping them separate prevents accidental retraining during inference and makes the runtime image smaller and safer.

## Batch Inference vs Online Inference

This project implements online inference: one request returns one prediction response through FastAPI.

Online inference is useful when:

- predictions are needed immediately by another service or UI;
- request-level latency matters;
- the caller needs model version and request id in the response;
- the service is integrated into a larger application.

Batch inference would be better when:

- predictions are produced on a fixed schedule, such as daily market close;
- throughput matters more than per-request latency;
- the output is written to a database, file, or portfolio report;
- features are generated from a batch pipeline.

For a financial prediction workflow, a realistic production system might use both: batch scoring after market close and online inference for ad hoc analysis or internal tools.

## Feature Consistency

Feature consistency is one of the most important production ML risks. A model can return wrong predictions even when the API appears healthy if features are ordered incorrectly or computed differently from training.

Current safeguards:

- `models/metadata.json` stores the ordered feature list.
- `features.py` rejects missing and unexpected feature keys.
- `request_to_feature_vector` constructs the numeric array in metadata order.
- Tests verify feature vector shape/order and missing-feature errors.
- `/metadata` exposes the feature contract to clients.

Future improvements:

- Save reference feature statistics in `models/reference_stats.json`.
- Use a shared feature transformation library for training and serving.
- Add feature-store integration if the project grows beyond a local demo.
- Add contract tests that compare training-time and serving-time feature generation.

## Reproducibility

The system is designed to be reproducible across local, CI, and containerized environments.

Current reproducibility mechanisms:

- `requirements.txt` defines Python dependencies.
- `pyproject.toml` defines package layout and pytest discovery.
- `Dockerfile` defines the serving runtime.
- `.dockerignore` excludes local state and logs.
- `models/metadata.json` records model version, training source, model type, and metrics.
- `data/sample_request.json` gives a deterministic smoke-test payload.
- GitHub Actions runs tests and builds the Docker image.

Stronger production reproducibility would require pinned exact dependency versions, immutable base-image digests, signed artifacts, and a model registry.

## Containerization

The Docker image uses `python:3.11-slim`, installs dependencies, copies only runtime assets, and runs the FastAPI app through Uvicorn.

Important container choices:

- `PYTHONPATH=/app/src` ensures package imports work inside the image.
- The model and metadata are copied into the image for a self-contained demo.
- The original training data is not copied into the serving image.
- A non-root `app` user runs the service.
- Docker healthcheck calls `/health`.
- `docker-compose.yml` provides a local wrapper for repeatable manual testing.

Production extension:

- Use immutable image tags instead of `latest`.
- Push images to ECR, GHCR, or Artifact Registry.
- Inject environment-specific config and secrets at runtime.
- Keep large or frequently changing model artifacts in a model registry or object store.

## Testing and CI

The project uses pytest and FastAPI TestClient.

Test coverage includes:

- Feature vector length and ordering.
- Missing-feature validation errors.
- Model artifact and metadata completeness.
- Prediction and probability output ranges.
- `/health`, `/metadata`, and `/predict` API behavior.
- Malformed request rejection.
- Monitoring feature summaries and CSV logging.

The GitHub Actions workflow runs on push and pull request:

1. Checkout.
2. Set up Python 3.11.
3. Install dependencies and editable package.
4. Run `python -m pytest -q`.
5. Build the Docker image.

This is CI, not full CD. It verifies package health and deployability but does not publish or deploy the image.

## Monitoring Plan

Monitoring is covered in detail in `reports/ml_monitoring_plan.md`. The core idea is to monitor four layers:

1. **Service health:** latency, request volume, error rate, 5xx rate.
2. **Data quality:** missing/null features, non-numeric features, out-of-range values.
3. **Prediction behavior:** class distribution, probability distribution, confidence extremes.
4. **Model performance:** delayed accuracy, balanced accuracy, log loss, Brier score, calibration, confusion matrix after labels arrive.

Each prediction event logs:

- timestamp
- request id
- endpoint
- ticker
- model version
- compact feature summary
- prediction
- probability
- latency
- error status and message

This supports debugging, dashboarding, drift analysis, and model-version auditability.

## Failure Modes

| Failure Mode | Symptom | Mitigation |
| --- | --- | --- |
| Missing model artifact | Service fails at startup | CI artifact checks; deploy only approved images. |
| Metadata/model mismatch | Prediction shape error or incorrect inference | Store feature contract with artifact; test feature shape. |
| Missing request features | HTTP 422 | Clear validation error and client contract docs. |
| Unexpected feature order | Wrong prediction | Build vectors only from metadata ordering. |
| Dependency regression | CI failure or runtime import error | CI tests; dependency pinning in future. |
| Docker build failure | CI build step fails | Keep Dockerfile minimal; build in CI before deploy. |
| Latency spike | Slow `/predict` responses | Monitor p95/p99; inspect host load and recent deploys. |
| Prediction drift | Output distribution changes | Compare production predictions against reference distribution. |
| Data drift | Feature distribution changes | Compare rolling feature stats against training/reference stats. |
| Model degradation | Worse delayed labels/metrics | Retrain, rollback, or disable consumers. |
| Bad deploy | Errors or degraded metrics after release | Blue/green or canary release; rollback to previous image/model. |

## Security Basics

Current project security posture is appropriate for a local portfolio demo but not production internet exposure.

Current safeguards:

- Container runs as a non-root user.
- Service validates schemas and feature keys.
- Training data is excluded from the serving image.
- Logs use compact feature summaries rather than requiring full raw payload logging.

Needed before production:

- Authentication and authorization.
- Rate limiting and abuse protection.
- HTTPS/TLS termination.
- Secrets manager for credentials.
- Strict artifact access controls.
- Dependency vulnerability scanning.
- Input-size limits and request timeout policies.
- Review of whether feature values or prediction logs contain sensitive data.

## Cloud Deployment Extension

### AWS Option

1. Build Docker image in GitHub Actions.
2. Push image to Amazon ECR.
3. Deploy to ECS/Fargate or SageMaker real-time endpoint.
4. Put API Gateway or Application Load Balancer in front.
5. Send logs to CloudWatch.
6. Store model artifacts in S3 or a model registry.
7. Use IAM roles and Secrets Manager.

### GCP Option

1. Build Docker image in GitHub Actions or Cloud Build.
2. Push image to Artifact Registry.
3. Deploy to Cloud Run for autoscaling HTTP serving.
4. Send logs to Cloud Logging and metrics to Cloud Monitoring.
5. Store model artifacts in Cloud Storage or Vertex AI Model Registry.
6. Use Secret Manager and service accounts.

### Deployment Strategy

For either cloud, use canary or blue/green deployment:

1. Deploy new model version with a small traffic slice.
2. Compare latency, error rate, prediction distribution, and delayed performance labels.
3. Promote if healthy.
4. Roll back to the previous model/image if metrics degrade.

## Scalability and Maintainability

### Scalability

This project is small, but the serving design can scale horizontally because the API is stateless after startup. Multiple containers can serve the same model artifact behind a load balancer. For large models, startup time and memory pressure would become important scaling constraints.

### Maintainability

The project keeps responsibilities separated:

- `features.py` for input contract and vector construction.
- `model.py` for artifact loading and prediction helper.
- `schemas.py` for request/response models.
- `service.py` for FastAPI endpoints.
- `monitoring.py` for logging and audit helpers.
- `tests/` for contract verification.

This makes it easier to change one part without silently breaking the rest.

## Limitations

1. The baseline model has weak predictive performance and is not a deployable trading strategy.
2. The artifact is local rather than managed by a model registry.
3. Dependency versions are lower-bound ranges rather than fully pinned hashes.
4. Drift checks are documented but not automated as scheduled production jobs.
5. No authentication, authorization, or rate limiting is implemented.
6. No cloud deployment is currently active.
7. True model-performance monitoring requires delayed labels and a label-join pipeline.

## Conclusion

This project demonstrates the core MLOps transition from experiment to service. It defines a saved model artifact, metadata-driven feature contract, FastAPI serving layer, Docker runtime, CI checks, and monitoring plan. The result is not a high-performing financial model, but it is a production-shaped ML system that can be tested, run, containerized, explained in interviews, and extended toward cloud deployment.

The most important design principle is that production ML is more than model accuracy. Reliable ML systems require explicit contracts, reproducible artifacts, tested serving paths, observable runtime behavior, and safe rollback plans.
