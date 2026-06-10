from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .features import FeatureValidationError, request_to_feature_vector
from .model import load_metadata, load_model
from .monitoring import latency_timer, log_event, new_request_id, summarize_features
from .schemas import HealthResponse, MetadataResponse, PredictionRequest, PredictionResponse

app = FastAPI(
    title="Financial MLOps Model Serving",
    version="0.1.0",
    description="FastAPI service for the SPY next-day direction baseline model.",
)

MODEL = load_model()
METADATA = load_metadata()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check for orchestration and smoke tests."""
    return HealthResponse(
        status="ok",
        model_loaded=MODEL is not None,
        model_name=METADATA["model_name"],
        model_version=METADATA["version"],
    )


@app.get("/metadata", response_model=MetadataResponse)
def metadata() -> MetadataResponse:
    """Return the public model contract and training summary."""
    return MetadataResponse(**METADATA)


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    """Validate features, run one model prediction, and emit monitoring fields."""
    request_id = request.request_id or new_request_id()
    feature_summary = summarize_features(request.features)

    with latency_timer() as elapsed:
        try:
            X = request_to_feature_vector(request.features, METADATA["features"])
            prediction = int(MODEL.predict(X)[0])
            probability = float(MODEL.predict_proba(X)[0][1]) if hasattr(MODEL, "predict_proba") else float(prediction)
        except FeatureValidationError as exc:
            log_event(
                "prediction_rejected",
                request_id=request_id,
                endpoint="/predict",
                ticker=request.ticker,
                model_version=METADATA["version"],
                latency_ms=elapsed["latency_ms"],
                error_status="feature_validation_error",
                error_message=str(exc),
                **feature_summary,
            )
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:  # defensive guard for service boundary
            log_event(
                "prediction_failed",
                request_id=request_id,
                endpoint="/predict",
                ticker=request.ticker,
                model_version=METADATA["version"],
                latency_ms=elapsed["latency_ms"],
                error_status="runtime_error",
                error_message=str(exc),
                **feature_summary,
            )
            raise HTTPException(status_code=500, detail="Prediction failed") from exc

    response = PredictionResponse(
        ticker=request.ticker,
        prediction=prediction,
        probability=probability,
        model_version=METADATA["version"],
        latency_ms=elapsed["latency_ms"],
        request_id=request_id,
    )
    log_event(
        "prediction_completed",
        request_id=request_id,
        endpoint="/predict",
        ticker=request.ticker,
        model_version=METADATA["version"],
        prediction=prediction,
        probability=round(probability, 6),
        latency_ms=response.latency_ms,
        **feature_summary,
    )
    return response
