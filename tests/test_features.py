import json
from pathlib import Path

import pytest

from financial_mlops.features import FeatureValidationError, request_to_feature_vector
from financial_mlops.model import load_metadata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
METADATA = load_metadata(PROJECT_ROOT / "models" / "metadata.json")


def load_sample_features() -> dict[str, float]:
    sample = json.loads((PROJECT_ROOT / "data" / "sample_request.json").read_text(encoding="utf-8"))
    return sample["features"]


def test_feature_vector_has_expected_length_and_order():
    features = load_sample_features()

    vector = request_to_feature_vector(features, METADATA["features"])

    assert vector.shape == (1, len(METADATA["features"]))
    assert vector[0, 0] == pytest.approx(features[METADATA["features"][0]])
    assert vector[0, -1] == pytest.approx(features[METADATA["features"][-1]])


def test_missing_feature_raises_clear_error():
    features = load_sample_features()
    missing_feature = METADATA["features"][0]
    features.pop(missing_feature)

    with pytest.raises(FeatureValidationError, match="missing keys") as exc_info:
        request_to_feature_vector(features, METADATA["features"])

    assert missing_feature in str(exc_info.value)


def test_non_numeric_feature_raises_clear_error():
    features = load_sample_features()
    bad_feature = METADATA["features"][0]
    features[bad_feature] = "not-a-number"

    with pytest.raises(FeatureValidationError) as exc_info:
        request_to_feature_vector(features, METADATA["features"])

    assert bad_feature in str(exc_info.value)
    assert "must be numeric" in str(exc_info.value)
