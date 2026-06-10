import json
from pathlib import Path

from financial_mlops.model import load_metadata, load_model, predict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "model.pkl"
METADATA_PATH = PROJECT_ROOT / "models" / "metadata.json"


def load_sample_features() -> dict[str, float]:
    sample = json.loads((PROJECT_ROOT / "data" / "sample_request.json").read_text(encoding="utf-8"))
    return sample["features"]


def test_artifacts_exist_and_metadata_is_complete():
    assert MODEL_PATH.exists()
    assert METADATA_PATH.exists()

    metadata = load_metadata(METADATA_PATH)

    assert metadata["model_name"] == "spy_direction_baseline"
    assert metadata["version"] == "0.1.0"
    assert metadata["target"] == "next_day_direction"
    assert len(metadata["features"]) > 10
    assert metadata["model_type"].startswith("sklearn.")
    assert set(metadata["metrics"]) >= {"accuracy", "f1", "roc_auc"}


def test_model_returns_prediction_and_probability_for_sample_request():
    model = load_model(MODEL_PATH)
    assert hasattr(model, "predict")

    result = predict(load_sample_features(), MODEL_PATH, METADATA_PATH)

    assert result["model_name"] == "spy_direction_baseline"
    assert result["version"] == "0.1.0"
    assert result["target"] == "next_day_direction"
    assert result["predicted_direction"] in {0, 1}
    assert "probability_up" in result
    assert 0.0 <= result["probability_up"] <= 1.0
