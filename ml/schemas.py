from pydantic import BaseModel, Field
from typing import List, Optional

class PredictionInput(BaseModel):
    data: List[float] = Field(..., description="Input data for prediction (List of 4 floats for Iris)")

class PredictionOutput(BaseModel):
    result: int
    model_version: str = "v1"

class BatchPredictionInput(BaseModel):
    inputs: List[PredictionInput]

class BatchPredictionOutput(BaseModel):
    results: List[PredictionOutput]
    processed_count: int
