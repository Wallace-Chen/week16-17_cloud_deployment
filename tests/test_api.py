import json
from pathlib import Path

from fastapi.testclient import TestClient

from financial_mlops.model import load_metadata
from financial_mlops.service import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
METADATA = load_metadata(PROJECT_ROOT / "models" / "metadata.json")


def load_sample_request() -> dict:
    return json.loads((PROJECT_ROOT / "data" / "sample_request.json").read_text(encoding="utf-8"))


def test_health_returns_status_ok():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["model_loaded"] is True
    assert payload["model_version"] == METADATA["version"]


def test_metadata_returns_model_version_and_contract():
    client = TestClient(app)

    response = client.get("/metadata")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_name"] == "spy_direction_baseline"
    assert payload["version"] == METADATA["version"]
    assert payload["features"] == METADATA["features"]


def test_predict_returns_valid_schema_for_sample_request():
    client = TestClient(app)

    response = client.post("/predict", json=load_sample_request())

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ticker", "prediction", "probability", "model_version", "latency_ms", "request_id"}
    assert payload["ticker"] == "SPY"
    assert payload["prediction"] in {0, 1}
    assert 0.0 <= payload["probability"] <= 1.0
    assert payload["model_version"] == METADATA["version"]
    assert payload["latency_ms"] >= 0.0
    assert payload["request_id"]


def test_predict_rejects_missing_feature_with_validation_error():
    client = TestClient(app)
    malformed_request = load_sample_request()
    missing_feature = METADATA["features"][0]
    malformed_request["features"].pop(missing_feature)

    response = client.post("/predict", json=malformed_request)

    assert response.status_code == 422
    assert "missing keys" in response.text
    assert missing_feature in response.text


def test_predict_rejects_malformed_request_body():
    client = TestClient(app)

    response = client.post("/predict", json={"ticker": "SPY", "features": "not-a-dict"})

    assert response.status_code == 422
