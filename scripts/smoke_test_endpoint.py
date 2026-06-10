#!/usr/bin/env python3
"""Smoke test a local or cloud Financial MLOps API endpoint.

Usage:
    python scripts/smoke_test_endpoint.py --url http://localhost:8000
    python scripts/smoke_test_endpoint.py --url https://your-cloud-run-url
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional
from urllib import request


def http_json(method: str, url: str, payload: Optional[dict] = None, timeout: float = 10.0) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        if resp.status < 200 or resp.status >= 300:
            raise RuntimeError(f"{method} {url} returned HTTP {resp.status}: {body}")
        return json.loads(body)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000", help="Base endpoint URL, local or Cloud Run")
    parser.add_argument("--sample", default="data/sample_request.json", help="Prediction sample JSON path")
    parser.add_argument("--retries", type=int, default=8, help="Health-check retries while service starts")
    parser.add_argument("--sleep", type=float, default=2.0, help="Seconds between health-check retries")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    sample_path = Path(args.sample)
    if not sample_path.exists():
        print(f"ERROR sample request not found: {sample_path}", file=sys.stderr)
        return 2

    last_exc: Optional[Exception] = None
    health = None
    for attempt in range(1, args.retries + 1):
        try:
            health = http_json("GET", f"{base_url}/health")
            break
        except Exception as exc:  # service may still be starting
            last_exc = exc
            print(f"health attempt {attempt}/{args.retries} failed: {exc}")
            time.sleep(args.sleep)

    if health is None:
        print(f"ERROR health check failed after {args.retries} attempts: {last_exc}", file=sys.stderr)
        return 1

    if health.get("status") != "ok":
        print(f"ERROR unexpected health payload: {health}", file=sys.stderr)
        return 1

    metadata = http_json("GET", f"{base_url}/metadata")
    sample = json.loads(sample_path.read_text())
    prediction = http_json("POST", f"{base_url}/predict", sample)

    required_prediction_keys = {"ticker", "prediction", "probability", "model_version", "latency_ms", "request_id"}
    missing = sorted(required_prediction_keys - set(prediction))
    if missing:
        print(f"ERROR prediction response missing keys: {missing}; response={prediction}", file=sys.stderr)
        return 1

    print("SMOKE_TEST_OK")
    print(json.dumps({
        "base_url": base_url,
        "health": health,
        "metadata_model_version": metadata.get("version") or metadata.get("model_version"),
        "prediction": prediction,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
