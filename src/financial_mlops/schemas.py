from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    ticker: str = Field(default="SPY", description="Ticker symbol for the request")
    features: Dict[str, float] = Field(description="Feature values keyed by metadata feature name")
    request_id: Optional[str] = Field(default=None, description="Optional client-supplied request id")


class PredictionResponse(BaseModel):
    ticker: str
    prediction: int
    probability: float
    model_version: str
    latency_ms: float
    request_id: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: str
    model_version: str


class MetadataResponse(BaseModel):
    model_name: str
    version: str
    target: str
    features: List[str]
    training_data: str
    model_type: str
    metrics: Dict[str, Any]
    notes: str
