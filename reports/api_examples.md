# API Examples

Run locally:

```bash
PYTHONPATH=src uvicorn financial_mlops.service:app --host 0.0.0.0 --port 8000
# or
python3 scripts/run_local_api.py
```

## Health

```bash
curl http://localhost:8000/health
```

Example response:

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_name": "spy_direction_baseline",
  "model_version": "0.1.0"
}
```

## Metadata

```bash
curl http://localhost:8000/metadata
```

Returns the model name, version, target, feature order, source training data, model type, metrics, and notes.

## Prediction

```bash
curl -X POST http://localhost:8000/predict \\
  -H "Content-Type: application/json" \\
  -d @data/sample_request.json
```

Request shape:

```json
{
  "ticker": "SPY",
  "features": {
    "Open": 628.24,
    "High": 629.10
  }
}
```

Response shape:

```json
{
  "ticker": "SPY",
  "prediction": 1,
  "probability": 0.57,
  "model_version": "0.1.0",
  "latency_ms": 3.2,
  "request_id": "..."
}
```

Invalid feature payloads return HTTP 422 with a message listing missing or unexpected keys.
