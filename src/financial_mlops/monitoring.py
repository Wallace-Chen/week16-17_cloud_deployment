from __future__ import annotations

import csv
import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional
from uuid import uuid4

logger = logging.getLogger("financial_mlops")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

CSV_FIELDS = [
    "timestamp_utc",
    "request_id",
    "endpoint",
    "ticker",
    "model_version",
    "feature_count",
    "feature_mean",
    "feature_std",
    "feature_min",
    "feature_max",
    "prediction",
    "probability",
    "latency_ms",
    "error_status",
    "error_message",
]


def new_request_id() -> str:
    """Create a lightweight request id for logs and responses."""
    return str(uuid4())


@contextmanager
def latency_timer() -> Iterator[Dict[str, float]]:
    """Measure elapsed time in milliseconds."""
    start = time.perf_counter()
    result: Dict[str, float] = {"latency_ms": 0.0}
    try:
        yield result
    finally:
        result["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)


def summarize_features(features: Mapping[str, Any]) -> Dict[str, Optional[float]]:
    """Return compact feature statistics for monitoring without logging raw payloads."""
    values = [float(value) for value in features.values()]
    if not values:
        return {
            "feature_count": 0,
            "feature_mean": None,
            "feature_std": None,
            "feature_min": None,
            "feature_max": None,
        }

    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return {
        "feature_count": len(values),
        "feature_mean": round(mean, 8),
        "feature_std": round(variance**0.5, 8),
        "feature_min": round(min(values), 8),
        "feature_max": round(max(values), 8),
    }


def log_event(event: str, **fields: Any) -> None:
    """Emit one structured JSON log line and optionally append prediction events to CSV.

    Set MLOPS_PREDICTION_LOG_CSV=logs/predictions.csv to enable local CSV audit logs.
    The default remains stdout-only, which is lightweight for tests and containers.
    """
    payload = {
        "event": event,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "error_status": "ok",
        "error_message": "",
        **fields,
    }
    logger.info(json.dumps(payload, sort_keys=True, default=str))

    csv_path = os.getenv("MLOPS_PREDICTION_LOG_CSV")
    if csv_path and event.startswith("prediction"):
        append_prediction_csv(Path(csv_path), payload)


def append_prediction_csv(path: Path, event: Mapping[str, Any]) -> None:
    """Append monitoring fields to a CSV file, creating headers on first write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({field: event.get(field, "") for field in CSV_FIELDS})
