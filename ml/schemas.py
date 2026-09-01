from pydantic import BaseModel, Field
from typing import List, Optional

class PredictionInput(BaseModel):
    data: List[float] = Field(..., description="Input data for prediction (List of 4 floats for Iris)")

class PredictionOutput(BaseModel):
    result: int
    model_version: str = "v1"

class BatchPredictionInput(BaseModel):
    inputs: List[PredictionInput] = Field(
        ...,
        max_length=100,
        description="Batch of prediction inputs. Capped at 100 items per request to prevent single-request DoS.",
    )

class BatchPredictionOutput(BaseModel):
    results: List[PredictionOutput]
    processed_count: int
