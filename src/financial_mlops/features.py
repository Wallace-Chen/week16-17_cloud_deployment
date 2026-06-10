from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping

import numpy as np


class FeatureValidationError(ValueError):
    """Raised when an inference request does not match the model contract."""


def validate_input_keys(payload: Mapping[str, Any], feature_names: Iterable[str]) -> None:
    """Validate that the request includes exactly the features expected by metadata."""
    expected = list(feature_names)
    expected_set = set(expected)
    actual_set = set(payload.keys())

    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing keys: {missing}")
        if extra:
            parts.append(f"unexpected keys: {extra}")
        raise FeatureValidationError("Invalid feature payload; " + "; ".join(parts))


def request_to_feature_vector(payload: Mapping[str, Any], feature_names: Iterable[str]) -> np.ndarray:
    """Convert request JSON into a 2D numeric vector preserving metadata feature order."""
    ordered_features: List[str] = list(feature_names)
    validate_input_keys(payload, ordered_features)

    values = []
    for name in ordered_features:
        try:
            values.append(float(payload[name]))
        except (TypeError, ValueError) as exc:
            raise FeatureValidationError(f"Feature {name!r} must be numeric") from exc

    return np.asarray(values, dtype=float).reshape(1, -1)


def build_request_from_row(row: Mapping[str, Any], feature_names: Iterable[str]) -> Dict[str, float]:
    """Create a deterministic sample request from a dataframe row or mapping."""
    return {name: float(row[name]) for name in feature_names}
