from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

import joblib

from .features import request_to_feature_vector

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "model.pkl"
DEFAULT_METADATA_PATH = PROJECT_ROOT / "models" / "metadata.json"


def load_metadata(metadata_path: str | Path = DEFAULT_METADATA_PATH) -> Dict[str, Any]:
    return json.loads(Path(metadata_path).read_text(encoding="utf-8"))


def load_model(model_path: str | Path = DEFAULT_MODEL_PATH):
    return joblib.load(Path(model_path))


def predict(payload: Mapping[str, Any], model_path: str | Path = DEFAULT_MODEL_PATH, metadata_path: str | Path = DEFAULT_METADATA_PATH) -> Dict[str, Any]:
    """Run one prediction using the saved baseline model and metadata contract."""
    metadata = load_metadata(metadata_path)
    model = load_model(model_path)
    X = request_to_feature_vector(payload, metadata["features"])
    predicted_direction = int(model.predict(X)[0])

    response: Dict[str, Any] = {
        "model_name": metadata["model_name"],
        "version": metadata["version"],
        "target": metadata["target"],
        "predicted_direction": predicted_direction,
    }
    if hasattr(model, "predict_proba"):
        probability_up = float(model.predict_proba(X)[0][1])
        response["probability_up"] = probability_up
    return response
