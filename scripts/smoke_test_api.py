#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test a running Financial MLOps API service.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--sample-request", default=str(PROJECT_ROOT / "data" / "sample_request.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    sample_payload = json.loads(Path(args.sample_request).read_text(encoding="utf-8"))

    health = requests.get(f"{base_url}/health", timeout=10)
    health.raise_for_status()
    health_payload = health.json()
    assert health_payload["status"] == "ok"
    assert health_payload["model_loaded"] is True

    prediction = requests.post(f"{base_url}/predict", json=sample_payload, timeout=10)
    prediction.raise_for_status()
    prediction_payload = prediction.json()
    required_keys = {"ticker", "prediction", "probability", "model_version", "latency_ms", "request_id"}
    missing = required_keys - set(prediction_payload)
    assert not missing, f"missing response keys: {sorted(missing)}"
    assert prediction_payload["ticker"] == sample_payload["ticker"]
    assert prediction_payload["prediction"] in [0, 1]
    assert 0.0 <= prediction_payload["probability"] <= 1.0

    print(json.dumps({"health": health_payload, "prediction": prediction_payload}, indent=2))


if __name__ == "__main__":
    main()
