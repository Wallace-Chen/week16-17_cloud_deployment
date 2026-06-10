#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from financial_mlops.features import build_request_from_row

DEFAULT_SOURCE_CSV = Path("/Users/yuanchen/Documents/2026_JobHunt/Job-hunt/week3-4_Mar2026/data/SPY_features.csv")
TARGET = "target_direction_1d"
DROP_COLUMNS = {"Date", "target_return_1d", "target_direction_1d", "target_return_5d", "target_direction_5d"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train SPY next-day direction baseline artifact.")
    parser.add_argument("--source-csv", default=str(DEFAULT_SOURCE_CSV))
    parser.add_argument("--model-dir", default=str(PROJECT_ROOT / "models"))
    parser.add_argument("--sample-request", default=str(PROJECT_ROOT / "data" / "sample_request.json"))
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_csv = Path(args.source_csv)
    model_dir = Path(args.model_dir)
    sample_request_path = Path(args.sample_request)
    model_dir.mkdir(parents=True, exist_ok=True)
    sample_request_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(source_csv).dropna().reset_index(drop=True)
    feature_names = [c for c in df.columns if c not in DROP_COLUMNS]

    X = df[feature_names]
    y = df[TARGET].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        shuffle=False,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        min_samples_leaf=5,
        random_state=args.random_state,
        class_weight="balanced_subsample",
    )
    model.fit(X_train.to_numpy(), y_train)

    preds = model.predict(X_test.to_numpy())
    probs = model.predict_proba(X_test.to_numpy())[:, 1]
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, preds)), 6),
        "f1": round(float(f1_score(y_test, preds)), 6),
        "roc_auc": round(float(roc_auc_score(y_test, probs)), 6),
    }

    metadata = {
        "model_name": "spy_direction_baseline",
        "version": "0.1.0",
        "target": "next_day_direction",
        "features": feature_names,
        "created_at": datetime.now(timezone.utc).date().isoformat(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_data": str(source_csv),
        "training_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "model_type": "sklearn.ensemble.RandomForestClassifier",
        "metrics": metrics,
        "notes": "Baseline SPY next-day direction model for MLOps serving demo. Trained with chronological split; not investment advice.",
    }

    model_path = model_dir / "model.pkl"
    metadata_path = model_dir / "metadata.json"
    joblib.dump(model, model_path)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    # Use the most recent available row as a deterministic serving sample.
    sample_payload = {
        "ticker": "SPY",
        "features": build_request_from_row(df.iloc[-1], feature_names),
    }
    sample_request_path.write_text(json.dumps(sample_payload, indent=2) + "\n", encoding="utf-8")

    print(f"Saved model: {model_path}")
    print(f"Saved metadata: {metadata_path}")
    print(f"Saved sample request: {sample_request_path}")
    print(json.dumps({"metrics": metrics, "features": len(feature_names)}, indent=2))


if __name__ == "__main__":
    main()
