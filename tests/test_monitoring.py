from __future__ import annotations

import csv
from pathlib import Path

from financial_mlops.monitoring import append_prediction_csv, summarize_features


def test_summarize_features_returns_compact_statistics() -> None:
    summary = summarize_features(
        {
            "return_1d": 0.002,
            "return_5d": -0.004,
            "volatility_20d": 0.018,
            "volume_zscore": 0.7,
        }
    )

    assert summary["feature_count"] == 4
    assert summary["feature_min"] == -0.004
    assert summary["feature_max"] == 0.7
    assert summary["feature_mean"] is not None
    assert summary["feature_std"] is not None


def test_append_prediction_csv_writes_header_and_event(tmp_path: Path) -> None:
    path = tmp_path / "predictions.csv"
    append_prediction_csv(
        path,
        {
            "timestamp_utc": "2026-06-07T14:00:00+00:00",
            "request_id": "req-1",
            "endpoint": "/predict",
            "ticker": "SPY",
            "model_version": "0.1.0",
            "feature_count": 4,
            "feature_mean": 0.179,
            "feature_std": 0.301,
            "feature_min": -0.004,
            "feature_max": 0.7,
            "prediction": 1,
            "probability": 0.57,
            "latency_ms": 3.2,
            "error_status": "ok",
            "error_message": "",
        },
    )

    rows = list(csv.DictReader(path.open("r", encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["request_id"] == "req-1"
    assert rows[0]["ticker"] == "SPY"
    assert rows[0]["error_status"] == "ok"
